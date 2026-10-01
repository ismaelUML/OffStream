"""Configuración global de pruebas para pytest."""
import pytest


@pytest.fixture
def anyio_backend():
    # AnyIO intenta por defecto parametrizar sobre trio y asyncio si no se especifica.
    # Como no usamos trio (ni queremos meter otra dependencia innecesaria en el runner de CI),
    # forzamos exclusivamente el backend asyncio nativo que utiliza FastAPI y Starlette.
    return "asyncio"
