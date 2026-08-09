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


async def transcribe_audio(audio_bytes: bytes) -> tuple[str | None, int]:
    """
    Wysyła surowe bajty audio do pierwszego dostępnego serwisu STT i zwraca rozpoznany tekst oraz czas ms.
    Zapewnia priorytetową obsługę bezportowych workerów WebSocket z awaryjnym fallbackiem do HTTP.
    """
    stt_nodes = client_registry.get_audio_clients()
    if not stt_nodes:
        logger.warning("Brak dostępnej usługi STT.")
        return None, 0

    stt_node = stt_nodes[0]
    client_id = stt_node.get("id")
    t_start = time.time()

    # 1. Najpierw próba komunikacji przez tunel WebSocket (Sidecar Worker)
    if client_id and client_manager.is_connected(client_id):
        task_id = str(uuid.uuid4())
        task_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        _pending_audio_tasks[task_id] = task_queue

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        ws_success = await client_manager.send_command(
            client_id, "transcribe", {"task_id": task_id, "audio_b64": audio_b64}
        )

        if ws_success:
            try:
                ev = await asyncio.wait_for(task_queue.get(), timeout=30.0)
                stt_ms = int((time.time() - t_start) * 1000)
                ev_type = ev.get("type")
                if ev_type == "stt_result":
                    text = ev.get("text", "")
                    return (text if text else None), stt_ms
                else:
                    logger.warning(f"Usługa STT Worker zwróciła błąd: {ev.get('content')}")
                    return None, stt_ms
            except asyncio.TimeoutError:
                logger.warning(f"Timeout (30s) podczas oczekiwania na transkrypcję z STT Worker (task_id={task_id}).")
                return None, int((time.time() - t_start) * 1000)
            finally:
                _pending_audio_tasks.pop(task_id, None)

    # 2. Fallback do bezpośredniego połączenia HTTP (dla serwerów samodzielnych)
    stt_url = f"{stt_node['base_url']}/v1/stt/transcribe"
    try:
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        stt_resp = await asyncio.to_thread(requests.post, stt_url, files=files, timeout=(1.0, 30.0))
        stt_resp.raise_for_status()
        stt_json = stt_resp.json()
        stt_content = stt_json.get("text", "")
        stt_ms = stt_json.get("elapsed_ms") or int((time.time() - t_start) * 1000)

        if not stt_content:
            logger.warning("Usługa STT nie rozpoznała żadnego tekstu z nagrania.")
            return None, stt_ms

        return stt_content, stt_ms
    except Exception as e:
        logger.exception(f"Błąd komunikacji z usługą STT: {e}")
        return None, int((time.time() - t_start) * 1000)


async def synthesize_speech(text: str) -> tuple[str | None, int]:
    """
    Wysyła tekst do pierwszego dostępnego serwisu TTS i zwraca bajty audio w base64 oraz czas ms.
    Zapewnia priorytetową obsługę bezportowych workerów WebSocket z awaryjnym fallbackiem do HTTP.
    """
    tts_nodes = client_registry.get_audio_clients()
    if not tts_nodes:
        logger.debug("Brak dostępnej usługi TTS.")
        return None, 0

    tts_node = tts_nodes[0]
    client_id = tts_node.get("id")
    t_start = time.time()

    # 1. Najpierw próba komunikacji przez tunel WebSocket (Sidecar Worker)
    if client_id and client_manager.is_connected(client_id):
        task_id = str(uuid.uuid4())
        task_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        _pending_audio_tasks[task_id] = task_queue

        ws_success = await client_manager.send_command(
            client_id, "synthesize", {"task_id": task_id, "text": text}
        )

        if ws_success:
            try:
                ev = await asyncio.wait_for(task_queue.get(), timeout=30.0)
                tts_ms = int((time.time() - t_start) * 1000)
                ev_type = ev.get("type")
                if ev_type == "tts_result":
                    b64_audio = ev.get("audio_b64")
                    return (b64_audio if b64_audio else None), tts_ms
                else:
                    logger.warning(f"Usługa TTS Worker zwróciła błąd: {ev.get('content')}")
                    return None, tts_ms
            except asyncio.TimeoutError:
                logger.warning(f"Timeout (30s) podczas oczekiwania na syntezę z TTS Worker (task_id={task_id}).")
                return None, int((time.time() - t_start) * 1000)
            finally:
                _pending_audio_tasks.pop(task_id, None)

    # 2. Fallback do bezpośredniego połączenia HTTP (dla serwerów samodzielnych)
    tts_url = f"{tts_node['base_url']}/v1/tts/synthesize"
    try:
        tts_resp = await asyncio.to_thread(
            requests.post, tts_url,
            json={"text": text},
            timeout=(1.0, 30.0),
        )
        if tts_resp.ok:
            tts_json = tts_resp.json()
            b64_audio = tts_json.get("audio_b64")
            tts_ms = tts_json.get("elapsed_ms") or int((time.time() - t_start) * 1000)
            return b64_audio, tts_ms

        logger.warning(f"Usługa TTS zwróciła kod odpowiedzi {tts_resp.status_code}")
        return None, int((time.time() - t_start) * 1000)
    except Exception as e:
        logger.warning(f"Błąd usługi TTS: {e}")
        return None, int((time.time() - t_start) * 1000)


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
