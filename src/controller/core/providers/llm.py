"""
Klasa LLMProvider dla zmysłu inteligencji agenta w Kontrolerze.
"""
from typing import Any
from controller.core.providers.base import BaseProvider


class LLMProvider(BaseProvider):
    """Obiektowa rola zmysłu inteligencji agenta (LLM) dla Orkiestratora."""

    def __init__(self, id: str, name: str, backend: Any = None, **kwargs):
        super().__init__(id=id, name=name, backend=backend, **kwargs)
