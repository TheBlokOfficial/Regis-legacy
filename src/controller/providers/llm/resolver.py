"""
Resolver / Fabryka Backendów LLM.

Jedno miejsce wyliczające i zwracające najlepszy dostępny backend LLM
(usługi aplikacji klienckich, konfiguracje chmurowe lub lokalną Ollamę) według priorytetów.
"""
import logging
import os

import controller.core.client_registry as client_registry
import controller.endpoints.cloud as endpoints_cloud
from controller.config import loader as config
from controller.providers.llm.base import LLMBackend
from controller.providers.llm.openrouter import OpenRouterBackend
from controller.providers.llm.client_app import ClientAppBackend
from controller.providers.llm.ollama import OllamaBackend

logger = logging.getLogger(__name__)


async def get_active_llm() -> LLMBackend | None:
    """Zwraca najlepszy dostępny backend LLM według priorytetu."""
    candidates: list[tuple[int, LLMBackend]] = []

    # 1. Zarejestrowane usługi aplikacji klienckich (np. Regis Desktop)
    for worker in client_registry.client_registry.values():
        prio = worker.get("priority", 10)
        model_name = worker.get("model_name", "qwen3.5:9b")
        client_id = worker.get("id", "")
        if client_id:
            candidates.append((prio, ClientAppBackend(client_id=client_id, model_name=model_name)))

    # 2. Dostawcy chmurowi zarejestrowani w cloud_store
    for cp in endpoints_cloud.get_cloud_providers():
        if cp.type == "openrouter" and cp.api_key and cp.model:
            try:
                backend = OpenRouterBackend(api_key=cp.api_key, model_name=cp.model)
                if await backend.is_available():
                    candidates.append((cp.priority, backend))
            except Exception as e:
                logger.warning(f"Błąd ładowania chmury {cp.id}: {e}")

    # 3. Lokalny OllamaBackend
    try:
        settings = config.load_config("settings")
        ollama_host = os.environ.get("OLLAMA_HOST", settings.get("ollama_url", "http://127.0.0.1:11434"))
        ollama_model = os.environ.get("OLLAMA_MODEL", settings.get("ollama_model", "qwen3.5:9b"))
        ollama_backend = OllamaBackend(host=ollama_host, model_name=ollama_model)
        if await ollama_backend.is_available():
            candidates.append((1, ollama_backend))
    except Exception as e:
        logger.warning(f"Błąd ładowania OllamaBackend: {e}")

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected_prio, selected_backend = candidates[0]

    logger.debug(f"Wybrano LLM Backend: {selected_backend.get_provider_name()} z priorytetem {selected_prio}")
    return selected_backend


async def has_active_llm() -> bool:
    """Zwraca True, jeśli dostępny jest jakikolwiek aktywny backend LLM."""
    return await get_active_llm() is not None
