"""
Usługa komunikacji ze zmysłami Audio (STT / TTS).

Odpowiada za połączenia z usługami audio (transkrypcję mowy i syntezę mowy)
zarówno przez zadania WebSocket (Sidecar Workers), jak i bezpośrednie API HTTP.
"""
import asyncio
import base64
import logging
import time
import uuid

import requests

import controller.core.client_registry as client_registry
from controller.endpoints.clients import client_manager
from controller.core.message_bus import message_bus
from controller.messages import RawAudioReceived, UserSpoke, AgentSpoke, PlayAudioMessage

logger = logging.getLogger(__name__)

# Słownik aktywnych zadań audio: {task_id: asyncio.Queue}
_pending_audio_tasks: dict[str, asyncio.Queue] = {}


def route_task_event(task_id: str, event: dict) -> None:
    """
    Przekierowuje ramkę task_event z api/clients.py do kolejki oczekującego zadania STT/TTS.
    """
    q = _pending_audio_tasks.get(task_id)
    if q is not None:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"[AudioService] Kolejka dla task_id={task_id} jest pełna — porzucam ramkę.")
    else:
        logger.debug(f"[AudioService] Odebrano task_event dla nieznanego task_id={task_id} — ignoruję.")


import controller.core.provider_registry as provider_registry

async def transcribe_audio(audio_bytes: bytes) -> tuple[str | None, int]:
    """
    Wysyła surowe bajty audio do aktywnego dostawcy STT przez obiekt VoiceChannel.
    """
    voice_channel = provider_registry.get_voice_channel()
    return await voice_channel.transcribe(audio_bytes)


async def synthesize_speech(text: str) -> tuple[str | None, int]:
    """
    Wysyła tekst do aktywnego dostawcy TTS przez obiekt VoiceChannel.
    """
    voice_channel = provider_registry.get_voice_channel()
    return await voice_channel.synthesize(text)


# =============================================================================
# REJESTRACJA W MAGISTRALI (EVENT SUBSCRIBERS)
# =============================================================================

async def _on_raw_audio(msg: RawAudioReceived):
    """Transkrybuje audio (STT), a następnie deleguje do handle_user_spoke jako async generator."""
    from controller.orchestrator import handle_user_spoke
    stt_text, _ = await transcribe_audio(msg.audio_bytes)
    if stt_text:
        async for item in handle_user_spoke(stt_text, msg.sender):
            yield item
    else:
        logger.warning(f"Odrzucono audio od klienta '{msg.sender}' - STT nie zwróciło tekstu.")
        yield {"type": "error", "content": "STT nie rozpoznało mowy."}


async def _on_agent_spoke(msg: AgentSpoke):
    """Nasłuchuje myśli/tekstu Agenta i po udanym TTS rzuca komendę PlayAudioMessage do klienta."""
    audio_b64, _ = await synthesize_speech(msg.text)
    if audio_b64:
        await message_bus.publish(PlayAudioMessage(client_id=msg.sender, audio_b64=audio_b64))
    else:
        logger.warning(f"Nie powiodła się synteza mowy (TTS) dla wiadomości do '{msg.sender}'.")


message_bus.subscribe_stream(RawAudioReceived, _on_raw_audio)
message_bus.subscribe(AgentSpoke, _on_agent_spoke)
