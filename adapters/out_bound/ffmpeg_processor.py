# Muxeo y transcodificación con FFmpeg.
# En resumen: une la pista de video muda con la pista de audio sin recomprimir el video,
# o convierte el Opus/M4A que escupe YouTube en un MP3 a 192k decente para el auto o el celu.
import shutil
import subprocess
from domain.exceptions import MuxingError

try:
    import imageio_ffmpeg
    # Salva vidas: usa el ejecutable compilado de imageio y nos ahorra
    # lidiar con usuarios que no saben cómo editar las Variables de Entorno de Windows.
    _BUNDLED_FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _BUNDLED_FFMPEG = None


class FFmpegProcessorAdapter:
    def __init__(self, custom_binary: str = "") -> None:
        self._binary = custom_binary or _BUNDLED_FFMPEG or shutil.which("ffmpeg")
        if not self._binary:
            raise MuxingError("No encontramos FFmpeg en ningún rincón del sistema. Instala imageio-ffmpeg o ponlo en el PATH.")

    def mux_video_audio(self, video_path: str, audio_path: str, output_path: str) -> str:
        # Copiamos el video bit por bit (-c:v copy) para que no tarde 15 minutos recomprimiendo.
        # El audio lo dejamos en AAC que es compatible hasta con televisores viejos.
        cmd = [
            self._binary,
            "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]
        self._run_command(cmd, "Falló la unión de pistas de video y audio.")
        return output_path

    def convert_to_mp3(self, source_audio_path: str, output_path: str) -> str:
        # Tiramos a la basura cualquier thumbnail o video (-vn) y sacamos MP3 a 192 kbps constantes.
        cmd = [
            self._binary,
            "-y",
            "-i", source_audio_path,
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ]
        self._run_command(cmd, "Falló la conversión del flujo a MP3.")
        return output_path

    def _run_command(self, cmd: list, error_context: str) -> None:
        # En Windows, si no pones CREATE_NO_WINDOW cada subproceso te parpadea
        # una consola negra de CMD en medio de la pantalla como si fuera un malware de 2003.
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0:
            raise MuxingError(f"{error_context} Detalle del error: {proc.stderr[-300:]}")
