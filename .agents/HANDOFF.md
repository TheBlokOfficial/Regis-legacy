# HANDOFF — Stan Projektu Regis

**Data sesji**: 2026-08-10

---

## Co zostało zrobione w tej sesji

### Refaktoryzacja Architektury Providers & Backends (pełna)

Przeprowadzono gruntowną refaktoryzację warstwy dostawców zmysłów w module `controller`. Zmiany są czysto strukturalne — nie dotknęły logiki biznesowej.

**Usunięto (zbędne warstwy):**
- `src/controller/core/providers/` — cały katalog (base.py, stt.py, tts.py, llm.py) — klasy `BaseProvider`, `STTProvider`, `TTSProvider`, `LLMProvider` były zbędnymi wrapperami
- `src/controller/providers/audio/service.py` — relikt z 4 martwymi importami; subskrypcje magistrali przeniesione do orkiestratora

**Przebudowano:**
- `providers/audio/backends.py` — dodano `STTBackend` (ABC) i `TTSBackend` (ABC); `AudioServiceSTTBackend`/`AudioServiceTTSBackend` dziedziczą po nich bezpośrednio; liveness (`last_seen`, `touch()`, `is_online`) przeniesione z wrapperów do backendów; `base_url` zamiast `host`+`port`; async httpx zamiast `asyncio.to_thread(requests.post)`
- `providers/llm/base.py` — `LLMBackend` ABC przepisany na async (`chat_stream` i `is_available` są teraz `async`)
- `providers/llm/ollama.py` — pełne przejście na `httpx.AsyncClient`; `preload_model`/`unload_model` też async
- `providers/llm/openrouter.py` — pełne przejście na `httpx.AsyncClient`
- `providers/llm/client_app.py` — drobne czyszczenie (już był async)
- `providers/llm/resolver.py` — `get_llm_backend()` → `get_active_llm()` (async); uproszczona struktura kandydatów
- `core/provider_registry.py` — przepisany od zera: nie buduje backendów, nie zna `AudioServiceSTTBackend`, operuje wyłącznie na `STTBackend`/`TTSBackend` ABC; usunięto `_llm_providers`, `get_active_llm_provider()`, `is_full_mode()`
- `core/voice_channel.py` — typy zmienione z `STTProvider`/`TTSProvider` na `STTBackend`/`TTSBackend`; pola `stt_provider`/`tts_provider` → `stt`/`tts`
- `orchestrator.py` — używa `llm_resolver.get_active_llm()` zamiast `provider_registry`; subskrypcje `RawAudioReceived` i `AgentSpoke` przeniesione z usuniętego `service.py`; stary docstring "Warstwa 1" usunięty
- `agent/engine.py` — `_consume_stream` jest teraz czysto async (usunięto fallback sync `_consume_sync_stream` i `asyncio.to_thread`)
- `endpoints/clients.py` — budowanie `AudioServiceSTTBackend`/`AudioServiceTTSBackend` przeniesione z `provider_registry` do endpointu rejestracji; `AudioServiceRegisterRequest` ma `base_url` property
- `app.py` — usunięty martwy import `audio_service`
- `tests/test_provider_registry.py` — przepisany pod nową architekturę (STTBackend/TTSBackend, bez STTProvider)
- `tests/test_llm_backends.py` — przepisany pod async API (anyio, AsyncMock)

**Wynik testów**: **44 passed, 0 failed**

---

## Aktualny stan kodu

### Architektura warstwy providers (docelowa, zaimplementowana)

```
providers/
├── llm/
│   ├── base.py          ← LLMBackend (ABC, async)
│   ├── ollama.py        ← OllamaBackend(LLMBackend) — httpx.AsyncClient
│   ├── openrouter.py    ← OpenRouterBackend(LLMBackend) — httpx.AsyncClient
│   ├── client_app.py    ← ClientAppBackend(LLMBackend) — WS relay
│   └── resolver.py      ← get_active_llm() async → LLMBackend | None
├── audio/
│   └── backends.py      ← STTBackend ABC, TTSBackend ABC,
│                           AudioServiceSTTBackend(STTBackend) + liveness,
│                           AudioServiceTTSBackend(TTSBackend) + liveness

core/
├── provider_registry.py ← register_stt(STTBackend), register_tts(TTSBackend),
│                           get_active_stt/tts, get_voice_channel, is_voice_channel_ready
├── voice_channel.py     ← VoiceChannel(stt: STTBackend, tts: TTSBackend)
└── ...
```

### Przepływ LLM
`orchestrator` → `llm_resolver.get_active_llm()` → `LLMBackend` → `chat_stream()` (async generator)

### Przepływ Audio
`orchestrator` → `provider_registry.get_voice_channel()` → `VoiceChannel` → `STTBackend`/`TTSBackend` → HTTP (httpx async)

### Rejestracja Audio Service
`POST /v1/audio/register` → endpoint buduje `AudioServiceSTTBackend` + `AudioServiceTTSBackend` → `provider_registry.register_stt/tts(backend)`

---

## Kroki startowe dla następnego agenta

1. Obowiązkowa procedura startowa (czytanie 4 plików)
2. **Refaktoryzacja `OllamaBackend`** — w `TASKS.md` był priorytet z poprzedniej sesji; w tej sesji zrefaktoryzowano go na httpx.AsyncClient, ale pominięto jedno: przy startupie Kontrolera można by zarejestrować Ollamę "raz na zawsze" jako stały backend LLM (bez odpytywania przy każdym wywołaniu `get_active_llm()`). Do rozważenia architektonicznie z użytkownikiem.
3. **Akcje edycyjne w dashboardzie UI** — drugi priorytet z poprzedniego HANDOFF, niezmieniony.
4. **FastAPI Dependency Injection** — `state.py` z globalami to krok przejściowy; docelowo `AppState` przez `Depends()`.

---

## Dług techniczny (aktualny)

- `resolver.get_active_llm()` odpytuje Ollamę (`GET /api/tags`) przy **każdym** wywołaniu — brak cache/persystencji
- Brak formalnego `LLMBackend` ABC dla rejestracji (Ollama nie rejestruje się aktywnie — push model jak Audio Service)
- `state.py` — globalne singletony zamiast DI
- Audio Service jako osobny proces — w `TASKS.md` jako zadanie przyszłe
- Pamięć długoterminowa — niezaprojektowana
- Scheduler zadań agenta — niezaprojektowany
