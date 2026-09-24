"""HTTP Streaming Media Downloader Adapter.
Implements MediaDownloaderPort.
Single Responsibility: Fetch raw media chunks over HTTP and report progress.
"""
from typing import Optional
import requests
from domain.exceptions import StreamNotFoundError
from domain.models import StreamFormat
from ports.out_bound import ProgressCallback

_CHUNK_SIZE = 1024 * 1024  # 1 MB chunks
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class HttpStreamingDownloader:
    """Streams video and audio bytes directly from remote CDNs."""

    def __init__(self, timeout: int = 30) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _USER_AGENT})
        self._timeout = timeout

    def download_stream(
        self,
        stream: StreamFormat,
        output_path: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        if not stream.url:
            raise StreamNotFoundError(f"Stream {stream.format_id} has no valid URL.")

        with self._session.get(stream.url, stream=True, timeout=self._timeout) as resp:
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("content-length", 0))
            self._write_chunks(resp, output_path, total_bytes, progress_callback)

        return output_path

    def _write_chunks(
        self,
        response: requests.Response,
        output_path: str,
        total_bytes: int,
        callback: Optional[ProgressCallback],
    ) -> None:
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if callback and total_bytes > 0:
                    pct = (downloaded / total_bytes) * 100.0
                    callback(min(pct, 100.0))
