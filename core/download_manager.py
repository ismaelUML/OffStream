# El cerebro de las descargas. Si dejáramos que el usuario encole 50 videos a la vez,
# FFmpeg y Python le prenderían fuego el procesador.
# Limitamos los workers en paralelo y coordinamos la resolución, descarga y unión final.
import queue
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional
from domain.exceptions import JobCancelledError, QueueFullError
from domain.models import (
    DownloadJob,
    DownloadRecord,
    JobStatus,
    MediaKind,
    QualityTarget,
    VideoMetadata,
)
from ports.in_bound import DownloadUseCasePort
from ports.out_bound import (
    HistoryRepositoryPort,
    MediaDownloaderPort,
    MediaProcessorPort,
    StoragePort,
    StreamResolverPort,
)
from .stream_selector import select_best_audio_stream, select_video_stream


class DownloadManager(DownloadUseCasePort):
    def __init__(
        self,
        resolver: StreamResolverPort,
        downloader: MediaDownloaderPort,
        processor: MediaProcessorPort,
        storage: StoragePort,
        max_workers: int = 3,  # 3 descargas simultáneas es el punto dulce antes de asfixiar la red y el disco
        max_queue_size: int = 25,
        max_history: int = 50,  # Evitamos que el daemon en segundo plano filtre memoria tras semanas de uso
        history_repo: Optional[HistoryRepositoryPort] = None,
    ) -> None:
        self._resolver = resolver
        self._downloader = downloader
        self._processor = processor
        self._storage = storage
        self._max_queue_size = max_queue_size
        self._max_history = max_history
        self._history_repo = history_repo
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, DownloadJob] = {}
        self._lock = threading.Lock()
        self._listeners: List[queue.Queue] = []
        self._listeners_lock = threading.Lock()

    def subscribe_events(self) -> queue.Queue:
        """Permite a clientes SSE o WebSockets recibir actualizaciones en tiempo real a 60 FPS."""
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._listeners_lock:
            self._listeners.append(q)
        return q

    def unsubscribe_events(self, q: queue.Queue) -> None:
        with self._listeners_lock:
            if q in self._listeners:
                self._listeners.remove(q)

    def _broadcast_job_event(self, job: DownloadJob) -> None:
        event_data = {
            "type": "job_update",
            "job_id": job.job_id,
            "status": job.status.value,
            "progress_percentage": job.progress_percentage,
            "source_url": job.source_url,
            "target_kind": job.target_kind.value,
            "target_quality": job.target_quality.value,
            "output_path": job.output_path,
            "error_message": job.error_message,
        }
        with self._listeners_lock:
            for q in list(self._listeners):
                try:
                    q.put_nowait(event_data)
                except queue.Full:
                    try:
                        q.get_nowait()
                        q.put_nowait(event_data)
                    except Exception:
                        pass

    def inspect_video(self, url: str) -> VideoMetadata:
        return self._resolver.resolve(url)

    def queue_download(
        self,
        url: str,
        kind: MediaKind,
        quality: QualityTarget,
    ) -> DownloadJob:
        with self._lock:
            self._check_queue_capacity()
            self._prune_history_locked()
            job_id = str(uuid.uuid4())[:8]
            job = DownloadJob(
                job_id=job_id,
                source_url=url,
                target_kind=kind,
                target_quality=quality,
            )
            self._jobs[job_id] = job
        self._broadcast_job_event(job)
        self._executor.submit(self._run_job_lifecycle, job)
        return job

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[DownloadJob]:
        with self._lock:
            return list(self._jobs.values())

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status in (JobStatus.PENDING, JobStatus.RESOLVING, JobStatus.DOWNLOADING, JobStatus.MUXING):
                job.mark_cancelled()
                self._broadcast_job_event(job)
                return True
            return False

    def clear_finished_jobs(self) -> int:
        with self._lock:
            finished_ids = [
                jid for jid, j in self._jobs.items()
                if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            ]
            for jid in finished_ids:
                del self._jobs[jid]
            return len(finished_ids)

    def get_history(self, limit: int = 100, query: Optional[str] = None) -> List[DownloadRecord]:
        if not self._history_repo:
            return []
        return self._history_repo.list_records(limit=limit, query=query)

    def delete_history_record(self, record_id: int) -> bool:
        if not self._history_repo:
            return False
        return self._history_repo.delete_record(record_id)

    def clear_history(self) -> int:
        if not self._history_repo:
            return 0
        return self._history_repo.clear_all()

    def _set_job_status(self, job: DownloadJob, status: JobStatus) -> None:
        job.status = status
        self._broadcast_job_event(job)

    def _update_job_progress(self, job: DownloadJob, pct: float) -> None:
        job.update_progress(pct)
        self._broadcast_job_event(job)

    def _mark_job_completed(self, job: DownloadJob, path: str, metadata: Optional[VideoMetadata]) -> None:
        job.mark_completed(path)
        self._record_history(job, path, metadata)
        self._broadcast_job_event(job)

    def _record_history(self, job: DownloadJob, path: str, metadata: Optional[VideoMetadata]) -> None:
        if not self._history_repo or not metadata:
            return
        try:
            record = DownloadRecord(
                id=None,
                video_id=metadata.video_id,
                title=metadata.clean_title,
                channel=metadata.uploader,
                duration_seconds=metadata.duration_seconds,
                created_at=datetime.utcnow().isoformat(),
                file_path=path,
                media_kind=job.target_kind.value if hasattr(job.target_kind, "value") else str(job.target_kind),
            )
            self._history_repo.add_record(record)
        except Exception:
            pass

    def _check_queue_capacity(self) -> None:
        active_count = sum(
            1 for j in self._jobs.values()
            if j.status in (JobStatus.PENDING, JobStatus.RESOLVING, JobStatus.DOWNLOADING, JobStatus.MUXING)
        )
        if active_count >= self._max_queue_size:
            raise QueueFullError("Download pipeline is at maximum capacity.")

    def _prune_history_locked(self) -> None:
        # Descartamos los jobs terminados más viejos si acumulamos más de max_history.
        # En Windows con inicio automático, si esto no existe, la RAM sube silenciosamente.
        finished = [
            (jid, j.created_at) for jid, j in self._jobs.items()
            if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        ]
        if len(finished) > self._max_history:
            finished.sort(key=lambda x: x[1])
            excess = len(finished) - self._max_history
            for jid, _ in finished[:excess]:
                del self._jobs[jid]

    def _execute_download_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
        if job.target_kind == MediaKind.AUDIO:
            return self._process_audio_pipeline(job, metadata)
        return self._process_video_pipeline(job, metadata)

    def _handle_lifecycle_error(self, job: DownloadJob, err: Exception) -> None:
        if isinstance(err, JobCancelledError):
            job.mark_cancelled()
        elif job.status != JobStatus.CANCELLED:
            job.mark_failed(str(err))
        self._broadcast_job_event(job)

    def _run_job_lifecycle(self, job: DownloadJob) -> None:
        try:
            if job.status == JobStatus.CANCELLED:
                return

            self._set_job_status(job, JobStatus.RESOLVING)
            metadata = self._resolver.resolve(job.source_url)
            if job.status == JobStatus.CANCELLED:
                return

            self._set_job_status(job, JobStatus.DOWNLOADING)
            path = self._execute_download_pipeline(job, metadata)
            if job.status == JobStatus.CANCELLED:
                return

            self._mark_job_completed(job, path, metadata)
        except Exception as err:
            self._handle_lifecycle_error(job, err)

    def _process_audio_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
        dest_path = self._storage.get_output_path(f"{metadata.clean_title}.mp3", is_audio=True)
        # Si el downloader tiene la ruta rápida acelerada directa, la usamos de cabeza.
        # Nos ahorra tener que bajar el archivo temporal a mano y llamar a ffmpeg por separado.
        if hasattr(self._downloader, "download_direct"):
            try:
                return self._downloader.download_direct(
                    job.source_url,
                    dest_path,
                    is_audio=True,
                    progress_callback=lambda p: self._update_job_progress(job, p),
                    is_cancelled=lambda: job.status == JobStatus.CANCELLED,
                )
            except JobCancelledError:
                self._storage.remove_files([dest_path])
                raise

        audio_stream = select_best_audio_stream(metadata.formats)
        temp_audio = self._storage.create_temp_path(f"audio_{job.job_id}", audio_stream.extension)
        try:
            self._downloader.download_stream(
                audio_stream,
                temp_audio,
                progress_callback=lambda p: self._update_job_progress(job, p * 0.85),
                is_cancelled=lambda: job.status == JobStatus.CANCELLED,
            )
            self._set_job_status(job, JobStatus.MUXING)
            return self._processor.convert_to_mp3(temp_audio, dest_path)
        finally:
            self._storage.remove_files([temp_audio])

    def _process_video_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
        dest_path = self._storage.get_output_path(f"{metadata.clean_title}.mp4", is_audio=False)
        # Mismo caso: la ruta rápida directa descarga fragments paralelos y une con ffmpeg en 2 segundos.
        if hasattr(self._downloader, "download_direct"):
            try:
                return self._downloader.download_direct(
                    job.source_url,
                    dest_path,
                    is_audio=False,
                    quality=job.target_quality,
                    progress_callback=lambda p: self._update_job_progress(job, p),
                    is_cancelled=lambda: job.status == JobStatus.CANCELLED,
                )
            except JobCancelledError:
                self._storage.remove_files([dest_path])
                raise

        video_stream = select_video_stream(metadata.formats, job.target_quality)
        audio_stream = select_best_audio_stream(metadata.formats)
        temp_video = self._storage.create_temp_path(f"video_{job.job_id}", video_stream.extension)
        temp_audio = self._storage.create_temp_path(f"audio_{job.job_id}", audio_stream.extension)
        try:
            self._downloader.download_stream(
                video_stream,
                temp_video,
                progress_callback=lambda p: self._update_job_progress(job, p * 0.5),
            )
            self._downloader.download_stream(
                audio_stream,
                temp_audio,
                progress_callback=lambda p: self._update_job_progress(job, 50.0 + (p * 0.35)),
            )
            self._set_job_status(job, JobStatus.MUXING)
            return self._processor.mux_video_audio(temp_video, temp_audio, dest_path)
        finally:
            self._storage.remove_files([temp_video, temp_audio])

