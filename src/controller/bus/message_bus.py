"""
Agnostyczna Magistrala Wiadomości Regis (MessageBus — Warstwa Komunikacji).

Czysty, agnostyczny mechanizm posiadający trzy metody:
- subscribe(topic_or_type, subscriber)        — fire-and-forget (coroutine lub sync)
- subscribe_stream(topic_or_type, subscriber) — async generator zwracany przez publish()
- publish(message)                            — zawsze zwraca async generator
"""
import asyncio
import logging
from typing import Callable, Any, AsyncGenerator

logger = logging.getLogger(__name__)


async def _empty_generator() -> AsyncGenerator:
    """Pusty async generator — wartość domyślna publish() gdy brak stream subskrybenta."""
    return
    yield  # noqa — wymuszenie typu async generator


class MessageBus:
    """
    Agnostyczna magistrala wiadomości z dwoma trybami subskrypcji:

    - subscribe()        → fire-and-forget (create_task), nie blokuje publish()
    - subscribe_stream() → zwraca async generator do wywołującego; max 1 na typ wiadomości
    """

    def __init__(self):
        self._subscribers: dict[Any, list[Callable[..., Any]]] = {}
        self._stream_subscribers: dict[Any, Callable[..., Any]] = {}

    def subscribe(self, topic_or_type: Any, subscriber: Callable[..., Any]) -> None:
        """Rejestruje słuchacza fire-and-forget dla danego typu wiadomości."""
        if topic_or_type not in self._subscribers:
            self._subscribers[topic_or_type] = []
        if subscriber not in self._subscribers[topic_or_type]:
            self._subscribers[topic_or_type].append(subscriber)

    def subscribe_stream(self, topic_or_type: Any, subscriber: Callable[..., Any]) -> None:
        """
        Rejestruje jednego subskrybenta-generatora dla danego typu wiadomości.
        publish() zwróci jego async generator bezpośrednio do wywołującego.
        Rzuca ValueError jeśli dla danego typu jest już zarejestrowany stream subskrybent.
        """
        if topic_or_type in self._stream_subscribers:
            raise ValueError(
                f"Stream subskrybent dla '{topic_or_type}' jest już zarejestrowany: "
                f"{self._stream_subscribers[topic_or_type]}. "
                "Może być tylko jeden subskrybent-generator na typ wiadomości."
            )
        self._stream_subscribers[topic_or_type] = subscriber

    async def publish(self, message: Any) -> AsyncGenerator:
        """
        Rozgłasza wiadomość do wszystkich zarejestrowanych słuchaczy.

        - Subskrybenci fire-and-forget (subscribe) uruchamiani są jako asyncio.create_task()
          i nie blokują publish().
        - Jeśli istnieje stream subskrybent (subscribe_stream), publish() zwraca jego
          async generator bezpośrednio. W przeciwnym razie zwraca pusty generator.
        """
        msg_type = type(message) if not isinstance(message, str) else message

        # Fire-and-forget subskrybenci — odpalone jako osobne taski, nie blokują publish()
        for sub in self._subscribers.get(msg_type, []):
            res = sub(message)
            if asyncio.iscoroutine(res):
                asyncio.create_task(res)
            # funkcje synchroniczne nie wymagają obsługi

        # Stream subskrybent — zwracamy generator bezpośrednio
        stream_sub = self._stream_subscribers.get(msg_type)
        if stream_sub is not None:
            return stream_sub(message)

        return _empty_generator()


# Globalna instancja agnostycznej magistrali wiadomości Kontrolera
message_bus = MessageBus()


async def publish(message: Any) -> AsyncGenerator:
    """Pomocnicza funkcja modułowa do publikacji wiadomości."""
    return await message_bus.publish(message)
