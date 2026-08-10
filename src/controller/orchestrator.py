"""
Orkiestrator Konwersacji Regis.

Jednolity koordynator tury konwersacji. Pełni rolę nasłuchiwacza na zdarzenia
UserSpoke i deleguje pracę do Agenta. Obsługuje też zdarzenia audio (STT/TTS)
jako subskrybent na magistrali wiadomości.
"""
import asyncio
import logging
import json
import time

import controller.agent.session.store as session_store
import controller.clients.registry as client_registry
from controller.providers.registry import llm, get_voice_channel
import controller.state as app_state
from controller.agent.engine import predict_next_action
from controller.agent.prompt.builder import build_system_prompt
from controller.agent.session.history import build_messages_from_history
from controller.bus.message_bus import message_bus
from controller.messages import (
    UserSpoke,
    AgentSpoke,
    ConversationTurnMessage,
    SystemLogMessage,
    AgentActionMessage,
    RawAudioReceived,
    PlayAudioMessage,
)

logger = logging.getLogger(__name__)


async def handle_user_spoke(text: str, sender: str):
    """
    Prywatna logika wykonawcza: pobiera pokój nadawcy, weryfikuje obecność LLM,
    uruchamia pętlę ReAct silnika agenta i publikuje to, co Agent powiedział.
    """
    if not llm.is_ready:
        logger.error("Brak dostępnego zmysłu LLM.")
        return

    room = client_registry.get_client_room(sender)

    # 0. Inicjujemy Obiekt Sesji
    session = session_store.get_session_for_client(sender)

    # 1. Zapisujemy wiadomość użytkownika bezpośrednio do obiektu sesji
    if text:
        session.append_message(role="user", content=text, room=room)
        await message_bus.publish(UserSpoke(text=text, sender=sender))

    # 2. Pobieramy pełną historię z obiektu
    session_history = session.get_history()
    provider_name = getattr(llm.backend, "get_provider_name", lambda: "llm")() if llm.backend else "llm"
    model_name = getattr(llm.backend, "model_name", "nieznany") if llm.backend else "nieznany"

    system_prompt = await asyncio.to_thread(build_system_prompt, room=room)
    messages = build_messages_from_history(
        system_prompt=system_prompt,
        history=session_history,
    )

    logger.info(f"Routing do: {provider_name} (model: {model_name}) dla sendera: {sender}")

    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    async def _runner():
        max_iterations = 10
        iteration_count = 0
        final_content = ""
        total_elapsed_ms = 0
        profiler_data = {}

        try:
            while iteration_count < max_iterations:
                iteration_count += 1

                session_history = session.get_history()
                messages = build_messages_from_history(
                    system_prompt=system_prompt,
                    history=session_history,
                )

                content, tool_calls, elapsed_ms, p_data = await predict_next_action(
                    stream_provider=llm,
                    messages=messages,
                    q=q,
                    loop=loop,
                    tools_schema=app_state.tools_registry.get_tools_schema() if app_state.tools_registry else [],
                )

                total_elapsed_ms += elapsed_ms
                profiler_data.update(p_data)

                if content or tool_calls:
                    session.append_message(
                        role="assistant",
                        content=content,
                        room=room,
                        tool_calls=tool_calls,
                        model=model_name,
                        worker_id=provider_name,
                    )

                if content:
                    final_content += content

                if not tool_calls:
                    break

                for tc in tool_calls:
                    func_name = tc.get("function", {}).get("name")
                    raw_args = tc.get("function", {}).get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    loop.call_soon_threadsafe(q.put_nowait, {
                        "type": "tool_call",
                        "content": {"name": func_name, "arguments": args},
                    })
                    await message_bus.publish(AgentActionMessage(
                        satellite_id=sender,
                        action_type="call",
                        tool_name=func_name,
                        tool_args=args,
                    ))

                    tool_res_str = await asyncio.to_thread(
                        app_state.tools_registry.execute_tool, func_name, args
                    )

                    try:
                        tool_res_obj = json.loads(tool_res_str)
                    except Exception:
                        tool_res_obj = {"result": tool_res_str}

                    loop.call_soon_threadsafe(q.put_nowait, {
                        "type": "tool_result",
                        "content": {"name": func_name, "result": tool_res_obj},
                    })
                    await message_bus.publish(AgentActionMessage(
                        satellite_id=sender,
                        action_type="result",
                        tool_name=func_name,
                        tool_args=args,
                        tool_result=tool_res_obj,
                    ))

                    session.append_message(
                        role="tool",
                        content=tool_res_str,
                        room=room,
                        tool_call_id=tc.get("id"),
                        name=func_name,
                    )

            if final_content:
                await message_bus.publish(AgentSpoke(text=final_content, sender=sender))

            await message_bus.publish(ConversationTurnMessage(
                user_text=text,
                assistant_text=final_content,
                worker_id=provider_name,
                satellite_id=sender,
                room=room,
                elapsed_ms=total_elapsed_ms,
                profiler=profiler_data,
                model=model_name,
            ))
            loop.call_soon_threadsafe(q.put_nowait, {
                "type": "done",
                "content": final_content,
                "elapsed_ms": total_elapsed_ms,
                "profiler": profiler_data,
            })

        except Exception as e:
            logger.exception(f"Błąd w pętli wywołania agenta: {e}")
            loop.call_soon_threadsafe(q.put_nowait, {"type": "error", "content": str(e)})
            await message_bus.publish(SystemLogMessage(
                level="ERROR",
                message=f"Błąd pętli agenta: {e}",
                source="orchestrator",
            ))
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    task = asyncio.create_task(_runner())

    while True:
        ev = await q.get()
        if ev is None:
            break
        yield ev

    await task


async def _on_user_spoke(msg: UserSpoke):
    async for item in handle_user_spoke(msg.text, msg.sender):
        yield item


async def _on_raw_audio(msg: RawAudioReceived):
    """Transkrybuje audio (STT), a następnie deleguje do handle_user_spoke."""
    stt_text, _ = await get_voice_channel().transcribe(msg.audio_bytes)
    if stt_text:
        async for item in handle_user_spoke(stt_text, msg.sender):
            yield item
    else:
        logger.warning(f"Odrzucono audio od klienta '{msg.sender}' - STT nie zwróciło tekstu.")
        yield {"type": "error", "content": "STT nie rozpoznało mowy."}


async def _on_agent_spoke(msg: AgentSpoke):
    """Nasłuchuje wypowiedzi Agenta i po udanym TTS rzuca komendę PlayAudio do klienta."""
    audio_b64, _ = await get_voice_channel().synthesize(msg.text)
    if audio_b64:
        await message_bus.publish(PlayAudioMessage(client_id=msg.sender, audio_b64=audio_b64))
    else:
        logger.warning(f"Nie powiodła się synteza mowy (TTS) dla wiadomości do '{msg.sender}'.")


message_bus.subscribe_stream(UserSpoke, _on_user_spoke)
message_bus.subscribe_stream(RawAudioReceived, _on_raw_audio)
message_bus.subscribe(AgentSpoke, _on_agent_spoke)
