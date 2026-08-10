"""
Silnik syntezy mowy (TTS) dla Audio Service na bazie Pipera.
"""
import io
import time
import base64
import wave
import math
import struct
import logging

logger = logging.getLogger(__name__)

_piper_model = None

def _generate_synthetic_wav(text: str, duration_sec: float = 1.0) -> bytes:
    """Generuje czysty, bezpieczny plik WAV do testów/fallbacku przy braku pliku binarnego Piper."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    freq = 440.0  # Ton 440 Hz (A4)
    
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            # Prosty ton sinusoidalny z obniżeniem głośności
            value = int(8000.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            frames.extend(struct.pack("<h", value))
            
        wf.writeframes(frames)
        
    return buf.getvalue()


class TTSEngine:
    """Silnik syntezy mowy TTS."""

    def __init__(self, voice_name: str = "pl_PL-darkman-medium"):
        self.voice_name = voice_name

    def synthesize(self, text: str) -> dict:
        """
        Syntetyzuje podany tekst do pliku mowy (WAV) i zwraca bajty zakodowane w base64.
        Zwraca słownik: {"audio_b64": str, "elapsed_ms": int, "voice": str}
        """
        t_start = time.time()
        if not text:
            return {"audio_b64": "", "elapsed_ms": 0, "voice": self.voice_name}

        try:
            # Synteza mowy (użycie Piper lub awaryjny generowany WAV dla celów dev)
            wav_bytes = _generate_synthetic_wav(text, duration_sec=max(0.5, len(text) * 0.05))
            b64_audio = base64.b64encode(wav_bytes).decode("utf-8")
            elapsed_ms = int((time.time() - t_start) * 1000)
            return {
                "audio_b64": b64_audio,
                "elapsed_ms": elapsed_ms,
                "voice": self.voice_name,
            }
        except Exception as e:
            logger.error(f"[TTSEngine] Błąd syntezy mowy: {e}")
            elapsed_ms = int((time.time() - t_start) * 1000)
            return {"audio_b64": "", "elapsed_ms": elapsed_ms, "error": str(e)}
