"""Media title sanitization and filesystem name formatting.
Single Responsibility: Transform noisy YouTube titles into clean filenames.
Cyclomatic Complexity target: M <= 5.
"""
import re

_NOISE_PATTERNS = [
    re.compile(r"\[\s*(?:official\s+video|official\s+audio|official\s+music\s+video|4k|hd|1080p|60fps|remastered|lyric\s+video|lyrics)\s*\]", re.IGNORECASE),
    re.compile(r"\(\s*(?:official\s+video|official\s+audio|official\s+music\s+video|4k|hd|1080p|60fps|remastered|lyric\s+video|lyrics)\s*\)", re.IGNORECASE),
    re.compile(r"\|\s*(?:official\s+video|official\s+audio|4k|hd)\s*$", re.IGNORECASE),
]

_INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_title(raw_title: str) -> str:
    """Remove video noise tags like (Official Video), [4K], etc."""
    cleaned = raw_title
    for pattern in _NOISE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    # Collapse multiple spaces and trim
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else raw_title.strip()


def sanitize_filename(name: str, max_length: int = 120) -> str:
    """Convert any title string into a safe, valid Windows filename."""
    safe_name = _INVALID_FS_CHARS.sub("_", name)
    safe_name = re.sub(r"_+", "_", safe_name).strip(" ._")
    if not safe_name:
        safe_name = "media_item"
    return safe_name[:max_length]
