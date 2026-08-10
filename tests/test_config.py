import pytest
from controller.config.loader import load_config, load
from controller.config.schemas import SystemSettings, AliasesConfig

def test_load_config_defaults():
    config_dict = load_config("non_existent_test_config", default={"test_key": "test_val"})
    assert config_dict == {"test_key": "test_val"}

def test_system_settings_schema():
    settings = load(SystemSettings)
    assert hasattr(settings, "ha_url")
    assert hasattr(settings, "ha_token")
    assert hasattr(settings, "log_level")

def test_aliases_config_schema():
    aliases = load(AliasesConfig)
    assert isinstance(aliases.root, dict)
