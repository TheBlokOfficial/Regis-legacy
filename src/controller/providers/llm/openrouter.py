import json
import logging
import time
import httpx
from typing import AsyncGenerator, Any

from controller.providers.llm.base import LLMBackend
from controller.exceptions import LLMConnectionError

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterBackend(LLMBackend):
    def __init__(self, api_key: str, model_name: str, temperature: float = 0.5, id: str = "openrouter"):
        super().__init__(id=id, name=f"OpenRouter ({model_name})")
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature

    @classmethod
    def create_and_register(cls, config_data: Any) -> None:
        from controller.providers import registry
        backend = cls(
            api_key=getattr(config_data, "api_key", ""),
            model_name=getattr(config_data, "model", "qwen/qwen-2.5-72b-instruct"),
            id=getattr(config_data, "id", "openrouter"),
        )
        registry.register_llm(backend)

    async def is_available(self) -> bool:
        return bool(self.api_key and self.model_name)

    def get_provider_name(self) -> str:
        return "openrouter"

    @staticmethod
    def _accumulate_tool_call(accumulator: dict[int, dict], tc: dict, tc_pos: int) -> None:
        """Bezpiecznie dokleja lub inicjalizuje fragment wywołania narzędzia ze strumienia delta SSE."""
        idx = tc.get("index", tc_pos)
        entry = accumulator.setdefault(idx, {
            "id": tc.get("id", f"call_{idx}"),
            "type": tc.get("type", "function"),
            "function": {"name": "", "arguments": ""}
        })
        if "id" in tc and tc["id"]:
            entry["id"] = tc["id"]
        fn = tc.get("function")
        if isinstance(fn, dict):
            if name := fn.get("name"):
                entry["function"]["name"] += name
            if args := fn.get("arguments"):
                entry["function"]["arguments"] += args

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Wysyła jednorazowe zapytanie do OpenRouter API i strumieniuje zdarzenia:
        - {\"type\": \"content\", \"content\": piece}
        - {\"type\": \"profiler\", \"metric\": \"llm_ttft\", \"value\": ms}
        - {\"type\": \"tool_calls\", \"tool_calls\": [...]}
        """
        if not await self.is_available():
            raise LLMConnectionError("Brak klucza OPENROUTER_API_KEY lub OPENROUTER_MODEL.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TheBlokOfficial/Regis",
            "X-Title": "Regis Smart Home",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools

        try:
            t_req_start = time.time()
            t_first_token = None
            tool_calls_accumulator: dict[int, dict] = {}
            usage_stats = None

            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)) as client:
                async with client.stream("POST", OPENROUTER_API_URL, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise LLMConnectionError(f"HTTP {response.status_code}: {body.decode()}")

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if "usage" in chunk and chunk["usage"]:
                                    usage_stats = chunk["usage"]
                                if not chunk.get("choices"):
                                    continue
                                delta = chunk["choices"][0].get("delta", {})

                                if "content" in delta and delta["content"]:
                                    piece = delta["content"]
                                    if t_first_token is None:
                                        t_first_token = time.time()
                                        ttft_ms = (t_first_token - t_req_start) * 1000.0
                                        yield {"type": "profiler", "metric": "llm_ttft", "value": ttft_ms}
                                    yield {"type": "content", "content": piece}

                                if "tool_calls" in delta:
                                    for tc_pos, tc in enumerate(delta["tool_calls"]):
                                        self._accumulate_tool_call(tool_calls_accumulator, tc, tc_pos)

                            except json.JSONDecodeError:
                                continue

            if t_first_token is not None:
                gen_ms = (time.time() - t_first_token) * 1000.0
                yield {"type": "profiler", "metric": "llm_gen", "value": gen_ms}

            if usage_stats:
                logging.debug(f"Zużycie tokenów OpenRouter: {usage_stats}")

            if tool_calls_accumulator:
                final_tool_calls = [tc for _, tc in sorted(tool_calls_accumulator.items())]
                yield {"type": "tool_calls", "tool_calls": final_tool_calls}

        except httpx.RequestError as e:
            logging.error(f"OpenRouter API Error: {e}")
            raise LLMConnectionError(f"Odrzucono zapytanie (HTTP Error): {e}")
