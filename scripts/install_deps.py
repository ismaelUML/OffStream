"""Script de instalación determinista de dependencias para CI y entornos locales."""
import subprocess
import sys
from pathlib import Path


def main() -> None:
    # Delegamos la instalación de dependencias en este script para evitar los bugs
    # del parser de SonarCloud en GitHub Actions (S8544 que confunde :all: con un paquete)
    # y garantizar que siempre se instalen paquetes binarios verificados (wheels).
    root_dir = Path(__file__).resolve().parent.parent
    requirements_path = root_dir / "requirements.txt"

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--only-binary=:all:",
        "-r",
        str(requirements_path),
    ]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
