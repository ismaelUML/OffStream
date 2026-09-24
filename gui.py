"""Desktop Dashboard for YT Global DL.
Built with CustomTkinter for a sleek, modern, user-friendly interface.
"""
import os
import subprocess
import threading
import time
from pathlib import Path
import customtkinter as ctk
import requests

API_BASE = "http://127.0.0.1:8765"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class YtGlobalDlApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YT Global DL — Media Companion")
        self.geometry("540x580")
        self.resizable(False, False)

        self._downloads_dir = Path.home() / "Downloads" / "yt-global-dl"
        self._video_dir = self._downloads_dir / "videos"
        self._music_dir = self._downloads_dir / "music"
        self._active_job_id = None

        self._build_ui()
        self._start_status_poller()

    def _build_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self, corner_radius=12, fg_color="#18181b")
        header.pack(fill="x", padx=16, pady=(16, 10))

        title_label = ctk.CTkLabel(
            header,
            text="YT Global DL",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff",
        )
        title_label.pack(side="left", padx=16, pady=12)

        self.status_badge = ctk.CTkLabel(
            header,
            text="Checking...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a1a1aa",
            fg_color="#27272a",
            corner_radius=12,
            padx=12,
            pady=4,
        )
        self.status_badge.pack(side="right", padx=16, pady=12)

        # Quick Downloader Card
        card = ctk.CTkFrame(self, corner_radius=12, fg_color="#18181b")
        card.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            card,
            text="QUICK MEDIA DOWNLOAD",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a1a1aa",
        ).pack(anchor="w", padx=16, pady=(14, 6))

        # URL Input Row
        url_row = ctk.CTkFrame(card, fg_color="transparent")
        url_row.pack(fill="x", padx=16, pady=(0, 10))

        self.url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="Paste YouTube URL or Video ID...",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = ctk.CTkButton(
            url_row,
            text="📋 Paste",
            width=70,
            height=38,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._paste_clipboard,
        )
        paste_btn.pack(side="right")

        # Format Selection
        self.format_seg = ctk.CTkSegmentedButton(
            card,
            values=["🎬 1080p+ Video", "🎧 Clean MP3", "⚡ 720p Fast"],
            height=34,
        )
        self.format_seg.set("🎬 1080p+ Video")
        self.format_seg.pack(fill="x", padx=16, pady=(0, 14))

        # Action Button
        self.download_btn = ctk.CTkButton(
            card,
            text="Start Download",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            command=self._on_download_click,
        )
        self.download_btn.pack(fill="x", padx=16, pady=(0, 14))

        # Progress Section
        self.progress_bar = ctk.CTkProgressBar(card, height=8, fg_color="#27272a", progress_color="#8b5cf6")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))

        self.progress_label = ctk.CTkLabel(
            card,
            text="Ready for download",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
        )
        self.progress_label.pack(padx=16, pady=(0, 14))

        # Folder & Controls Card
        bottom_card = ctk.CTkFrame(self, corner_radius=12, fg_color="#18181b")
        bottom_card.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            bottom_card,
            text="OUTPUT DIRECTORIES & CONTROLS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a1a1aa",
        ).pack(anchor="w", padx=16, pady=(12, 8))

        btn_row = ctk.CTkFrame(bottom_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        open_vid_btn = ctk.CTkButton(
            btn_row,
            text="📁 Videos Folder",
            height=34,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=lambda: self._open_folder(self._video_dir),
        )
        open_vid_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        open_mus_btn = ctk.CTkButton(
            btn_row,
            text="🎵 Music Folder",
            height=34,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=lambda: self._open_folder(self._music_dir),
        )
        open_mus_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Daemon toggle row
        daemon_row = ctk.CTkFrame(bottom_card, fg_color="transparent")
        daemon_row.pack(fill="x", padx=16, pady=(0, 12))

        self.daemon_toggle_btn = ctk.CTkButton(
            daemon_row,
            text="Start Daemon",
            height=32,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._toggle_daemon,
        )
        self.daemon_toggle_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        startup_btn = ctk.CTkButton(
            daemon_row,
            text="⚡ Run on Windows Boot",
            height=32,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._setup_autostart,
        )
        startup_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

    def _paste_clipboard(self):
        try:
            text = self.clipboard_get()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text.strip())
        except Exception:
            pass

    def _open_folder(self, folder_path: Path):
        folder_path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(folder_path))

    def _toggle_daemon(self):
        is_online = self._check_daemon_health()
        if is_online:
            subprocess.run(["cmd", "/c", "stop_daemon.bat"], creationflags=0x08000000)
            self._update_status(False)
        else:
            subprocess.Popen(["wscript.exe", "start_silent.vbs"], creationflags=0x08000000)
            time.sleep(1.0)
            self._update_status(self._check_daemon_health())

    def _setup_autostart(self):
        subprocess.run(["cmd", "/c", "install_autostart.bat"])

    def _check_daemon_health(self) -> bool:
        try:
            r = requests.get(f"{API_BASE}/health", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    def _start_status_poller(self):
        def loop():
            while True:
                online = self._check_daemon_health()
                self._update_status(online)
                if self._active_job_id:
                    self._poll_active_job()
                time.sleep(1.5)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()

    def _update_status(self, is_online: bool):
        if is_online:
            self.status_badge.configure(text="● Daemon Online", text_color="#34d399", fg_color="rgba(16, 185, 129, 0.15)")
            self.daemon_toggle_btn.configure(text="Stop Daemon", fg_color="#ef4444", hover_color="#dc2626")
        else:
            self.status_badge.configure(text="○ Daemon Offline", text_color="#f87171", fg_color="rgba(239, 68, 68, 0.15)")
            self.daemon_toggle_btn.configure(text="Start Daemon", fg_color="#10b981", hover_color="#059669")

    def _on_download_click(self):
        url = self.url_entry.get().strip()
        if not url:
            self.progress_label.configure(text="Please paste a valid YouTube URL first.", text_color="#f87171")
            return

        fmt = self.format_seg.get()
        if "MP3" in fmt:
            kind, quality = "audio", "audio_high"
        elif "720p" in fmt:
            kind, quality = "video", "720p"
        else:
            kind, quality = "video", "best"

        # If daemon is offline, start it silently
        if not self._check_daemon_health():
            subprocess.Popen(["wscript.exe", "start_silent.vbs"], creationflags=0x08000000)
            time.sleep(1.2)

        try:
            res = requests.post(
                f"{API_BASE}/api/download",
                json={"url": url, "kind": kind, "quality": quality},
                timeout=5,
            )
            if res.status_code == 200:
                job_data = res.json()
                self._active_job_id = job_data["job_id"]
                self.progress_label.configure(text=f"Queueing Job #{self._active_job_id}...", text_color="#a78bfa")
                self.download_btn.configure(state="disabled")
            else:
                self.progress_label.configure(text=f"Error: {res.text}", text_color="#f87171")
        except Exception as err:
            self.progress_label.configure(text=f"Connection Error: {err}", text_color="#f87171")

    def _poll_active_job(self):
        if not self._active_job_id:
            return

        try:
            r = requests.get(f"{API_BASE}/api/jobs/{self._active_job_id}", timeout=2)
            if r.status_code != 200:
                return

            job = r.json()
            pct = job.get("progress_percentage", 0.0)
            status = job.get("status", "pending")
            self.progress_bar.set(pct / 100.0)

            if status == "completed":
                self.progress_label.configure(
                    text="✓ Finished! Saved to Downloads folder.",
                    text_color="#34d399",
                )
                self._active_job_id = None
                self.download_btn.configure(state="normal")
            elif status == "failed":
                self.progress_label.configure(
                    text=f"✗ Failed: {job.get('error_message')}",
                    text_color="#f87171",
                )
                self._active_job_id = None
                self.download_btn.configure(state="normal")
            else:
                self.progress_label.configure(
                    text=f"[{status.upper()}] {pct:.0f}%",
                    text_color="#60a5fa",
                )
        except Exception:
            pass


if __name__ == "__main__":
    app = YtGlobalDlApp()
    app.mainloop()
