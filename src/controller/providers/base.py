"""
Abstrakcyjny Interfejs Bazowy dla Wszystkich Dostawców Zmysłów (BaseBackend).

Definiuje tożsamość, stan liveness oraz polimorficzny kontrakt rejestracji z konfiguracji.
"""
import time
from abc import ABC, abstractmethod
from typing import Any


class BaseBackend(ABC):
    """Bazowy interfejs infrastrukturalny dla każdego silnika zmysłu (LLM, STT, TTS)."""

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.last_seen: float = time.time()

    def touch(self) -> None:
        """Odświeża znacznik czasu ostatniego pingu/heartbeatu zmysłu."""
        self.last_seen = time.time()

    @property
    def is_online(self) -> bool:
        """Zwraca True jeśli dostawca był widziany w ciągu ostatnich 30 sekund."""
        return (time.time() - self.last_seen) <= 30

    @classmethod
    @abstractmethod
    def create_and_register(cls, config_data: Any) -> None:
        """
        Tworzy instancję dostawcy na podstawie jego wycinka konfiguracji 
        i rejestruje ją w centralnym ProviderRegistry.
        """
        pass
