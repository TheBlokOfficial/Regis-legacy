"""
Klasa STTProvider dla zmysłu transkrypcji mowy w Kontrolerze.
"""
import logging
from typing import Any
from controller.core.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class STTProvider(BaseProvider):
    """Obiektowa rola zmysłu transkrypcji mowy (STT) dla Orkiestratora."""

    def __init__(self, id: str, name: str, backend: Any = None, **kwargs):
        super().__init__(id=id, name=name, backend=backend, **kwargs)

    async def transcribe(self, audio_bytes: bytes) -> tuple[str | None, int]:
        """Deleguje wykonanie transkrypcji mowy do podłączonego backendu STT."""
        if self.backend and hasattr(self.backend, "transcribe"):
            return await self.backend.transcribe(audio_bytes)
        logger.warning(f"[STTProvider:{self.id}] Podłączony backend nie obsługuje metody transcribe.")
        return None, 0
