import json
import logging
import asyncio

from client.config import (
    save_settings, _get_settings, _get_client_id
)
from protocol.schemas import (
    ClientRegistrationRequest, ServiceName
)
from protocol.discovery import get_local_ip
from client.network.ws_transport import get_ws_client, get_ws_loop

logger = logging.getLogger(__name__)
_last_applied_config: dict | None = None


def apply_service_config(config_data: dict, from_registration: bool = False) -> None:
    """
    Aplikuje profil konfiguracji otrzymany z Kontrolera (Web UI).
    Zapisuje ustawienia tożsamości klienta (name, room) oraz parametry Satelity.
    """
    global _last_applied_config
    if _last_applied_config == config_data:
        return
    _last_applied_config = config_data

    settings = _get_settings()
    modified = False

    if "name" in config_data and settings.get("instance_name") != config_data["name"]:
        settings["instance_name"] = config_data["name"]
        modified = True

    if "room" in config_data and settings.get("room") != config_data["room"]:
        settings["room"] = config_data["room"]
        modified = True

    services = config_data.get("services", {})
    if "satellite" in services:
        sat_cfg = services["satellite"]
        if isinstance(sat_cfg, dict):
            for k in ("room", "wakeword_threshold", "silence_timeout_ms"):
                if k in sat_cfg and settings.get(k) != sat_cfg[k]:
                    settings[k] = sat_cfg[k]
                    modified = True

    if modified:
        save_settings(settings)

    if not from_registration:
        logger.info("[Klient] Zastosowano nową konfigurację Satelity z Kontrolera (Web UI).")
        register()


def get_satellite_service_registration() -> dict:
    """Zwraca słownik konfiguracji zmysłu Satelity dla ramki rejestracyjnej."""
    settings = _get_settings()
    return {
        ServiceName.SATELLITE.value: {
            "room": settings.get("room", "pracownia"),
            "node_type": "desktop",
            "capabilities": ["audio_in", "audio_out", "text"],
            "wakeword_local": True,
            "wakeword_threshold": settings.get("wakeword_threshold", 0.65),
            "silence_timeout_ms": settings.get("silence_timeout_ms", 1500),
        }
    }


def register() -> None:
    """Wysyła ramkę rejestracyjną Satelity Desktopowej przez gniazdo WebSocket."""
    ws_loop = get_ws_loop()
    ws_client = get_ws_client()
    
    if not ws_loop or not ws_client:
        logger.warning("Nie można wysłać rejestracji: brak aktywnego gniazda WebSocket.")
        return

    client_id = _get_client_id()
    settings = _get_settings()
    instance_name = settings.get("instance_name") or f"Desktop-{client_id[:6]}"
    reg_request = ClientRegistrationRequest(
        id=client_id,
        name=instance_name,
        host=get_local_ip(),
        services=get_satellite_service_registration(),
    )
    
    payload = json.dumps({
        "type": "register",
        "data": reg_request.model_dump()
    })
    
    asyncio.run_coroutine_threadsafe(ws_client.send(payload), ws_loop)
    logger.info(f"Przesłano ramkę rejestracji Satelity Desktopowej '{client_id}' przez WebSocket.")


def unregister() -> None:
    """Wyrejestrowanie klienta po stronie serwera odbywa się automatycznie przy zamknięciu gniazda WS."""
    pass
