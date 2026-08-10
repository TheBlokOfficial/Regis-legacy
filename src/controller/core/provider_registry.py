"""
Centralny Rejestr Dostawców Zmysłów (ProviderRegistry) w pamięci RAM.

Zarządza instancjami silnie typowanych klas zmysłów:
1. LLMProvider (OpenRouter w chmurze, Ollama Direct lokalnie)
2. STTProvider (transkrypcja mowy)
3. TTSProvider (synteza głosu)
4. VoiceChannel ( dynamicznie zasilany zarządca Kanału Głosowego )
"""
import time
import logging
import os
from typing import Optional

from controller.config import loader as config
from controller.config.schemas import CloudProvidersConfig
from controller.core.providers import (
    BaseProvider,
    STTProvider,
    TTSProvider,
    LLMProvider,
)
from controller.core.voice_channel import VoiceChannel

logger = logging.getLogger(__name__)

# Rejestry instancji obiektów w pamięci RAM
_stt_providers: dict[str, STTProvider] = {}
_tts_providers: dict[str, TTSProvider] = {}
_llm_providers: dict[str, LLMProvider] = {}


# =============================================================================
# REJESTRACJA I PING ZMYSŁÓW
# =============================================================================

def register_stt_provider(provider: STTProvider | dict) -> STTProvider:
    """Rejestruje lub odświeża obiekt dostawcy STT (transkrypcja mowy)."""
    if isinstance(provider, dict):
        from controller.providers.audio.backends import AudioServiceSTTBackend
        backend = AudioServiceSTTBackend(
            id=provider.get("id", "default_stt"),
            name=provider.get("name", "STT Provider"),
            host=provider.get("host", "127.0.0.1"),
            port=provider.get("port", 8002),
            model_size=provider.get("model_size", "small"),
        )
        provider_obj = STTProvider(
            id=provider.get("id", "default_stt"),
            name=provider.get("name", "STT Provider"),
            backend=backend,
        )
    else:
        provider_obj = provider

    provider_obj.touch()
    _stt_providers[provider_obj.id] = provider_obj
    logger.debug(f"[ProviderRegistry] Zarejestrowano STTProvider: {provider_obj.id}")
    return provider_obj


def register_tts_provider(provider: TTSProvider | dict) -> TTSProvider:
    """Rejestruje lub odświeża obiekt dostawcy TTS (synteza mowy)."""
    if isinstance(provider, dict):
        from controller.providers.audio.backends import AudioServiceTTSBackend
        backend = AudioServiceTTSBackend(
            id=provider.get("id", "default_tts"),
            name=provider.get("name", "TTS Provider"),
            host=provider.get("host", "127.0.0.1"),
            port=provider.get("port", 8002),
            voice_name=provider.get("voice_name", "pl_PL-darkman-medium"),
        )
        provider_obj = TTSProvider(
            id=provider.get("id", "default_tts"),
            name=provider.get("name", "TTS Provider"),
            backend=backend,
        )
    else:
        provider_obj = provider

    provider_obj.touch()
    _tts_providers[provider_obj.id] = provider_obj
    logger.debug(f"[ProviderRegistry] Zarejestrowano TTSProvider: {provider_obj.id}")
    return provider_obj


# =============================================================================
# RESOLVER STT / TTS & VOICE CHANNEL
# =============================================================================

def get_active_stt_provider() -> Optional[STTProvider]:
    """Zwraca instancję aktywnego STTProvider (heartbeat < 30s)."""
    for p_id, provider in list(_stt_providers.items()):
        if provider.is_online:
            return provider
    return None


def get_active_tts_provider() -> Optional[TTSProvider]:
    """Zwraca instancję aktywnego TTSProvider (heartbeat < 30s)."""
    for p_id, provider in list(_tts_providers.items()):
        if provider.is_online:
            return provider
    return None


def get_voice_channel() -> VoiceChannel:
    """
    Zwraca instancję obiektu VoiceChannel zasilonego aktualnie aktywnym STT i TTS.
    """
    return VoiceChannel(
        stt_provider=get_active_stt_provider(),
        tts_provider=get_active_tts_provider(),
    )


def is_voice_channel_ready() -> bool:
    """Kanał głosowy jest gotowy, jeśli get_voice_channel().is_ready zwraca True."""
    return get_voice_channel().is_ready


# =============================================================================
# RESOLVER LLM (AGENT)
# =============================================================================

def get_active_llm_provider() -> Optional[LLMProvider]:
    """
    Zwraca aktywnego dostawcę LLM.
    Priorytet: Dostawcy chmurowi (cloud_providers.json) -> Ollama Direct HTTP.
    """
    try:
        cfg = config.load(CloudProvidersConfig)
        if cfg.root:
            p = cfg.root[0]
            return LLMProvider(
                id=p.id,
                name=f"Cloud ({p.type})",
                provider_type=p.type,
                model=p.model,
                api_key=p.api_key,
                source="cloud",
            )
    except Exception:
        pass

    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b")
    return LLMProvider(
        id="ollama_direct",
        name=f"Ollama Direct ({model_name})",
        provider_type="ollama",
        model=model_name,
        host=ollama_host,
        source="local",
    )


def is_full_mode() -> bool:
    """Zwraca True jeśli agent posiada aktywnego dostawcę LLM."""
    return get_active_llm_provider() is not None
