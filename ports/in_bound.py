"""Inbound (Driving) Ports for yt-global-dl.
Defines use case boundaries for consumers (CLI, Extension API, GUI).
"""
from typing import List, Optional, Protocol
from domain.models import DownloadJob, MediaKind, QualityTarget, VideoMetadata


class DownloadUseCasePort(Protocol):
    """Primary inbound port for submitting and monitoring download operations."""

    def inspect_video(self, url: str) -> VideoMetadata:
        """Fetch video information without starting a download."""
        ...

    def queue_download(
        self,
        url: str,
        kind: MediaKind,
        quality: QualityTarget,
    ) -> DownloadJob:
        """Submit a download job to the managed worker pool."""
        ...

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        """Fetch status and progress of an existing job."""
        ...

    def list_jobs(self) -> List[DownloadJob]:
        """List all current jobs in the pipeline."""
        ...

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        ...

    def clear_finished_jobs(self) -> int:
        """Remove completed, failed, or cancelled jobs from memory."""
        ...

