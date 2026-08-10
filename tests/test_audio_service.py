"""
Testy jednostkowe dla daemona Audio Service (STT + TTS).
"""
import pytest
from fastapi.testclient import TestClient
from audio_service.main import app
from audio_service.stt import STTEngine
from audio_service.tts import TTSEngine

client = TestClient(app)


def test_audio_service_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "audio_service"
    assert "stt_model" in data
    assert "tts_voice" in data


def test_stt_engine_transcribe():
    engine = STTEngine(model_size="small", language="pl")
    res = engine.transcribe(b"fake_wav_bytes")
    assert "text" in res
    assert "elapsed_ms" in res
    assert res["language"] == "pl"


def test_tts_engine_synthesize():
    engine = TTSEngine(voice_name="pl_PL-darkman-medium")
    res = engine.synthesize("Witaj w systemie Regis")
    assert "audio_b64" in res
    assert len(res["audio_b64"]) > 0
    assert "elapsed_ms" in res
    assert res["voice"] == "pl_PL-darkman-medium"


def test_stt_transcribe_endpoint():
    response = client.post(
        "/v1/stt/transcribe",
        files={"file": ("test.wav", b"dummy_wav_data", "audio/wav")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "elapsed_ms" in data


def test_tts_synthesize_endpoint():
    response = client.post(
        "/v1/tts/synthesize",
        json={"text": "Test syntezy mowy"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "audio_b64" in data
    assert len(data["audio_b64"]) > 0
    assert "elapsed_ms" in data
