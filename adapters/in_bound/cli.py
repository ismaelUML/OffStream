# Interfaz por línea de comandos (CLI).
# Para cuando estás en un servidor remoto, automatizando tareas por cron/powershell,
# o simplemente querés bajar un video en dos segundos sin abrir la GUI ni el navegador.
import argparse
import sys
import time
from typing import Any, Optional
from domain.models import JobStatus, MediaKind, QualityTarget
from bootstrap import build_default_manager



def _build_argument_parser() -> argparse.ArgumentParser:
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
    return parser


def _print_inspected_video(info) -> None:
    print(f"\n[Title]     : {info.clean_title}")
    print(f"[Channel]   : {info.uploader}")
    print(f"[Duration]  : {info.duration_seconds} seconds")
    print(f"[Streams]   : {len(info.formats)} formats discovered\n")


def _monitor_job_progress(job) -> None:
    # En Windows, la terminal almacena en buffer la salida estándar si no hay salto de línea.
    # Usamos \r para sobreescribir la misma línea (sin spamear 200 filas de texto en pantalla)
    # y sys.stdout.flush() obligatorio para forzar el renderizado inmediato de cada porcentaje.
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


def run_cli() -> None:
    parser = _build_argument_parser()
    args = parser.parse_args()
    manager = build_default_manager(cookies_browser=args.cookies_browser)

    try:
        if args.inspect:
            info = manager.inspect_video(args.url)
            _print_inspected_video(info)
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
        _monitor_job_progress(job)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as err:
        print(f"\n[Error] {err}")


if __name__ == "__main__":
    run_cli()
