"""
Pakiet ról Providerów (zmysłów) w Kontrolerze.
"""
from controller.core.providers.base import BaseProvider
from controller.core.providers.stt import STTProvider
from controller.core.providers.tts import TTSProvider
from controller.core.providers.llm import LLMProvider

__all__ = [
    "BaseProvider",
    "STTProvider",
    "TTSProvider",
    "LLMProvider",
]
