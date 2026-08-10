"""Narzędzia agenta dostarczane przez integrację Home Assistant."""
from __future__ import annotations

import json
from typing import Any

from controller.agent.tools.registry import ToolsRegistry


GET_DEVICE_STATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_device_state",
        "description": "Zwraca dokładny obecny stan urządzenia dla podanego entity_id.",
        "parameters": {
            "type": "object",
            "properties": {"entity_id": {"type": "array", "items": {"type": "string"}}},
            "required": ["entity_id"],
        },
    },
}

EXECUTE_ACTION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_action",
        "description": "Wykonuje akcję Home Assistant na urządzeniu z kontekstu agenta.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["turn_on", "turn_off", "toggle"]},
                "entity_id": {"type": "array", "items": {"type": "string"}},
                "parameters": {"type": "object"},
            },
            "required": ["action", "entity_id"],
        },
    },
}

PHONE_BATTERY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_phone_battery",
        "description": "Zwraca poziom baterii telefonu skonfigurowanego w Home Assistant.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


class HomeAssistantTools:
    """Adapter narzędziowy nad obiektem integracji Home Assistant."""

    def __init__(self, integration: Any, rooms: dict[str, Any] | None = None) -> None:
        self.integration = integration
        if rooms is None:
            from controller.config.loader import load
            from controller.config.schemas import RoomsConfig

            rooms = load(RoomsConfig).root
        self.rooms = rooms

    def register_tools(self, registry: ToolsRegistry) -> None:
        registry.register(GET_DEVICE_STATE_SCHEMA, self._get_device_state, menu_provider=self.get_menu)
        registry.register(EXECUTE_ACTION_SCHEMA, self._execute_action)
        registry.register(PHONE_BATTERY_SCHEMA, self._get_phone_battery)

    @staticmethod
    def _extract_room_info(room_data: Any) -> tuple[str | None, list[str], list[str]]:
        if hasattr(room_data, "devices"):
            return (
                getattr(room_data, "name", None),
                getattr(room_data, "metadata", []) or [],
                getattr(room_data, "devices", []) or [],
            )
        if isinstance(room_data, dict):
            return room_data.get("name"), room_data.get("metadata", []) or [], room_data.get("devices", []) or []
        if isinstance(room_data, list):
            return None, [], room_data
        return None, [], []

    def _get_devices(self, domain: str | None = None, room: str | None = None) -> list[dict[str, Any]]:
        states = self.integration.get_all_states() if self.integration else {}
        raw_room_data = self.rooms.get(room) if room and self.rooms else None
        _, _, room_filter = self._extract_room_info(raw_room_data) if raw_room_data is not None else (None, [], None)

        virtual_groups = getattr(self.integration, "virtual_groups", {}) if self.integration else {}
        aliases = getattr(self.integration, "aliases", {}) if self.integration else {}
        virtual_groups = virtual_groups if isinstance(virtual_groups, dict) else {}
        aliases = aliases if isinstance(aliases, dict) else {}

        room_entities = {
            entity
            for room_data in self.rooms.values()
            for entity in self._extract_room_info(room_data)[2]
        }
        devices: list[dict[str, Any]] = []

        for entity_id, data in states.items():
            if domain and not entity_id.startswith(f"{domain}."):
                continue
            if room_filter is not None and entity_id not in room_filter:
                continue
            if any(entity_id in children for children in virtual_groups.values()):
                continue
            if entity_id in aliases or entity_id in room_entities:
                devices.append({"entity_id": entity_id, "name": data.get("friendly_name", "Nieznana nazwa")})

        for group_id, children in virtual_groups.items():
            group_domain = group_id.split(".", 1)[0] if "." in group_id else ""
            if domain and group_domain != domain:
                continue
            belongs_to_room = room_filter is None or (room and room in group_id) or any(
                child in room_filter for child in children
            )
            if belongs_to_room:
                group_name = group_id.split(".", 1)[-1].replace("_", " ").title()
                devices.append({"entity_id": group_id, "name": f"{group_name} (Grupa)"})

        return devices

    def get_menu(self, room: str | None = None) -> str:
        """Zwraca menu urządzeń ograniczone do pokoju, gdy jest on znany."""
        devices = self._get_devices(room=room)
        if not devices:
            return "BRAK URZĄDZEŃ W DOSTĘPNYM KONTEKŚCIE."

        title = f"DOSTĘPNE URZĄDZENIA W POKOJU {room.upper()}:" if room else "DOSTĘPNE URZĄDZENIA:"
        return "\n".join([title, *(f"- {device['entity_id']} ({device['name']})" for device in devices)])

    def _get_device_state(self, arguments: dict[str, Any]) -> str:
        entity_id = arguments.get("entity_id")
        if not entity_id:
            return json.dumps({"error": "Brak entity_id."}, ensure_ascii=False)

        states = self.integration.get_all_states()
        groups = getattr(self.integration, "virtual_groups", {}) or {}
        entity_ids = [entity_id] if isinstance(entity_id, str) else entity_id
        results: dict[str, Any] = {}
        for current_id in entity_ids:
            if current_id in groups:
                children = self.integration._flatten_entities(current_id)
                results[current_id] = {
                    "state": "on" if any(states.get(child, {}).get("state") == "on" for child in children) else "off",
                    "friendly_name": f"{current_id.split('.')[-1].replace('_', ' ').title()} (Grupa)",
                    "attributes": {},
                }
            else:
                results[current_id] = states.get(current_id, {"error": "Urządzenie nie znalezione."})

        return json.dumps(results[entity_id] if isinstance(entity_id, str) else results, ensure_ascii=False)

    def _execute_action(self, arguments: dict[str, Any]) -> str:
        action = arguments.get("action")
        entity_id = arguments.get("entity_id")
        if action not in {"turn_on", "turn_off", "toggle"}:
            return json.dumps({"error": f"Nieprawidłowa akcja: '{action}'."}, ensure_ascii=False)
        try:
            success = self.integration.execute_action(action, entity_id, arguments.get("parameters"))
        except Exception as exc:
            return json.dumps({"error": f"Wystąpił błąd podczas wykonania akcji: {exc}"}, ensure_ascii=False)
        if success:
            return json.dumps({"result": "success", "message": f"Wykonano {action} na {entity_id}."}, ensure_ascii=False)
        return json.dumps({"error": f"Akcja {action} nie powiodła się dla {entity_id}."}, ensure_ascii=False)

    def _get_phone_battery(self, _: dict[str, Any]) -> str:
        try:
            return json.dumps(self.integration.get_phone_battery(), ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"battery_level": "unknown", "battery_state": "error", "detail": str(exc)}, ensure_ascii=False)
