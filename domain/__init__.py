"""Domain package for yt-global-dl."""
from .models import (
    MediaKind,
    QualityTarget,
    JobStatus,
    StreamFormat,
    VideoMetadata,
    DownloadJob,
)
from .exceptions import (
    DomainError,
    InvalidVideoURLError,
    StreamNotFoundError,
    ResolutionError,
    QueueFullError,
    MuxingError,
)

__all__ = [
    "MediaKind",
    "QualityTarget",
    "JobStatus",
    "StreamFormat",
    "VideoMetadata",
    "DownloadJob",
    "DomainError",
    "InvalidVideoURLError",
    "StreamNotFoundError",
    "ResolutionError",
    "QueueFullError",
    "MuxingError",
]
