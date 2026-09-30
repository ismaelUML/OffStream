# Abstracciones puras del dominio sin dependencias externas.
# Siguiendo a Robert C. Martin, un paquete debe balancear abstracción (A)
# e inestabilidad (I) para mantenerse cerca de la Secuencia Principal (D < 0.70).
from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol, TypeVar

T = TypeVar("T")


class IdentifiableProtocol(Protocol):
    """Protocolo estructural para cualquier objeto del dominio con identidad única."""
    @property
    def id(self) -> Any:
        ...


class ValueObjectProtocol(Protocol):
    """Protocolo para objetos inmutables definidos exclusivamente por sus atributos."""
    def to_dict(self) -> Dict[str, Any]:
        ...


class DomainEntityProtocol(Protocol):
    """Protocolo base para entidades de negocio mutables con ciclo de vida e identidad."""
    @property
    def identity(self) -> str:
        ...


class AggregateRootProtocol(DomainEntityProtocol, Protocol):
    """Protocolo para raíces de agregación que encapsulan límites de consistencia."""
    def validate_invariants(self) -> bool:
        ...


class DomainEventProtocol(Protocol):
    """Protocolo para eventos inmutables disparados por cambios de estado del dominio."""
    @property
    def event_name(self) -> str:
        ...


class BaseValueObject(ABC):
    """Clase base abstracta para Value Objects inmutables del dominio."""
    @abstractmethod
    def validate(self) -> None:
        """Verifica que los atributos satisfagan las reglas invariantes del VO."""
        pass


class BaseEntity(ABC):
    """Clase base abstracta para entidades con identidad y ciclo de vida."""
    @abstractmethod
    def get_id(self) -> str:
        """Retorna el identificador unívoco de la entidad."""
        pass
