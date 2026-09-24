"""FFmpeg Media Processor Adapter.
Implements MediaProcessorPort.
Handles lossless multiplexing and audio conversion using local ffmpeg binary.
"""
import shutil
import subprocess
from domain.exceptions import MuxingError

try:
    import imageio_ffmpeg
    _BUNDLED_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _BUNDLED_FFMPEG = None


class FFmpegProcessorAdapter:
    """Invokes FFmpeg for media stream operations."""

    def __init__(self, custom_binary: str = "") -> None:
        self._binary = custom_binary or _BUNDLED_FFMPEG or shutil.which("ffmpeg")
        if not self._binary:
            raise MuxingError("FFmpeg binary not detected on system or in virtual environment.")

    def mux_video_audio(self, video_path: str, audio_path: str, output_path: str) -> str:
        cmd = [
            self._binary,
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]
        self._run_command(cmd, "Failed to mux video and audio tracks.")
        return output_path

    def convert_to_mp3(self, source_audio_path: str, output_path: str) -> str:
        cmd = [
            self._binary,
            "-y",
            "-i", source_audio_path,
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ]
        self._run_command(cmd, "Failed to convert audio stream to MP3.")
        return output_path

    def _run_command(self, cmd: list, error_context: str) -> None:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0:
            raise MuxingError(f"{error_context} Error: {proc.stderr[-300:]}")
