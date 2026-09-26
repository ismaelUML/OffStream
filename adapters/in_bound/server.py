import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from domain.models import MediaKind, QualityTarget
from .cli import build_default_manager

# Si arrancamos con pythonw.exe en segundo plano, Windows deja sys.stdout y stderr como None.
# Si uvicorn o cualquier print intenta escupir algo sin esto, explota con un AttributeError ridículo.
# Mandamos todo al hoyo negro de devnull para que no rompa las pelotas en silencio.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


app = FastAPI(
    title="yt-global-dl Local Companion Daemon",
    description="Hexagonal media downloader daemon powering the browser extension.",
    version="1.0.0",
)

# Bloqueamos orígenes web arbitrarios para evitar ataques SSRF/CSRF desde páginas maliciosas en el navegador.
# Solo permitimos extensiones de navegador (Chrome/Firefox) y peticiones locales desde localhost o 127.0.0.1.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(chrome-extension://.*|moz-extension://.*|http://(localhost|127\.0\.0\.1)(:\d+)?)$",
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


class HistoryRecordResponse(BaseModel):
    id: int
    video_id: str
    title: str
    channel: str
    duration_seconds: int
    created_at: str
    file_path: str
    media_kind: str
    file_exists: bool


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


@app.delete("/api/jobs/{job_id}")
def cancel_job(job_id: str):
    success = manager.cancel_job(job_id)
    if not success:
        job = manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=400, detail="Job is not in a cancellable state")
    return {"status": "cancelled", "job_id": job_id}


@app.post("/api/jobs/clear")
def clear_finished_jobs():
    cleared_count = manager.clear_finished_jobs()
    return {"status": "ok", "cleared_count": cleared_count}


@app.get("/api/events")
async def stream_events():
    """Server-Sent Events (SSE) stream para recibir progreso a 60 FPS sin saturar la red con polling."""
    q = manager.subscribe_events()

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    event = await asyncio.to_thread(q.get, timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except Exception:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            manager.unsubscribe_events(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/history", response_model=List[HistoryRecordResponse])
def get_history(query: Optional[str] = None, limit: int = 100):
    records = manager.get_history(limit=limit, query=query)
    return [
        HistoryRecordResponse(
            id=r.id or 0,
            video_id=r.video_id,
            title=r.title,
            channel=r.channel,
            duration_seconds=r.duration_seconds,
            created_at=r.created_at,
            file_path=r.file_path,
            media_kind=r.media_kind,
            file_exists=Path(r.file_path).is_file(),
        )
        for r in records
    ]


@app.delete("/api/history/{record_id}")
def delete_history_record(record_id: int):
    success = manager.delete_history_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"status": "ok", "deleted_id": record_id}


@app.post("/api/history/clear")
def clear_all_history():
    count = manager.clear_history()
    return {"status": "ok", "cleared_count": count}


def _find_history_file(record_id: int) -> Path:
    records = manager.get_history(limit=500)
    matched = next((r for r in records if r.id == record_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    p = Path(matched.file_path)
    if not p.is_file():
        raise HTTPException(status_code=410, detail="Archivo movido o eliminado")
    return p


@app.post("/api/history/{record_id}/open")
def open_history_file(record_id: int):
    p = _find_history_file(record_id)
    try:
        os.startfile(str(p))
        return {"status": "ok", "opened": str(p)}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"No se pudo abrir el archivo: {err}")


def start_server(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    # Uvicorn asume con optimismo que siempre hay una terminal conectada.
    # En modo daemon silencioso (pythonw), llamar a isatty() sobre None revienta todo el proceso.
    # Si no hay tty real, le apagamos su logging por defecto para que nos deje vivir en paz.
    has_tty = False
    try:
        has_tty = sys.stdout is not None and sys.stdout.isatty()
    except Exception:
        has_tty = False

    log_config = uvicorn.config.LOGGING_CONFIG if has_tty else None
    uvicorn.run(app, host=host, port=port, log_config=log_config)



if __name__ == "__main__":
    start_server()
