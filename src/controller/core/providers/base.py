"""
Klasa bazowa BaseProvider dla wszystkich dostawców zmysłów w Kontrolerze.
"""
import time
from typing import Any


class BaseProvider:
    """Bazowa klasa dla wszystkich dostawców zmysłów w Kontrolerze."""

    def __init__(self, id: str, name: str, backend: Any = None, **kwargs):
        self.id = id
        self.name = name
        self.backend = backend
        self.last_seen = time.time()

        # Automatyczne przypisanie dodatkowych metadanych (np. model, source itp.)
        for k, v in kwargs.items():
            setattr(self, k, v)

    def touch(self) -> None:
        """Odświeża znacznik czasu ostatniej aktywności (heartbeat)."""
        self.last_seen = time.time()

    @property
    def is_online(self) -> bool:
        """Zwraca True jeśli dostawca wysłał heartbeat w ciągu ostatnich 30 sekund."""
        return (time.time() - self.last_seen) <= 30
