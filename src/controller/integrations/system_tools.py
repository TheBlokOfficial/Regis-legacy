"""Wbudowane, niezależne od urządzeń narzędzia systemowe Regisa."""
from __future__ import annotations

import datetime
import json
from typing import Any

import requests

from controller.agent.tools.registry import ToolsRegistry


CURRENT_TIME_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Zwraca bieżącą datę i czas systemowy wraz z dniem tygodnia.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

WEATHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Zwraca aktualne informacje o pogodzie w podanym mieście.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Nazwa miasta, np. 'Warszawa'."}
            },
            "required": ["location"],
        },
    },
}


class SystemTools:
    """Rejestruje podstawowe narzędzia, które nie należą do zewnętrznej integracji."""

    def register_tools(self, registry: ToolsRegistry) -> None:
        registry.register(CURRENT_TIME_SCHEMA, self._get_current_time)
        registry.register(WEATHER_SCHEMA, self._get_weather)

    @staticmethod
    def _get_current_time(_: dict[str, Any]) -> str:
        now = datetime.datetime.now()
        days = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        return json.dumps(
            {"current_time": now.strftime("%Y-%m-%d %H:%M:%S"), "day_of_week": days[now.weekday()]},
            ensure_ascii=False,
        )

    @staticmethod
    def _get_weather(arguments: dict[str, Any]) -> str:
        location = arguments.get("location")
        if not location:
            return json.dumps({"error": "Musisz podać nazwę miasta."}, ensure_ascii=False)

        try:
            response = requests.get(f"https://wttr.in/{location}?format=j1", timeout=10)
            response.raise_for_status()
            current = response.json().get("current_condition", [{}])[0]
            if not current:
                return json.dumps({"error": "Nie znaleziono danych o pogodzie."}, ensure_ascii=False)

            descriptions = current.get("lang_pl", [])
            description = descriptions[0].get("value") if descriptions else current.get("weatherDesc", [{}])[0].get("value")
            return json.dumps(
                {
                    "location": location,
                    "description": description,
                    "temperature_C": current.get("temp_C"),
                    "feels_like_C": current.get("FeelsLikeC"),
                    "humidity_percent": current.get("humidity"),
                    "wind_speed_kmh": current.get("windspeedKmph"),
                },
                ensure_ascii=False,
            )
        except requests.RequestException as exc:
            return json.dumps({"error": f"Nie udało się połączyć z serwisem pogodowym: {exc}"}, ensure_ascii=False)
