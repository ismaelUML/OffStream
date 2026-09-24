"""Stream Selection Strategy.
Single Responsibility: Find best matching streams based on requested quality targets.
Complexity Target: M <= 4.
"""
from typing import List, Optional
from domain.exceptions import StreamNotFoundError
from domain.models import QualityTarget, StreamFormat


def select_best_audio_stream(formats: List[StreamFormat]) -> StreamFormat:
    """Find the highest bitrate audio stream."""
    audio_candidates = [f for f in formats if f.is_audio]
    if not audio_candidates:
        raise StreamNotFoundError("No audio stream available for this media.")
    return max(audio_candidates, key=_get_bitrate)


def select_video_stream(formats: List[StreamFormat], quality: QualityTarget) -> StreamFormat:
    """Find optimal video stream matching quality target."""
    video_candidates = [f for f in formats if f.is_video]
    if not video_candidates:
        raise StreamNotFoundError("No video stream available for this media.")

    if quality == QualityTarget.P720:
        match = _find_720p_stream(video_candidates)
        if match:
            return match

    return max(video_candidates, key=_get_bitrate)


def _find_720p_stream(streams: List[StreamFormat]) -> Optional[StreamFormat]:
    for stream in streams:
        if stream.resolution and "720" in stream.resolution:
            return stream
    return None


def _get_bitrate(stream: StreamFormat) -> int:
    return stream.bitrate or 0
