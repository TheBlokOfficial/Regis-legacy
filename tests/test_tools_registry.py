import json

import pytest
from unittest.mock import MagicMock

from controller.agent.tools.registry import ToolsRegistry
from controller.integrations.ha_tools import HomeAssistantTools


def _schema(name: str) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "description": name, "parameters": {"type": "object"}},
    }


def test_registry_is_agnostic_and_executes_registered_handler():
    registry = ToolsRegistry()
    registry.register(_schema("example"), lambda arguments: json.dumps({"value": arguments["value"]}))

    assert json.loads(registry.execute_tool("example", {"value": 7})) == {"value": 7}
    assert [schema["function"]["name"] for schema in registry.get_tools_schema()] == ["example"]


def test_registry_rejects_duplicate_tool_name():
    registry = ToolsRegistry()
    registry.register(_schema("example"), lambda _: "{}")

    with pytest.raises(ValueError, match="już zarejestrowane"):
        registry.register(_schema("example"), lambda _: "{}")


def test_home_assistant_menu_is_limited_to_requested_room():
    integration = MagicMock()
    integration.get_all_states.return_value = {
        "light.salon": {"friendly_name": "Lampa salon"},
        "light.sypialnia": {"friendly_name": "Lampa sypialnia"},
    }
    integration.virtual_groups = {}
    integration.aliases = {}
    tools = HomeAssistantTools(
        integration,
        rooms={"salon": ["light.salon"], "sypialnia": ["light.sypialnia"]},
    )

    menu = tools.get_menu("salon")

    assert "light.salon" in menu
    assert "light.sypialnia" not in menu


def test_prompt_builder_passes_room_to_tool_menu():
    import controller.state as app_state
    from controller.agent.prompt.builder import build_system_prompt

    registry = ToolsRegistry()
    registry.register(_schema("example"), lambda _: "{}", menu_provider=lambda room: f"menu:{room}")
    previous_registry = app_state.tools_registry
    app_state.tools_registry = registry
    try:
        prompt = build_system_prompt("salon")
    finally:
        app_state.tools_registry = previous_registry

    assert "menu:salon" in prompt
