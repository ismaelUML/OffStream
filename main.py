"""Main entrypoint for yt-global-dl.
Supports running as a background daemon (for the extension) or as a CLI.
"""
import os
import sys
from adapters.in_bound.cli import run_cli
from adapters.in_bound.server import start_server

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")



import traceback

def main():
    try:
        if len(sys.argv) > 1 and sys.argv[1] != "--daemon":
            run_cli()
        else:
            start_server()
    except Exception:
        with open("daemon_crash.log", "a") as f:
            traceback.print_exc(file=f)



if __name__ == "__main__":
    main()
