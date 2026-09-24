"""InnerTube API Stream Resolver (Algorithm "Code Finder").
Implements StreamResolverPort.
Connects directly to YouTube's internal InnerTube JSON endpoint to extract
streaming data, bitrates, and direct stream URLs without external binaries.
"""
from typing import Any, Dict, List
import requests
from core.title_cleaner import clean_title
from core.url_parser import extract_video_id
from domain.exceptions import ResolutionError
from domain.models import StreamFormat, VideoMetadata

_INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/player"
_ANDROID_CLIENT_CONTEXT = {
    "context": {
        "client": {
            "clientName": "ANDROID",
            "clientVersion": "19.09.37",
            "androidSdkVersion": 30,
            "hl": "en",
            "gl": "US",
        }
    }
}


class InnerTubeResolver:
    """Discovers video metadata and stream manifests via the InnerTube API."""

    def __init__(self, timeout: int = 15) -> None:
        self._session = requests.Session()
        self._timeout = timeout

    def can_handle(self, url_or_id: str) -> bool:
        try:
            extract_video_id(url_or_id)
            return True
        except Exception:
            return False

    def resolve(self, url_or_id: str) -> VideoMetadata:
        video_id = extract_video_id(url_or_id)
        payload = {**_ANDROID_CLIENT_CONTEXT, "videoId": video_id}

        try:
            resp = self._session.post(_INNERTUBE_URL, json=payload, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as err:
            raise ResolutionError(f"InnerTube request failed: {err}")

        playability = data.get("playabilityStatus", {})
        if playability.get("status") != "OK":
            reason = playability.get("reason", "Video unavailable or restricted.")
            raise ResolutionError(f"InnerTube playability error: {reason}")

        return self._parse_metadata(video_id, data)

    def _parse_metadata(self, video_id: str, data: Dict[str, Any]) -> VideoMetadata:
        details = data.get("videoDetails", {})
        raw_title = details.get("title", f"video_{video_id}")
        uploader = details.get("author", "Unknown Artist")
        duration = int(details.get("lengthSeconds", 0))

        thumbnails = details.get("thumbnail", {}).get("thumbnails", [])
        thumb_url = thumbnails[-1]["url"] if thumbnails else ""

        streaming_data = data.get("streamingData", {})
        formats = self._extract_formats(streaming_data)

        if not formats:
            raise ResolutionError("InnerTube returned no direct playable stream URLs.")

        return VideoMetadata(
            video_id=video_id,
            raw_title=raw_title,
            clean_title=clean_title(raw_title),
            uploader=uploader,
            duration_seconds=duration,
            thumbnail_url=thumb_url,
            formats=formats,
        )

    def _extract_formats(self, streaming_data: Dict[str, Any]) -> List[StreamFormat]:
        raw_list = streaming_data.get("adaptiveFormats", []) + streaming_data.get("formats", [])
        extracted: List[StreamFormat] = []

        for item in raw_list:
            fmt = self._parse_single_item(item)
            if fmt:
                extracted.append(fmt)

        return extracted

    def _parse_single_item(self, item: Dict[str, Any]) -> Optional[StreamFormat]:
        direct_url = item.get("url")
        if not direct_url:
            return None

        mime_type = item.get("mimeType", "")
        is_audio = "audio" in mime_type
        is_video = "video" in mime_type
        ext = "m4a" if is_audio and "mp4" in mime_type else ("webm" if "webm" in mime_type else "mp4")

        return StreamFormat(
            format_id=str(item.get("itag", "unknown")),
            extension=ext,
            url=direct_url,
            bitrate=item.get("bitrate"),
            resolution=item.get("qualityLabel"),
            is_video=is_video,
            is_audio=is_audio,
            filesize_estimate=int(item.get("contentLength", 0)) or None,
        )

