"""High-Speed Media Downloader Adapter.
Implements MediaDownloaderPort using yt-dlp native parallel chunk engine
with bundled FFmpeg location to bypass YouTube CDN bitrate throttling.
Complexity target: M <= 5.
"""
from typing import Any, Dict, Optional
from domain.exceptions import StreamNotFoundError
from domain.models import QualityTarget, StreamFormat
from ports.out_bound import MediaDownloaderPort, ProgressCallback

try:
    import imageio_ffmpeg
    _BUNDLED_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _BUNDLED_FFMPEG = None

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class FastMediaDownloader(MediaDownloaderPort):
    """Downloads media streams at unthrottled gigabit speeds."""

    def download_stream(
        self,
        stream: StreamFormat,
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        if not stream.url:
            raise StreamNotFoundError(f"Stream {stream.format_id} has no valid URL.")

        if yt_dlp is None:
            raise StreamNotFoundError("yt-dlp is not available.")

        ydl_opts = self._build_opts(output_path, progress_callback)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([stream.url])

        return output_path

    def download_direct(
        self,
        url: str,
        output_path: str,
        is_audio: bool = False,
        quality: QualityTarget = QualityTarget.BEST,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Download directly from YouTube watch URL at max unthrottled line speed."""
        if yt_dlp is None:
            raise StreamNotFoundError("yt-dlp is not available.")

        ydl_opts = self._build_direct_opts(output_path, is_audio, quality, progress_callback)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return output_path

    def _build_opts(self, output_path: str, callback: Optional[ProgressCallback]) -> Dict[str, Any]:
        return {
            "outtmpl": output_path,
            "progress_hooks": [self._make_progress_hook(callback)],
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "continuedl": False,
            "concurrent_fragment_downloads": 4,
            "ffmpeg_location": _BUNDLED_FFMPEG,
        }

    def _build_direct_opts(
        self,
        output_path: str,
        is_audio: bool,
        quality: QualityTarget,
        callback: Optional[ProgressCallback],
    ) -> Dict[str, Any]:
        base_opts = self._build_opts(output_path, callback)

        if is_audio:
            base_opts["format"] = "bestaudio/best"
            base_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
            # yt-dlp appends .mp3 automatically when postprocessing
            clean_out = output_path.replace(".mp3", "")
            base_opts["outtmpl"] = f"{clean_out}.%(ext)s"
        elif quality == QualityTarget.P720:
            base_opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            base_opts["merge_output_format"] = "mp4"
        else:
            base_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
            base_opts["merge_output_format"] = "mp4"

        return base_opts

    def _make_progress_hook(self, callback: Optional[ProgressCallback]):
        def hook(d: Dict[str, Any]) -> None:
            if d.get("status") == "downloading" and callback:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                downloaded = d.get("downloaded_bytes", 0)
                pct = min(100.0, (downloaded / total) * 100.0)
                callback(pct)
        return hook
