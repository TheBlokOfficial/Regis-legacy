"""
Testy jednostkowe dla architektury backendów zmysłów i VoiceChannel.
"""
import time
import pytest
from unittest.mock import AsyncMock, patch

from controller.providers.audio.base import STTBackend, TTSBackend
from controller.providers.audio.audio_service import AudioServiceSTTBackend, AudioServiceTTSBackend
from controller.providers.voice_channel import VoiceChannel
from controller.providers.registry import (
    clear_audio_backends,
    register_stt,
    register_tts,
    register_llm,
    get_all_stt_backends,
    get_all_tts_backends,
    get_all_llm_backends,
    voice_channel,
    llm,
)


@pytest.fixture(autouse=True)
def _clear_providers():
    clear_audio_backends()
    yield
    clear_audio_backends()


# =============================================================================
# Testy VoiceChannel i rejestru
# =============================================================================

def test_voice_channel_empty():
    assert not voice_channel.is_ready


def test_voice_channel_readiness():
    stt = AudioServiceSTTBackend(id="stt-1", name="Faster Whisper", base_url="http://127.0.0.1:8002")
    tts = AudioServiceTTSBackend(id="tts-1", name="Piper TTS", base_url="http://127.0.0.1:8002")

    register_stt(stt)
    assert not voice_channel.is_ready
    assert voice_channel.stt.id == "stt-1"
    assert voice_channel.tts is None

    register_tts(tts)
    assert voice_channel.is_ready
    assert voice_channel.stt.id == "stt-1"
    assert voice_channel.tts.id == "tts-1"


def test_direct_provider_assignment():
    stt1 = AudioServiceSTTBackend(id="stt-1", name="STT 1", base_url="http://127.0.0.1:8002")
    stt2 = AudioServiceSTTBackend(id="stt-2", name="STT 2", base_url="http://127.0.0.1:8002")
    register_stt(stt1)
    register_stt(stt2)

    assert "stt-1" in get_all_stt_backends()
    assert "stt-2" in get_all_stt_backends()

    stt_target = get_all_stt_backends().get("stt-2")
    voice_channel.set_stt(stt_target)
    assert voice_channel.stt.id == "stt-2"


def test_provider_expiration():
    stt = AudioServiceSTTBackend(id="exp-stt", name="Expired STT", base_url="http://127.0.0.1:8002")
    register_stt(stt)
    stt.last_seen = time.time() - 40  # Przedawniony heartbeat

    assert not stt.is_online
    assert not voice_channel.is_ready


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
    from controller.providers.registry import llm

    class DummyBackend:
        model_name = "test_model:latest"

        async def is_available(self):
            return True

        def get_provider_name(self):
            return "dummy_provider"

        async def chat_stream(self, messages, tools=None):
            yield {"type": "content", "content": "Test response"}

    dummy_backend = DummyBackend()
    llm.set_backend(dummy_backend)

    with patch("controller.orchestrator.predict_next_action", new_callable=AsyncMock) as mock_predict:
        mock_predict.return_value = ("Test response", [], 100, {})

        items = []
        async for item in handle_user_spoke(text="Cześć", sender="test_sender"):
            items.append(item)

        assert mock_predict.called
        call_kwargs = mock_predict.call_args.kwargs
        assert call_kwargs["stream_provider"] == llm


@pytest.mark.anyio
async def test_orchestrator_no_llm_returns_early():
    from controller.orchestrator import handle_user_spoke
    from controller.providers.registry import llm

    llm.set_backend(None)
    items = []
    async for item in handle_user_spoke(text="Cześć", sender="test_sender"):
        items.append(item)
    assert items == []


@pytest.mark.anyio
async def test_orchestrator_streams_structured_tool_events():
    import controller.state as app_state
    from controller.agent.tools.registry import ToolsRegistry
    from controller.orchestrator import handle_user_spoke
    from controller.providers.registry import llm

    class DummyBackend:
        model_name = "test-model"

        def get_provider_name(self):
            return "dummy"

    registry = ToolsRegistry()
    registry.register(
        {"type": "function", "function": {"name": "test_tool", "parameters": {}}},
        lambda _: '{"result": "ok"}',
    )
    previous_registry = app_state.tools_registry
    previous_backend = llm.backend
    app_state.tools_registry = registry
    llm.set_backend(DummyBackend())

    try:
        with patch("controller.orchestrator.predict_next_action", new_callable=AsyncMock) as mock_predict:
            mock_predict.side_effect = [
                ("", [{"id": "call-1", "function": {"name": "test_tool", "arguments": "{}"}}], 1, {}),
                ("Gotowe.", [], 1, {}),
            ]
            events = [item async for item in handle_user_spoke("uruchom", "tool-event-test")]

        tool_call = next(event for event in events if event["type"] == "tool_call")
        tool_result = next(event for event in events if event["type"] == "tool_result")
        assert tool_call["content"] == {"name": "test_tool", "arguments": {}}
        assert tool_result["content"]["name"] == "test_tool"
        assert any(event["type"] == "done" for event in events)
    finally:
        app_state.tools_registry = previous_registry
        llm.set_backend(previous_backend)
