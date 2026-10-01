# Funciones auxiliares puras para la GUI.
# Las sacamos del monolito de tkinter para poder testear formateos y calculos de pipeline
# en pytest sin tener que levantar una ventana de Tkinter que cuelgue el servidor de CI.
from typing import List, Tuple


def _format_duration(seconds: int) -> str:
    """Convierte segundos a formato MM:SS o HH:MM:SS para no marear al usuario con numeros crudos."""
    if seconds <= 0:
        return "0:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _truncate_title(title: str, max_chars: int = 46) -> str:
    """Recorta titulos kilometricos de YouTube para que no revienten el layout de las tarjetas en la biblioteca."""
    if len(title) <= max_chars:
        return title
    return title[: max_chars - 3].rstrip() + "..."


def _format_active_status(active_jobs: list) -> Tuple[float, str, str]:
    latest = active_jobs[-1]
    pct = latest.get("progress_percentage", 0.0)
    status = latest.get("status", "pending")
    return (
        pct / 100.0,
        f"[{status.upper()}] {pct:.0f}% ({len(active_jobs)} active in queue)",
        "#60a5fa",
    )


def _format_idle_status(jobs: list, is_active_bar: bool) -> Tuple[float, str, str]:
    if not is_active_bar:
        return 0.0, "Ready for download", "#a1a1aa"
    for j in reversed(jobs):
        if j.get("status") == "failed":
            return 1.0, f"✗ Last download failed: {j.get('error_message')}", "#f87171"
        if j.get("status") == "completed":
            break
    return 1.0, "✓ Ready (All downloads finished)", "#34d399"


def _compute_pipeline_display(jobs: list, is_active_bar: bool) -> Tuple[float, str, str]:
    """Calcula el estado visual de la UI (progreso, texto, color) segun los jobs del pipeline."""
    active = [j for j in jobs if j.get("status") in ("pending", "resolving", "downloading", "muxing")]
    if active:
        return _format_active_status(active)
    return _format_idle_status(jobs, is_active_bar)
