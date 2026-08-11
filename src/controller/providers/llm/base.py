"""
Abstrakcyjny interfejs backendu LLM.

Wszystkie konkretne backendy (Ollama, OpenRouter, ClientApp) dziedziczą
po tej klasie i implementują wymaganą logikę komunikacji z usługą LLM.
"""
from abc import abstractmethod
from typing import AsyncGenerator

from controller.providers.base import BaseBackend


class LLMBackend(BaseBackend):
    """Abstrakcyjny interfejs silnika LLM."""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Wykonuje pojedyncze zapytanie strumieniowe do dostawcy LLM.

        Generuje zdarzenia w postaci słowników:
        - {\"type\": \"content\", \"content\": token}
        - {\"type\": \"tool_calls\", \"tool_calls\": [...]}
        - {\"type\": \"profiler\", \"metric\": \"llm_ttft\", \"value\": ms}
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Zwraca True jeśli backend jest aktualnie dostępny."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Zwraca identyfikator dostawcy (np. 'ollama', 'openrouter')."""
        pass
