# OffStream

A local, decoupled media downloader and browser companion built with Hexagonal Architecture.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-30%2F30_passed-success.svg)](tests/)

---

## Quick Start

### 1. Requirements & Setup
Requires Python 3.11+ and Windows 10/11 (FFmpeg is bundled automatically via `imageio-ffmpeg`).

```bash
git clone https://github.com/ismaelUML/OffStream.git
cd OffStream

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the Local Daemon
```bash
python main.py
# Runs on http://127.0.0.1:8765
```

For invisible background execution on Windows without an open terminal window, double-click `start_silent.vbs` (or run `install_autostart.bat` to launch on boot).

---

## Usage

### 1. Browser Extension (Chrome / Edge / Brave)
1. Open `chrome://extensions/` and enable **Developer mode**.
2. Click **Load unpacked** and select the `extension/` directory.
3. Pin **OffStream** to your toolbar.
4. On any YouTube or YouTube Music tab, click the icon: the URL is prefilled automatically. Click **Video** or **Audio**.

### 2. Desktop GUI
```bash
python gui.py
```
Or double-click `Launch_Dashboard.bat`.

### 3. CLI
```bash
# Download 1080p video with lossless remux
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080p

# Download audio converted directly to MP3
python main.py -a "https://www.youtube.com/watch?v=VIDEO_ID"

# Inspect stream metadata without downloading
python main.py -i "https://www.youtube.com/watch?v=VIDEO_ID"
```

All files are saved to `Downloads/yt-global-dl/{videos,music}`.

---

## Why This Exists

Web converters (`y2mate`, `savefrom`) are full of spam ads, redirects, and severe bandwidth throttling (~50 KB/s). OffStream runs entirely on your local machine, using 4 parallel chunk streams and local FFmpeg remuxing to complete downloads in 2–3 seconds.

---

## Architecture

OffStream uses **Hexagonal Architecture (Ports and Adapters)** to decouple business logic from external APIs:

- **Domain (`domain/`)**: Pure Python standard library dataclasses (`DownloadJob`, `StreamFormat`). Zero external dependencies.
- **Ports (`ports/`)**: Protocols defining boundaries (`StreamResolverPort`, `MediaDownloaderPort`, `MediaProcessorPort`, `StoragePort`).
- **Core (`core/`)**: Orchestration services (`DownloadManager`, `ResilientStreamResolver`, `TitleSanitizer`). Concurrency is bounded to 3 parallel workers via ThreadPoolExecutor.
- **Adapters (`adapters/`)**: Concrete integrations (FastAPI server, CLI, CustomTkinter GUI, yt-dlp fragment engine, FFmpeg process runner).

---

## Features & Non-Goals

### Features
- **Unthrottled parallel streaming**: Downloads fragments concurrently to bypass YouTube CDN bandwidth limits.
- **Lossless muxing**: Combines 1080p+ video and audio streams using `-c:v copy` without expensive re-encoding.
- **Automatic fallback resolver**: If the primary resolver hits bot challenges, it switches to yt-dlp's cipher solver without failing the job.
- **Title sanitation**: Removes clickbait noise tags (`[OFFICIAL VIDEO]`, `4K`, `60FPS`) and replaces invalid filesystem characters.
- **Windowless Windows execution**: Suppresses subprocess console windows via `CREATE_NO_WINDOW`.

### Non-Goals
- **No cloud SaaS**: OffStream will not be hosted as a public web service; it is strictly a personal local tool.
- **No DOM injection**: OffStream does not inject buttons into YouTube's web components to avoid layout breakage across site updates. It operates exclusively via the extension toolbar popup.
- **No DRM circumvention**: Does not download encrypted, rented, or private member-only streams.
- **No mass crawler**: Not built for archiving entire channels or multi-thousand video playlists.

---

## Tests

Run the unit test suite:

```bash
python -m pytest tests/ -v
```

Complexity and maintainability check:

```bash
python -m radon cc domain ports core adapters -s -a
python -m radon mi domain ports core adapters -s
```

---

## Disclaimer

This software is for personal media backup and educational analysis only. Users are responsible for complying with local copyright laws and platform terms of service.

---

## License

[MIT](LICENSE)
