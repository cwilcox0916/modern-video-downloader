import asyncio
import os
import traceback
import glob
from typing import Any, Dict, List, Optional, Tuple, Callable
from uuid import uuid4

from yt_dlp import YoutubeDL

DEFAULT_DOWNLOAD_DIR = os.getenv("DEFAULT_DOWNLOAD_DIR", "/downloads")

YTDLP_COMMON_OPTS: Dict[str, Any] = {
    "noprogress": True,
    "outtmpl": os.path.join(DEFAULT_DOWNLOAD_DIR, "%(title)s [%(id)s].%(ext)s"),
    "restrictfilenames": True,
    "merge_output_format": "mp4",
    "quiet": True,
    "ignoreerrors": True,
}


def _info(url: str) -> Dict[str, Any]:
    if not url or not isinstance(url, str):
        raise ValueError("Invalid URL")
    with YoutubeDL({**YTDLP_COMMON_OPTS}) as ydl:
        info = ydl.extract_info(url, download=False)
    if info is None:
        raise RuntimeError("Failed to fetch metadata")
    return info


def get_best_thumbnail(info: Dict[str, Any]) -> Optional[str]:
    # Try thumbnails list (prefer largest by area)
    thumbnails = info.get("thumbnails") or []
    best_url: Optional[str] = None
    best_area: int = -1
    for t in thumbnails:
        width = int(t.get("width") or 0)
        height = int(t.get("height") or 0)
        area = width * height
        if area > best_area and t.get("url"):
            best_area = area
            best_url = t["url"]

    if best_url:
        return best_url

    # Fallback to single thumbnail field
    return info.get("thumbnail")


def _pick_stream_url_from_info(info: Dict[str, Any]) -> Optional[str]:
    # Emulate --get-url behavior for a single video
    # Priority: requested_formats[0].url -> info["url"]
    requested_formats = info.get("requested_formats")
    if isinstance(requested_formats, list) and requested_formats:
        first = requested_formats[0]
        if isinstance(first, dict):
            url = first.get("url")
            if url:
                return url

    url = info.get("url")
    if url:
        return url

    # Some extractors return "formats" only; pick best by 'height' then 'abr'
    formats = info.get("formats")
    if isinstance(formats, list) and formats:
        def format_sort_key(fmt: Dict[str, Any]) -> Tuple[int, float]:
            height = int(fmt.get("height") or 0)
            abr = float(fmt.get("abr") or 0.0)
            return (height, abr)

        best_fmt = max(formats, key=format_sort_key)
        if best_fmt and best_fmt.get("url"):
            return best_fmt["url"]

    return None


def get_stream_url(url: str) -> Optional[str]:
    if not url:
        return None
    with YoutubeDL({**YTDLP_COMMON_OPTS}) as ydl:
        info = ydl.extract_info(url, download=False)
    if info is None:
        return None

    # Handle playlists by selecting the first entry
    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if entries:
            return _pick_stream_url_from_info(entries[0])  # type: ignore[arg-type]

    return _pick_stream_url_from_info(info)


