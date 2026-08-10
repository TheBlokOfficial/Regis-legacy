"""
Testy jednostkowe dla architektury backendów zmysłów i VoiceChannel.
"""
import time
import pytest
from unittest.mock import AsyncMock, patch

from controller.providers.audio.backends import STTBackend, TTSBackend, AudioServiceSTTBackend, AudioServiceTTSBackend
from controller.core.voice_channel import VoiceChannel
from controller.core.provider_registry import (
    _stt,
    _tts,
    register_stt,
    register_tts,
    get_active_stt,
    get_active_tts,
    get_voice_channel,
    is_voice_channel_ready,
)


@pytest.fixture(autouse=True)
def _clear_providers():
    _stt.clear()
    _tts.clear()
    yield
    _stt.clear()
    _tts.clear()


# =============================================================================
# Testy VoiceChannel i rejestru
# =============================================================================

def test_voice_channel_empty():
    vc = get_voice_channel()
    assert not vc.is_ready


def test_voice_channel_readiness():
    stt = AudioServiceSTTBackend(id="stt-1", name="Faster Whisper", base_url="http://127.0.0.1:8002")
    tts = AudioServiceTTSBackend(id="tts-1", name="Piper TTS", base_url="http://127.0.0.1:8002")

    register_stt(stt)
    vc = get_voice_channel()
    assert not vc.is_ready
    assert vc.stt.id == "stt-1"
    assert vc.tts is None

    register_tts(tts)
    vc = get_voice_channel()
    assert vc.is_ready
    assert vc.stt.id == "stt-1"
    assert vc.tts.id == "tts-1"
    assert is_voice_channel_ready()


def test_provider_expiration():
    stt = AudioServiceSTTBackend(id="exp-stt", name="Expired STT", base_url="http://127.0.0.1:8002")
    register_stt(stt)
    stt.last_seen = time.time() - 40  # Przedawniony heartbeat

    assert not stt.is_online
    assert get_active_stt() is None
    vc = get_voice_channel()
    assert not vc.is_ready


def test_backend_touch_refreshes_liveness():
    stt = AudioServiceSTTBackend(id="stt-touch", name="Touch STT", base_url="http://127.0.0.1:8002")
    stt.last_seen = time.time() - 40
    assert not stt.is_online

    stt.touch()
    assert stt.is_online


# =============================================================================
# Testy STTBackend / TTSBackend ABC
# =============================================================================

def test_stt_backend_is_abstract():
    """STTBackend jest klasą abstrakcyjną — nie można jej instancjonować bezpośrednio."""
    with pytest.raises(TypeError):
        STTBackend()  # type: ignore


def test_tts_backend_is_abstract():
    """TTSBackend jest klasą abstrakcyjną — nie można jej instancjonować bezpośrednio."""
    with pytest.raises(TypeError):
        TTSBackend()  # type: ignore


# =============================================================================
# Testy integracji orkiestratora z LLM resolverem
# =============================================================================

@pytest.mark.anyio
async def test_orchestrator_integration_with_llm_backend():
    from controller.orchestrator import handle_user_spoke

    class DummyBackend:
        model_name = "test_model:latest"

        async def is_available(self):
            return True

        def get_provider_name(self):
            return "dummy_provider"

        async def chat_stream(self, messages, tools=None):
            yield {"type": "content", "content": "Test response"}

    dummy_backend = DummyBackend()

    with patch("controller.orchestrator.llm_resolver.get_active_llm", new_callable=AsyncMock, return_value=dummy_backend), \
         patch("controller.orchestrator.predict_next_action", new_callable=AsyncMock) as mock_predict:

        mock_predict.return_value = ("Test response", [], 100, {})

        items = []
        async for item in handle_user_spoke(text="Cześć", sender="test_sender"):
            items.append(item)

        assert mock_predict.called
        call_kwargs = mock_predict.call_args.kwargs
        assert call_kwargs["stream_provider"] == dummy_backend


@pytest.mark.anyio
async def test_orchestrator_no_llm_returns_early():
    from controller.orchestrator import handle_user_spoke

    with patch("controller.orchestrator.llm_resolver.get_active_llm", new_callable=AsyncMock, return_value=None):
        items = []
        async for item in handle_user_spoke(text="Cześć", sender="test_sender"):
            items.append(item)
        assert items == []
