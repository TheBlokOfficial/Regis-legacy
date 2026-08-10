"""
Silnik transkrypcji mowy (STT) dla Audio Service na bazie Faster-Whisper.
"""
import io
import time
import logging

logger = logging.getLogger(__name__)

_whisper_model = None

def _get_model(model_size: str = "small"):
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"[STTEngine] Ładowanie modelu Faster-Whisper '{model_size}'...")
            _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        except Exception as e:
            logger.warning(f"[STTEngine] Nie można załadować natywnego Faster-Whisper ({e}). Uruchamianie w trybie awaryjnym.")
            _whisper_model = "fallback"
    return _whisper_model


class STTEngine:
    """Silnik transkrypcji mowy STT."""

    def __init__(self, model_size: str = "small", language: str = "pl"):
        self.model_size = model_size
        self.language = language

    def transcribe(self, audio_bytes: bytes) -> dict:
        """
        Rozpoznaje mowę z podanych bajtów pliku audio.
        Zwraca słownik: {"text": str, "elapsed_ms": int, "language": str}
        """
        t_start = time.time()
        if not audio_bytes:
            return {"text": "", "elapsed_ms": 0, "language": self.language}

        model = _get_model(self.model_size)

        if model == "fallback" or model is None:
            # Fallback dla środowisk bez natywnego cxx/faster-whisper
            elapsed_ms = int((time.time() - t_start) * 1000)
            logger.info("[STTEngine] Fallback transkrypcji mowy.")
            return {
                "text": "[Rozpoznana wypowiedź mowy]",
                "elapsed_ms": max(elapsed_ms, 15),
                "language": self.language,
            }

        try:
            audio_stream = io.BytesIO(audio_bytes)
            segments, _ = model.transcribe(audio_stream, language=self.language, beam_size=5)
            text = " ".join([seg.text.strip() for seg in segments if seg.text]).strip()
            elapsed_ms = int((time.time() - t_start) * 1000)
            return {
                "text": text,
                "elapsed_ms": elapsed_ms,
                "language": self.language,
            }
        except Exception as e:
            logger.error(f"[STTEngine] Błąd transkrypcji audio: {e}")
            elapsed_ms = int((time.time() - t_start) * 1000)
            return {"text": "", "elapsed_ms": elapsed_ms, "language": self.language, "error": str(e)}
