"""Domain Exceptions for yt-global-dl.
"""

class DomainError(Exception):
    """Base domain exception."""
    pass


class InvalidVideoURLError(DomainError):
    """Raised when the provided URL cannot be parsed into a valid video identifier."""
    pass


class StreamNotFoundError(DomainError):
    """Raised when no compatible stream could be located for requested format."""
    pass


class ResolutionError(DomainError):
    """Raised when an external resolver fails to extract video data."""
    pass


class QueueFullError(DomainError):
    """Raised when the download queue has reached capacity according to Little's Law."""
    pass


class MuxingError(DomainError):
    """Raised when merging or processing audio/video streams fails."""
    pass


class JobCancelledError(DomainError):
    """Raised when a download job is cancelled while in progress."""
    pass
