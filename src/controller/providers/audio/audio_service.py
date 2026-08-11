"""
Silniki Wykonawcze HTTP dla Stacjonarnej Usługi Audio Service (Faster-Whisper STT / Piper TTS).
"""
import time
import logging
import httpx
from typing import Any

from controller.providers.audio.base import STTBackend, TTSBackend

logger = logging.getLogger(__name__)


class AudioServiceSTTBackend(STTBackend):
    """Silnik transkrypcji mowy (STT) komunikujący się z daemonem Audio Service (Faster-Whisper)."""

    def __init__(
        self,
        id: str = "audio-service-stt",
        name: str = "Audio Service STT (Faster-Whisper)",
        base_url: str = "http://127.0.0.1:8002",
        model_size: str = "small",
    ):
        super().__init__(id=id, name=name)
        self.base_url = base_url.rstrip("/")
        self.model_size = model_size
        self.last_seen: float = time.time()

    @classmethod
    def create_and_register(cls, config_data: Any) -> None:
        from controller.providers import registry
        host = getattr(config_data, "host", "127.0.0.1")
        port = getattr(config_data, "port", 8002)
        base_url = getattr(config_data, "base_url", f"http://{host}:{port}")
        backend_id = f"{getattr(config_data, 'id', 'audio-service')}-stt"
        backend_name = f"{getattr(config_data, 'name', 'Audio Service')} (STT)"
        
        backend = cls(id=backend_id, name=backend_name, base_url=base_url)
        backend.last_seen = 0  # Domyślnie offline przed pierwszym heartbeatem
        registry.register_stt(backend)

    def touch(self) -> None:
        """Odświeża znacznik czasu ostatniego heartbeatu."""
        self.last_seen = time.time()

    @property
    def is_online(self) -> bool:
        """Zwraca True jeśli daemon wysłał heartbeat w ciągu ostatnich 30 sekund."""
        return (time.time() - self.last_seen) <= 30

    async def transcribe(self, audio_bytes: bytes) -> tuple[str | None, int]:
        """Wysyła plik WAV multipart do /v1/stt/transcribe."""
        t_start = time.time()
        url = f"{self.base_url}/v1/stt/transcribe"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=1.0, read=30.0, write=5.0, pool=5.0)) as client:
                response = await client.post(
                    url,
                    files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("text", "")
                elapsed_ms = data.get("elapsed_ms") or int((time.time() - t_start) * 1000)
                return (text if text else None), elapsed_ms
        except Exception as e:
            logger.exception(f"[AudioServiceSTTBackend] Błąd transkrypcji mowy: {e}")
            return None, int((time.time() - t_start) * 1000)


class AudioServiceTTSBackend(TTSBackend):
    """Silnik syntezy głosu (TTS) komunikujący się z daemonem Audio Service (Piper)."""

    def __init__(
        self,
        id: str = "audio-service-tts",
        name: str = "Audio Service TTS (Piper)",
        base_url: str = "http://127.0.0.1:8002",
        voice_name: str = "pl_PL-darkman-medium",
    ):
        super().__init__(id=id, name=name)
        self.base_url = base_url.rstrip("/")
        self.voice_name = voice_name

    @classmethod
    def create_and_register(cls, config_data: Any) -> None:
        from controller.providers import registry
        host = getattr(config_data, "host", "127.0.0.1")
        port = getattr(config_data, "port", 8002)
        base_url = getattr(config_data, "base_url", f"http://{host}:{port}")
        backend_id = f"{getattr(config_data, 'id', 'audio-service')}-tts"
        backend_name = f"{getattr(config_data, 'name', 'Audio Service')} (TTS)"
        
        backend = cls(id=backend_id, name=backend_name, base_url=base_url)
        backend.last_seen = 0
        registry.register_tts(backend)

    def touch(self) -> None:
        """Odświeża znacznik czasu ostatniego heartbeatu."""
        self.last_seen = time.time()

    @property
    def is_online(self) -> bool:
        """Zwraca True jeśli daemon wysłał heartbeat w ciągu ostatnich 30 sekund."""
        return (time.time() - self.last_seen) <= 30

    async def synthesize(self, text: str) -> tuple[str | None, int]:
        """Wysyła JSON {\"text\": ...} do /v1/tts/synthesize."""
        t_start = time.time()
        url = f"{self.base_url}/v1/tts/synthesize"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=1.0, read=30.0, write=5.0, pool=5.0)) as client:
                response = await client.post(url, json={"text": text})
                if response.is_success:
                    data = response.json()
                    b64_audio = data.get("audio_b64")
                    elapsed_ms = data.get("elapsed_ms") or int((time.time() - t_start) * 1000)
                    return b64_audio, elapsed_ms
                logger.warning(f"[AudioServiceTTSBackend] Błąd odpowiedzi HTTP {response.status_code}")
                return None, int((time.time() - t_start) * 1000)
        except Exception as e:
            logger.warning(f"[AudioServiceTTSBackend] Wyjątek syntezy głosu: {e}")
            return None, int((time.time() - t_start) * 1000)
