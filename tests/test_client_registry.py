import time
import pytest
from protocol.schemas import ServiceName
from controller.clients.registry import (
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
        "last_seen": time.time(),
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


def test_desktop_satellite_registration():
    client_registry["desktop-sat-1"] = {
        "id": "desktop-sat-1",
        "host": "192.168.1.50",
        "last_seen": time.time(),
        "services": {
            ServiceName.SATELLITE.value: {
                "room": "pracownia",
                "node_type": "desktop",
                "capabilities": ["audio_in", "audio_out", "text"],
                "wakeword_local": True
            }
        }
    }

    satellites = get_satellite_clients()
    assert len(satellites) == 1
    assert satellites[0]["id"] == "desktop-sat-1"
    assert satellites[0]["room"] == "pracownia"
    assert satellites[0]["type"] == "desktop"
    assert satellites[0]["wakeword_local"] is True

    # Klient Satelita nie dostarcza workerów LLM ani Audio, więc bez rejestracji audio_service lista get_audio_clients jest pusta
    assert len(get_llm_clients()) == 0
    assert len(get_audio_clients()) == 0
    assert get_client_room("desktop-sat-1") == "pracownia"


@pytest.mark.anyio
async def test_connection_manager_removes_failed_connection():
    from controller.clients.connections import ClientConnectionManager

    class BrokenWebSocket:
        async def send_text(self, _):
            raise RuntimeError("connection closed")

    manager = ClientConnectionManager()
    manager.active_connections["client-1"] = BrokenWebSocket()

    assert not await manager.send_command("client-1", "status")
    assert not manager.is_connected("client-1")
