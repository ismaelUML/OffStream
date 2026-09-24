"""Pure Domain Models for yt-global-dl.
Zero external dependencies. Pure standard library.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MediaKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"


class QualityTarget(str, Enum):
    BEST = "best"
    P1080 = "1080p"
    P720 = "720p"
    AUDIO_HIGH = "audio_high"


class JobStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    MUXING = "muxing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class StreamFormat:
    format_id: str
    extension: str
    url: str
    bitrate: Optional[int] = None
    resolution: Optional[str] = None
    is_video: bool = True
    is_audio: bool = False
    filesize_estimate: Optional[int] = None


@dataclass(frozen=True)
class VideoMetadata:
    video_id: str
    raw_title: str
    clean_title: str
    uploader: str
    duration_seconds: int
    thumbnail_url: str
    formats: List[StreamFormat] = field(default_factory=list)


@dataclass
class DownloadJob:
    job_id: str
    source_url: str
    target_kind: MediaKind
    target_quality: QualityTarget
    status: JobStatus = JobStatus.PENDING
    progress_percentage: float = 0.0
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def update_progress(self, progress: float) -> None:
        self.progress_percentage = max(0.0, min(100.0, progress))

    def mark_completed(self, path: str) -> None:
        self.status = JobStatus.COMPLETED
        self.progress_percentage = 100.0
        self.output_path = path
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()
