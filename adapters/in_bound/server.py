"""FastAPI Server Driving Adapter.
Provides a local REST API for browser extensions and external integrations.
"""
import os
import sys
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from domain.models import MediaKind, QualityTarget
from .cli import build_default_manager

# Ensure windowless Python (pythonw.exe) has valid write streams
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


app = FastAPI(
    title="yt-global-dl Local Companion Daemon",
    description="Hexagonal media downloader daemon powering the browser extension.",
    version="1.0.0",
)

# Enable CORS for Chrome and Firefox extensions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = build_default_manager()


class InspectRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL or ID")


class DownloadRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL or ID")
    kind: MediaKind = Field(default=MediaKind.VIDEO)
    quality: QualityTarget = Field(default=QualityTarget.BEST)


class JobResponse(BaseModel):
    job_id: str
    source_url: str
    target_kind: str
    target_quality: str
    status: str
    progress_percentage: float
    output_path: Optional[str] = None
    error_message: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "yt-global-dl", "version": "1.0.0"}


@app.post("/api/inspect")
def inspect_video(req: InspectRequest):
    try:
        meta = manager.inspect_video(req.url)
        return {
            "video_id": meta.video_id,
            "title": meta.clean_title,
            "raw_title": meta.raw_title,
            "uploader": meta.uploader,
            "duration": meta.duration_seconds,
            "thumbnail": meta.thumbnail_url,
            "format_count": len(meta.formats),
        }
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.post("/api/download", response_model=JobResponse)
def queue_download(req: DownloadRequest):
    try:
        job = manager.queue_download(req.url, req.kind, req.quality)
        return JobResponse(
            job_id=job.job_id,
            source_url=job.source_url,
            target_kind=job.target_kind.value,
            target_quality=job.target_quality.value,
            status=job.status.value,
            progress_percentage=job.progress_percentage,
            output_path=job.output_path,
            error_message=job.error_message,
        )
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str):
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id=job.job_id,
        source_url=job.source_url,
        target_kind=job.target_kind.value,
        target_quality=job.target_quality.value,
        status=job.status.value,
        progress_percentage=job.progress_percentage,
        output_path=job.output_path,
        error_message=job.error_message,
    )


@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs():
    return [
        JobResponse(
            job_id=j.job_id,
            source_url=j.source_url,
            target_kind=j.target_kind.value,
            target_quality=j.target_quality.value,
            status=j.status.value,
            progress_percentage=j.progress_percentage,
            output_path=j.output_path,
            error_message=j.error_message,
        )
        for j in manager.list_jobs()
    ]


def start_server(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    # In windowless mode, pass log_config=None to avoid sys.stdout.isatty() crash
    has_tty = False
    try:
        has_tty = sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        has_tty = False

    log_config = uvicorn.config.LOGGING_CONFIG if has_tty else None
    uvicorn.run(app, host=host, port=port, log_config=log_config)



if __name__ == "__main__":
    start_server()
