"""
Schematy Pydantic dla konfiguracji i struktur danych w rdzeniu Kontrolera.
"""
from typing import Any
from pydantic import BaseModel, Field, RootModel


class BaseConfigModel(BaseModel):
    """Bazowa klasa dla wszystkich struktur konfiguracyjnych Regis.
    
    Wymusza zdefiniowanie wewnętrznej klasy `Meta` z polem `file_name`,
    separując metadane pliku od właściwych pól konfiguracji.
    """
    class Meta:
        file_name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ == "BaseConfigModel":
            return

        meta = getattr(cls, "Meta", None)
        file_name = getattr(meta, "file_name", None) if meta else None

        if not file_name or not isinstance(file_name, str):
            raise TypeError(
                f"Błąd Architektury: Klasa konfiguracyjna '{cls.__name__}' "
                f"MUSI definiować wewnętrzną klasę 'Meta' z polem 'file_name: str'! "
                f"Przykład:\n  class Meta:\n      file_name = 'nazwa_pliku'"
            )


class SystemSettings(BaseConfigModel):
    """Silnie typowany schemat głównych ustawień systemowych Kontrolera."""
    class Meta:
        file_name = "settings"

    ha_url: str = Field(default="", description="URL instalacji Home Assistant")
    ha_token: str = Field(default="", description="Token dostępowy Home Assistant")
    log_level: str = Field(default="INFO", description="Poziom logowania serwera")


class RoomDetail(BaseModel):
    """Rozbudowany opis pokoju z nazwą wyświetlaną, metadanymi i listą urządzeń."""
    name: str | None = None
    metadata: list[str] = Field(default_factory=list)
    devices: list[str] = Field(default_factory=list)


class RoomsConfig(BaseConfigModel, RootModel[dict[str, list[str] | RoomDetail | dict[str, Any]]]):
    """Silnie typowany schemat pokoi z config/rooms.json."""
    class Meta:
        file_name = "rooms"

    root: dict[str, list[str] | RoomDetail | dict[str, Any]] = Field(default_factory=dict)


class AliasesConfig(BaseConfigModel, RootModel[dict[str, str]]):
    """Silnie typowany schemat aliasów urządzeń z config/aliases.json."""
    class Meta:
        file_name = "aliases"

    root: dict[str, str] = Field(default_factory=dict)


class VirtualGroupsConfig(BaseConfigModel, RootModel[dict[str, list[str]]]):
    """Silnie typowany schemat wirtualnych grup urządzeń z config/virtual_groups.json."""
    class Meta:
        file_name = "virtual_groups"

    root: dict[str, list[str]] = Field(default_factory=dict)


class LlmProviderConfig(BaseModel):
    """Zunifikowana konfiguracja pojedynczego dostawcy LLM (chmurowego lub lokalnego)."""
    id: str
    type: str  # np. "openrouter", "ollama", "groq"
    name: str | None = None
    api_key: str | None = ""
    model: str | None = None
    host: str | None = None
    port: int | None = None
    priority: int = 50


class LlmProvidersConfig(BaseConfigModel, RootModel[list[LlmProviderConfig]]):
    """Zunifikowany schemat listy dostawców LLM z data/llm_providers.json."""
    class Meta:
        file_name = "llm_providers"
        
    root: list[LlmProviderConfig] = Field(default_factory=list)


# Zachowane dla wstecznej kompatybilności
CloudProviderConfig = LlmProviderConfig
CloudProvidersConfig = LlmProvidersConfig



class ClientsConfig(BaseConfigModel, RootModel[dict[str, dict[str, Any]]]):
    """Zapisane profile konfiguracji klientów z data/clients.json."""
    class Meta:
        file_name = "clients"
        
    root: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AudioProviderConfig(BaseModel):
    """Konfiguracja zewnętrznej usługi Audio Service."""
    id: str
    name: str
    host: str
    port: int
    stt_model_size: str | None = None
    tts_model_name: str | None = None


class AudioProvidersConfig(BaseConfigModel, RootModel[list[AudioProviderConfig]]):
    """Zapisane zewnętrzne usługi audio z data/audio_providers.json."""
    class Meta:
        file_name = "audio_providers"
        
    root: list[AudioProviderConfig] = Field(default_factory=list)


class SatelliteConfig(BaseModel):
    """Konfiguracja zadeklarowanej Satelity (urządzenia stykowe w pokoju)."""
    id: str
    name: str
    room: str
    type: str = "desktop"  # desktop / esp32 / terminal
    capabilities: list[str] = Field(default_factory=lambda: ["audio_in", "audio_out"])


class SatellitesConfig(BaseConfigModel, RootModel[list[SatelliteConfig]]):
    """Zapisane zadeklarowane satelity z data/satellites.json."""
    class Meta:
        file_name = "satellites"

    root: list[SatelliteConfig] = Field(default_factory=list)
