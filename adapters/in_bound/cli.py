"""Command Line Interface (CLI) Adapter.
Driving adapter implementing user interactions from the terminal.
"""
import argparse
import sys
import time
from core.circuit_breaker import ResilientStreamResolver
from core.download_manager import DownloadManager
from domain.models import JobStatus, MediaKind, QualityTarget
from adapters.out_bound.ffmpeg_processor import FFmpegProcessorAdapter
from adapters.out_bound.http_downloader import HttpStreamingDownloader
from adapters.out_bound.innertube_resolver import InnerTubeResolver
from adapters.out_bound.local_storage import LocalStorageAdapter
from adapters.out_bound.ytdlp_resolver import YtDlpResolver


def build_default_manager() -> DownloadManager:
    """Dependency Injection bootstrap assembling the hexagonal graph."""
    storage = LocalStorageAdapter()
    downloader = HttpStreamingDownloader()
    processor = FFmpegProcessorAdapter()
    primary_resolver = InnerTubeResolver()
    fallback_resolver = YtDlpResolver()

    router = ResilientStreamResolver([primary_resolver, fallback_resolver])
    return DownloadManager(
        resolver=router,
        downloader=downloader,
        processor=processor,
        storage=storage,
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

    args = parser.parse_args()
    manager = build_default_manager()

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
            print(f"[✓] Download Finished! Saved to: {job.output_path}\n")
        else:
            print(f"[✗] Download Failed: {job.error_message}\n")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as err:
        print(f"\n[Error] {err}")


if __name__ == "__main__":
    run_cli()
