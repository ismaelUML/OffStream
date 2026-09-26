"""yt-dlp Stream Resolver Adapter.
Implements StreamResolverPort as a robust secondary engine with dynamic cipher solving.
"""
from typing import Any, Dict, List, Optional
from core.title_cleaner import clean_title
from core.url_parser import build_canonical_url, extract_video_id
from domain.exceptions import ResolutionError
from domain.models import StreamFormat, VideoMetadata

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


from .cookies_helper import is_cookie_error, resolve_cookie_opts


class YtDlpResolver:
    """Uses yt-dlp internal API to extract metadata and decipher scrambled streams."""

    def __init__(self, cookies_browser: Optional[str] = None) -> None:
        if yt_dlp is None:
            raise ResolutionError("yt-dlp package is not installed.")

        self._cookies_browser = cookies_browser
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }

    def can_handle(self, url_or_id: str) -> bool:
        try:
            extract_video_id(url_or_id)
            return True
        except Exception:
            return False

    def _retry_without_cookies(self, canonical_url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        opts.pop("cookiesfrombrowser", None)
        opts.pop("cookiefile", None)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(canonical_url, download=False) or {}
        except Exception as inner_err:
            raise ResolutionError(f"yt-dlp extraction failed: {inner_err}")

    @staticmethod
    def _has_cookies(opts: Dict[str, Any]) -> bool:
        return "cookiesfrombrowser" in opts or "cookiefile" in opts

    def _extract_info_safely(self, canonical_url: str) -> Dict[str, Any]:
        opts = dict(self._ydl_opts)
        opts.update(resolve_cookie_opts(self._cookies_browser))
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(canonical_url, download=False) or {}
        except Exception as err:
            if is_cookie_error(err) and self._has_cookies(opts):
                return self._retry_without_cookies(canonical_url, opts)
            raise ResolutionError(f"yt-dlp extraction failed: {err}")

    def resolve(self, url_or_id: str) -> VideoMetadata:
        video_id = extract_video_id(url_or_id)
        canonical_url = build_canonical_url(video_id)
        info = self._extract_info_safely(canonical_url)

        if not info:
            raise ResolutionError("yt-dlp returned no video info dictionary.")

        return self._map_to_metadata(video_id, info)

    def _map_to_metadata(self, video_id: str, info: Dict[str, Any]) -> VideoMetadata:
        raw_title = info.get("title", f"video_{video_id}")
        uploader = info.get("uploader") or info.get("channel", "Unknown Artist")
        duration = int(info.get("duration", 0))
        thumbnail = info.get("thumbnail", "")

        raw_formats = info.get("formats", [])
        formats = self._extract_formats(raw_formats)

        return VideoMetadata(
            video_id=video_id,
            raw_title=raw_title,
            clean_title=clean_title(raw_title),
            uploader=uploader,
            duration_seconds=duration,
            thumbnail_url=thumbnail,
            formats=formats,
        )

    def _extract_formats(self, raw_formats: List[Dict[str, Any]]) -> List[StreamFormat]:
        extracted: List[StreamFormat] = []
        for f in raw_formats:
            fmt = self._parse_single_format(f)
            if fmt:
                extracted.append(fmt)
        return extracted

    @staticmethod
    def _parse_resolution(f: Dict[str, Any]) -> Optional[str]:
        if f.get("format_note"):
            return str(f["format_note"])
        height = f.get("height")
        return f"{height}p" if height else None

    @staticmethod
    def _parse_bitrate(f: Dict[str, Any]) -> Optional[int]:
        val = f.get("tbr") or f.get("abr")
        return int(val) * 1000 if val else None

    def _parse_single_format(self, f: Dict[str, Any]) -> Optional[StreamFormat]:
        url = f.get("url")
        if not url:
            return None

        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        filesize = f.get("filesize") or f.get("filesize_approx")

        return StreamFormat(
            format_id=str(f.get("format_id", "")),
            extension=f.get("ext", "mp4"),
            url=url,
            bitrate=self._parse_bitrate(f),
            resolution=self._parse_resolution(f),
            is_video=(vcodec != "none"),
            is_audio=(acodec != "none"),
            filesize_estimate=filesize,
        )

