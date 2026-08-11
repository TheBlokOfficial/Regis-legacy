"""
Ładowacz Dostawców (Agnostic Config-First Provider Loader).

Odczytuje konfigurację zapisanych zmysłów (LLM, STT, TTS) i deleguje 
ich rejestrację bezpośrednio do polimorficznych klas backendów.
"""
import logging

from controller.config import loader as config
from controller.config.schemas import LlmProvidersConfig, AudioProvidersConfig, SatellitesConfig
from controller.clients import registry as client_registry
from controller.providers.base import BaseBackend

from controller.providers.llm.openrouter import OpenRouterBackend
from controller.providers.llm.ollama import OllamaBackend
from controller.providers.audio.audio_service import AudioServiceSTTBackend, AudioServiceTTSBackend

logger = logging.getLogger(__name__)

# Rejestry klas backendów per kategoria zmysłu i typ z konfiguracji
PROVIDER_REGISTRY: dict[str, dict[str, type[BaseBackend]]] = {
    "llm": {
        "openrouter": OpenRouterBackend,
        "ollama": OllamaBackend,
    },
    "stt": {
        "audio_service": AudioServiceSTTBackend,
    },
    "tts": {
        "audio_service": AudioServiceTTSBackend,
    },
}


def provider_factory(category: str, provider_type: str) -> type[BaseBackend] | None:
    """Zwraca klasę backendu dla danej kategorii zmysłu (llm/stt/tts) oraz typu z konfiguracji."""
    return PROVIDER_REGISTRY.get(category, {}).get(provider_type)


def load_providers() -> None:
    """Wczytuje zadeklarowane zmysły oraz Satelity w sposób agnostyczny z plików konfiguracji."""
    logger.info("[ProviderLoader] Rozpoczynam odczyt zadeklarowanych dostawców i Satelit z konfiguracji...")

    # 1. Ładowanie zmysłów LLM (Mózg / Agent) z zunifikowanej konfiguracji llm_providers.json
    llm_config = config.load(LlmProvidersConfig)
    for p in llm_config.root:
        provider_cls = provider_factory("llm", p.type)
        if provider_cls:
            provider_cls.create_and_register(p)
            logger.info(f"[ProviderLoader] Załadowano dostawcę LLM: {p.id} ({p.type})")
        else:
            logger.warning(f"[ProviderLoader] Ominięto dostawcę LLM {p.id}, brak zmapowanego backendu dla typu '{p.type}'")




    # 2. i 3. Ładowanie zmysłów STT oraz TTS (Kanał Głosowy)
    audio_config = config.load(AudioProvidersConfig)
    for a in audio_config.root:
        # Obecnie wszystkie usługi audio definiowane w audio_providers.json to serwisy 'audio_service'
        audio_type = "audio_service"
        
        stt_cls = provider_factory("stt", audio_type)
        if stt_cls:
            stt_cls.create_and_register(a)
            
        tts_cls = provider_factory("tts", audio_type)
        if tts_cls:
            tts_cls.create_and_register(a)
            
        logger.info(f"[ProviderLoader] Załadowano usługę Audio: {a.id} ({a.host}:{a.port})")

    # 4. Ładowanie zadeklarowanych Satelit w pokojach
    satellites_config = config.load(SatellitesConfig)
    for s in satellites_config.root:
        client_registry.client_registry[s.id] = {
            "id": s.id,
            "name": s.name,
            "room": s.room,
            "node_type": s.type,
            "capabilities": s.capabilities,
            "services": {"satellite": {"room": s.room, "node_type": s.type, "capabilities": s.capabilities}},
            "last_seen": 0,
        }
        logger.info(f"[ProviderLoader] Załadowano zadeklarowaną Satelitę: {s.id} ({s.room})")

    logger.info("[ProviderLoader] Zakończono ładowanie konfiguracji zmysłów i Satelit.")

