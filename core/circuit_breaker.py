# YouTube cambia firmas, ciphers y endpoints cada dos semanas para romper descargadores.
# Si dependemos de un solo motor, tarde o temprano el usuario se come un error 500 en la cara.
# Esta clase encadena resolvers: si el principal se estampa contra una pared de YouTube,
# pasamos al plan B sin hacer preguntas ni molestar al usuario.
import logging
from typing import List
from domain.exceptions import ResolutionError
from domain.models import VideoMetadata
from ports.out_bound import StreamResolverPort

logger = logging.getLogger(__name__)


class ResilientStreamResolver:
    def __init__(self, resolvers: List[StreamResolverPort]) -> None:
        if not resolvers:
            raise ValueError("Necesitamos al menos un resolver o no hay forma de hablar con YouTube.")
        self._resolvers = resolvers

    def resolve(self, url_or_id: str) -> VideoMetadata:
        errors: List[str] = []

        for resolver in self._resolvers:
            if not resolver.can_handle(url_or_id):
                continue

            resolver_name = resolver.__class__.__name__
            try:
                logger.info(f"Attempting resolution with {resolver_name}...")
                metadata = resolver.resolve(url_or_id)
                logger.info(f"Successfully resolved with {resolver_name}")
                return metadata
            except Exception as err:
                logger.warning(f"Resolver {resolver_name} failed: {err}")
                errors.append(f"{resolver_name}: {str(err)}")

        joined_errors = "; ".join(errors) if errors else "No compatible resolver found."
        raise ResolutionError(f"All stream resolvers exhausted. Errors: {joined_errors}")
