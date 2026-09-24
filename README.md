# ⚡ OffStream

> **High-Performance, Ad-Free Local Media Companion & Downloader**  
> Built with **Hexagonal Architecture (Ports & Adapters)**, **SOLID Principles**, and **Quantitative Software Engineering Metrics**.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Manifest V3](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-green.svg)](https://developer.chrome.com/docs/extensions/mv3/intro/)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-indigo.svg)](https://customtkinter.tomschimansky.com/)
[![Tests](https://img.shields.io/badge/pytest-17%2F17_passed-success.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 💡 The Problem OffStream Solves

Common web downloaders (`y2mate`, `savefrom`, etc.) are plagued with:
- **Intrusive popups, scam ads, and malicious redirects.**
- **Aggressive CDN rate-limiting** (50 KB/s stream throttles).
- **Fragile browser scrapers** that break as soon as YouTube alters DOM layouts.

**OffStream** runs 100% locally on your machine. It pairs a **Manifest V3 browser toolbar extension** and a **CustomTkinter dark-mode desktop GUI** with a background Python daemon powered by a resilient, unthrottled streaming engine.

---

## 🏛️ 1. Architecture: Hexagonal (Ports & Adapters)

OffStream strictly separates core domain business logic from external delivery mechanisms, APIs, and frameworks.

```
                            +-----------------------------------+
                            |           Driving Ports           |
                            |       (DownloadUseCasePort)       |
                            +-----------------+-----------------+
                                              ^
                 +----------------------------+----------------------------+
                 |                            |                            |
    +------------+-------------+ +------------+-------------+ +------------+-------------+
    |  Inbound Adapter: CLI   | | Inbound Adapter: FastAPI  | | Inbound Adapter: GUI     |
    | (Terminal Interface)     | | (Local Companion Daemon)  | | (CustomTkinter App)      |
    +--------------------------+ +--------------------------+ +--------------------------+
                                              |
                                              v
                            +-----------------------------------+
                            |            Core Domain            |
                            |   - DownloadJob & Status Lifecycle|
                            |   - Title Sanitizer & Safe Filename|
                            |   - Bounded Queue (Little's Law)  |
                            |   - Circuit Breaker Router        |
                            +-----------------+-----------------+
                                              |
                 +----------------------------+----------------------------+
                 |                            |                            |
                 v                            v                            v
    +------------+-------------+ +------------+-------------+ +------------+-------------+
    |    StreamResolverPort    | |    MediaProcessorPort    | |       StoragePort        |
    +------------+-------------+ +------------+-------------+ +------------+-------------+
                 ^                            ^                            ^
                 |                            |                            |
    +------------+-------------+ +------------+-------------+ +------------+-------------+
    | Outbound Adapters:       | | Outbound Adapter:        | | Outbound Adapter:        |
    | - FastMediaDownloader    | | - FFmpegProcessor        | | - LocalStorage           |
    | - InnerTubeResolver (T1) | |   (Lossless remux & MP3) | |   (Downloads folder)     |
    | - YtDlpResolver (T2)     | |   (CREATE_NO_WINDOW safe)| |   (Temp file lifecycle)  |
    +--------------------------+ +--------------------------+ +--------------------------+
```

### Architectural Principles:
1. **Core Domain (`domain/`):** Pure Python standard library dataclasses and exceptions. **Zero external dependencies**.
2. **Ports (`ports/`):** Abstract interfaces (`typing.Protocol`) enforcing the **Interface Segregation Principle (ISP)** and **Dependency Inversion Principle (DIP)**.
3. **Core Services (`core/`):** High-level orchestrators (`DownloadManager`, `ResilientStreamResolver`, `TitleSanitizer`) depending *only* on port abstractions.
4. **Adapters (`adapters/`):** Concrete implementations (FastAPI, yt-dlp native fragment downloader, FFmpeg processor, local filesystem).

---

## 📐 2. Engineering Models & Metrics

| Law / Model | Formula | Application in OffStream |
| :--- | :--- | :--- |
| **Cyclomatic Complexity (McCabe)** | $M = D + 1$ | Every module maintained at **Grade A** ($M \le 6$). Repository average is **$M = 2.11$** via `radon cc`. |
| **Maintainability Index** | $MI = \max\left(0, \frac{171 - 5.2 \ln(V) - 0.23 G - 16.2 \ln(LOC)}{171} \times 100\right)$ | 100% of source files score **Grade A ($MI \ge 75$)** via `radon mi`. |
| **Little's Law (Queueing)** | $L = \lambda \cdot W$ | Bounded concurrency worker pool ($L=3$ workers, max queue 25) prevents CPU thrashing and out-of-memory crashes during multi-gigabyte 4K downloads. |
| **Amdahl's Law** | $S_{lat}(s) = \frac{1}{(1-p) + \frac{p}{s}}$ | Maximizes the parallel speedup ($p$) through 4 concurrent chunk fragments and eliminates remux latency ($1-p$) using stream-copy (`-c:v copy`). |
| **Circuit Breaker** | Resilience Pattern | Tier-1 custom InnerTube resolver automatically trips over to Tier-2 dynamic cipher solving upon YouTube platform updates. |

---

## 🎮 3. How to Use OffStream

### Option A: The Browser Extension (Manifest V3)
1. In your browser (Chrome, Edge, Brave), go to `chrome://extensions/`.
2. Enable **Developer mode** (top right).
3. Click **Load unpacked** and select the `extension/` folder from this repo.
4. Pin the **OffStream (DL)** icon to your toolbar.
5. On any YouTube or YouTube Music tab, click the extension icon: URL is auto-detected — click **🎬 Video** or **🎧 Audio** for an instant download!

### Option B: The Desktop GUI
Run the modern CustomTkinter dashboard:
```bash
python gui.py
```
Or double click `Launch_Dashboard.bat` on Windows.

### Option C: The CLI
```bash
# Inspect available streams
python main.py -i "https://www.youtube.com/watch?v=VIDEO_ID"

# Download 1080p video with lossless audio remux
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080p

# Download highest bitrate audio converted directly to MP3
python main.py -a "https://www.youtube.com/watch?v=VIDEO_ID"
```

---

## ⚡ 4. Installation & Setup (Windows / Linux / macOS)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/ismaelUML/OffStream.git
cd OffStream

python -m venv venv
venv\Scripts\activate       # On Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Silent Windows Autostart (Optional)
To let OffStream's lightweight daemon run silently in the background on system boot:
* Double-click `install_autostart.bat`.
* *To remove*: Double-click `uninstall_autostart.bat`.

---

## 🧪 5. Verification & Tests

Run the full pytest suite:
```bash
python -m pytest tests/ -v
```
*(All 17 unit tests pass in < 0.1s)*

Verify cyclomatic complexity and maintainability index:
```bash
python -m radon cc domain ports core adapters -s -a
python -m radon mi domain ports core adapters -s
```

---

## ⚖️ Disclaimer & Educational Notice

This project is developed for **educational, reverse-engineering, and personal media backup purposes only**. Respect content creators and the Terms of Service of content providers. The authors and contributors do not condone copyright infringement or unauthorized redistribution of copyrighted material.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
