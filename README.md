# YT Global DL (Stream & Audio Companion)

A modern, virus-free local media pipeline and browser extension built with **Hexagonal Architecture (Ports & Adapters)**, **SOLID principles**, and **quantitative software engineering metrics**.

---

## 🏛️ 1. Architecture: Hexagonal (Ports & Adapters)

```
                            +-----------------------------------+
                            |           Driving Ports           |
                            |       (DownloadUseCasePort)       |
                            +-----------------+-----------------+
                                              ^
                 +----------------------------+----------------------------+
                 |                                                         |
    +------------+-------------+                             +-------------+------------+
    |  Inbound Adapter: CLI   |                             | Inbound Adapter: FastAPI  |
    | (Terminal User Interface)|                             | (Daemon for Browser Ext.) |
    +--------------------------+                             +--------------------------+
                                              |
                                              v
                            +-----------------------------------+
                            |            Core Domain            |
                            |   - DownloadJob & Lifecycle       |
                            |   - Title Sanitizer & Filename    |
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
    | - InnerTubeResolver (T1) | | - FFmpegProcessor        | | - LocalStorage           |
    | - YtDlpResolver (T2)     | |   (Lossless mux & MP3)   | |   (Downloads folder)     |
    +--------------------------+ +--------------------------+ +--------------------------+
```

### Dependency Rules:
1. **Core Domain (`domain/`):** Pure Python standard library dataclasses and exceptions. Zero external dependencies.
2. **Ports (`ports/`):** Pure abstract protocols (`typing.Protocol`) following the **Interface Segregation Principle (ISP)** and **Dependency Inversion Principle (DIP)**.
3. **Core Use Cases (`core/`):** High-level orchestrators (`DownloadManager`, `ResilientStreamResolver`, `TitleSanitizer`) that depend *only* on Port protocols.
4. **Adapters (`adapters/`):** Pluggable concrete implementations (FastAPI, CLI, HTTP downloader, FFmpeg, yt-dlp).

---

## 📐 2. Software Engineering Formulas & Metrics

| Metric / Law | Formula | Realized Implementation |
| :--- | :--- | :--- |
| **Cyclomatic Complexity (McCabe)** | $M = D + 1$ | Every function maintained at **Grade A** ($M \le 6$). Entire repo averages **$M = 2.11$** via `radon cc`. |
| **Maintainability Index** | $MI = \max\left(0, \frac{171 - 5.2 \ln(V) - 0.23 G - 16.2 \ln(LOC)}{171} \times 100\right)$ | All source files score **Grade A ($MI \ge 54$ to $100$)** via `radon mi`. |
| **Little's Law (Queueing)** | $L = \lambda \cdot W$ | Bounded concurrency worker pool ($L=3$ workers, max queue 25) prevents memory thrashing during concurrent downloads. |
| **Amdahl's Law** | $S_{lat}(s) = \frac{1}{(1-p) + \frac{p}{s}}$ | Identifies that chunk parallelization ($p$) is bounded by the sequential remuxing step ($1-p$); uses lossless stream-copy (`-c copy`) in FFmpeg to minimize $(1-p)$. |
| **Circuit Breaker / Fallback** | Resilience Pattern | Tier-1 custom InnerTube resolver automatically trips over to Tier-2 `yt-dlp` upon YouTube bot challenges with zero downtime. |

---

## ⚡ 3. SOLID Principles Enforcement

* **S (Single Responsibility):** 
  * `TitleSanitizer` cleans title noise tags.
  * `UrlParser` extracts 11-char IDs.
  * `StreamSelector` chooses optimal formats.
  * `HttpStreamingDownloader` only handles byte streams.
  * `FFmpegProcessor` only manages media transcoding.
* **O (Open/Closed):** Adding a new media source (e.g. SoundCloud, Twitch) requires implementing `StreamResolverPort` without touching `DownloadManager`.
* **L (Liskov Substitution):** Both `InnerTubeResolver` and `YtDlpResolver` conform transparently to `StreamResolverPort`.
* **I (Interface Segregation):** Small, focused ports (`MediaDownloaderPort`, `MediaProcessorPort`, `StoragePort`) instead of a single giant interface.
* **D (Dependency Inversion):** `DownloadManager` receives port abstractions via dependency injection in its constructor.

---

## 🚀 4. How to Use

### A. Run via CLI
```bash
# Inspect video streams
python main.py -i "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Download high-quality audio (Clean MP3)
python main.py -a "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Download 1080p video (Lossless MP4)
python main.py "https://www.youtube.com/watch?v=jNQXAC9IVRw" -q 1080p
```

### B. Run the Browser Extension (One-Click In-Browser)
1. **Start the local daemon:**
   ```bash
   python main.py
   # Or: python -m adapters.in_bound.server
   ```
   *Runs locally on `http://127.0.0.1:8765`.*

2. **Load Extension in your Browser (Chrome / Edge / Brave):**
   * Open `chrome://extensions/`
   * Enable **Developer mode** (toggle in top right).
   * Click **Load unpacked**.
   * Select the `extension/` directory from this project.
   * Open any YouTube video. You will see the native gradient **Download** button right next to YouTube's Like/Share bar!

---

## 🧪 5. Testing & Verification

Run the test suite:
```bash
python -m pytest tests/ -v
```

Check code complexity and maintainability index:
```bash
python -m radon cc domain ports core adapters -s -a
python -m radon mi domain ports core adapters -s
```
