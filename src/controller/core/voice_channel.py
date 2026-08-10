"""
Klasa VoiceChannel — Zarządca Kanału Głosowego w rdzeniu Kontrolera.

Spaja ze sobą aktywnego STTProvider oraz TTSProvider z worka zmysłów
i udostępnia spójny interfejs transkrypcji i syntezy dla Orkiestratora.
"""
import logging
from typing import Optional
from controller.core.providers.stt import STTProvider
from controller.core.providers.tts import TTSProvider

logger = logging.getLogger(__name__)


class VoiceChannel:
    """
    Zarządca i wrapper Kanału Głosowego.
    Spina niezależne obiekty STTProvider oraz TTSProvider z worka zmysłów.
    """

    def __init__(
        self,
        stt_provider: Optional[STTProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
    ):
        self.stt_provider = stt_provider
        self.tts_provider = tts_provider

    @property
    def is_ready(self) -> bool:
        """
        Kanał głosowy uznaje się za aktywny, gdy zarówno STT jak i TTS są podłączone i online.
        """
        return (
            self.stt_provider is not None
            and self.stt_provider.is_online
            and self.tts_provider is not None
            and self.tts_provider.is_online
        )

    async def transcribe(self, audio_bytes: bytes) -> tuple[str | None, int]:
        """Wykonuje transkrypcję mowy przez przypisany STTProvider."""
        if not self.stt_provider or not self.stt_provider.is_online:
            logger.warning("[VoiceChannel] Brak aktywnego STTProvider dla transkrypcji.")
            return None, 0
        return await self.stt_provider.transcribe(audio_bytes)

    async def synthesize(self, text: str) -> tuple[str | None, int]:
        """Wykonuje syntezę głosu przez przypisany TTSProvider."""
        if not self.tts_provider or not self.tts_provider.is_online:
            logger.warning("[VoiceChannel] Brak aktywnego TTSProvider dla syntezy.")
            return None, 0
        return await self.tts_provider.synthesize(text)
