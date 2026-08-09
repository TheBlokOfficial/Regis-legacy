"""
Generyczna Magistrala Komend Usług (Service Command Bus) dla Aplikacji Klienckiej.

Umożliwia bezdomenowy routing komend z magistrali Kontrolera (WebSocket)
do odpowiednich lokalnych usług uruchomionych pod Klientem (np. Satelita, Worker itp.).

Architektura Pub/Sub: każda podłączona usługa SSE tworzy własną kolejkę subskrybenta.
Przy każdym push_command kopia komendy trafia do WSZYSTKICH aktywnych subskrybentów.
Eliminuje Race Condition, gdzie jedna usługa "kradła" zadanie przeznaczone dla innej.
"""
import asyncio
import logging
from typing import Callable, Any, Optional

_loop: Optional[asyncio.AbstractEventLoop] = None
_handlers: dict[str, Callable[[dict], Any]] = {}
_subscribers: list[asyncio.Queue] = []


def init(loop: asyncio.AbstractEventLoop) -> None:
    """Inicjalizuje magistralę komend usług. Wywoływane przy starcie klienta/proxy."""
    global _loop
    _loop = loop


def subscribe() -> asyncio.Queue:
    """
    Rejestruje nowego subskrybenta (nową usługę SSE).
    Zwraca dedykowaną kolejkę dla tego subskrybenta.
    """
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    """Wyrejestrowuje subskrybenta (np. gdy usługa SSE się rozłączy)."""
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


def register_handler(command_name: str, handler: Callable[[dict], Any]) -> None:
    """Rejestruje handler komendy specyficzny dla wybranej usługi."""
    _handlers[command_name] = handler


def unregister_handler(command_name: str) -> None:
    """Wyrejestrowuje handler komendy."""
    _handlers.pop(command_name, None)


async def dispatch(command_name: str, payload: dict) -> dict:
    """
    Kieruje komendę do zarejestrowanego handlera. Jeśli handler nie istnieje,
    rozgłasza komendę do wszystkich aktywnych subskrybentów SSE.
    """
    if command_name in _handlers:
        handler = _handlers[command_name]
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            else:
                return handler(payload)
        except Exception as e:
            logging.error(f"Błąd wykonania handlera dla komendy '{command_name}': {e}")
            return {"success": False, "error": str(e)}

    # Domyślny fallback: rozgłoś do wszystkich subskrybentów
    push_command({"command": command_name, **payload})
    return {"success": True}


def push_command(cmd_dict: dict) -> None:
    """
    Rozgłasza komendę do WSZYSTKICH aktywnych subskrybentów (thread-safe).
    Każda podłączona usługa SSE dostaje własną kopię polecenia.
    """
    if _loop:
        for q in list(_subscribers):
            asyncio.run_coroutine_threadsafe(q.put(cmd_dict), _loop)


async def get_command(q: asyncio.Queue) -> Optional[dict]:
    """Pobiera komendę z kolejki konkretnego subskrybenta."""
    return await q.get()
