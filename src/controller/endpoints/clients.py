import time
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from controller.agent.models import SUPPORTED_REGIS_MODELS
from protocol.schemas import (
    ClientRegistrationRequest,
    ClientConfigRequest,
    WSClientEvent,
    WSCommandResult,
)
import controller.clients.registry as client_registry
from controller.clients.connections import client_manager
from controller.bus.message_bus import message_bus
from controller.messages import (
    PlayAudioMessage,
    PauseSatelliteMessage,
    ResumeSatelliteMessage,
    SendClientCommandMessage,
    ClientCommandResultMessage,
    SatelliteEventMessage,
    ClientUpdatedMessage,
    ClientRegisteredMessage,
    ClientUnregisteredMessage
)
from controller.config import loader as config
from controller.config.schemas import ClientsConfig


router_clients = APIRouter()


class ClientCommandRequest(BaseModel):
    command: str  # np. service_control, status, config
    data: dict = {}


def _get_persistent_clients() -> dict:
    return config.load(ClientsConfig).root


def _save_persistent_clients(clients_dict: dict) -> None:
    config.save(ClientsConfig(clients_dict))


async def send_client_command(client_id: str, command: str, payload: dict) -> dict:
    client = client_registry.client_registry.get(client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Klient '{client_id}' nie jest zarejestrowany.")

    if not client_manager.is_connected(client_id):
        error_msg = f"Klient {client_id} jest nieosiągalny (brak aktywnego połączenia WebSocket)."
        logging.warning(f"[Clients] Komenda '{command}' do klienta '{client_id}' nie powiodła się: {error_msg}")
        await message_bus.publish(ClientCommandResultMessage(
            client_id=client_id,
            command=command,
            success=False,
            error=error_msg,
        ))
        raise HTTPException(status_code=502, detail=error_msg)

    await message_bus.publish(SendClientCommandMessage(
        client_id=client_id,
        command=command,
        data=payload
    ))

    logging.info(f"[Clients] Opublikowano komendę '{command}' dla klienta '{client_id}' na MessageBus.")
    return {"status": "pending", "client_id": client_id, "command": command}


class AudioServiceRegisterRequest(BaseModel):
    id: str = "audio-service-standalone"
    name: str = "Lokalny Audio Service (Faster-Whisper + Piper)"
    host: str = "127.0.0.1"
    port: int = 8002
    stt_model_size: str = "small"
    tts_model_name: str = "pl_PL-darkman-medium"

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@router_clients.post("/v1/audio/register")
@router_clients.post("/v1/clients/audio_ping")
async def register_audio_service(req: AudioServiceRegisterRequest):
    """Rejestracja/Heartbeat dla stacjonarnego daemona Audio Service w ProviderRegistry."""
    import controller.providers.registry as provider_registry
    from controller.providers.audio.audio_service import AudioServiceSTTBackend, AudioServiceTTSBackend

    client_id = req.id
    stt_id = f"{client_id}-stt"
    tts_id = f"{client_id}-tts"
    
    # 1. Sprawdzamy, czy ten zmysł jest zadeklarowany w konfiguracji (czy istnieje w katalogu)
    stt_touched = provider_registry.touch_stt(stt_id)
    tts_touched = provider_registry.touch_tts(tts_id)
    
    is_known_provider = stt_touched or tts_touched

    if is_known_provider:
        # Zapisujemy w rejestrze węzłów na pulpicie
        is_new_client = client_id not in client_registry.client_registry
        client_registry.client_registry[client_id] = {
            "id": client_id,
            "name": req.name,
            "host": req.host,
            "port": req.port,
            "base_url": req.base_url,
            "services": {
                "stt_worker": {"stt_model_size": req.stt_model_size, "port": req.port},
                "tts_worker": {"tts_model_name": req.tts_model_name, "port": req.port},
            },
            "last_seen": time.time(),
        }
        if is_new_client:
            logging.info(f"[Kontroler] Odebrano połączenie od zadeklarowanego Audio Service: {req.name}")
            await message_bus.publish(ClientRegisteredMessage(
                client_id=client_id,
                client_type="http",
                name=req.name
            ))
        return {"status": "ok", "registered": True, "known": True}
    else:
        # 2. Nieznana usługa z sieci. Zapisujemy do pending discoveries.
        payload = {
            "id": client_id,
            "name": req.name,
            "host": req.host,
            "port": req.port,
            "base_url": req.base_url,
            "stt_model_size": req.stt_model_size,
            "tts_model_name": req.tts_model_name,
        }
        provider_registry.register_pending_discovery(client_id, payload)
        return {"status": "ok", "registered": False, "pending_approval": True, "known": False}


@router_clients.get("/v1/clients/supported_models")
async def get_supported_models():
    """Zwraca oficjalną listę wspieranych modeli Regis dla Klientów."""
    return {"models": SUPPORTED_REGIS_MODELS}


@router_clients.post("/v1/clients/{client_id}/command")
@router_clients.post("/api/node/{client_id}/command")  # Alias dla wstecznej kompatybilności z UI
async def send_client_command_endpoint(client_id: str, body: ClientCommandRequest):
    """Wysyła komendę do Aplikacji Klienckiej przez aktywny tunel WebSocket."""
    return await send_client_command(client_id, body.command, body.data)


@router_clients.get("/v1/clients/{client_id}/config")
async def get_client_config(client_id: str):
    """Zwraca profil konfiguracji Klienta przechowywany w Kontrolerze."""
    persistent_configs = _get_persistent_clients()
    if client_id in persistent_configs:
        return persistent_configs[client_id]
    if client_id in client_registry.client_registry:
        client = client_registry.client_registry[client_id]
        return {"name": client.get("name"), "services": client.get("services", {})}
    raise HTTPException(status_code=404, detail=f"Klient {client_id} nie został odnaleziony.")


@router_clients.post("/v1/clients/{client_id}/config")
async def update_client_config(client_id: str, body: ClientConfigRequest):
    """Zapisuje konfigurację Klienta w Kontrolerze i synchronizuje ją przez WebSocket."""
    persistent_configs = _get_persistent_clients()
    current_profile = persistent_configs.get(client_id, {})

    new_name = body.name if body.name is not None else current_profile.get("name", client_id)
    new_room = body.room if body.room is not None else current_profile.get("room", "")
    new_services = body.services if body.services is not None else current_profile.get("services", {})

    # Usuń ewentualny room ze słownika usług satelity, by nie wyciekał do operacyjnej konfiguracji klienta
    if isinstance(new_services, dict) and "satellite" in new_services and isinstance(new_services["satellite"], dict):
        new_services["satellite"].pop("room", None)

    updated_profile = {
        "name": new_name,
        "room": new_room,
        "services": new_services,
    }
    persistent_configs[client_id] = updated_profile
    _save_persistent_clients(persistent_configs)

    if client_id in client_registry.client_registry:
        if not client_manager.is_connected(client_id):
            persistent_configs[client_id] = current_profile
            _save_persistent_clients(persistent_configs)
            logging.warning(f"Nie udało się wysłać konfiguracji przez WS do Klienta {client_id}. Zmiany wycofane.")
            raise HTTPException(
                status_code=502,
                detail=f"Klient {client_id} jest nieosiągalny (brak połączenia WebSocket). Nie można zaaplikować konfiguracji."
            )

        # Wysyłamy komendę konfiguracji przez MessageBus
        await message_bus.publish(SendClientCommandMessage(
            client_id=client_id,
            command="config",
            data={
                "name": new_name,
                "services": new_services,
            }
        ))

        client_registry.client_registry[client_id]["name"] = new_name
        client_registry.client_registry[client_id]["room"] = new_room
        client_registry.client_registry[client_id]["services"] = new_services

    await message_bus.publish(ClientUpdatedMessage(
        client_id=client_id,
        client=client_registry.client_registry.get(client_id, {"id": client_id, **updated_profile}),
    ))

    return {"status": "ok", "config": updated_profile}


# ─── Obsługa Wiadomości WebSocket ─────────────────────────────────────────────

async def _handle_ws_register(client_id: str, data: dict, websocket: WebSocket):
    try:
        reg_payload = data.get("data", {})
        req = ClientRegistrationRequest(**reg_payload)

        is_new = req.id not in client_registry.client_registry
        incoming_services = req.services

        persistent_configs = _get_persistent_clients()
        stored_profile = persistent_configs.get(req.id)

        if stored_profile:
            name = stored_profile.get("name", req.name or req.id)
            room = stored_profile.get("room", "")
            services_dict = stored_profile.get("services", incoming_services)
        else:
            name = req.name or req.id
            room = ""
            services_dict = incoming_services
            persistent_configs[req.id] = {
                "name": name,
                "room": room,
                "services": services_dict,
            }
            _save_persistent_clients(persistent_configs)

        client_data = {
            "id": req.id,
            "name": name,
            "room": room,
            "host": req.host,
            "services": services_dict,
            "last_seen": time.time(),
        }
        client_registry.client_registry[req.id] = client_data

        if is_new:
            service_names = list(services_dict.keys())
            logging.info(
                f"Zarejestrowano Klienta (WebSocket): {req.id} "
                f"(host={req.host}, usługi={service_names})"
            )
            await message_bus.publish(ClientRegisteredMessage(
                client_id=req.id,
                client_type="websocket",
                room=room,
                name=name
            ))

        await websocket.send_json({
            "type": "config",
            "data": {
                "name": name,
                "services": services_dict,
            }
        })

        if "satellite" in services_dict:
            await message_bus.publish(ResumeSatelliteMessage(client_id=req.id))
    except Exception as e:
        logging.error(f"Błąd rejestracji przez WebSocket dla {client_id}: {e}")

async def _handle_ws_satellite_event(client_id: str, data: dict, websocket: WebSocket):
    try:
        event = WSClientEvent(**data)
        await message_bus.publish(SatelliteEventMessage(
            satellite_id=client_id,
            event_type=event.event_type,
            data=event.data,
        ))

        if event.event_type == "state" and event.data.get("state") == "WAITING":
            import controller.providers.registry as providers
            audio_clients = client_registry.get_audio_clients()
            if audio_clients and providers.is_llm_ready():
                await client_manager.send_command(client_id, "satellite_control", {"action": "resume"})
    except Exception as e:
        logging.error(f"Błąd parsowania WSClientEvent: {e}")

async def _handle_ws_command_result(client_id: str, data: dict, websocket: WebSocket):
    try:
        res = WSCommandResult(**data)
        await message_bus.publish(ClientCommandResultMessage(
            client_id=client_id,
            command=res.command,
            success=res.success,
            error=res.error,
            result=res.result,
        ))
    except Exception as e:
        logging.error(f"Błąd parsowania WSCommandResult: {e}")

async def _handle_ws_task_event(client_id: str, data: dict, websocket: WebSocket):
    logging.debug(f"Odebrano task_event od klienta {client_id}")

async def _handle_ws_wake_check(client_id: str, data: dict, websocket: WebSocket):
    import controller.providers.registry as providers
    audio_clients = client_registry.get_audio_clients()
    if not audio_clients:
        await websocket.send_json({"type": "wake_check_result", "permitted": False, "reason": "Brak dostępnej usługi Audio (STT/TTS)"})
    elif not providers.is_llm_ready():
        await websocket.send_json({"type": "wake_check_result", "permitted": False, "reason": "Brak dostępnych usług LLM"})
    else:
        await websocket.send_json({"type": "wake_check_result", "permitted": True})

async def _handle_ws_audio_complete(client_id: str, data: dict, websocket: WebSocket):
    await client_manager.send_command(client_id, "satellite_control", {"action": "resume"})

WS_EVENT_HANDLERS = {
    "register": _handle_ws_register,
    "satellite_event": _handle_ws_satellite_event,
    "client_event": _handle_ws_satellite_event,
    "command_result": _handle_ws_command_result,
    "task_event": _handle_ws_task_event,
    "wake_check": _handle_ws_wake_check,
    "audio_complete": _handle_ws_audio_complete,
    "status": lambda c, d, w: None,
}

async def handle_ws_message(client_id: str, data: dict, websocket: WebSocket):
    msg_type = data.get("type")
    handler = WS_EVENT_HANDLERS.get(msg_type)
    if handler:
        result = handler(client_id, data, websocket)
        if asyncio.iscoroutine(result):
            await result
    else:
        logging.warning(f"Otrzymano nieznany typ wiadomości od {client_id}: {msg_type}")


@router_clients.websocket("/v1/ws/clients/{client_id}")
async def websocket_client_endpoint(websocket: WebSocket, client_id: str):
    """Stałe połączenie WebSocket utrzymywane przez Aplikację Kliencką (Single-Step Registration & Events)."""
    await client_manager.connect(client_id, websocket)

    # Push zapamiętanej konfiguracji po połączeniu
    persistent_configs = _get_persistent_clients()
    if client_id in persistent_configs:
        stored_profile = persistent_configs[client_id]
        await client_manager.send_command(client_id, "config", stored_profile)

    try:
        while True:
            data = await websocket.receive_json()
            if client_id in client_registry.client_registry:
                client_registry.client_registry[client_id]["last_seen"] = time.time()

            await handle_ws_message(client_id, data, websocket)

    except WebSocketDisconnect:
        client_manager.disconnect(client_id)
        if client_id in client_registry.client_registry:
            del client_registry.client_registry[client_id]
            logging.info(f"Klient {client_id} rozłączył się (WebSocket) i został automatycznie wyrejestrowany.")
            await message_bus.publish(ClientUnregisteredMessage(client_id=client_id))

# Rejestracja słuchaczy do sterowania satelitą

async def _on_play_audio(msg: PlayAudioMessage):
    await client_manager.send_command(msg.client_id, "play_audio", {"audio_b64": msg.audio_b64})

async def _on_pause_satellite(msg: PauseSatelliteMessage):
    await client_manager.send_command(msg.client_id, "satellite_control", {"action": "pause"})

async def _on_resume_satellite(msg: ResumeSatelliteMessage):
    await client_manager.send_command(msg.client_id, "satellite_control", {"action": "resume"})

async def _on_send_client_command(msg: SendClientCommandMessage):
    await client_manager.send_command(msg.client_id, msg.command, msg.data or {})

message_bus.subscribe(PlayAudioMessage, _on_play_audio)
message_bus.subscribe(PauseSatelliteMessage, _on_pause_satellite)
message_bus.subscribe(ResumeSatelliteMessage, _on_resume_satellite)
message_bus.subscribe(SendClientCommandMessage, _on_send_client_command)
