# A la gente le encanta pegar links con tracking, timestamps (?t=42s),
# listas de reproducción infinitas o links recortados de youtu.be.
# Esta porquería de regex solo busca los benditos 11 caracteres del video y descarta el resto.
import re
from typing import Optional
from domain.exceptions import InvalidVideoURLError

# YouTube usa exactamente 11 caracteres alfanuméricos (más guiones y guiones bajos).
_YT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{11}$")
_URL_PATTERNS = [
    re.compile(r"(?:v=|\/v\/|embed\/|shorts\/)([a-zA-Z0-9_-]{11})"),
    re.compile(r"youtu\.be\/([a-zA-Z0-9_-]{11})"),
]


def extract_video_id(url_or_id: str) -> str:
    # Si el usuario ya nos pasó el ID pelado de 11 caracteres, nos ahorramos el regex.
    clean_input = url_or_id.strip()

    if _YT_ID_REGEX.match(clean_input):
        return clean_input

    for pattern in _URL_PATTERNS:
        match = pattern.search(clean_input)
        if match:
            return match.group(1)

    raise InvalidVideoURLError(f"Cannot extract valid YouTube video ID from: {url_or_id}")


def build_canonical_url(video_id: str) -> str:
    # URL canónica y limpia, sin basura de telemetría de Google.
    return f"https://www.youtube.com/watch?v={video_id}"