async def download(
    url: str,
    format_selector: str = "bv*+ba/b",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    if not url:
        raise ValueError("URL is required")

    opts: Dict[str, Any] = {
        **YTDLP_COMMON_OPTS,
        "format": format_selector,
        # Progress hook is invoked frequently during download
        # We pass through yt-dlp's progress dict to our callback
        **({"progress_hooks": [progress_callback]} if progress_callback else {}),
        # Enable progress when we have a callback - disable quiet and noprogress
        **({"noprogress": False, "quiet": False} if progress_callback else {}),
    }

    def run_sync_download() -> Dict[str, Any]:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise RuntimeError("Download failed")
            # Compute final file path (best effort)
            filepath = ydl.prepare_filename(info)
            title = info.get("title") or "unknown"
            video_id = info.get("id") or "unknown"
            # For merged formats, final ext should be mp4 as per merge_output_format
            return {"title": title, "id": video_id, "filepath": filepath}

    # yt-dlp is sync; run in thread to avoid blocking the event loop
    result = await asyncio.to_thread(run_sync_download)
    return result


# --- Simple in-memory FIFO queue (sequential processing) ---

QUEUE: List[Dict[str, Any]] = []
_QUEUE_LOCK = asyncio.Lock()
_RUNNER_TASK: Optional[asyncio.Task] = None
_STOP_SIGNAL = False
_CANCELLED_JOBS: set[str] = set()  # Track cancelled job IDs


def _ensure_runner() -> None:
    global _RUNNER_TASK
    if _RUNNER_TASK is None or _RUNNER_TASK.done():
        _RUNNER_TASK = asyncio.create_task(_runner())


async def _runner() -> None:
    while not _STOP_SIGNAL:
        job: Optional[Dict[str, Any]] = None
        # Find the next queued job
        async with _QUEUE_LOCK:
            for item in QUEUE:
                if item.get("status") == "queued":
                    job = item
                    break
            if job:
                job["status"] = "running"

        if not job:
            await asyncio.sleep(0.5)
            continue

        # Check if job was cancelled before starting
        job_id = job.get("id")
        if job_id in _CANCELLED_JOBS:
            async with _QUEUE_LOCK:
                job["status"] = "cancelled"
                job["error"] = "Download cancelled by user"
                _CANCELLED_JOBS.discard(job_id)
            continue

        try:
            def on_progress(p: Dict[str, Any]) -> None:
                # Check for cancellation during download
                if job_id in _CANCELLED_JOBS:
                    # yt-dlp doesn't have a clean cancellation mechanism
                    # We'll let the download complete but mark it as cancelled
                    return

                # p can include: status, downloaded_bytes, total_bytes, elapsed, speed, eta, fragment_index, fragment_count
                prog: Dict[str, Any] = {}
                status = p.get("status")
                if status:
                    prog["status"] = status
                downloaded = int(p.get("downloaded_bytes") or 0)
                total = int(
                    p.get("total_bytes")
                    or p.get("total_bytes_estimate")
                    or 0
                )
                if downloaded:
                    prog["downloaded_bytes"] = downloaded
                if total:
                    prog["total_bytes"] = total
                if total > 0:
                    prog["progress_pct"] = max(0.0, min(100.0, downloaded * 100.0 / total))
                speed = p.get("speed")
                if speed:
                    prog["speed"] = speed
                eta = p.get("eta")
                if eta is not None:
                    prog["eta"] = eta

                # Update job progress snapshot
                # Store progress in the job dict directly (thread-safe enough for our use case)
                # The main event loop will pick this up via the queue polling
                job["progress"] = prog

            result = await download(job["url"], progress_callback=on_progress)
            
            # Check if cancelled after download completed
            async with _QUEUE_LOCK:
                if job_id in _CANCELLED_JOBS:
                    job["status"] = "cancelled"
                    job["error"] = "Download cancelled by user"
                    _CANCELLED_JOBS.discard(job_id)
                    # Clean up all downloaded and partial files
                    _cleanup_download_files(job.get("url", ""), result)
                else:
                    job["result"] = result
                    job["status"] = "done"
        except Exception as e:
            async with _QUEUE_LOCK:
                if job_id in _CANCELLED_JOBS:
                    job["status"] = "cancelled"
                    job["error"] = "Download cancelled by user"
                    _CANCELLED_JOBS.discard(job_id)
                    # Clean up any partial files even on error
                    _cleanup_download_files(job.get("url", ""))
                else:
                    job["error"] = str(e)
                    job["traceback"] = traceback.format_exc()
                    job["status"] = "error"


def add_to_queue(urls: List[str]) -> List[str]:
    if not isinstance(urls, list):
        raise ValueError("urls must be a list of strings")
    job_ids: List[str] = []
    for raw in urls:
        url = (raw or "").strip()
        if not url:
            continue
        job_id = str(uuid4())
        QUEUE.append(
            {
                "id": job_id,
                "url": url,
                "status": "queued",
                "progress": {"progress_pct": 0.0},
                "result": None,
                "error": None,
            }
        )
        job_ids.append(job_id)

    if job_ids:
        _ensure_runner()
    return job_ids


def get_queue_statuses() -> List[Dict[str, Any]]:
    # Return a simplified snapshot for UI
    return [
        {
            "id": item.get("id"),
            "url": item.get("url"),
            "status": item.get("status"),
            "title": (item.get("result") or {}).get("title"),
            "filepath": (item.get("result") or {}).get("filepath"),
            "error": item.get("error"),
            "progress": item.get("progress"),
        }
        for item in QUEUE
    ]


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    for item in QUEUE:
        if item.get("id") == job_id:
            return item
    return None


def _cleanup_download_files(url: str, result: Optional[Dict[str, Any]] = None) -> None:
    """
    Clean up all files related to a download, including partial and temporary files.
    """
    try:
        # Extract video ID from URL for pattern matching
        from yt_dlp.utils import extract_video_id
        video_id = None
        try:
            video_id = extract_video_id(url)
        except:
            pass
        
        files_to_clean = []
        
        # Clean up the completed file if provided
        if result and result.get("filepath"):
            filepath = result["filepath"]
            if os.path.exists(filepath):
                files_to_clean.append(filepath)
        
        # Clean up partial and temporary files in download directory
        if video_id:
            # yt-dlp creates various temporary files during download:
            # - *.part files (partial downloads)
            # - *.temp files (temporary files)
            # - *.ytdl files (metadata)
            # - fragments for segmented downloads
            patterns = [
                f"*{video_id}*.part",
                f"*{video_id}*.temp", 
                f"*{video_id}*.ytdl",
                f"*{video_id}*.f*",  # fragment files
                f"*{video_id}*.webm.part",
                f"*{video_id}*.mp4.part",
                f"*{video_id}*.m4a.part",
            ]
            
            for pattern in patterns:
                pattern_path = os.path.join(DEFAULT_DOWNLOAD_DIR, pattern)
                for file_path in glob.glob(pattern_path):
                    if os.path.isfile(file_path):
                        files_to_clean.append(file_path)
        
        # Also look for any .part or .temp files in the download directory that might be from this download
        # This is a fallback in case we can't extract the video ID
        temp_patterns = [
            os.path.join(DEFAULT_DOWNLOAD_DIR, "*.part"),
            os.path.join(DEFAULT_DOWNLOAD_DIR, "*.temp"),
            os.path.join(DEFAULT_DOWNLOAD_DIR, "*.ytdl"),
        ]
        
        for pattern in temp_patterns:
            for file_path in glob.glob(pattern):
                if os.path.isfile(file_path):
                    # Check if file was modified recently (within last 60 seconds)
                    # This helps ensure we only clean up files from current download
                    import time
                    if time.time() - os.path.getmtime(file_path) < 60:
                        files_to_clean.append(file_path)
        
        # Remove duplicates and clean up files
        for file_path in set(files_to_clean):
            try:
                os.remove(file_path)
            except OSError:
                pass  # Ignore individual file cleanup errors
                
    except Exception:
        # Ignore all cleanup errors - cleanup is best effort
        pass


def cancel_job(job_id: str) -> bool:
    """Cancel a job by ID. Returns True if job was found and cancelled."""
    for item in QUEUE:
        if item.get("id") == job_id:
            status = item.get("status")
            if status in ("queued", "running"):
                _CANCELLED_JOBS.add(job_id)
                if status == "queued":
                    # If queued, immediately mark as cancelled
                    item["status"] = "cancelled"
                    item["error"] = "Download cancelled by user"
                    # Clean up any potential files immediately for queued jobs
                    _cleanup_download_files(item.get("url", ""))
                return True
            # Job already completed, errored, or cancelled
            return False
    return False

