"""Helper for loading browser cookies or cookies.txt with defensive fallback.
En Windows, Chrome bloquea su base de datos SQLite si el navegador está abierto.
Este módulo provee la configuración y reintentos limpios sin cookies si falla.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _find_existing_cookie_file() -> Optional[str]:
    candidate_paths = [
        Path.cwd() / "cookies.txt",
        Path.home() / "Downloads" / "yt-global-dl" / "cookies.txt",
        Path.home() / ".offstream" / "cookies.txt",
    ]
    for p in candidate_paths:
        try:
            if p.is_file() and p.stat().st_size > 0:
                logger.info(f"Loaded cookies from: {p}")
                return str(p)
        except OSError:
            pass
    return None


def _resolve_browser_name(preferred_browser: Optional[str]) -> Optional[str]:
    browser = preferred_browser or os.getenv("OFFSTREAM_COOKIES_BROWSER")
    return browser.lower().strip() if browser else None


def resolve_cookie_opts(preferred_browser: Optional[str] = None) -> Dict[str, Any]:
    """Busca cookies.txt o configura el navegador solicitado (chrome/firefox/edge/brave)."""
    cookie_file = _find_existing_cookie_file()
    if cookie_file:
        return {"cookiefile": cookie_file}

    browser = _resolve_browser_name(preferred_browser)
    if browser:
        return {"cookiesfrombrowser": (browser, None, None, None)}

    return {}


def is_cookie_error(err: Exception) -> bool:
    """Detecta si la excepción fue provocada por un bloqueo de cookies de Windows/navegador."""
    err_msg = str(err).lower()
    return "cookie" in err_msg or "dpapi" in err_msg or "could not copy" in err_msg
