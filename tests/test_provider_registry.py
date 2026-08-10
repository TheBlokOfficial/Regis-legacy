"""
Testy jednostkowe dla obiektowej architektury dostawców zmysłów i VoiceChannel.
"""
import time
import pytest
from controller.core.providers import STTProvider, TTSProvider
from controller.core.voice_channel import VoiceChannel
from controller.core.provider_registry import (
    _stt_providers,
    _tts_providers,
    register_stt_provider,
    register_tts_provider,
    get_active_stt_provider,
    get_active_tts_provider,
    get_voice_channel,
    is_voice_channel_ready,
    get_active_llm_provider,
    is_full_mode,
)


@pytest.fixture(autouse=True)
def _clear_providers():
    _stt_providers.clear()
    _tts_providers.clear()
    yield
    _stt_providers.clear()
    _tts_providers.clear()


def test_voice_channel_object_readiness():
    vc = get_voice_channel()
    assert not vc.is_ready

    stt = STTProvider(id="stt-1", name="Faster Whisper", port=8002)
    tts = TTSProvider(id="tts-1", name="Piper TTS", port=8002)

    register_stt_provider(stt)
    vc = get_voice_channel()
    assert not vc.is_ready
    assert vc.stt_provider.id == "stt-1"
    assert vc.tts_provider is None

    register_tts_provider(tts)
    vc = get_voice_channel()
    assert vc.is_ready
    assert vc.stt_provider.id == "stt-1"
    assert vc.tts_provider.id == "tts-1"
    assert is_voice_channel_ready()


def test_provider_expiration_object():
    stt = STTProvider(id="exp-stt", name="Expired STT")
    register_stt_provider(stt)
    stt.last_seen = time.time() - 40  # Przedawniony heartbeat

    assert not stt.is_online
    assert get_active_stt_provider() is None
    vc = get_voice_channel()
    assert not vc.is_ready


def test_llm_provider_object():
    llm = get_active_llm_provider()
    assert llm is not None
    assert llm.is_online
    assert is_full_mode()
