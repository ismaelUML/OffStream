"""Download Manager orchestrating use cases.
Governed by Little's Law (L = lambda * W) for bounded concurrency.
Adheres strictly to SOLID and Dependency Inversion Principle.
"""
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
    """Core domain service managing the download queue and workers."""

    def __init__(
        self,
        resolver: StreamResolverPort,
        downloader: MediaDownloaderPort,
        processor: MediaProcessorPort,
        storage: StoragePort,
        max_workers: int = 3,
        max_queue_size: int = 25,
    ) -> None:
        self._resolver = resolver
        self._downloader = downloader
        self._processor = processor
        self._storage = storage
        self._max_queue_size = max_queue_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, DownloadJob] = {}

    def inspect_video(self, url: str) -> VideoMetadata:
        return self._resolver.resolve(url)

    def queue_download(
        self,
        url: str,
        kind: MediaKind,
        quality: QualityTarget,
    ) -> DownloadJob:
        self._check_queue_capacity()
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
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[DownloadJob]:
        return list(self._jobs.values())

    def _check_queue_capacity(self) -> None:
        active_count = sum(
            1 for j in self._jobs.values()
            if j.status in (JobStatus.PENDING, JobStatus.RESOLVING, JobStatus.DOWNLOADING, JobStatus.MUXING)
        )
        if active_count >= self._max_queue_size:
            raise QueueFullError("Download pipeline is at maximum capacity.")

    def _run_job_lifecycle(self, job: DownloadJob) -> None:
        try:
            job.status = JobStatus.RESOLVING
            metadata = self._resolver.resolve(job.source_url)

            job.status = JobStatus.DOWNLOADING
            if job.target_kind == MediaKind.AUDIO:
                path = self._process_audio_pipeline(job, metadata)
            else:
                path = self._process_video_pipeline(job, metadata)

            job.mark_completed(path)
        except Exception as err:
            job.mark_failed(str(err))

    def _process_audio_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
        audio_stream = select_best_audio_stream(metadata.formats)
        temp_audio = self._storage.create_temp_path(f"audio_{job.job_id}", audio_stream.extension)

        try:
            self._downloader.download_stream(
                audio_stream,
                temp_audio,
                progress_callback=lambda p: job.update_progress(p * 0.85),
            )
            job.status = JobStatus.MUXING
            dest_path = self._storage.get_output_path(f"{metadata.clean_title}.mp3", is_audio=True)
            return self._processor.convert_to_mp3(temp_audio, dest_path)
        finally:
            self._storage.remove_files([temp_audio])

    def _process_video_pipeline(self, job: DownloadJob, metadata: VideoMetadata) -> str:
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
            dest_path = self._storage.get_output_path(f"{metadata.clean_title}.mp4", is_audio=False)
            return self._processor.mux_video_audio(temp_video, temp_audio, dest_path)
        finally:
            self._storage.remove_files([temp_video, temp_audio])
