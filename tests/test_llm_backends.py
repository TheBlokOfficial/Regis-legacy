import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from controller.providers.llm.ollama import OllamaBackend
from controller.providers.llm.openrouter import OpenRouterBackend
import controller.providers.llm as providers


# =============================================================================
# is_available (async)
# =============================================================================

@pytest.mark.anyio
async def test_ollama_is_available_true():
    backend = OllamaBackend(model_name="test")
    with patch("controller.providers.llm.ollama.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=mock_response)))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await backend.is_available()
    assert result is True


@pytest.mark.anyio
async def test_ollama_is_available_false():
    backend = OllamaBackend(model_name="test")
    with patch("controller.providers.llm.ollama.httpx.AsyncClient") as mock_client_cls:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=mock_response)))
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await backend.is_available()
    assert result is False


@pytest.mark.anyio
async def test_openrouter_is_available_true():
    backend = OpenRouterBackend(api_key="test_key", model_name="test_model")
    assert await backend.is_available() is True


@pytest.mark.anyio
async def test_openrouter_is_available_false():
    backend = OpenRouterBackend(api_key="", model_name="")
    assert await backend.is_available() is False


# =============================================================================
# Zmysł LLM (async)
# =============================================================================

@pytest.mark.anyio
async def test_llm_registration_and_selection():
    from controller.providers.registry import (
        register_llm,
        get_all_llm_backends,
        llm,
        clear_audio_backends,
    )
    clear_audio_backends()
    assert not llm.is_ready

    mock_backend = OpenRouterBackend(api_key="test_key", model_name="test_model")
    register_llm(mock_backend)

    assert llm.is_ready
    assert llm.backend is mock_backend
    assert "openrouter" in get_all_llm_backends()

    clear_audio_backends()
    assert not llm.is_ready
    assert llm.backend is None


# =============================================================================
# Testy logiki domenowej
# =============================================================================

def test_build_messages_from_history_flat():
    from controller.agent.session.history import build_messages_from_history

    history = [
        {"role": "user", "content": "Wyłącz światło"},
        {"role": "assistant", "content": "Światło wyłączone."}
    ]

    messages = build_messages_from_history("System Prompt", history, current_message=None)

    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "System Prompt"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Wyłącz światło"
    assert messages[2]["role"] == "assistant"
    assert messages[2]["content"] == "Światło wyłączone."


def test_openrouter_accumulate_tool_call():
    accumulator = {}

    chunk_1 = {"index": 0, "id": "call_abc123", "function": {"name": "execute_action", "arguments": '{"action":'}}
    OpenRouterBackend._accumulate_tool_call(accumulator, chunk_1, 0)

    assert 0 in accumulator
    assert accumulator[0]["id"] == "call_abc123"
    assert accumulator[0]["function"]["name"] == "execute_action"
    assert accumulator[0]["function"]["arguments"] == '{"action":'

    chunk_2 = {"index": 0, "function": {"arguments": ' "turn_on"}'}}
    OpenRouterBackend._accumulate_tool_call(accumulator, chunk_2, 0)
    assert accumulator[0]["function"]["arguments"] == '{"action": "turn_on"}'


def test_predict_next_action_simple():
    from controller.agent.engine import predict_next_action

    class MockStreamProvider:
        async def chat_stream(self, messages, tools=None):
            yield {"type": "content", "content": "Cześć!"}

    async def _test():
        q = asyncio.Queue()
        loop = asyncio.get_running_loop()
        messages = [{"role": "system", "content": "Jesteś agentem"}, {"role": "user", "content": "Hej"}]
        content, tool_calls, ms, profiler = await predict_next_action(
            stream_provider=MockStreamProvider(),
            messages=messages,
            q=q,
            loop=loop,
        )
        return content

    result = asyncio.run(_test())
    assert result == "Cześć!"


def test_predict_next_action_propagates_backend_error():
    from controller.agent.engine import predict_next_action

    class BrokenStreamProvider:
        async def chat_stream(self, messages, tools=None):
            raise RuntimeError("backend unavailable")
            yield  # pragma: no cover

    async def _test():
        with pytest.raises(RuntimeError, match="backend unavailable"):
            await predict_next_action(
                stream_provider=BrokenStreamProvider(),
                messages=[],
                q=asyncio.Queue(),
                loop=asyncio.get_running_loop(),
            )

    asyncio.run(_test())
