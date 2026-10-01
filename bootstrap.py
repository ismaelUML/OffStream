# Composition Root del sistema (Inyección de Dependencias).
# Este es el ÚNICO archivo del proyecto donde se cruzan los cables entre adaptadores concretos y el core.
# Al centralizar la instanciación acá, la CLI, la GUI y el servidor HTTP no saben (ni les importa)
# si usamos yt-dlp, FFmpeg o SQLite; solo conocen los puertos limpios y se pueden testear sin dolor.
from typing import Any, Optional
from core.circuit_breaker import ResilientStreamResolver
from core.download_manager import DownloadManager
from adapters.out_bound.fast_downloader import FastMediaDownloader
from adapters.out_bound.ffmpeg_processor import FFmpegProcessorAdapter
from adapters.out_bound.innertube_resolver import InnerTubeResolver
from adapters.out_bound.local_storage import LocalStorageAdapter
from adapters.out_bound.sqlite_history import SqliteHistoryAdapter
from adapters.out_bound.ytdlp_resolver import YtDlpResolver


def build_default_manager(
    cookies_browser: Optional[str] = None,
    history_repo: Optional[Any] = None,
) -> DownloadManager:
    """Ensambla el grafo hexagonal completo conectando adaptadores concretos al orquestador central."""
    # 1. Almacenamiento local seguro en la carpeta Downloads/yt-global-dl del usuario
    storage = LocalStorageAdapter()
    # 2. Motor acelerado de descarga por fragmentos concurrentes
    downloader = FastMediaDownloader(cookies_browser=cookies_browser)
    # 3. Binario compilado de FFmpeg para muxeo y transcodificación a MP3
    processor = FFmpegProcessorAdapter()
    # 4. Cadena de resolución: yt-dlp de titular y InnerTube ligero como reemplazo
    primary_resolver = YtDlpResolver(cookies_browser=cookies_browser)
    fallback_resolver = InnerTubeResolver()
    router = ResilientStreamResolver([primary_resolver, fallback_resolver])
    # 5. Persistencia SQLite para que el historial sobreviva reinicios del sistema operativo
    history = history_repo if history_repo is not None else SqliteHistoryAdapter()

    return DownloadManager(
        resolver=router,
        downloader=downloader,
        processor=processor,
        storage=storage,
        history_repo=history,
    )
