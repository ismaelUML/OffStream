"""Outbound (Driven) Ports for yt-global-dl.
Following Interface Segregation Principle (ISP) and Dependency Inversion Principle (DIP).
"""
from typing import Callable, List, Optional, Protocol
from domain.models import StreamFormat, VideoMetadata


class StreamResolverPort(Protocol):
    """Port for discovering and resolving stream manifests and URLs."""

    def resolve(self, url_or_id: str) -> VideoMetadata:
        """Extract metadata and available streams for a given video."""
        ...

    def can_handle(self, url_or_id: str) -> bool:
        """Check if this resolver can handle the specified URL."""
        ...


ProgressCallback = Callable[[float], None]
CancellationCheck = Callable[[], bool]


class MediaDownloaderPort(Protocol):
    """Port for streaming bytes from remote servers."""

    def download_stream(
        self,
        stream: StreamFormat,
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Download raw stream data to disk."""
        ...


class MediaProcessorPort(Protocol):
    """Port for multiplexing, transcoding, or tagging media files."""

    def mux_video_audio(self, video_path: str, audio_path: str, output_path: str) -> str:
        """Combine separate video and audio tracks into a unified MP4."""
        ...

    def convert_to_mp3(self, source_audio_path: str, output_path: str) -> str:
        """Transcode or remux an audio stream to standard MP3."""
        ...


class StoragePort(Protocol):
    """Port for managing local files and directories."""

    def get_output_path(self, filename: str, is_audio: bool = False) -> str:
        """Determine final destination path."""
        ...

    def create_temp_path(self, prefix: str, ext: str) -> str:
        """Create a temporary filepath for intermediate chunks."""
        ...

    def remove_files(self, paths: List[str]) -> None:
        """Safely remove temporary working files."""
        ...
