"""
Klasa TTSProvider dla zmysłu syntezy głosu w Kontrolerze.
"""
import logging
from typing import Any
from controller.core.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class TTSProvider(BaseProvider):
    """Obiektowa rola zmysłu syntezy głosu (TTS) dla Orkiestratora."""

    def __init__(self, id: str, name: str, backend: Any = None, **kwargs):
        super().__init__(id=id, name=name, backend=backend, **kwargs)

    async def synthesize(self, text: str) -> tuple[str | None, int]:
        """Deleguje wykonanie syntezy mowy do podłączonego backendu TTS."""
        if self.backend and hasattr(self.backend, "synthesize"):
            return await self.backend.synthesize(text)
        logger.warning(f"[TTSProvider:{self.id}] Podłączony backend nie obsługuje metody synthesize.")
        return None, 0
