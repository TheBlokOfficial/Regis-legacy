"""
Klasa LLMChannel — Zarządca Zmysłu Językowego w Kontrolerze.

Przechowuje przypisany aktywny silnik LLMBackend i udostępnia spójny interfejs
strumieniowania tekstu dla Orkiestratora, ukrywając przed aplikacją konkretną
implementację silnika (Ollama, OpenRouter, itp.).
"""
import logging
from typing import Optional, AsyncGenerator
from controller.providers.llm.base import LLMBackend

logger = logging.getLogger(__name__)


class LLMChannel:
    """
    Zarządca Zmysłu Językowego (LLM).
    Hermetyzuje wybrany backend wykonawczy LLMBackend.
    """

    def __init__(self, backend: Optional[LLMBackend] = None):
        self._backend = backend

    def set_backend(self, backend: Optional[LLMBackend]) -> None:
        """Ustawia lub podmienia aktywny silnik LLM."""
        self._backend = backend
        name = backend.get_provider_name() if backend else "Brak"
        logger.debug(f"[LLMChannel] Ustawiono aktywny backend LLM: {name}")

    @property
    def backend(self) -> Optional[LLMBackend]:
        """Zwraca obecny silnik LLM lub None."""
        return self._backend

    @property
    def is_ready(self) -> bool:
        """Zmysł językowy jest aktywny, gdy silnik jest przypisany i zgłasza dostępność."""
        return self._backend is not None

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Deleguje strumieniowanie odpowiedzi konwersacyjnej bezpośrednio do silnika.
        Rzuca RuntimeError jeśli zmysł LLM jest niegotowy.
        """
        if not self._backend:
            raise RuntimeError("Zmysł LLM jest nieaktywny — brak przypisanego silnika LLMBackend.")

        async for chunk in self._backend.chat_stream(messages, tools=tools):
            yield chunk
