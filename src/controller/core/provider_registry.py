"""
Centralny Rejestr Backendów Zmysłów (ProviderRegistry) w pamięci RAM.

Przechowuje aktualnie aktywne backendy audio (STT i TTS), które zarejestrowały się
w Kontrolerze przez model push (heartbeat). Nie wie nic o konkretnych implementacjach —
operuje wyłącznie na abstrakcyjnych interfejsach STTBackend i TTSBackend.

Backendy LLM są obsługiwane przez osobny moduł: providers/llm/resolver.py
"""
import logging
from typing import Optional

from controller.providers.audio.backends import STTBackend, TTSBackend
from controller.core.voice_channel import VoiceChannel

logger = logging.getLogger(__name__)

# Rejestry aktywnych backendów w pamięci RAM
_stt: dict[str, STTBackend] = {}
_tts: dict[str, TTSBackend] = {}


# =============================================================================
# REJESTRACJA
# =============================================================================

def register_stt(backend: STTBackend) -> None:
    """Rejestruje lub odświeża backend STT w rejestrze."""
    backend.touch()
    _stt[backend.id] = backend
    logger.debug(f"[ProviderRegistry] Zarejestrowano STTBackend: {backend.id}")


def register_tts(backend: TTSBackend) -> None:
    """Rejestruje lub odświeża backend TTS w rejestrze."""
    backend.touch()
    _tts[backend.id] = backend
    logger.debug(f"[ProviderRegistry] Zarejestrowano TTSBackend: {backend.id}")


# =============================================================================
# ODPYTYWANIE
# =============================================================================

def get_active_stt() -> Optional[STTBackend]:
    """Zwraca pierwszy aktywny backend STT (heartbeat < 30s) lub None."""
    return next((b for b in _stt.values() if b.is_online), None)


def get_active_tts() -> Optional[TTSBackend]:
    """Zwraca pierwszy aktywny backend TTS (heartbeat < 30s) lub None."""
    return next((b for b in _tts.values() if b.is_online), None)


def get_voice_channel() -> VoiceChannel:
    """Zwraca VoiceChannel zasilony aktualnie aktywnymi backendami STT i TTS."""
    return VoiceChannel(
        stt=get_active_stt(),
        tts=get_active_tts(),
    )


def is_voice_channel_ready() -> bool:
    """Zwraca True jeśli oba backendy (STT i TTS) są aktywne."""
    return get_voice_channel().is_ready
