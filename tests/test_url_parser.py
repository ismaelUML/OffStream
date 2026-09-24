"""Unit tests for URL parsing."""
import pytest
from core.url_parser import build_canonical_url, extract_video_id
from domain.exceptions import InvalidVideoURLError


def test_extract_video_id_from_standard_url():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_from_short_url():
    url = "https://youtu.be/dQw4w9WgXcQ?t=42"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_from_shorts():
    url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_direct_id():
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_raises_error():
    with pytest.raises(InvalidVideoURLError):
        extract_video_id("https://vimeo.com/1234567")

    with pytest.raises(InvalidVideoURLError):
        extract_video_id("too_short")


def test_build_canonical_url():
    assert build_canonical_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
