# YouTube no te sirve videos en 1080p con audio pegado; divide todo en streams DASH separados
# para ahorrar ancho de banda. Si no cazamos el audio y el video por separado y los unimos,
# te queda una película muda. Este módulo se encarga de elegir las mejores pistas.
from typing import List, Optional
from domain.exceptions import StreamNotFoundError
from domain.models import QualityTarget, StreamFormat


def select_best_audio_stream(formats: List[StreamFormat]) -> StreamFormat:
    # Filtramos solo pistas de audio y nos quedamos con la de mayor bitrate (menos compresión)
    audio_candidates = [f for f in formats if f.is_audio]
    if not audio_candidates:
        raise StreamNotFoundError("YouTube no devolvió ninguna pista de audio para este video.")
    return max(audio_candidates, key=_get_bitrate)


def select_video_stream(formats: List[StreamFormat], quality: QualityTarget) -> StreamFormat:
    # Si el usuario quiere 720p buscamos ese perfil; si no, le mandamos la resolución más bestia que haya
    video_candidates = [f for f in formats if f.is_video]
    if not video_candidates:
        raise StreamNotFoundError("No encontramos ninguna pista de video válida en la respuesta.")

    if quality == QualityTarget.P720:
        match = _find_720p_stream(video_candidates)
        if match:
            return match

    return max(video_candidates, key=_get_bitrate)


def _find_720p_stream(streams: List[StreamFormat]) -> Optional[StreamFormat]:
    for stream in streams:
        if stream.resolution and "720" in stream.resolution:
            return stream
    return None


def _get_bitrate(stream: StreamFormat) -> int:
    return stream.bitrate or 0
