"""Domain package for yt-global-dl."""
from .base import (
    AggregateRootProtocol,
    BaseEntity,
    BaseValueObject,
    DomainEntityProtocol,
    DomainEventProtocol,
    IdentifiableProtocol,
    ValueObjectProtocol,
)
from .exceptions import (
    DomainError,
    InvalidVideoURLError,
    JobCancelledError,
    MuxingError,
    QueueFullError,
    ResolutionError,
    StreamNotFoundError,
)
from .models import (
    DownloadJob,
    DownloadRecord,
    JobStatus,
    MediaKind,
    QualityTarget,
    StreamFormat,
    VideoMetadata,
)
from .title_cleaner import clean_title, sanitize_filename
from .url_parser import build_canonical_url, extract_video_id

__all__ = [
    "MediaKind",
    "QualityTarget",
    "JobStatus",
    "StreamFormat",
    "VideoMetadata",
    "DownloadJob",
    "DownloadRecord",
    "DomainError",
    "InvalidVideoURLError",
    "JobCancelledError",
    "StreamNotFoundError",
    "ResolutionError",
    "QueueFullError",
    "MuxingError",
    "IdentifiableProtocol",
    "ValueObjectProtocol",
    "DomainEntityProtocol",
    "AggregateRootProtocol",
    "DomainEventProtocol",
    "BaseValueObject",
    "BaseEntity",
    "clean_title",
    "sanitize_filename",
    "extract_video_id",
    "build_canonical_url",
]
