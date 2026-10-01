# Punto de entrada universal de OffStream / yt-global-dl.
# Discrimina si arrancamos como daemon silencioso en background (para la extensión de navegador),
# como interfaz gráfica de escritorio con CustomTkinter, o como herramienta CLI interactiva.
import os
import sys
import traceback
from adapters.in_bound.cli import run_cli
from adapters.in_bound.server import start_server

# Cuando Windows ejecuta mediante pythonw.exe (modo background sin consola),
# asigna sys.stdout y sys.stderr como None. Cualquier llamada inocente a print() o
# log de librerías lanzaría un AttributeError silencioso y mataría el proceso sin dejar rastro.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


def _dispatch_mode(args: list) -> None:
    # Si no vienen argumentos (ej: doble click en OffStream.exe o script de inicio):
    # Si estamos empaquetados como binario congelado, abrimos la GUI de escritorio directamente.
    # Si se ejecuta como script sin argumentos en desarrollo, levanta el daemon para la extensión.
    if not args:
        if getattr(sys, "frozen", False):
            from adapters.in_bound.gui import launch_gui
            launch_gui()
            return
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
        # En modo pythonw sin consola, si algo explota Windows mata el proceso en silencio total.
        # Volcar el stacktrace a daemon_crash.log es la única forma de no volverse loco depurando.
        with open("daemon_crash.log", "a") as f:
            traceback.print_exc(file=f)


if __name__ == "__main__":
    main()
