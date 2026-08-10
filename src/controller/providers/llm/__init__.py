"""
Pakiet zmysłu językowego (LLM).
"""
import os
import logging
from typing import Optional

from controller.endpoints import cloud as endpoints_cloud
from controller.providers.llm.base import LLMBackend
from controller.providers.llm.ollama import OllamaBackend
from controller.providers.llm.openrouter import OpenRouterBackend
from controller.providers.llm.service import LLMChannel

logger = logging.getLogger(__name__)


async def get_active_llm() -> Optional[LLMBackend]:
    """Inicjalizuje domyślny silnik LLM (OpenRouter chmura lub Ollama) na podstawie konfiguracji."""
    for cp in endpoints_cloud.get_cloud_providers():
        if cp.type == "openrouter" and cp.api_key and cp.model:
            try:
                backend = OpenRouterBackend(api_key=cp.api_key, model_name=cp.model)
                if await backend.is_available():
                    return backend
            except Exception as e:
                logger.warning(f"[LLM] Błąd inicjalizacji chmury {cp.id}: {e}")

    try:
        from controller.config import loader as config
        settings = config.load_config("settings")
        ollama_host = os.environ.get("OLLAMA_HOST", settings.get("ollama_url", "http://127.0.0.1:11434"))
        ollama_model = os.environ.get("OLLAMA_MODEL", settings.get("ollama_model", "qwen3.5:9b"))
        ollama_backend = OllamaBackend(host=ollama_host, model_name=ollama_model)
        if await ollama_backend.is_available():
            return ollama_backend
    except Exception as e:
        logger.warning(f"[LLM] Błąd inicjalizacji OllamaBackend: {e}")

    return None


__all__ = [
    "endpoints_cloud",
    "LLMBackend",
    "OllamaBackend",
    "OpenRouterBackend",
    "LLMChannel",
    "get_active_llm",
]
