# Regis Project Handoff

**Data sesji**: 2026-08-09 / 2026-08-10

## 1. Co Zostało Wykonane w Ostatniej Sesji
- **Wdrożenie Architektury Split View dla Wywołań Narzędzi**:
  - Przebudowano główny strumień czatu i dodano wysuwany prawy panel inspektora debuggowego (`#chat-inspector-panel`) z `z-index: 100` ([views/chat.html](file:///d:/Projekty/Regis/src/controller/web/views/chat.html), [chat.css](file:///d:/Projekty/Regis/src/controller/web/css/chat.css)).
- **Friendly Action Resolver & Wzór z Google Antigravity**:
  - Wyeliminowano surowe nazwy `snake_case` (`execute_action`, `get_device_state`) i nawiasy `(wynik)` z czatu na rzecz przyjaznych polskich opisów (np. `⚡ Wykonanie akcji: turn_on na light.pracownia_glowna ↗`).
  - Zastosowano bezramkowy wiersz akcji z pigułką reagującą na najechanie myszką (`hover pill` 1:1 z Antigravity). Kliknięcie otwiera pełen panel inspektora JSON.
- **Ujednolicenie Typografii Konwersacji**:
  - Zapytania użytkownika (`.msg-user-text`) oraz odpowiedzi agenta (`.msg-assistant-content`) mają dokładnie ten sam ujednolicony krój `15px` (`#ececed`), zachowując pionowe wyrównanie z lewej strony (20px).
- **Naprawa Asynchroniczności SSE & Kolejkowania Wyników**:
  - Przeniesiono blokujące wykonanie narzędzi `app_state.tools_registry.execute_tool` na `await asyncio.to_thread(...)` w [orchestrator.py](file:///d:/Projekty/Regis/src/controller/orchestrator.py), dzięki czemu opóźnienia sieciowe Home Assistanta nie blokują pętli zdarzeń SSE FastAPI.
  - Zastąpiono pojedynczą zmienną śledzącą kolejką FIFO `pendingToolChips` w [chat.js](file:///d:/Projekty/Regis/src/controller/web/chat.js), gwarantując bezbłędne przypisywanie wyników narzędzi.
- **Analiza TTS & Formatowania Markdown / Typografii Unicode**:
  - Zdiagnozowano przyczynę braku syntezy mowy Piper TTS dla dłuższego tekstu: powodem były surowe znaki formatowania Markdown (`**`, `-`) oraz półpauza Unicode `–` (`\u2013`). Ustalono plan rozwiązania (prompt systemowy + funkcja oczyszczająca w przyszłości).

## 2. Aktualny Stan Kodu & Architektury
- Frontend czatu w [src/controller/web/](file:///d:/Projekty/Regis/src/controller/web/) jest w 100% zrefaktoryzowany, zachowując stonowany, ascetyczny wygląd bez kiczowatych emotikonów.
- Pętle orkiestratora i strumieniowanie SSE działają nieblokująco. Testy jednostkowe `pytest tests/test_llm_backends.py` przechodzą 10/10.

## 3. Kroki Startowe Dla Następnego Agenta
1. Przeczytaj pliki w obowiązkowej kolejności startowej (`docs/MANIFEST.md`, `docs/AGENT_GUIDE.md`, `.agents/HANDOFF.md`, `.agents/TASKS.md`).
2. Sprawdź testy: `pytest tests/test_llm_backends.py`.
3. Jeżeli użytkownik zechce wdrożyć filtry czyszczące tekst dla TTS przed wywołaniem Pipera, zrealizuj funkcję `clean_text_for_speech` usuwającą znaki Markdown oraz Unicode En-Dash/Em-Dash przed `synthesize_speech`.
