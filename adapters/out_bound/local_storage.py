# Manejo del sistema de archivos local.
# Centraliza dónde guardamos los videos y la música sin ensuciarle el escritorio al usuario,
# y maneja los archivos temporales para que dos descargas simultáneas no se pisen.
import ctypes
import os
import shutil
import sys
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
        self._configure_windows_folder(self._audio_dir, "Music")
        self._configure_windows_folder(self._video_dir, "Videos")

    def _configure_windows_folder(self, folder_path: Path, folder_type: str) -> None:
        # En Windows, el Explorador de Archivos muestra carpetas genéricas por defecto.
        # Si le plantamos un desktop.ini con FolderType=Music o Videos, Windows abre la carpeta
        # mostrando columnas útiles como Artista, Duración o Resolución en vez de sólo 'Fecha de modificación'.
        # Trampa de Windows: el archivo desktop.ini DEBE tener atributos Hidden+System (0x06),
        # y la carpeta padre DEBE tener el bit ReadOnly (0x01); si falta alguno, Explorer lo ignora como si nada.
        if sys.platform != "win32":
            return
        ini_path = folder_path / "desktop.ini"
        if not ini_path.exists():
            content = f"[ViewState]\r\nFolderType={folder_type}\r\nLogo=\r\n"
            try:
                ini_path.write_text(content, encoding="utf-8")
                # 0x06 = FILE_ATTRIBUTE_HIDDEN (0x02) | FILE_ATTRIBUTE_SYSTEM (0x04)
                # 0x01 = FILE_ATTRIBUTE_READONLY (habilita la lectura de desktop.ini en el Shell de Windows)
                ctypes.windll.kernel32.SetFileAttributesW(str(ini_path), 0x06)
                ctypes.windll.kernel32.SetFileAttributesW(str(folder_path), 0x01)
            except (OSError, AttributeError):
                pass

    def get_output_path(self, filename: str, is_audio: bool = False) -> str:
        target_dir = self._audio_dir if is_audio else self._video_dir
        dest = target_dir / filename

        # Si no existe, lo usamos directo sin tocar nada
        if not dest.exists():
            return str(dest)

        # Si ya existe un archivo con el mismo nombre exacto, le encajamos un sufijo (1), (2)...
        # No queremos que el usuario pierda un archivo que ya tenía guardado por un pisotón silencioso.
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = target_dir / f"{stem} ({counter}){suffix}"
            counter += 1

        return str(dest)

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
