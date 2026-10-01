# Excepciones del Dominio Puro.
# Cero dependencias externas. Si una de estas vuela, sabemos exactamente qué regla
# de negocio se rompió y no nos comemos un stacktrace misterioso de una librería ajena.


class DomainError(Exception):
    """Excepción raíz del dominio. Si hereda de acá, es un error controlado por nuestra arquitectura."""
    pass


class InvalidVideoURLError(DomainError):
    """El usuario pegó un link deforme, una búsqueda de Google o algo que ningún regex puede salvar."""
    pass


class StreamNotFoundError(DomainError):
    """YouTube devolvió la metadata pero el video es privado, de pago o las pistas están bloqueadas por región."""
    pass


class ResolutionError(DomainError):
    """YouTube cambió un token o bloqueó la IP. Señal para que el circuit breaker active el resolver de respaldo."""
    pass


class QueueFullError(DomainError):
    """Freno de mano por contrapresión: la cola está saturada y meter más jobs colapsaría la CPU y el disco."""
    pass


class MuxingError(DomainError):
    """FFmpeg falló al ensamblar pistas. Suele pasar por códecs exóticos o chunks corruptos por corte de red."""
    pass


class JobCancelledError(DomainError):
    """El usuario abortó la descarga. Cortamos sockets y limpiamos archivos temporales para no dejar basura."""
    pass
