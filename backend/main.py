from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from downloader import (
    _info,
    add_to_queue,
    get_best_thumbnail,
    get_queue_statuses,
    get_stream_url,
    get_job,
    cancel_job,
)

app = FastAPI(title="Modern Video Downloader API", version="0.1.0")

# CORS: local-only use, but allow any origin for convenience when running different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UrlBody(BaseModel):
    url: str


class UrlsBody(BaseModel):
    urls: List[str]


@app.post("/api/thumbnail")
def api_thumbnail(body: UrlBody) -> Dict[str, Optional[str]]:
    try:
        info = _info(body.url)
        thumb = get_best_thumbnail(info)
        if not thumb:
            raise HTTPException(status_code=400, detail="No thumbnail found")
        return {"thumbnail": thumb}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/preview")
def api_preview(body: UrlBody) -> Dict[str, Optional[str]]:
    try:
        stream = get_stream_url(body.url)
        if not stream:
            raise HTTPException(status_code=400, detail="No preview URL found")
        return {"stream_url": stream}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
async def api_download(body: UrlBody) -> Dict[str, Any]:
    try:
        job_ids = add_to_queue([body.url])
        return {"queued": len(job_ids), "job_ids": job_ids}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/queue/add")
async def api_queue_add(body: UrlsBody) -> Dict[str, Any]:
    try:
        job_ids = add_to_queue(body.urls or [])
        return {"queued": len(job_ids), "job_ids": job_ids}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/queue")
def api_queue() -> Dict[str, Any]:
    try:
        return {"queue": get_queue_statuses()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/proxy")
async def api_proxy(request: Request) -> Response:
    """
    Simple streaming proxy to work around browser CORS on third-party media URLs.
    Usage: /api/proxy?url=<encoded_target_url>
    """
    target_url = request.query_params.get("url")
    if not target_url:
        raise HTTPException(status_code=400, detail="Missing url")

    # Stream the response and forward essential headers
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            upstream = await client.get(target_url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))

    # Pass through content-type and status code; do not add CORS headers here since frontend and API share origin
    headers = {}
    ct = upstream.headers.get("content-type")
    if ct:
        headers["content-type"] = ct
    cl = upstream.headers.get("content-length")
    if cl:
        headers["content-length"] = cl
    accept_ranges = upstream.headers.get("accept-ranges")
    if accept_ranges:
        headers["accept-ranges"] = accept_ranges

    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


@app.get("/api/jobs/{job_id}/file")
def api_job_file(job_id: str) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail="Job not completed yet")

    result = job.get("result") or {}
    path = result.get("filepath")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure file is within configured downloads dir
    downloads_root = os.path.realpath(os.getenv("DEFAULT_DOWNLOAD_DIR", "/downloads"))
    real_path = os.path.realpath(path)
    if not real_path.startswith(downloads_root):
        raise HTTPException(status_code=403, detail="Access denied")

    filename = os.path.basename(real_path)
    # Let starlette set Content-Disposition: attachment; filename="..."
    return FileResponse(real_path, media_type="application/octet-stream", filename=filename)


@app.delete("/api/jobs/{job_id}")
async def api_cancel_job(job_id: str) -> Dict[str, Any]:
    """Cancel a download job"""
    try:
        success = cancel_job(job_id)
        if success:
            return {"success": True, "message": "Job cancelled successfully"}
        else:
            return {"success": False, "message": "Job not found or cannot be cancelled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# TODO: progress hooks ✓ + cancel endpoint for a running download ✓
# TODO: quality selector (1080p/720p/audio-only) via format syntax
# TODO: persistent queue (SQLite/Redis) instead of in-memory

