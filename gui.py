# Panel de control de escritorio en CustomTkinter.
# Para el que no quiere tocar una terminal en su vida ni abrir el navegador:
# pega el link, elige si quiere video o audio, ve la barra avanzar,
# y busca en su biblioteca histórica qué bajó la semana pasada para reproducirlo directo.
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional
import customtkinter as ctk
import requests
from adapters.out_bound.sqlite_history import SqliteHistoryAdapter
from domain.models import DownloadRecord

API_BASE = "http://127.0.0.1:8765"

# Modo oscuro siempre. No queremos quemarle las retinas a nadie a las 3 de la mañana.
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def _format_duration(seconds: int) -> str:
    """Convierte segundos a formato MM:SS o HH:MM:SS."""
    if seconds <= 0:
        return "0:00"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _truncate_title(title: str, max_chars: int = 46) -> str:
    """Recorta títulos largos para que no rompan el layout de las tarjetas."""
    if len(title) <= max_chars:
        return title
    return title[: max_chars - 3].rstrip() + "..."


def _format_active_status(active_jobs: list) -> tuple:
    latest = active_jobs[-1]
    pct = latest.get("progress_percentage", 0.0)
    status = latest.get("status", "pending")
    return (
        pct / 100.0,
        f"[{status.upper()}] {pct:.0f}% ({len(active_jobs)} active in queue)",
        "#60a5fa",
    )


def _format_idle_status(jobs: list, is_active_bar: bool) -> tuple:
    if not is_active_bar:
        return 0.0, "Ready for download", "#a1a1aa"
    for j in reversed(jobs):
        if j.get("status") == "failed":
            return 1.0, f"✗ Last download failed: {j.get('error_message')}", "#f87171"
        if j.get("status") == "completed":
            break
    return 1.0, "✓ Ready (All downloads finished)", "#34d399"


def _compute_pipeline_display(jobs: list, is_active_bar: bool) -> tuple:
    """Calcula el estado visual de la UI (progreso, texto, color) según los jobs del pipeline."""
    active = [j for j in jobs if j.get("status") in ("pending", "resolving", "downloading", "muxing")]
    if active:
        return _format_active_status(active)
    return _format_idle_status(jobs, is_active_bar)


class YtGlobalDlApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YT Global DL — Media Companion")
        self.geometry("620x680")
        self.minsize(580, 600)

        self._downloads_dir = Path.home() / "Downloads" / "yt-global-dl"
        self._video_dir = self._downloads_dir / "videos"
        self._music_dir = self._downloads_dir / "music"
        self._history_adapter = SqliteHistoryAdapter()

        self._build_ui()
        self._refresh_library()
        self._start_status_poller()

    def _build_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self, corner_radius=12, fg_color="#18181b")
        header.pack(fill="x", padx=16, pady=(16, 8))

        title_label = ctk.CTkLabel(
            header,
            text="OffStream / YT Global DL",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff",
        )
        title_label.pack(side="left", padx=16, pady=10)

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
        self.status_badge.pack(side="right", padx=16, pady=10)

        # Tabview
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color="#18181b",
            segmented_button_selected_color="#7c3aed",
            segmented_button_selected_hover_color="#6d28d9",
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        tab_dl = self.tabview.add("⬇ Descargas")
        tab_lib = self.tabview.add("📚 Biblioteca / Historial")

        self._build_downloads_tab(tab_dl)
        self._build_library_tab(tab_lib)

    def _build_downloads_tab(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#121214")
        card.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(
            card,
            text="NUEVA DESCARGA",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a1a1aa",
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # URL Input Row
        url_row = ctk.CTkFrame(card, fg_color="transparent")
        url_row.pack(fill="x", padx=14, pady=(0, 10))

        self.url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="Pegar URL de YouTube o ID de video...",
            height=38,
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = ctk.CTkButton(
            url_row,
            text="📋 Pegar",
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
        self.format_seg.pack(fill="x", padx=14, pady=(0, 12))

        # Action Button
        self.download_btn = ctk.CTkButton(
            card,
            text="Descargar Ahora",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            command=self._on_download_click,
        )
        self.download_btn.pack(fill="x", padx=14, pady=(0, 12))

        # Progress Section
        self.progress_bar = ctk.CTkProgressBar(card, height=8, fg_color="#27272a", progress_color="#8b5cf6")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=14, pady=(0, 6))

        self.progress_label = ctk.CTkLabel(
            card,
            text="Listo para descargar",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
        )
        self.progress_label.pack(padx=14, pady=(0, 12))

        # Folder & Controls Card
        bottom_card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#121214")
        bottom_card.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            bottom_card,
            text="DIRECTORIOS Y DAEMON LOCAL",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a1a1aa",
        ).pack(anchor="w", padx=14, pady=(10, 6))

        btn_row = ctk.CTkFrame(bottom_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 10))

        open_vid_btn = ctk.CTkButton(
            btn_row,
            text="📁 Videos",
            height=32,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=lambda: self._open_folder(self._video_dir),
        )
        open_vid_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        open_mus_btn = ctk.CTkButton(
            btn_row,
            text="🎵 Música",
            height=32,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=lambda: self._open_folder(self._music_dir),
        )
        open_mus_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Daemon toggle row
        daemon_row = ctk.CTkFrame(bottom_card, fg_color="transparent")
        daemon_row.pack(fill="x", padx=14, pady=(0, 10))

        self.daemon_toggle_btn = ctk.CTkButton(
            daemon_row,
            text="Iniciar Daemon",
            height=32,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._toggle_daemon,
        )
        self.daemon_toggle_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        startup_btn = ctk.CTkButton(
            daemon_row,
            text="⚡ Autoarranque Windows",
            height=32,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._setup_autostart,
        )
        startup_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

    def _build_library_tab(self, parent):
        # Search Top Bar
        search_card = ctk.CTkFrame(parent, corner_radius=10, fg_color="#121214")
        search_card.pack(fill="x", padx=8, pady=(8, 4))

        search_row = ctk.CTkFrame(search_card, fg_color="transparent")
        search_row.pack(fill="x", padx=10, pady=8)

        self.search_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="🔍 Buscar en historial (título, artista o canal)...",
            height=36,
            font=ctk.CTkFont(size=12),
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        refresh_btn = ctk.CTkButton(
            search_row,
            text="🔄",
            width=36,
            height=36,
            fg_color="#27272a",
            hover_color="#3f3f46",
            command=self._refresh_library,
        )
        refresh_btn.pack(side="right")

        # Scrollable Cards Area
        self.history_scroll = ctk.CTkScrollableFrame(
            parent,
            corner_radius=10,
            fg_color="#121214",
        )
        self.history_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # Bottom Count Bar
        self.history_footer = ctk.CTkLabel(
            parent,
            text="Mostrando 0 descargas",
            font=ctk.CTkFont(size=11),
            text_color="#71717a",
        )
        self.history_footer.pack(side="bottom", pady=(2, 6))

    def _on_search_key(self, _event=None):
        query = self.search_entry.get().strip()
        self._load_history_view(query=query if query else None)

    def _refresh_library(self):
        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else None
        self._load_history_view(query=query if query else None)

    def _load_history_view(self, query: Optional[str] = None):
        # Limpiamos los widgets previos
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        records = self._history_adapter.list_records(limit=100, query=query)
        self.history_footer.configure(text=f"Mostrando {len(records)} descargas en biblioteca")

        if not records:
            ctk.CTkLabel(
                self.history_scroll,
                text="No se encontraron descargas en el historial local." if query else "La biblioteca está vacía.",
                font=ctk.CTkFont(size=12),
                text_color="#71717a",
            ).pack(pady=30)
            return

        for rec in records:
            self._render_record_card(rec)

    def _render_record_card(self, rec: DownloadRecord):
        exists = Path(rec.file_path).is_file()
        card = ctk.CTkFrame(self.history_scroll, corner_radius=8, fg_color="#1a1a1e", border_width=1, border_color="#27272a")
        card.pack(fill="x", padx=4, pady=4)

        # Top row: Title + Kind Badge
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            top_row,
            text=_truncate_title(rec.title),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        badge_color = "#8b5cf6" if rec.media_kind == "audio" else "#3b82f6"
        ctk.CTkLabel(
            top_row,
            text=rec.media_kind.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#ffffff",
            fg_color=badge_color,
            corner_radius=6,
            padx=6,
            pady=2,
        ).pack(side="right")

        # Subtitle row: Channel · Duration · Date
        sub_text = f"{rec.channel} · {_format_duration(rec.duration_seconds)} · {rec.created_at[:10]}"
        ctk.CTkLabel(
            card,
            text=sub_text,
            font=ctk.CTkFont(size=10),
            text_color="#71717a",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 6))

        # Action row
        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(0, 8))

        if exists:
            ctk.CTkLabel(
                action_row,
                text="✓ En disco",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#34d399",
            ).pack(side="left")

            ctk.CTkButton(
                action_row,
                text="▶ Reproducir",
                height=26,
                width=85,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#059669",
                hover_color="#047857",
                command=lambda p=rec.file_path: self._play_file(p),
            ).pack(side="right", padx=(4, 0))

            ctk.CTkButton(
                action_row,
                text="📁 Carpeta",
                height=26,
                width=75,
                font=ctk.CTkFont(size=11),
                fg_color="#27272a",
                hover_color="#3f3f46",
                command=lambda p=rec.file_path: self._reveal_file(p),
            ).pack(side="right", padx=(4, 0))
        else:
            ctk.CTkLabel(
                action_row,
                text="⚠️ Archivo movido o eliminado",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#f59e0b",
            ).pack(side="left")

        # Botón borrar del historial
        ctk.CTkButton(
            action_row,
            text="✕",
            width=28,
            height=26,
            fg_color="#27272a",
            hover_color="#ef4444",
            command=lambda rid=rec.id: self._delete_record(rid),
        ).pack(side="right", padx=(4, 0))

    def _play_file(self, file_path: str):
        p = Path(file_path)
        if p.is_file():
            os.startfile(str(p))

    def _reveal_file(self, file_path: str):
        p = Path(file_path)
        if p.is_file():
            subprocess.run(["explorer", f"/select,{str(p)}"])
        elif p.parent.is_dir():
            os.startfile(str(p.parent))

    def _delete_record(self, record_id: Optional[int]):
        if record_id:
            self._history_adapter.delete_record(record_id)
            self._refresh_library()

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

    def _start_daemon_process(self):
        main_script = str(Path(__file__).parent / "main.py")
        subprocess.Popen(
            [sys.executable, main_script],
            cwd=str(Path(__file__).parent),
            creationflags=0x08000000,
        )

    def _stop_daemon_process(self):
        cmd = "$conn = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue; if ($conn) { foreach ($c in $conn) { taskkill.exe /F /T /PID $c.OwningProcess 2>$null } }"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], creationflags=0x08000000)

    def _toggle_daemon(self):
        def _do_toggle():
            is_online = self._check_daemon_health()
            if is_online:
                self._stop_daemon_process()
                time.sleep(0.5)
                self.after(0, lambda: self._update_status(False))
            else:
                self._start_daemon_process()
                time.sleep(1.2)
                healthy = self._check_daemon_health()
                self.after(0, lambda: self._update_status(healthy))

        threading.Thread(target=_do_toggle, daemon=True).start()

    def _setup_autostart(self):
        subprocess.run(["cmd", "/c", "install_autostart.bat"], cwd=str(Path(__file__).parent))

    def _check_daemon_health(self) -> bool:
        try:
            r = requests.get(f"{API_BASE}/health", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    def _start_status_poller(self):
        self._poll_status_cycle()

    def _poll_status_cycle(self):
        try:
            online = self._check_daemon_health()
            self._update_status(online)
            if online:
                self._poll_jobs_status()
        except Exception:
            pass
        finally:
            self.after(1500, self._poll_status_cycle)

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

        self.progress_label.configure(text="Queueing media...", text_color="#a78bfa")
        self.url_entry.delete(0, "end")

        def _do_submit():
            if not self._check_daemon_health():
                self._start_daemon_process()
                time.sleep(1.2)

            try:
                res = requests.post(
                    f"{API_BASE}/api/download",
                    json={"url": url, "kind": kind, "quality": quality},
                    timeout=5,
                )
                if res.status_code == 200:
                    job_data = res.json()
                    jid = job_data["job_id"]
                    self.after(0, lambda: self.progress_label.configure(
                        text=f"✓ Job #{jid} queued! You can add more downloads.",
                        text_color="#34d399",
                    ))
                else:
                    self.after(0, lambda: self.progress_label.configure(
                        text=f"Error: {res.text}",
                        text_color="#f87171",
                    ))
            except Exception as err:
                self.after(0, lambda: self.progress_label.configure(
                    text=f"Connection Error: {err}",
                    text_color="#f87171",
                ))

        threading.Thread(target=_do_submit, daemon=True).start()

    def _poll_jobs_status(self):
        try:
            r = requests.get(f"{API_BASE}/api/jobs", timeout=2)
            if r.status_code != 200:
                return

            jobs = r.json()
            progress, text, color = _compute_pipeline_display(jobs, self.progress_bar.get() > 0)
            self.progress_bar.set(progress)
            self.progress_label.configure(text=text, text_color=color)
            if any(j.get("status") == "completed" for j in jobs):
                self._refresh_library()
        except Exception:
            pass


if __name__ == "__main__":
    app = YtGlobalDlApp()
    app.mainloop()
