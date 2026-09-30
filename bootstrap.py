"""Composition Root / Dependency Injection Bootstrap for yt-global-dl.
Assembles the hexagonal graph at the application boundary without coupling
driving adapters to each other.
"""
from typing import Any, Optional
from core.circuit_breaker import ResilientStreamResolver
from core.download_manager import DownloadManager
from adapters.out_bound.fast_downloader import FastMediaDownloader
from adapters.out_bound.ffmpeg_processor import FFmpegProcessorAdapter
from adapters.out_bound.innertube_resolver import InnerTubeResolver
from adapters.out_bound.local_storage import LocalStorageAdapter
from adapters.out_bound.sqlite_history import SqliteHistoryAdapter
from adapters.out_bound.ytdlp_resolver import YtDlpResolver


def build_default_manager(
    cookies_browser: Optional[str] = None,
    history_repo: Optional[Any] = None,
) -> DownloadManager:
    """Dependency Injection bootstrap assembling the hexagonal graph."""
    storage = LocalStorageAdapter()
    downloader = FastMediaDownloader(cookies_browser=cookies_browser)
    processor = FFmpegProcessorAdapter()
    primary_resolver = YtDlpResolver(cookies_browser=cookies_browser)
    fallback_resolver = InnerTubeResolver()

    router = ResilientStreamResolver([primary_resolver, fallback_resolver])
    history = history_repo if history_repo is not None else SqliteHistoryAdapter()
    return DownloadManager(
        resolver=router,
        downloader=downloader,
        processor=processor,
        storage=storage,
        history_repo=history,
    )
