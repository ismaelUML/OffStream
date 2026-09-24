"""Outbound Adapters for yt-global-dl."""
from .ffmpeg_processor import FFmpegProcessorAdapter
from .http_downloader import HttpStreamingDownloader
from .innertube_resolver import InnerTubeResolver
from .local_storage import LocalStorageAdapter
from .ytdlp_resolver import YtDlpResolver

__all__ = [
    "FFmpegProcessorAdapter",
    "HttpStreamingDownloader",
    "InnerTubeResolver",
    "LocalStorageAdapter",
    "YtDlpResolver",
]
