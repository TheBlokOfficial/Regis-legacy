"""
Abstrakcyjne Kontrakty (ABC) Silników Mowy (STT / TTS).

Definiuje bazowe interfejsy dla dostawców transkrypcji mowy (STTBackend)
oraz syntezy głosu (TTSBackend).
"""
from abc import ABC, abstractmethod


class STTBackend(ABC):
    """Abstrakcyjny interfejs silnika transkrypcji mowy (STT)."""

    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> tuple[str | None, int]:
        """Transkrybuje surowe bajty audio na tekst. Zwraca (tekst, czas_ms)."""
        pass


class TTSBackend(ABC):
    """Abstrakcyjny interfejs silnika syntezy głosu (TTS)."""

    @abstractmethod
    async def synthesize(self, text: str) -> tuple[str | None, int]:
        """Syntetyzuje tekst na audio (base64). Zwraca (audio_b64, czas_ms)."""
        pass
