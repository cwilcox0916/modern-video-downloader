from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from downloader import (
    _info,
    add_to_queue,
    get_best_thumbnail,
    get_queue_statuses,
    get_stream_url,
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
def api_download(body: UrlBody) -> Dict[str, Any]:
    try:
        job_ids = add_to_queue([body.url])
        return {"queued": len(job_ids), "job_ids": job_ids}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/queue/add")
def api_queue_add(body: UrlsBody) -> Dict[str, Any]:
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


# TODO: progress hooks + cancel endpoint for a running download
# TODO: quality selector (1080p/720p/audio-only) via format syntax
# TODO: persistent queue (SQLite/Redis) instead of in-memory

