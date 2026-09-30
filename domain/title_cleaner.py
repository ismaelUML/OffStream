# Los títulos de YouTube son un basurero de SEO: "[OFFICIAL VIDEO HD 4K 60FPS]".
# Si guardamos los archivos con esos nombres, tu carpeta de descargas da pena.
# Además, Windows se atraganta y revienta si un archivo tiene caracteres como : / \ ? * < > |
import re

# Basura publicitaria y de formato típica que ensucia los títulos
_NOISE_TOKENS = r"(?:official\s+(?:music\s+)?video|official\s+audio|4k|hd|1080p|60fps|remastered|lyrics?|audio|video)"

_NOISE_PATTERNS = [
    re.compile(rf"\[(?:\s*{_NOISE_TOKENS}\s*)+\]", re.IGNORECASE),
    re.compile(rf"\((?:\s*{_NOISE_TOKENS}\s*)+\)", re.IGNORECASE),
    re.compile(rf"\|\s*{_NOISE_TOKENS}\s*$", re.IGNORECASE),
]

_INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_title(raw_title: str) -> str:
    # Barremos los corchetes y paréntesis molestos sin romper el nombre real de la canción
    cleaned = raw_title
    for pattern in _NOISE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else raw_title.strip()


def sanitize_filename(name: str, max_length: int = 120) -> str:
    # Reemplazamos cualquier carácter que Windows odia por guiones bajos.
    # Y acortamos a 120 caracteres porque MAX_PATH en Windows sigue dando pesadillas.
    safe_name = _INVALID_FS_CHARS.sub("_", name)
    safe_name = re.sub(r"_+", "_", safe_name).strip(" ._")
    if not safe_name:
        safe_name = "media_item"
    return safe_name[:max_length]
