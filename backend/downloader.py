import asyncio
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple
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


async def download(url: str, format_selector: str = "bv*+ba/b") -> Dict[str, Any]:
    if not url:
        raise ValueError("URL is required")

    opts: Dict[str, Any] = {
        **YTDLP_COMMON_OPTS,
        "format": format_selector,
        # TODO: progress hooks for live progress and cancel
        # "progress_hooks": [progress_hook_function],
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

        try:
            result = await download(job["url"])
            async with _QUEUE_LOCK:
                job["result"] = result
                job["status"] = "done"
        except Exception as e:
            async with _QUEUE_LOCK:
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
        }
        for item in QUEUE
    ]

