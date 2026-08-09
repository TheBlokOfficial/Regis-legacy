import pytest
from unittest.mock import patch
import os

from controller.providers.llm.ollama import OllamaBackend
from controller.providers.llm.openrouter import OpenRouterBackend
import controller.providers.llm.resolver as providers

@patch("requests.get")
def test_ollama_is_available_true(mock_get):
    mock_get.return_value.status_code = 200
    backend = OllamaBackend(model_name="test")
    assert backend.is_available() is True

@patch("requests.get")
def test_ollama_is_available_false(mock_get):
    mock_get.return_value.status_code = 500
    backend = OllamaBackend(model_name="test")
    assert backend.is_available() is False

def test_openrouter_is_available_true():
    backend = OpenRouterBackend(api_key="test_key", model_name="test_model")
    assert backend.is_available() is True

def test_openrouter_is_available_false():
    backend = OpenRouterBackend(api_key="", model_name="")
    assert backend.is_available() is False

@patch.object(OpenRouterBackend, "is_available", return_value=True)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers")
def test_get_llm_backend_returns_openrouter(mock_get_cloud, mock_openrouter_avail):
    from controller.config.schemas import CloudProviderConfig
    mock_get_cloud.return_value = [CloudProviderConfig(
        id="test",
        type="openrouter",
        api_key="test_key",
        model="test_model",
        priority=50
    )]
    backend = providers.get_llm_backend()
    assert isinstance(backend, OpenRouterBackend)

from controller.providers.llm.client_app import ClientAppBackend

@patch.object(OpenRouterBackend, "is_available", return_value=False)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers", return_value=[])
def test_get_llm_backend_returns_client_app_if_registered(mock_get_cloud, mock_openrouter_avail):
    providers.client_registry.client_registry.clear()
    providers.client_registry.client_registry["worker_1"] = {"id": "worker_1", "priority": 10, "model_name": "qwen3.5:9b"}
    backend = providers.get_llm_backend()
    assert isinstance(backend, ClientAppBackend)
    assert backend.model_name == "qwen3.5:9b"
    providers.client_registry.client_registry.clear()
    
@patch.object(OpenRouterBackend, "is_available", return_value=False)
@patch("controller.providers.llm.resolver.endpoints_cloud.get_cloud_providers", return_value=[])
def test_get_llm_backend_returns_none_if_no_worker(mock_get_cloud, mock_openrouter_avail):
    providers.client_registry.client_registry.clear()
    backend = providers.get_llm_backend()
    assert backend is None


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

    # Chunk 1: inicjalizacja nazwy i id
    chunk_1 = {
        "index": 0,
        "id": "call_abc123",
        "function": {"name": "execute_action", "arguments": '{"action":'}
    }
    OpenRouterBackend._accumulate_tool_call(accumulator, chunk_1, 0)

    assert 0 in accumulator
    assert accumulator[0]["id"] == "call_abc123"
    assert accumulator[0]["function"]["name"] == "execute_action"
    assert accumulator[0]["function"]["arguments"] == '{"action":'

    # Chunk 2: doklejenie argumentów
    chunk_2 = {
        "index": 0,
        "function": {"arguments": ' "turn_on"}'}
    }
    OpenRouterBackend._accumulate_tool_call(accumulator, chunk_2, 0)

    assert accumulator[0]["function"]["arguments"] == '{"action": "turn_on"}'


def test_predict_next_action_simple():
    import asyncio
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
