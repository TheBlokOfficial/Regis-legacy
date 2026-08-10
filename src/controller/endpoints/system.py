"""
Router Systemowy (Status) dla Kontrolera.

Obsługuje endpointy:
- GET  /api/status              — REST: snapshot stanu systemu
- GET  /api/events              — SSE: strumieniowanie zdarzeń EventBus
"""
import time
import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

import controller.state as state
import controller.clients.registry as client_registry
import controller.bus.telemetry as telemetry

router_system = APIRouter()




import controller.providers.registry as provider_registry

async def get_status_snapshot() -> dict:
    """Zwraca aktualny stan systemu: węzły, satelity, integracje, zmysły, info o Kontrolerze."""
    uptime_s = int(time.time() - state.controller_start_time)

    integrations = []
    for integration in state.integration_registry.values():
        try:
            status = await integration.check_status()
        except Exception:
            status = "offline"
        integrations.append(integration.to_dict(status))

    ha_integration = state.integration_registry.get("home_assistant")
    ha_status = integrations[0]["status"] if ha_integration and integrations else "unknown"

    clients = list(client_registry.client_registry.values())
    workers = client_registry.get_llm_clients()
    satellites = client_registry.get_satellite_clients()

    # Wyliczanie zmysłów z aktualnego kontraktu ProviderRegistry.
    active_stt = provider_registry.get_active_stt()
    active_tts = provider_registry.get_active_tts()
    active_llm = provider_registry.llm.backend

    stt_count = 1 if active_stt else 0
    tts_count = 1 if active_tts else 0
    llm_count = 1 if active_llm else 0

    voice_channel_ready = provider_registry.is_voice_channel_ready()
    full_mode = active_llm is not None and voice_channel_ready

    audio_workers = []
    if active_stt or active_tts:
        audio_workers.append({
            "id": "audio-service-standalone",
            "name": "Lokalny Audio Service",
            "stt_model_size": getattr(active_stt, "model_size", "small") if active_stt else None,
            "tts_model_name": getattr(active_tts, "voice_name", "pl_PL-darkman-medium") if active_tts else None,
        })

    return {
        "nodes": clients,
        "clients": clients,
        "workers": workers,
        "audio_workers": audio_workers,
        "satellites": satellites,
        "integrations": integrations,
        "controller": {
            "uptime_s": uptime_s,
            "ha_status": ha_status,
            "full_mode": full_mode,
            "voice_channel_ready": voice_channel_ready,
            "llm_count": llm_count,
            "stt_count": stt_count,
            "tts_count": tts_count,
        }
    }


@router_system.get("/api/status")
async def get_status():
    """Zwraca aktualny stan systemu: węzły, satelity, integracje, info o Kontrolerze."""
    return await get_status_snapshot()


@router_system.get("/api/events")
async def get_events(request: Request):
    """
    Endpoint SSE (Server-Sent Events) dla zdarzeń systemowych (EventBus).
    Zwraca historyczne zdarzenia od razu po podłączeniu, a następnie strumieniuje na żywo.
    """
    queue, history = await telemetry.subscribe_sse()

    async def event_generator():
        try:
            for past_event in history:
                yield f"data: {json.dumps(past_event)}\n\n"
            
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        finally:
            telemetry.unsubscribe_sse(queue)



    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
