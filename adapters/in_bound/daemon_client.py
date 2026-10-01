# Cliente HTTP y control del subproceso daemon desacoplado de la UI.
# Mandar comandos de red y de OS aca evita que el codigo de widgets de Tkinter
# se mezcle con llamadas a subprocess, requests y sockets de Windows.
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
import requests
from domain.models import DownloadRecord

API_BASE = "http://127.0.0.1:8765"


def check_daemon_health(api_base: str = API_BASE) -> bool:
    """Verifica si el daemon local uvicorn esta vivo y respondiendo /health."""
    try:
        r = requests.get(f"{api_base}/health", timeout=0.8)
        return r.status_code == 200
    except Exception:
        return False


def start_daemon_process() -> None:
    """Arranca el daemon en segundo plano suprimiendo la consola negra de Windows."""
    # En modo congelado (.exe), sys.executable ya es OffStream.exe; le pasamos --daemon directamente.
    if getattr(sys, "frozen", False):
        subprocess.Popen(
            [sys.executable, "--daemon"],
            creationflags=0x08000000,
        )
        return
    repo_root = Path(__file__).resolve().parents[2]
    main_script = str(repo_root / "main.py")
    # Flag 0x08000000 (CREATE_NO_WINDOW) para no espantar al usuario con un flash de cmd.exe
    subprocess.Popen(
        [sys.executable, main_script, "--daemon"],
        cwd=str(repo_root),
        creationflags=0x08000000,
    )


def stop_daemon_process() -> None:
    """Rastrea el socket del puerto 8765 y liquida el arbol de procesos del daemon."""
    cmd = (
        "$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue; "
        "if ($conn) { foreach ($c in $conn) { taskkill.exe /F /T /PID $c.OwningProcess 2>$null } }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], creationflags=0x08000000)


def setup_windows_autostart() -> None:
    """Invoca el script batch para registrar el acceso directo en shell:startup."""
    repo_root = Path(__file__).resolve().parents[2]
    bat_script = str(repo_root / "scripts" / "windows" / "install_autostart.bat")
    subprocess.run(["cmd", "/c", bat_script], cwd=str(repo_root))


def fetch_history(query: Optional[str] = None, api_base: str = API_BASE) -> List[DownloadRecord]:
    """Obtiene los registros de descarga de la API HTTP local."""
    try:
        params = {"limit": 100}
        if query:
            params["query"] = query
        res = requests.get(f"{api_base}/api/history", params=params, timeout=1.5)
        if res.status_code == 200:
            return [
                DownloadRecord(
                    id=r["id"],
                    video_id=r["video_id"],
                    title=r["title"],
                    channel=r["channel"],
                    duration_seconds=r["duration_seconds"],
                    created_at=r["created_at"],
                    file_path=r["file_path"],
                    media_kind=r.get("media_kind", "video"),
                )
                for r in res.json()
            ]
    except Exception:
        pass
    return []


def delete_history_record(record_id: Optional[int], api_base: str = API_BASE) -> bool:
    """Solicita a la API eliminar un registro del historial."""
    if not record_id:
        return False
    try:
        res = requests.delete(f"{api_base}/api/history/{record_id}", timeout=2.0)
        return res.status_code == 200
    except Exception:
        return False


def submit_download_job(url: str, kind: str, quality: str, api_base: str = API_BASE) -> dict:
    """Encola un nuevo trabajo de descarga en el daemon local."""
    res = requests.post(
        f"{api_base}/api/download",
        json={"url": url, "kind": kind, "quality": quality},
        timeout=5,
    )
    res.raise_for_status()
    return res.json()
