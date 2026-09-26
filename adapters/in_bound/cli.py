"""Command Line Interface (CLI) Adapter.
Driving adapter implementing user interactions from the terminal.
"""
import argparse
import sys
import time
from typing import Any, Optional
from core.circuit_breaker import ResilientStreamResolver
from core.download_manager import DownloadManager
from domain.models import JobStatus, MediaKind, QualityTarget
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



def run_cli() -> None:
    parser = argparse.ArgumentParser(description="yt-global-dl: Clean, local YouTube media pipeline.")
    parser.add_argument("url", help="YouTube video URL or Video ID")
    parser.add_argument(
        "-a", "--audio",
        action="store_true",
        help="Download audio only as high-quality MP3",
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["best", "1080p", "720p"],
        default="best",
        help="Target video resolution",
    )
    parser.add_argument(
        "-i", "--inspect",
        action="store_true",
        help="Inspect video information without downloading",
    )
    parser.add_argument(
        "--cookies-from-browser",
        dest="cookies_browser",
        choices=["chrome", "firefox", "edge", "brave", "opera", "vivaldi", "safari"],
        default=None,
        help="Extract session cookies directly from your local browser",
    )

    args = parser.parse_args()
    manager = build_default_manager(cookies_browser=args.cookies_browser)

    try:
        if args.inspect:
            info = manager.inspect_video(args.url)
            print(f"\n[Title]     : {info.clean_title}")
            print(f"[Channel]   : {info.uploader}")
            print(f"[Duration]  : {info.duration_seconds} seconds")
            print(f"[Streams]   : {len(info.formats)} formats discovered\n")
            return

        kind = MediaKind.AUDIO if args.audio else MediaKind.VIDEO
        quality_map = {
            "best": QualityTarget.BEST,
            "1080p": QualityTarget.P1080,
            "720p": QualityTarget.P720,
        }
        target_quality = quality_map[args.quality]

        print(f"\n[+] Queueing download for: {args.url} ({kind.value.upper()})")
        job = manager.queue_download(args.url, kind, target_quality)

        last_progress = -1.0
        while job.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
            time.sleep(0.5)
            if int(job.progress_percentage) != int(last_progress):
                last_progress = job.progress_percentage
                status_str = f"[{job.status.value.upper()}] {job.progress_percentage:.1f}%"
                sys.stdout.write(f"\r{status_str}")
                sys.stdout.flush()

        sys.stdout.write("\n")
        if job.status == JobStatus.COMPLETED:
            print(f"[SUCCESS] Download Finished! Saved to: {job.output_path}\n")
        else:
            print(f"[FAILED] Download Failed: {job.error_message}\n")


    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as err:
        print(f"\n[Error] {err}")


if __name__ == "__main__":
    run_cli()
