"""
Testy jednostkowe dla refaktoryzowanej magistrali wiadomości (MessageBus).
"""
import asyncio
import pytest
from controller.core.message_bus import MessageBus


class _Msg:
    pass


@pytest.mark.anyio
async def test_subscribe_fire_and_forget_does_not_block_publish():
    """Fire-and-forget subskrybent nie blokuje publish — task jest odpalony asynchronicznie."""
    bus = MessageBus()
    called = []

    async def slow_handler(msg):
        await asyncio.sleep(0.05)
        called.append("done")

    bus.subscribe(_Msg, slow_handler)

    # publish() powinno zakończyć się natychmiast, bez czekania na slow_handler
    gen = await bus.publish(_Msg())
    assert called == []  # handler jeszcze nie skończył

    # Pozwalamy eventloop przetworzyć task
    await asyncio.sleep(0.1)
    assert called == ["done"]

    # Zwrócony generator powinien być pusty (brak stream subskrybenta)
    items = [item async for item in gen]
    assert items == []


@pytest.mark.anyio
async def test_subscribe_stream_returns_generator():
    """subscribe_stream powoduje że publish() zwraca async generator subskrybenta."""
    bus = MessageBus()

    async def stream_handler(msg):
        yield {"type": "chunk", "value": 1}
        yield {"type": "chunk", "value": 2}

    bus.subscribe_stream(_Msg, stream_handler)

    gen = await bus.publish(_Msg())
    items = [item async for item in gen]
    assert items == [{"type": "chunk", "value": 1}, {"type": "chunk", "value": 2}]


@pytest.mark.anyio
async def test_publish_without_any_subscriber_returns_empty_generator():
    """publish() bez żadnego subskrybenta zwraca pusty async generator (nie listę)."""
    bus = MessageBus()
    gen = await bus.publish(_Msg())
    assert hasattr(gen, "__aiter__")
    items = [item async for item in gen]
    assert items == []


def test_subscribe_stream_raises_on_duplicate():
    """Próba rejestracji drugiego stream subskrybenta na ten sam typ rzuca ValueError."""
    bus = MessageBus()

    async def handler_a(msg):
        yield

    async def handler_b(msg):
        yield

    bus.subscribe_stream(_Msg, handler_a)
    with pytest.raises(ValueError, match="jest już zarejestrowany"):
        bus.subscribe_stream(_Msg, handler_b)


@pytest.mark.anyio
async def test_fire_and_forget_and_stream_coexist():
    """Fire-and-forget i stream subskrybent mogą działać razem dla tego samego typu."""
    bus = MessageBus()
    side_effects = []

    async def ff_handler(msg):
        side_effects.append("ff")

    async def stream_handler(msg):
        yield {"type": "ok"}

    bus.subscribe(_Msg, ff_handler)
    bus.subscribe_stream(_Msg, stream_handler)

    gen = await bus.publish(_Msg())
    items = [item async for item in gen]
    assert items == [{"type": "ok"}]

    await asyncio.sleep(0.01)
    assert side_effects == ["ff"]
