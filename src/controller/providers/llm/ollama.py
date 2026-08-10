import logging
import json
import time
import httpx
from typing import AsyncGenerator

from controller.providers.llm.base import LLMBackend
from controller.exceptions import LLMConnectionError
from controller.config import loader as config


class OllamaBackend(LLMBackend):
    def __init__(self, host: str | None = None, model_name: str = "qwen3.5:9b", temperature: float = 0.5):
        if not host:
            settings = config.load_config("settings")
            host = settings.get("ollama_url", "http://127.0.0.1:11434")
        self.host = host.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        logging.info(f"Zainicjalizowano OllamaBackend: Host={self.host}, Model={self.model_name}, Temp={temperature}")

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Wysyła jednorazowe zapytanie strumieniowe do API Ollama (/api/chat) i generuje zdarzenia:
        - {\"type\": \"content\", \"content\": piece}
        - {\"type\": \"profiler\", \"metric\": \"llm_ttft\", \"value\": ms}
        - {\"type\": \"tool_calls\", \"tool_calls\": [...]}
        """
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self.temperature},
        }
        if tools:
            payload["tools"] = tools

        try:
            t_req_start = time.time()
            t_first_token = None
            final_tool_calls = []

            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise LLMConnectionError(f"HTTP {response.status_code}: {body.decode()}")

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            msg = chunk.get("message", {})

                            if "content" in msg and msg["content"]:
                                piece = msg["content"]
                                if t_first_token is None:
                                    t_first_token = time.time()
                                    ttft_ms = (t_first_token - t_req_start) * 1000.0
                                    yield {"type": "profiler", "metric": "llm_ttft", "value": ttft_ms}
                                yield {"type": "content", "content": piece}

                            if "tool_calls" in msg and msg["tool_calls"]:
                                final_tool_calls = msg["tool_calls"]

                        except json.JSONDecodeError:
                            continue

            if t_first_token is not None:
                gen_ms = (time.time() - t_first_token) * 1000.0
                yield {"type": "profiler", "metric": "llm_gen", "value": gen_ms}

            if final_tool_calls:
                yield {"type": "tool_calls", "tool_calls": final_tool_calls}

        except httpx.RequestError as e:
            logging.error(f"Ollama API Error: {e}")
            raise LLMConnectionError(f"Błąd komunikacji z modelem: {e}")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except httpx.RequestError:
            return False

    def get_provider_name(self) -> str:
        return "ollama"

    async def preload_model(self) -> None:
        url = f"{self.host}/api/generate"
        payload = {"model": self.model_name, "keep_alive": -1}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=120.0, write=5.0, pool=5.0)) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logging.info(f"Wstępnie załadowano model {self.model_name} do VRAM.")
        except httpx.RequestError as e:
            logging.error(f"Nie udało się połączyć z Ollamą lub załadować modelu: {e}")
            raise LLMConnectionError(f"Ollama Preload Error: {e}")

    async def unload_model(self) -> None:
        url = f"{self.host}/api/generate"
        payload = {"model": self.model_name, "keep_alive": 0}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload)
                logging.info(f"Wysłano żądanie wyładowania modelu {self.model_name} z VRAM.")
        except Exception as e:
            logging.warning(f"Nie udało się wyładować modelu: {e}")
