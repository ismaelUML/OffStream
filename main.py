"""Main entrypoint for yt-global-dl.
Supports running as a background daemon (for the extension) or as a CLI.
"""
import os
import sys
from adapters.in_bound.cli import run_cli
from adapters.in_bound.server import start_server

# Cuando Windows ejecuta mediante pythonw.exe (modo background sin consola),
# asigna sys.stdout y sys.stderr como None. Cualquier llamada inocente a print() o
# log de librerías lanzaría un AttributeError silencioso y mataría el proceso sin dejar rastro.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import traceback

def _dispatch_mode(args: list) -> None:
    if not args:
        start_server()
        return
    mode = args[0]
    if mode == "--gui":
        from adapters.in_bound.gui import launch_gui
        launch_gui()
    elif mode == "--daemon":
        start_server()
    else:
        run_cli()


def main() -> None:
    try:
        _dispatch_mode(sys.argv[1:])
    except Exception:
        with open("daemon_crash.log", "a") as f:
            traceback.print_exc(file=f)



if __name__ == "__main__":
    main()
