"""Testy jednostkowe dla Spatial Context Filtering.

Testują:
- Filtrowanie urządzeń w ToolsRegistry per pokój (_get_devices)
"""
import json
import pytest
from unittest.mock import MagicMock

from controller.agent.tools.registry import ToolsRegistry


# ─── Fixtures ─────────────────────────────────────────────────────────────────

ROOMS = {
    "salon": ["light.salon_lampa", "switch.salon_tv"],
    "sypialnia": ["light.sypialnia_lampa"],
}

HA_STATES = {
    "light.salon_lampa":    {"state": "on",  "friendly_name": "Lampa w salonie"},
    "switch.salon_tv":      {"state": "off", "friendly_name": "Telewizor"},
    "light.sypialnia_lampa":{"state": "off", "friendly_name": "Lampa w sypialni"},
    "light.kuchnia_spot":   {"state": "on",  "friendly_name": "Spot kuchenny"},
}


def _make_registry(rooms: dict = None) -> ToolsRegistry:
    """Buduje ToolsRegistry z mockiem HA i opcjonalnym słownikiem pokojów."""
    ha_mock = MagicMock()
    ha_mock.get_all_states.return_value = HA_STATES
    return ToolsRegistry(ha_client=ha_mock, rooms=rooms if rooms is not None else {})


# ─── Testy filtrowania w ToolsRegistry ────────────────────────────────────────

def test_get_devices_no_room_returns_all():
    """Brak room → wszystkie urządzenia z listy room_entities / aliasów."""
    registry = _make_registry(ROOMS)
    result = json.loads(registry._get_devices(room=None))
    entity_ids = [d["entity_id"] for d in result["devices"]]
    assert len(entity_ids) == 3
    assert "light.salon_lampa" in entity_ids
    assert "light.kuchnia_spot" not in entity_ids


def test_get_devices_room_salon():
    """room='salon' → tylko urządzenia z salonu."""
    registry = _make_registry(ROOMS)
    result = json.loads(registry._get_devices(room="salon"))
    entity_ids = [d["entity_id"] for d in result["devices"]]
    assert set(entity_ids) == {"light.salon_lampa", "switch.salon_tv"}


def test_get_devices_room_sypialnia():
    """room='sypialnia' → tylko urządzenia z sypialni."""
    registry = _make_registry(ROOMS)
    result = json.loads(registry._get_devices(room="sypialnia"))
    entity_ids = [d["entity_id"] for d in result["devices"]]
    assert entity_ids == ["light.sypialnia_lampa"]


def test_get_devices_unknown_room_returns_all():
    """Nieznany pokój → urządzenia przypisane do dowolnego pokoju."""
    registry = _make_registry(ROOMS)
    result = json.loads(registry._get_devices(room="garaz"))
    assert len(result["devices"]) == 3


def test_get_devices_no_rooms_config_returns_empty():
    """Brak pokoi (pusty słownik) → brak filtrów i przypisanych urządzeń."""
    registry = _make_registry(rooms={})
    result = json.loads(registry._get_devices(room="salon"))
    assert len(result["devices"]) == 0


def test_get_devices_room_and_domain_combined():
    """Filtrowanie po room i domain jednocześnie."""
    registry = _make_registry(ROOMS)
    result = json.loads(registry._get_devices(domain="switch", room="salon"))
    entity_ids = [d["entity_id"] for d in result["devices"]]
    assert entity_ids == ["switch.salon_tv"]
