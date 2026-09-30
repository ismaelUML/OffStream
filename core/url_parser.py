# Re-export de conveniencia para mantener compatibilidad hacia atrás.
# La lógica canónica pertenece a domain.url_parser como servicio puro de dominio.
from domain.url_parser import build_canonical_url, extract_video_id

__all__ = ["extract_video_id", "build_canonical_url"]
