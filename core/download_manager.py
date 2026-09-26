# El cerebro de las descargas. Si dejáramos que el usuario encole 50 videos a la vez,
# FFmpeg y Python le prenderían fuego el procesador.
# Limitamos los workers en paralelo y coordinamos la resolución, descarga y unión final.
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from domain.exceptions import QueueFullError
from domain.models import (
    DownloadJob,
    JobStatus,
    MediaKind,
    QualityTarget,
    VideoMetadata,
)
from ports.in_bound import DownloadUseCasePort
from ports.out_bound import (
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
    ) -> None:
        self._resolver = resolver
        self._downloader = downloader
        self._processor = processor
        self._storage = storage
        self._max_queue_size = max_queue_size
        self._max_history = max_history
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

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

    def _run_job_lifecycle(self, job: DownloadJob) -> None:
        try:
            if job.status == JobStatus.CANCELLED:
                return

            job.status = JobStatus.RESOLVING
            metadata = self._resolver.resolve(job.source_url)

            if job.status == JobStatus.CANCELLED:
                return

            job.status = JobStatus.DOWNLOADING
            if job.target_kind == MediaKind.AUDIO:
                path = self._process_audio_pipeline(job, metadata)
            else:
                path = self._process_video_pipeline(job, metadata)

            if job.status == JobStatus.CANCELLED:
                return

            job.mark_completed(path)
        except Exception as err:
            if job.status != JobStatus.CANCELLED:
                job.mark_failed(str(err))

    def _process_audio_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
        dest_path = self._storage.get_output_path(f"{metadata.clean_title}.mp3", is_audio=True)
        # Si el downloader tiene la ruta rápida acelerada directa, la usamos de cabeza.
        # Nos ahorra tener que bajar el archivo temporal a mano y llamar a ffmpeg por separado.
        if hasattr(self._downloader, "download_direct"):
            return self._downloader.download_direct(
                job.source_url,
                dest_path,
                is_audio=True,
                progress_callback=job.update_progress,
            )

        audio_stream = select_best_audio_stream(metadata.formats)
        temp_audio = self._storage.create_temp_path(f"audio_{job.job_id}", audio_stream.extension)
        try:
            self._downloader.download_stream(
                audio_stream,
                temp_audio,
                progress_callback=lambda p: job.update_progress(p * 0.85),
            )
            job.status = JobStatus.MUXING
            return self._processor.convert_to_mp3(temp_audio, dest_path)
        finally:
            # Limpiamos el archivo temporal sí o sí; nadie quiere gigabytes de basura huérfana.
            self._storage.remove_files([temp_audio])

    def _process_video_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
        dest_path = self._storage.get_output_path(f"{metadata.clean_title}.mp4", is_audio=False)
        # Mismo caso: la ruta rápida directa descarga fragments paralelos y une con ffmpeg en 2 segundos.
        if hasattr(self._downloader, "download_direct"):
            return self._downloader.download_direct(
                job.source_url,
                dest_path,
                is_audio=False,
                quality=job.target_quality,
                progress_callback=job.update_progress,
            )

        # Plan B de respaldo: bajamos la mejor pista de video y la mejor pista de audio por separado
        video_stream = select_video_stream(metadata.formats, job.target_quality)
        audio_stream = select_best_audio_stream(metadata.formats)
        temp_video = self._storage.create_temp_path(f"video_{job.job_id}", video_stream.extension)
        temp_audio = self._storage.create_temp_path(f"audio_{job.job_id}", audio_stream.extension)
        try:
            self._downloader.download_stream(
                video_stream,
                temp_video,
                progress_callback=lambda p: job.update_progress(p * 0.5),
            )
            self._downloader.download_stream(
                audio_stream,
                temp_audio,
                progress_callback=lambda p: job.update_progress(50.0 + (p * 0.35)),
            )
            job.status = JobStatus.MUXING
            return self._processor.mux_video_audio(temp_video, temp_audio, dest_path)
        finally:
            # Borramos los dos pedazos temporales para no dejar el disco C tapado de mugre
            self._storage.remove_files([temp_video, temp_audio])

