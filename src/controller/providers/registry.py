"""
Rejestr i Trwałe Instancje Usług Zmysłów Systemowych (llm oraz voice_channel).

Udostępnia 2 unikalne w skali Kontrolera obiekty domenowe zmysłów:
- llm           (instancja LLMChannel)
- voice_channel (instancja VoiceChannel)
"""
import logging
from typing import Optional

from controller.providers.llm.base import LLMBackend
from controller.providers.llm.service import LLMChannel
from controller.providers.audio.base import STTBackend, TTSBackend
from controller.providers.voice_channel import VoiceChannel

logger = logging.getLogger(__name__)

# Trwałe instancje usług zmysłów w Kontrolerze.
# VoiceChannel pozostaje stabilnym punktem dostępu dla konsumentów, ale wybór
# backendu pochodzi z rejestrów — pozwala to niezależnie podmieniać STT i TTS.
llm = LLMChannel()
voice_channel = VoiceChannel()
_stt_backends: dict[str, STTBackend] = {}
_tts_backends: dict[str, TTSBackend] = {}


def _refresh_voice_channel() -> VoiceChannel:
    """Odświeża wybór aktywnych backendów bez zmiany tożsamości kanału."""
    voice_channel.set_stt(get_active_stt())
    voice_channel.set_tts(get_active_tts())
    return voice_channel


# =============================================================================
# REJESTRACJA I REJESTRY POMOCNICZE
# =============================================================================

def register_stt(backend: STTBackend) -> None:
    """Rejestruje lub odświeża backend STT i aktualizuje kanał głosowy."""
    backend.touch()
    _stt_backends[backend.id] = backend
    _refresh_voice_channel()
    logger.debug(f"[ProviderRegistry] Przypisano STTBackend: {backend.id}")


def register_tts(backend: TTSBackend) -> None:
    """Rejestruje lub odświeża backend TTS i aktualizuje kanał głosowy."""
    backend.touch()
    _tts_backends[backend.id] = backend
    _refresh_voice_channel()
    logger.debug(f"[ProviderRegistry] Przypisano TTSBackend: {backend.id}")


def register_llm(backend: LLMBackend) -> None:
    """Rejestruje backend LLM i wstrzykuje go do zmysłu llm."""
    llm.set_backend(backend)
    logger.debug(f"[ProviderRegistry] Przypisano LLMBackend: {backend.get_provider_name()}")


async def get_active_llm() -> Optional[LLMBackend]:
    """Zwraca aktywny silnik LLM ze zmysłu llm (lub podejmuje próbę inicjalizacji z konfigu)."""
    if llm.backend and await llm.backend.is_available():
        return llm.backend

    # Jeśli zmysł llm nie ma jeszcze przypisanego backendu, zainicjalizuj domyślny z konfigu
    from controller.providers.llm import get_active_llm as init_default_llm
    backend = await init_default_llm()
    if backend:
        llm.set_backend(backend)
        return backend

    return None


def get_active_stt() -> Optional[STTBackend]:
    """Zwraca pierwszy aktywny backend STT albo None."""
    return next((backend for backend in _stt_backends.values() if backend.is_online), None)


def get_active_tts() -> Optional[TTSBackend]:
    """Zwraca pierwszy aktywny backend TTS albo None."""
    return next((backend for backend in _tts_backends.values() if backend.is_online), None)


def get_voice_channel() -> VoiceChannel:
    """Zwraca trwałą instancję kanału z aktualnie wybranymi backendami."""
    return _refresh_voice_channel()


def is_voice_channel_ready() -> bool:
    """Zwraca True jeśli kanał głosowy jest aktywny i gotowy."""
    return get_voice_channel().is_ready


def clear_audio_backends() -> None:
    """Czyści rejestry audio; używane przy kontrolowanym shutdownie i w testach."""
    _stt_backends.clear()
    _tts_backends.clear()
    _refresh_voice_channel()
