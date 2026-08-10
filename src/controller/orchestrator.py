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
import controller.core.client_registry as client_registry
import controller.core.provider_registry as provider_registry
import controller.core.state as app_state
import controller.providers.llm.resolver as llm_resolver
from controller.agent.engine import predict_next_action
from controller.agent.prompt.builder import build_system_prompt
from controller.agent.session.history import build_messages_from_history
from controller.core.message_bus import message_bus
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
    llm_backend = await llm_resolver.get_active_llm()
    if not llm_backend or not await llm_backend.is_available():
        logger.error("Brak dostępnego backendu LLM.")
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
    provider_name = llm_backend.get_provider_name()
    model_name = getattr(llm_backend, "model_name", "nieznany")

    system_prompt = build_system_prompt(room=room)
    messages = build_messages_from_history(
        system_prompt=system_prompt,
        history=session_history,
    )

    logger.info(f"Routing do: {provider_name} (model: {model_name}) dla sendera: {sender}")

    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def emit_tool_log(q, loop, type_, content):
        loop.call_soon_threadsafe(q.put_nowait, {"type": type_, "content": content})

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
                    stream_provider=llm_backend,
                    messages=messages,
                    q=q,
                    loop=loop,
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
                    final_content = content
                    await message_bus.publish(AgentSpoke(text=content, sender=sender))

                if not tool_calls:
                    break

                for tc in tool_calls:
                    function_name = tc.get("function", {}).get("name", "")
                    arguments_raw = tc.get("function", {}).get("arguments", {})

                    if isinstance(arguments_raw, str):
                        try:
                            args_dict = json.loads(arguments_raw)
                        except json.JSONDecodeError:
                            args_dict = {}
                    else:
                        args_dict = arguments_raw or {}

                    args_str = ", ".join(f"{k}={v}" for k, v in args_dict.items())
                    emit_tool_log(q, loop, "tool_call", {"name": function_name, "arguments": args_dict})
                    await message_bus.publish(AgentActionMessage(
                        satellite_id=sender,
                        action_type="tool_call",
                        tool_name=function_name,
                        tool_args=args_dict,
                    ))
                    await message_bus.publish(SystemLogMessage(
                        level="INFO",
                        source="Agent ReAct",
                        message=f"Wywołanie narzędzia: {function_name}({args_str})",
                    ))

                    t_tool_start = time.time()
                    try:
                        tool_result_raw = await asyncio.to_thread(app_state.tools_registry.execute_tool, function_name, args_dict)
                        tool_result = json.dumps(tool_result_raw, ensure_ascii=False) if not isinstance(tool_result_raw, str) else tool_result_raw
                    except Exception as exc:
                        logger.error(f"Błąd narzędzia '{function_name}': {exc}")
                        tool_result = f'{{"error": "{str(exc)}"}}'

                    t_tool_dur = int((time.time() - t_tool_start) * 1000.0)

                    emit_tool_log(q, loop, "tool_result", {"name": function_name, "result": tool_result})
                    await message_bus.publish(AgentActionMessage(
                        satellite_id=sender,
                        action_type="tool_result",
                        tool_name=function_name,
                        tool_result=tool_result,
                    ))

                    tool_msg = {"role": "tool", "name": function_name, "content": tool_result}
                    if "id" in tc:
                        tool_msg["tool_call_id"] = tc["id"]

                    session.append_message(room=room, **tool_msg)

            if final_content:
                await message_bus.publish(ConversationTurnMessage(
                    satellite_id=sender,
                    user_text=text,
                    assistant_text=final_content,
                    worker_id=provider_name,
                    room=room,
                    tools=[],
                    elapsed_ms=total_elapsed_ms,
                    profiler=profiler_data,
                    model=model_name,
                ))

        except Exception as e:
            logger.exception(f"Błąd w pętli orkiestratora: {e}")
        finally:
            loop.call_soon_threadsafe(q.put_nowait, {"type": "done", "content": final_content, "elapsed_ms": total_elapsed_ms})

    task = asyncio.create_task(_runner())

    while True:
        item = await q.get()
        yield item
        if item["type"] in ("done", "error"):
            break

    await task


# =============================================================================
# REJESTRACJA W MAGISTRALI (EVENT SUBSCRIBERS)
# =============================================================================

async def _on_user_spoke(msg: UserSpoke):
    async for item in handle_user_spoke(msg.text, msg.sender):
        yield item


async def _on_raw_audio(msg: RawAudioReceived):
    """Transkrybuje audio (STT), a następnie deleguje do handle_user_spoke."""
    voice_channel = provider_registry.get_voice_channel()
    stt_text, _ = await voice_channel.transcribe(msg.audio_bytes)
    if stt_text:
        async for item in handle_user_spoke(stt_text, msg.sender):
            yield item
    else:
        logger.warning(f"Odrzucono audio od klienta '{msg.sender}' - STT nie zwróciło tekstu.")
        yield {"type": "error", "content": "STT nie rozpoznało mowy."}


async def _on_agent_spoke(msg: AgentSpoke):
    """Nasłuchuje wypowiedzi Agenta i po udanym TTS rzuca komendę PlayAudio do klienta."""
    voice_channel = provider_registry.get_voice_channel()
    audio_b64, _ = await voice_channel.synthesize(msg.text)
    if audio_b64:
        await message_bus.publish(PlayAudioMessage(client_id=msg.sender, audio_b64=audio_b64))
    else:
        logger.warning(f"Nie powiodła się synteza mowy (TTS) dla wiadomości do '{msg.sender}'.")


message_bus.subscribe_stream(UserSpoke, _on_user_spoke)
message_bus.subscribe_stream(RawAudioReceived, _on_raw_audio)
message_bus.subscribe(AgentSpoke, _on_agent_spoke)
