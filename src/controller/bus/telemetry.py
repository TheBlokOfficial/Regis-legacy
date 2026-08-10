"""
Usługa telemetryczna i bufor zdarzeń SSE dla Dashboardu Web UI.

Słucha typowanych klas wiadomości domenowych na agnostycznej magistrali MessageBus
i konwertuje je na bufor historii dla interfejsu przeglądarkowego.
"""
import asyncio
import datetime
from collections import deque
from controller.bus.message_bus import message_bus
from controller.messages import (
    UserSpoke,
    AgentSpoke,
    ConversationTurnMessage,
    ClientRegisteredMessage,
    ClientUnregisteredMessage,
    SystemLogMessage,
    AgentActionMessage,
)

_history: deque = deque(maxlen=500)
_sse_queues: list[asyncio.Queue] = []


def _record_event(event_dict: dict) -> None:
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    _history.append(event_dict)
    for q in list(_sse_queues):
        try:
            q.put_nowait(event_dict)
        except asyncio.QueueFull:
            pass


async def _on_user_spoke(msg: UserSpoke) -> None:
    _record_event({
        "type": "user_spoke",
        "satellite_id": msg.sender,
        "text": msg.text,
    })


async def _on_agent_spoke(msg: AgentSpoke) -> None:
    _record_event({
        "type": "agent_spoke",
        "satellite_id": msg.sender,
        "text": msg.text,
    })


async def _on_conversation_turn(msg: ConversationTurnMessage) -> None:
    _record_event({
        "type": "conversation_turn",
        "user_text": msg.user_text,
        "assistant_text": msg.assistant_text,
        "worker_id": msg.worker_id,
        "satellite_id": msg.satellite_id,
        "room": msg.room,
        "tools": msg.tools or [],
        "tool_count": len(msg.tools or []),
        "elapsed_ms": msg.elapsed_ms,
        "profiler": msg.profiler or {},
        "model": msg.model,
    })


async def _on_client_registered(msg: ClientRegisteredMessage) -> None:
    _record_event({
        "type": "client_registered",
        "id": msg.client_id,
        "client_type": msg.client_type,
        "room": msg.room,
        "name": msg.name,
    })


async def _on_client_unregistered(msg: ClientUnregisteredMessage) -> None:
    _record_event({
        "type": "client_unregistered",
        "id": msg.client_id,
    })


async def _on_system_log(msg: SystemLogMessage) -> None:
    _record_event({
        "type": "system_log",
        "level": msg.level,
        "message": msg.message,
        "source": msg.source,
    })


async def _on_agent_action(msg: AgentActionMessage) -> None:
    _record_event({
        "type": "agent_action",
        "satellite_id": msg.satellite_id,
        "action_type": msg.action_type,
        "tool_name": msg.tool_name,
        "tool_args": msg.tool_args,
        "tool_result": msg.tool_result,
    })


# Rejestracja słuchaczy w agnostycznej magistrali MessageBus
message_bus.subscribe(UserSpoke, _on_user_spoke)
message_bus.subscribe(AgentSpoke, _on_agent_spoke)
message_bus.subscribe(ConversationTurnMessage, _on_conversation_turn)
message_bus.subscribe(ClientRegisteredMessage, _on_client_registered)
message_bus.subscribe(ClientUnregisteredMessage, _on_client_unregistered)
message_bus.subscribe(SystemLogMessage, _on_system_log)
message_bus.subscribe(AgentActionMessage, _on_agent_action)


async def subscribe_sse() -> tuple[asyncio.Queue, list[dict]]:
    """Rejestruje subskrybenta SSE i odtwarza bufor historii zdarzeń."""
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    _sse_queues.append(q)
    return q, list(_history)


def unsubscribe_sse(q: asyncio.Queue) -> None:
    """Wyrejestrowuje subskrybenta SSE."""
    try:
        _sse_queues.remove(q)
    except ValueError:
        pass
