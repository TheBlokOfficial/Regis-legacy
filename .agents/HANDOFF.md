# HANDOFF — Regis (2026-08-10, sesja zamknięta)

## Stan projektu

Kontroler jest po stabilizacji refaktoryzacji providerów i narzędzi. Bieżący
kod nie używa już usuniętego katalogu `core/` ani równoległego rejestru audio.
Zmiany z tej sesji zostały zweryfikowane i są przeznaczone do zapisu w Git.

## Zrealizowane w tej sesji

- Naprawiono kontrakt `endpoints/system.py` ↔ `providers/registry.py`; `/api/status`
  nie odwołuje się już do nieistniejących metod.
- Inicjalizacja aktywnego LLM odbywa się w `lifespan` Kontrolera, niezależnie od
  ścieżki `wake_check` satelity.
- `providers/registry.py` jest jedynym rejestrem STT/TTS. Usunięto martwy
  `providers/audio/registry.py` i zaktualizowano testy do faktycznego runtime.
- `agent/tools/registry.py` zawiera wyłącznie mechanizm rejestracji/wykonania.
  Konkretne narzędzia są w `integrations/ha_tools.py` i `integrations/system_tools.py`.
- Menu narzędzi w prompcie jest filtrowane według pokoju nadawcy.
- Orkiestrator emituje ustrukturyzowane eventy SSE `tool_call`, `tool_result` i
  `done`; błędy backendu LLM są propagowane do warstwy obsługującej turę.
- `ClientConnectionManager` przeniesiono do `clients/connections.py`.
- Blokujące wywołania narzędzi HA/pogodowych wykonywane są przez `asyncio.to_thread`.

## Weryfikacja końcowa

- `python -m pytest -q` — **51 passed**, 1 znane ostrzeżenie deprecacji Starlette/httpx.
- `python -m compileall -q src\\controller` — przechodzi.
- `git diff --check` — brak błędów whitespace; Git jedynie zgłasza planowaną
  normalizację LF → CRLF w istniejącym środowisku Windows.

## Kolejny start

1. Zacząć od `git status` i pobrania aktualnego stanu gałęzi po pushu tej sesji.
2. Następny większy krok architektoniczny: zastąpić globalny `controller.state`
   obiektem `AppState` wstrzykiwanym przez FastAPI.
3. Opcjonalnie wydzielić profile oraz rejestrację klientów z `endpoints/clients.py`
   do warstwy usługowej; transport WebSocket jest już wydzielony.
4. Przed kolejnym commitem uruchomić pełne `python -m pytest -q`.
