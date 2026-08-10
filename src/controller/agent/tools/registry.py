"""Mechanizm rejestracji i wykonywania narzędzi agenta.

Moduł jest agnostyczny wobec źródła narzędzia. Konkretne implementacje należą
do integracji, które rejestrują swoje kontrakty podczas startu aplikacji.
"""
from __future__ import annotations

import copy
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


ToolHandler = Callable[[dict[str, Any]], str]
MenuProvider = Callable[[str | None], str]


@dataclass(frozen=True)
class RegisteredTool:
    """Kompletny kontrakt pojedynczego narzędzia dostępnego dla LLM."""

    schema: dict[str, Any]
    handler: ToolHandler


class ToolsRegistry:
    """Rejestr kontraktów narzędzi i ich handlerów, bez logiki integracji."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._menu_providers: list[MenuProvider] = []

    def register(
        self,
        schema: dict[str, Any],
        handler: ToolHandler,
        *,
        menu_provider: MenuProvider | None = None,
    ) -> None:
        """Rejestruje narzędzie zgodne z formatem function calling."""
        name = schema.get("function", {}).get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("Schemat narzędzia musi zawierać function.name.")
        if name in self._tools:
            raise ValueError(f"Narzędzie '{name}' jest już zarejestrowane.")

        self._tools[name] = RegisteredTool(schema=copy.deepcopy(schema), handler=handler)
        if menu_provider is not None and menu_provider not in self._menu_providers:
            self._menu_providers.append(menu_provider)

    def get_tools_schema(self, names: list[str] | None = None) -> list[dict[str, Any]]:
        """Zwraca niezależne kopie schematów narzędzi dostępnych dla modelu."""
        selected = self._tools.items() if names is None else (
            (name, self._tools[name]) for name in names if name in self._tools
        )
        return [copy.deepcopy(tool.schema) for _, tool in selected]

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Wykonuje handler zarejestrowanego narzędzia i normalizuje błąd do JSON."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return json.dumps({"error": f"Narzędzie '{tool_name}' nie istnieje."}, ensure_ascii=False)

        try:
            return tool.handler(arguments)
        except Exception as exc:
            logging.exception("Błąd wykonania narzędzia %s", tool_name)
            return json.dumps(
                {"error": f"Wystąpił błąd podczas wykonania narzędzia: {exc}"},
                ensure_ascii=False,
            )

    def get_menu(self, room: str | None = None) -> str:
        """Buduje kontekst narzędziowy, opcjonalnie ograniczony do pokoju."""
        sections = [provider(room).strip() for provider in self._menu_providers]
        return "\n\n".join(section for section in sections if section)
