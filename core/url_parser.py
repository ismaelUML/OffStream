"""URL parsing and validation for YouTube media.
Single Responsibility: Extract valid 11-character video IDs from various URL formats.
Cyclomatic Complexity target: M <= 5.
"""
import re
from typing import Optional
from domain.exceptions import InvalidVideoURLError

# Standard patterns for youtube.com, youtu.be, shorts, and music
_YT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")
_URL_PATTERNS = [
    re.compile(r"(?:v=|\/v\/|embed\/|shorts\/)([a-zA-Z0-9_-]{11})"),
    re.compile(r"youtu\.be\/([a-zA-Z0-9_-]{11})"),
]


def extract_video_id(url_or_id: str) -> str:
    """Extract and validate the 11-char YouTube video ID.

    Raises:
        InvalidVideoURLError: If no valid ID is found.
    """
    clean_input = url_or_id.strip()

    if _YT_ID_REGEX.match(clean_input):
        return clean_input

    for pattern in _URL_PATTERNS:
        match = pattern.search(clean_input)
        if match:
            return match.group(1)

    raise InvalidVideoURLError(f"Cannot extract valid YouTube video ID from: {url_or_id}")


def build_canonical_url(video_id: str) -> str:
    """Construct a clean canonical watch URL from an ID."""
    return f"https://www.youtube.com/watch?v={video_id}"
