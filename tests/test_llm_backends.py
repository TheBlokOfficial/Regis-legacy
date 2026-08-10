import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from controller.providers.llm.ollama import OllamaBackend
from controller.providers.llm.openrouter import OpenRouterBackend
from controller.providers.llm.client_app import ClientAppBackend
import controller.providers.llm.resolver as providers


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
# Resolver (async)
# =============================================================================

@pytest.mark.anyio
@patch.object(OpenRouterBackend, "is_available", new_callable=AsyncMock, return_value=True)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers")
async def test_get_active_llm_returns_openrouter(mock_get_cloud, mock_openrouter_avail):
    from controller.config.schemas import CloudProviderConfig
    mock_get_cloud.return_value = [CloudProviderConfig(
        id="test",
        type="openrouter",
        api_key="test_key",
        model="test_model",
        priority=50,
    )]
    providers.client_registry.client_registry.clear()
    backend = await providers.get_active_llm()
    assert isinstance(backend, OpenRouterBackend)


@pytest.mark.anyio
@patch.object(OpenRouterBackend, "is_available", new_callable=AsyncMock, return_value=False)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers", return_value=[])
async def test_get_active_llm_returns_client_app_if_registered(mock_get_cloud, mock_openrouter_avail):
    providers.client_registry.client_registry.clear()
    providers.client_registry.client_registry["worker_1"] = {"id": "worker_1", "priority": 10, "model_name": "qwen3.5:9b"}
    backend = await providers.get_active_llm()
    assert isinstance(backend, ClientAppBackend)
    assert backend.model_name == "qwen3.5:9b"
    providers.client_registry.client_registry.clear()


@pytest.mark.anyio
@patch.object(OllamaBackend, "is_available", new_callable=AsyncMock, return_value=True)
@patch.object(OpenRouterBackend, "is_available", new_callable=AsyncMock, return_value=False)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers", return_value=[])
async def test_get_active_llm_returns_ollama_if_available(mock_get_cloud, mock_openrouter_avail, mock_ollama_avail):
    providers.client_registry.client_registry.clear()
    backend = await providers.get_active_llm()
    assert isinstance(backend, OllamaBackend)


@pytest.mark.anyio
@patch.object(OllamaBackend, "is_available", new_callable=AsyncMock, return_value=False)
@patch.object(OpenRouterBackend, "is_available", new_callable=AsyncMock, return_value=False)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers", return_value=[])
async def test_get_active_llm_returns_none_if_none_available(mock_get_cloud, mock_openrouter_avail, mock_ollama_avail):
    providers.client_registry.client_registry.clear()
    backend = await providers.get_active_llm()
    assert backend is None


# =============================================================================
# Bez zmian — testy logiki domenowej
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
