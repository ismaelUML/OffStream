"""Script de empaquetado autónomo para Windows (OffStream.exe).
Genera una distribución portable sin dependencias externas de Python.
"""
import argparse
import os
import shutil
import sys
import zipfile
from pathlib import Path


def _copy_browser_extension(dist_dir: Path, repo_root: Path) -> None:
    """Copia la extensión de navegador empaquetada junto al ejecutable."""
    src_ext = repo_root / "clients" / "browser-extension"
    dest_ext = dist_dir / "browser-extension"
    if src_ext.exists():
        if dest_ext.exists():
            shutil.rmtree(dest_ext)
        shutil.copytree(src_ext, dest_ext)


def _create_portable_readme(dist_dir: Path) -> None:
    """Crea la guía rápida de usuario en la raíz del paquete portable."""
    readme_path = dist_dir / "LEEME_PRIMERO.txt"
    content = (
        "==============================================================\n"
        " OffStream Desktop - Edicion Portable para Windows\n"
        "==============================================================\n\n"
        "1. EJECUTAR EL PROGRAMA:\n"
        "   Haz doble clic sobre 'OffStream.exe'.\n"
        "   No requiere tener Python instalado ni configurar variables de entorno.\n\n"
        "2. INSTALAR LA EXTENSION DE NAVEGADOR (Chrome / Edge / Brave):\n"
        "   a) Abre tu navegador y escribe en la barra de direcciones:\n"
        "      chrome://extensions  (o edge://extensions)\n"
        "   b) Activa la opcion 'Modo de desarrollador' (arriba a la derecha).\n"
        "   c) Haz clic en el boton 'Cargar descomprimida' (Load unpacked).\n"
        "   d) Selecciona la carpeta 'browser-extension' incluida en este directorio.\n"
        "   e) Fija el icono de OffStream a tu barra de herramientas.\n\n"
        "3. CARPETA DE DESCARGAS:\n"
        "   Tus archivos se guardaran automaticamente en:\n"
        "   Descargas/yt-global-dl/music/  (audios MP3 con etiquetas de artista y titulo)\n"
        "   Descargas/yt-global-dl/videos/ (videos MP4)\n\n"
        "==============================================================\n"
    )
    readme_path.write_text(content, encoding="utf-8")


def _create_zip_archive(dist_dir: Path, zip_output_path: Path) -> None:
    """Comprime el directorio portable en un archivo .zip listo para publicar."""
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(dist_dir.parent)
                zipf.write(file_path, arcname)


def build(onefile: bool = False, make_zip: bool = True) -> None:
    """Ejecuta el ciclo de compilación con PyInstaller."""
    try:
        import PyInstaller.__main__
    except ImportError:
        print("[ERROR] PyInstaller no esta instalado. Ejecuta: pip install pyinstaller")
        sys.exit(1)

    repo_root = Path(__file__).resolve().parent.parent
    entry_point = repo_root / "main.py"
    dist_base = repo_root / "dist"
    build_base = repo_root / "build"

    args = [
        str(entry_point),
        "--name=OffStream",
        "--noconsole",
        "--clean",
        "--noconfirm",
        f"--distpath={dist_base}",
        f"--workpath={build_base}",
        "--collect-all=customtkinter",
        "--collect-all=imageio_ffmpeg",
        "--collect-all=uvicorn",
        "--collect-submodules=adapters",
        "--collect-submodules=core",
        "--collect-submodules=domain",
        "--collect-submodules=ports",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    print(f"[*] Iniciando compilacion de OffStream con PyInstaller ({'onefile' if onefile else 'onedir'})...")
    PyInstaller.__main__.run(args)

    target_dist = dist_base / "OffStream" if not onefile else dist_base
    _copy_browser_extension(target_dist, repo_root)
    _create_portable_readme(target_dist)

    if make_zip and not onefile:
        zip_path = dist_base / "OffStream-Windows-Portable.zip"
        print(f"[*] Generando archivo comprimido {zip_path.name}...")
        _create_zip_archive(target_dist, zip_path)

    print(f"[OK] Compilacion completada con exito en: {target_dist}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Empaquetador de OffStream para Windows.")
    parser.add_argument("--onefile", action="store_true", help="Generar un unico ejecutable autocontenido.")
    parser.add_argument("--no-zip", action="store_true", help="Omitir la compresion .zip final.")
    cli_args = parser.parse_args()

    build(onefile=cli_args.onefile, make_zip=not cli_args.no_zip)
