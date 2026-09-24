"""Main entrypoint for yt-global-dl.
Supports running as a background daemon (for the extension) or as a CLI.
"""
import sys
from adapters.in_bound.cli import run_cli
from adapters.in_bound.server import start_server


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "--daemon":
        # Interactive CLI mode
        run_cli()
    else:
        # Default: Start local daemon for browser extension
        print("=" * 60)
        print("  YT Global DL - Local Companion Daemon")
        print("  Architecture: Hexagonal (Ports & Adapters) + SOLID")
        print("  Status: Listening on http://127.0.0.1:8765")
        print("=" * 60)
        start_server()


if __name__ == "__main__":
    main()
