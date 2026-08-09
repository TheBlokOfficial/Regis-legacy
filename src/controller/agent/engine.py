"""
Silnik Agenta ReAct (Warstwa 1 — Core / Agent Engine).

Jedno miejsce orkiestracji wieloturowej konwersacji agenta ReAct.
Obsługuje:
- Pętlę iteracji ReAct (max_iterations)
- Strumieniowanie odpowiedzi i zdarzeń do kolejki SSE (q)
- Wywoływanie narzędzi w rejestrze (tools_registry)
- Mierzenie statystyk wykonania (profiler)
- Zapis ukończonej tury konwersacji do historii sesji
"""
import asyncio
import json
import logging
import time
from typing import Any

from controller.agent.prompt.tools_schema import get_tools_schema


logger = logging.getLogger(__name__)


class _SSEEmitter:
    """Klasa pomocnicza ukrywająca szczegóły przekazywania zdarzeń do kolejki asyncio."""
    
    def __init__(self, q: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.q = q
        self.loop = loop
        self.profiler_data: dict = {}

    def emit_content(self, event: dict):
        self.loop.call_soon_threadsafe(self.q.put_nowait, event)

    def emit_tool_call_raw(self, function_name: str, args_str: str):
        log_text = f"> Regis używa: {function_name}({args_str})"
        self.loop.call_soon_threadsafe(self.q.put_nowait, {"type": "tool_call_raw", "content": log_text})

    def emit_profiler_metric(self, metric: str, value: float):
        self.profiler_data[metric] = self.profiler_data.get(metric, 0) + value
        self.loop.call_soon_threadsafe(self.q.put_nowait, {
            "type": "profiler", 
            "content": {"metric": metric, "value": value}
        })

    def emit_done(self, final_content: str, elapsed_ms: int):
        self.loop.call_soon_threadsafe(self.q.put_nowait, {
            "type": "done",
            "content": final_content,
            "elapsed_ms": elapsed_ms,
            "profiler": self.profiler_data,
        })
        
    def process_stream_event(self, ev: dict):
        """Pomocnicze przekierowanie zdarzeń ze strumienia do kolejki SSE i profilerów."""
        ev_type = ev.get("type")
        if ev_type == "content":
            self.emit_content(ev)
        elif ev_type == "profiler":
            m = ev.get("metric") or (ev.get("content", {}).get("metric") if isinstance(ev.get("content"), dict) else None)
            val = ev.get("value") or (ev.get("content", {}).get("value") if isinstance(ev.get("content"), dict) else 0)
            if m:
                self.emit_profiler_metric(m, val)


async def _consume_stream(stream_res: Any, emitter: _SSEEmitter) -> tuple[str, list[dict]]:
    """Pobiera i scala strumień od modelu, używając SSEEmitter do propagacji na żywo."""
    current_content = ""
    current_tool_calls: list[dict] = []

    if hasattr(stream_res, "__aiter__"):
        async for event in stream_res:
            emitter.process_stream_event(event)
            if event.get("type") == "content":
                current_content += event.get("content", "")
            elif event.get("type") == "tool_calls":
                current_tool_calls = event.get("tool_calls", [])
    else:
        for event in stream_res:
            emitter.process_stream_event(event)
            if event.get("type") == "content":
                current_content += event.get("content", "")
            elif event.get("type") == "tool_calls":
                current_tool_calls = event.get("tool_calls", [])

    return current_content, current_tool_calls


async def predict_next_action(
    stream_provider: Any,
    messages: list[dict],
    q: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
) -> tuple[str, list[dict], int, dict]:
    """
    Wysyła jedno żądanie do modelu LLM i strumieniuje odpowiedź.
    Zwraca krotkę: (content, tool_calls, elapsed_ms, profiler_data)
    """
    emitter = _SSEEmitter(q, loop)
    t_start = time.time()
    
    current_content = ""
    current_tool_calls = []

    tools_schema = get_tools_schema()

    try:
        if hasattr(stream_provider, "chat_stream"):
            stream_res = stream_provider.chat_stream(messages, tools=tools_schema)
        elif callable(stream_provider):
            stream_res = stream_provider(messages, tools=tools_schema)
        else:
            raise ValueError("stream_provider musi posiadać metodę chat_stream lub być callable")

        current_content, current_tool_calls = await _consume_stream(stream_res, emitter)
            
    except Exception as e:
        logger.exception(f"Błąd podczas wywołania stream_provider: {e}")
        
    elapsed_ms = int((time.time() - t_start) * 1000.0)
    
    return current_content.strip() if current_content else "", current_tool_calls, elapsed_ms, emitter.profiler_data
