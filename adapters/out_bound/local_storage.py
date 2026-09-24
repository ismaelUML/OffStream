# Manejo del sistema de archivos local.
# Centraliza dónde guardamos los videos y la música sin ensuciarle el escritorio al usuario,
# y maneja los archivos temporales para que dos descargas simultáneas no se pisen.
import os
import shutil
import tempfile
from pathlib import Path
from typing import List


class LocalStorageAdapter:
    def __init__(self, base_output_dir: str = "") -> None:
        if not base_output_dir:
            # En Windows Path.home() resuelve C:\Users\Nombre.
            # Tiramos todo a Downloads/yt-global-dl para que el usuario encuentre sus cosas
            # sin tener que adivinar dónde carajo quedó guardado el archivo.
            home = Path.home()
            self._base_dir = home / "Downloads" / "yt-global-dl"
        else:
            self._base_dir = Path(base_output_dir)

        self._video_dir = self._base_dir / "videos"
        self._audio_dir = self._base_dir / "music"
        self._temp_dir = Path(tempfile.gettempdir()) / "yt_global_dl_temp"

        self._initialize_directories()

    def _initialize_directories(self) -> None:
        # Creamos las carpetas si no existen; si ya existen, no chilla
        self._video_dir.mkdir(parents=True, exist_ok=True)
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def get_output_path(self, filename: str, is_audio: bool = False) -> str:
        target_dir = self._audio_dir if is_audio else self._video_dir
        return str(target_dir / filename)

    def create_temp_path(self, prefix: str, ext: str) -> str:
        # Metemos el PID del proceso y bytes aleatorios para que dos hilos
        # descargando al mismo tiempo no se pisen el mismo archivo temporal ni de casualidad.
        clean_ext = ext.lstrip(".")
        filename = f"{prefix}_{os.getpid()}_{os.urandom(4).hex()}.{clean_ext}"
        return str(self._temp_dir / filename)

    def remove_files(self, paths: List[str]) -> None:
        for p in paths:
            if not p:
                continue
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass
