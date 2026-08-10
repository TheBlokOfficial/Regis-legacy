"""
Silniki Wykonawcze (Backendy) mowy (STT / TTS).

Klasy wykonujące niskopoziomowe zapytania sieciowe HTTP do serwerów mowy.
"""
import time
import logging
import asyncio
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAudioBackend:
    """Bazowa klasa dla backendów audio."""

    def __init__(self, id: str, name: str, host: str = "127.0.0.1", port: int = 8002, endpoint_path: str = ""):
        self.id = id
        self.name = name
        self.host = host
        self.port = port
        self.endpoint_path = endpoint_path

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}{self.endpoint_path}"


class AudioServiceSTTBackend(BaseAudioBackend):
    """Silnik transkrypcji mowy (STT) dla daemona Audio Service (Faster-Whisper)."""

    def __init__(
        self,
        id: str = "audio-service-stt",
        name: str = "Audio Service STT (Faster-Whisper)",
        host: str = "127.0.0.1",
        port: int = 8002,
        model_size: str = "small",
    ):
        super().__init__(
            id=id,
            name=name,
            host=host,
            port=port,
            endpoint_path="/v1/stt/transcribe",
        )
        self.model_size = model_size

    async def transcribe(self, audio_bytes: bytes) -> tuple[str | None, int]:
        """Wysyła plik WAV multipart do /v1/stt/transcribe."""
        t_start = time.time()
        try:
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            resp = await asyncio.to_thread(requests.post, self.url, files=files, timeout=(1.0, 30.0))
            resp.raise_for_status()
            data = resp.json()
            text = data.get("text", "")
            elapsed_ms = data.get("elapsed_ms") or int((time.time() - t_start) * 1000)
            return (text if text else None), elapsed_ms
        except Exception as e:
            logger.exception(f"[AudioServiceSTTBackend] Błąd transkrypcji mowy: {e}")
            return None, int((time.time() - t_start) * 1000)


class AudioServiceTTSBackend(BaseAudioBackend):
    """Silnik syntezy głosu (TTS) dla daemona Audio Service (Piper)."""

    def __init__(
        self,
        id: str = "audio-service-tts",
        name: str = "Audio Service TTS (Piper)",
        host: str = "127.0.0.1",
        port: int = 8002,
        voice_name: str = "pl_PL-darkman-medium",
    ):
        super().__init__(
            id=id,
            name=name,
            host=host,
            port=port,
            endpoint_path="/v1/tts/synthesize",
        )
        self.voice_name = voice_name

    async def synthesize(self, text: str) -> tuple[str | None, int]:
        """Wysyła JSON {"text": ...} do /v1/tts/synthesize."""
        t_start = time.time()
        try:
            resp = await asyncio.to_thread(
                requests.post, self.url, json={"text": text}, timeout=(1.0, 30.0)
            )
            if resp.ok:
                data = resp.json()
                b64_audio = data.get("audio_b64")
                elapsed_ms = data.get("elapsed_ms") or int((time.time() - t_start) * 1000)
                return b64_audio, elapsed_ms

            logger.warning(f"[AudioServiceTTSBackend] Błąd odpowiedzi HTTP {resp.status_code}")
            return None, int((time.time() - t_start) * 1000)
        except Exception as e:
            logger.warning(f"[AudioServiceTTSBackend] Wyjątek syntezy głosu: {e}")
            return None, int((time.time() - t_start) * 1000)
