"""
Klasa VoiceChannel — Zarządca Kanału Głosowego (Zmysł Mowy).

Spaja ze sobą aktywny STTBackend oraz TTSBackend z worka zmysłów
i udostępnia spójny interfejs transkrypcji i syntezy dla Orkiestratora.
"""
import logging
from typing import Optional
from controller.providers.audio.base import STTBackend, TTSBackend

logger = logging.getLogger(__name__)


class VoiceChannel:
    """
    Zarządca Kanału Głosowego (Zmysł Mowy).
    Hermetyzuje wybrane silniki STT i TTS.
    """

    def __init__(
        self,
        stt: Optional[STTBackend] = None,
        tts: Optional[TTSBackend] = None,
    ):
        self.stt = stt
        self.tts = tts

    def set_stt(self, stt: Optional[STTBackend]) -> None:
        """Ustawia lub podmienia silnik transkrypcji mowy (STT)."""
        self.stt = stt

    def set_tts(self, tts: Optional[TTSBackend]) -> None:
        """Ustawia lub podmienia silnik syntezy głosu (TTS)."""
        self.tts = tts

    @property
    def is_ready(self) -> bool:
        """Kanał głosowy jest aktywny gdy zarówno STT jak i TTS są podłączone i online."""
        return (
            self.stt is not None
            and self.stt.is_online
            and self.tts is not None
            and self.tts.is_online
        )

    async def transcribe(self, audio_bytes: bytes) -> tuple[str | None, int]:
        """Wykonuje transkrypcję mowy przez przypisany STTBackend."""
        if not self.stt or not self.stt.is_online:
            logger.warning("[VoiceChannel] Brak aktywnego STTBackend dla transkrypcji.")
            return None, 0
        return await self.stt.transcribe(audio_bytes)

    async def synthesize(self, text: str) -> tuple[str | None, int]:
        """Wykonuje syntezę głosu przez przypisany TTSBackend."""
        if not self.tts or not self.tts.is_online:
            logger.warning("[VoiceChannel] Brak aktywnego TTSBackend dla syntezy.")
            return None, 0
        return await self.tts.synthesize(text)
