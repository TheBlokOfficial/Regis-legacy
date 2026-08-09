"""
Zarządzanie nasłuchiwaniem na zdarzenia historii.
"""
import logging
import requests
import asyncio

import controller.core.client_registry as client_registry
import controller.agent.session.store as session_store
from controller.core.message_bus import message_bus
from controller.messages import ClearHistoryMessage

logger = logging.getLogger(__name__)

async def _on_clear_history(msg: ClearHistoryMessage) -> None:
    """Resetuje historię konwersacji w pamięci Kontrolera oraz powiązanych węzłach/usługach."""
    session = session_store.get_session_for_client(msg.satellite_id)
    session.clear()

    def _notify_worker(worker_url: str):
        try:
            requests.post(f"{worker_url}/v1/clear_history", timeout=2)
        except Exception as e:
            logger.debug(f"Nie udało się powiadomić usługi LLM o czyszczeniu historii: {e}")

    workers = client_registry.get_llm_clients()
    await asyncio.gather(*[
        asyncio.to_thread(_notify_worker, w['base_url']) for w in workers
    ])

message_bus.subscribe(ClearHistoryMessage, _on_clear_history)
