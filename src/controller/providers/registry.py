"""
Rejestr i Trwałe Instancje Usług Zmysłów Systemowych (llm oraz voice_channel).

Udostępnia katalogi zarejestrowanych backendów oraz 2 obiekty domenowe zmysłów:
- llm           (instancja LLMChannel z przypisanym backendem LLM)
- voice_channel (instancja VoiceChannel z przypisanymi backendami STT/TTS)
"""
import logging

from controller.providers.llm.base import LLMBackend
from controller.providers.llm_channel import LLMChannel
from controller.providers.audio.base import STTBackend, TTSBackend
from controller.providers.voice_channel import VoiceChannel

logger = logging.getLogger(__name__)

# Trwałe instancje zmysłów w Kontrolerze
llm = LLMChannel()
voice_channel = VoiceChannel()

# Katalogi dostępnych silników zmysłów
_stt_backends: dict[str, STTBackend] = {}
_tts_backends: dict[str, TTSBackend] = {}
_llm_backends: dict[str, LLMBackend] = {}

# Słownik niezadeklarowanych usług sieciowych (oczekujących na akceptację przez użytkownika)
_pending_discoveries: dict[str, dict] = {}


# =============================================================================
# REJESTRACJA DO KATALOGU
# =============================================================================

def register_stt(backend: STTBackend) -> None:
    """Rejestruje lub odświeża backend STT w katalogu."""
    _stt_backends[backend.id] = backend
    if voice_channel.stt is None or voice_channel.stt.id == backend.id:
        voice_channel.set_stt(backend)
    logger.debug(f"[ProviderRegistry] Zarejestrowano STTBackend: {backend.id}")


def register_tts(backend: TTSBackend) -> None:
    """Rejestruje lub odświeża backend TTS w katalogu."""
    _tts_backends[backend.id] = backend
    if voice_channel.tts is None or voice_channel.tts.id == backend.id:
        voice_channel.set_tts(backend)
    logger.debug(f"[ProviderRegistry] Zarejestrowano TTSBackend: {backend.id}")


def register_llm(backend: LLMBackend) -> None:
    """Rejestruje backend LLM w katalogu."""
    backend_id = getattr(backend, "id", None) or backend.get_provider_name()
    _llm_backends[backend_id] = backend
    if llm.backend is None:
        llm.set_backend(backend)
    logger.debug(f"[ProviderRegistry] Zarejestrowano LLMBackend: {backend_id}")


# =============================================================================
# LIVENESS (HEARTBEAT TOUCH)
# =============================================================================

def touch_stt(backend_id: str) -> bool:
    """Odświeża last_seen dla STT jeśli backend istnieje w konfiguracji."""
    if backend_id in _stt_backends:
        _stt_backends[backend_id].touch()
        return True
    return False


def touch_tts(backend_id: str) -> bool:
    """Odświeża last_seen dla TTS jeśli backend istnieje w konfiguracji."""
    if backend_id in _tts_backends:
        _tts_backends[backend_id].touch()
        return True
    return False


def register_pending_discovery(discovery_id: str, payload: dict) -> None:
    """Zapisuje zgłaszaną z sieci usługę jako oczekującą na akceptację w konfigu."""
    import time
    payload["last_seen"] = time.time()
    _pending_discoveries[discovery_id] = payload
    logger.info(f"[ProviderRegistry] Wykryto niezadeklarowaną usługę {discovery_id}. Oczekuje na dodanie do konfigu.")


def get_pending_discoveries() -> dict[str, dict]:
    return dict(_pending_discoveries)


# =============================================================================
# POBIERANIE KATALOGÓW DLA INTERFEJSU
# =============================================================================

def get_all_stt_backends() -> dict[str, STTBackend]:
    """Zwraca słownik wszystkich zarejestrowanych silników STT."""
    return dict(_stt_backends)


def get_all_tts_backends() -> dict[str, TTSBackend]:
    """Zwraca słownik wszystkich zarejestrowanych silników TTS."""
    return dict(_tts_backends)


def get_all_llm_backends() -> dict[str, LLMBackend]:
    """Zwraca słownik wszystkich zarejestrowanych silników LLM."""
    return dict(_llm_backends)


def clear_audio_backends() -> None:
    """Czyści katalogi i resetuje kanały; używane w testach i shutdownie."""
    _stt_backends.clear()
    _tts_backends.clear()
    _llm_backends.clear()
    _pending_discoveries.clear()
    llm.set_backend(None)
    voice_channel.set_stt(None)
    voice_channel.set_tts(None)
