"""
Testy jednostkowe dla rejestru klientów w Kontrolerze (client_registry.py).
"""
import pytest
from protocol.schemas import ServiceName
from controller.core.client_registry import (
    client_registry,
    get_audio_clients,
    get_llm_clients,
    get_satellite_clients,
    get_client_room,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    client_registry.clear()
    yield
    client_registry.clear()


def test_get_audio_clients_with_stt_and_tts_worker():
    client_registry["node-test"] = {
        "id": "node-test",
        "host": "192.168.0.100",
        "services": {
            ServiceName.SATELLITE.value: {"room": "salon"},
            ServiceName.STT_WORKER.value: {"port": 8002, "stt_model_size": "small"},
            ServiceName.TTS_WORKER.value: {"port": 8002, "tts_model_name": "pl_PL-darkman-medium"},
            ServiceName.OLLAMA_WORKER.value: {"port": 8001, "model_name": "qwen3.5:9b"},
        },
    }

    audio_clients = get_audio_clients()
    assert len(audio_clients) == 1
    assert audio_clients[0]["id"] == "node-test"
    assert audio_clients[0]["base_url"] == "http://192.168.0.100:8002"
    assert audio_clients[0]["stt_model_size"] == "small"

    llm_clients = get_llm_clients()
    assert len(llm_clients) == 1
    assert llm_clients[0]["id"] == "node-test"
    assert llm_clients[0]["model_name"] == "qwen3.5:9b"

    satellites = get_satellite_clients()
    assert len(satellites) == 1
    assert satellites[0]["id"] == "node-test"
    assert satellites[0]["room"] == "salon"

    assert get_client_room("node-test") == "salon"
