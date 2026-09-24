"""Unit tests for stream selection strategies."""
import pytest
from core.stream_selector import select_best_audio_stream, select_video_stream
from domain.exceptions import StreamNotFoundError
from domain.models import QualityTarget, StreamFormat


def test_select_best_audio_stream():
    formats = [
        StreamFormat(format_id="140", extension="m4a", url="http://1", bitrate=128000, is_audio=True, is_video=False),
        StreamFormat(format_id="251", extension="webm", url="http://2", bitrate=160000, is_audio=True, is_video=False),
        StreamFormat(format_id="137", extension="mp4", url="http://3", bitrate=2500000, is_audio=False, is_video=True),
    ]
    best_audio = select_best_audio_stream(formats)
    assert best_audio.format_id == "251"
    assert best_audio.bitrate == 160000


def test_select_audio_empty_raises_error():
    formats = [
        StreamFormat(format_id="137", extension="mp4", url="http://3", bitrate=2500000, is_audio=False, is_video=True),
    ]
    with pytest.raises(StreamNotFoundError):
        select_best_audio_stream(formats)


def test_select_video_stream_720p():
    formats = [
        StreamFormat(format_id="137", extension="mp4", url="http://1", resolution="1080p", bitrate=3000000, is_video=True),
        StreamFormat(format_id="136", extension="mp4", url="http://2", resolution="720p", bitrate=1500000, is_video=True),
    ]
    selected = select_video_stream(formats, QualityTarget.P720)
    assert selected.format_id == "136"
    assert selected.resolution == "720p"
