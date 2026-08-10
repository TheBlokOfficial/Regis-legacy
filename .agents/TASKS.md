# Lista Zadań Projektu Regis (TASKS)

## Rejestr Zrealizowanych Zadań (Sesja 2026-08-10 - Asymetryczny Bento Grid, Reaktywność SSE i Audyt UI/UX Pulpitu)

- [x] **Asymetryczny Layout Bento Grid (~60% / 40%) (`src/controller/web/views/dashboard.html` & `css/layout.css`)**:
  - Przebudowano siatkę Pulpitu z ciasnych 4 kolumn w 1 rzędzie na dwukolumnowy układ Bento Grid (`1.4fr 1fr`).
  - Lewa szeroka kolumna (~640px) wyeliminowała ciasnotę horyzontalną Zmysłów i łamanie nazw urządzeń/modeli.
  - Prawa kolumna (~440px) połączyła Satelity i Integracje, znosząc poszarpany "efekt schodkowy".
- [x] **Eliminacja Szumu Wizualnego, Emotikonów i Ramkowości (`src/controller/web/css/components.css` & `renderer.js`)**:
  - Usunięto kiczowate emotikony emoji ze wszystkich nagłówków sekcji Zmysłów.
  - Zlikwidowano podwójne zagnieżdżenia ramek na rzecz czystej architektury bezramkowej.
  - Zastąpiono etykiety CAPS LOCK (`LOKALNY`, `ONLINE`, `CISZA`, `KONFIGURUJ`) estetycznymi pigułkami (`Lokalny`, `Online`, `Cisza`) i lekkimi przyciskami `.btn-ghost` (`Konfiguruj`, `Edytuj`).
- [x] **Pomocniczy Banner Stanu Pustego (`src/controller/web/css/components.css` & `renderer.js`)**:
  - Wdrożono komponent `.empty-banner` w sekcji Zmysłów informujący o pracy w `TRYBIE FALLBACK` i podpowiadający instrukcję aktywacji.
- [x] **Reaktywne Odświeżanie Live SSE Bez F5 (`src/controller/web/api.js` & `events.js`)**:
  - Zbudowano funkcję `refreshDashboardStatus()` i podłączono ją pod zdarzenia `client_registered`, `client_unregistered` i `client_updated`.
  - Rozłączenie lub podłączenie klienta `RegisDesktop` natychmiastowo czyści lub dodaje karty na żywo bez potrzeby wciskania F5.
- [x] **Wskaźnik Dwustanowej Degradacji (`src/controller/web/renderer.js` & `css/components.css`)**:
  - Wdrożono odznakę `badge-readiness` sygnalizującą stan `TRYB PEŁNY (ReAct)` vs `TRYB FALLBACK (Offline NLU)`.
- [x] **Rozszerzenie Snapshotu REST (`src/controller/endpoints/system.py`)**:
  - Dodano do `GET /api/status` statystyki zmysłów (`llm_count`, `stt_count`, `tts_count`) oraz flagę `full_mode`.

## Rejestr Zrealizowanych Zadań (Sesja 2026-08-09 - Naprawa Asynchroniczności SSE & Kolejkowania Wyników)

- [x] **Asynchroniczne Wykonywanie Narzędzi (`src/controller/orchestrator.py`)**:
  - Przeniesiono `execute_tool` na `await asyncio.to_thread(...)`, co zapobiega blokowaniu pętli zdarzeń asyncio i natychmiastowo emituje zdarzenia SSE do przeglądarki nawet przy długich operacjach sieciowych.
- [x] **Kolejkowanie FIFO Wyników SSE (`src/controller/web/chat.js`)**:
  - Zastąpiono pojedynczą zmienną `lastStreamToolChip` kolejką FIFO `pendingToolChips`, co gwarantuje, że każde wywołanie narzędzia otrzymuje swój własny, właściwy wynik w inspektorze.
- [x] **Ujednolicenie Typografii Konwersacji (`src/controller/web/css/chat.css`)**:
  - Ustalono dokładnie ten sam rozmiar czcionki `15px` (`#ececed`) dla zapytań użytkownika i wypowiedzi agenta.
- [x] **Pełna Warstwa Inspektora (`z-index: 100`) ([views/chat.html](file:///d:/Projekty/Regis/src/controller/web/views/chat.html))**:
  - Przeniesiono panel inspektora z `z-index: 100` na poziom sekcji czatu, unikając ucinania przez dolny pasek zasilania.
  - Akcje narzędzi zachowują dyskretny, mniejszy rozmiar `13.5px` w szarości `#888888`.
- [x] **Bezbłędne Warstwowanie Panelu Inspektora (`z-index: 100`) ([views/chat.html](file:///d:/Projekty/Regis/src/controller/web/views/chat.html) & [chat.css](file:///d:/Projekty/Regis/src/controller/web/css/chat.css))**:
  - Przeniesiono panel inspektora na poziom całej sekcji czatu z `z-index: 100`.
  - Panel wysuwa się czysto nad dolnym paskiem zasilania, nie jest w żaden sposób przysłaniany ani ucinany na dole.
  - Akcje w czacie stają się lekkim bezramkowym tekstem, a sama pigułka nazwy (np. `turn_on na light.pracownia_glowna ↗`) podświetla się subtelnym tłem po najechaniu myszką (`hover pill`).
- [x] **Złagodzenie Typografii Użytkownika (`src/controller/web/css/chat.css`)**:
  - Zmniejszono krój zawiadomienia użytkownika z `16.5px bold` do czytelnego, ujednoliconego `14.5px regular` (`#ececed`) z wcięciem `padding: 10px 18px`.
- [x] **Bezbłędne Przewijanie i Brak Ucinania Dołu Inspektora (`src/controller/web/css/chat.css`)**:
  - Dodano `padding-bottom: 60px` w `.inspector-content` oraz wyznaczono max-height bloków kodu JSON (`calc(50vh - 60px)`), eliminując jakiekolwiek ucinanie dołu panelu przez pasek zasilania.
  - Wdrożono funkcję `resolveToolDisplayName` tłumaczącą narządzia na zwięzłe opisy po polsku (np. `⚡ Wykonanie akcji: turn_on na light.pracownia_glowna`).
- [x] **Jednolity Lekki Chip Akcji (`src/controller/web/chat.js` & `chat.css`)**:
  - Zespolono wywołanie narzędzia (`tool_calls`) z jego wynikiem (`role: tool`) w 1 spójny chip z przyciskiem `[Szczegóły ↗]`.
  - Usunięto puste znaczniki `<details>`, duplikaty oraz sztuczne teksty `(wynik)` w nawiasach.
- [x] **Wysuwany Prawy Panel Inspektora Debuggowego (`#chat-inspector-panel`)**:
  - Dodano prawy panel boczny w widoku czatu ([views/chat.html](file:///d:/Projekty/Regis/src/controller/web/views/chat.html), [chat.css](file:///d:/Projekty/Regis/src/controller/web/css/chat.css)).
  - Kliknięcie w chip w czacie płynnie wysuwa panel z prawej strony, dając 100% pełnego miejsca na surowe dane JSON (Input Payload, Output Result) z opcją zamknięcia `✕`.
- [x] **Formatowanie Timestampu `HH:MM` (`src/controller/web/chat.js`)**:
  - Dodano funkcję `formatTimestamp(ts)` skracającą zbyt szczegółowe znaczniki czasu do czytelnego formatu godzin i minut (np. `21:38`).
- [x] **Pionowe Wyrównanie Liter i Odstęp Górny (`src/controller/web/css/chat.css`)**:
  - Ujednolicono wcięcie tekstu odpowiedzi agenta (`padding: 6px 20px`), dzięki czemu pierwsze litery zapytania i odpowiedzi układają się w idealnie prostej linii pionowej (wzór z Antigravity).
  - Zwiększono górny padding kontenera wiadomości do `48px`, zapewniając przestrzeń do "oddychania".
- [x] **Obsługa Awarii Silnika LLM (Assistant Engine Error Turn) (`src/controller/web/chat.js` & `chat.css`)**:
  - W przypadku braku workera Ollama, błędu 503 OpenRoutera czy awarii sieci, pod czystym dymkiem użytkownika generowany jest dedykowany blok błędu agenta (`.engine-error-card`) z przyciskiem `[ Ponów zapytanie do agenta ]`.
  - Kliknięcie przycisku ponowienia automatycznie przesyła ponowny strumień do Orkiestratora dla zarejestrowanej komendy.
- [x] **Wycentrowanie Pigułek Sesji (`src/controller/web/css/chat.css`)**:
  - Przełącznik pigułkowy sesji (`.session-segmented-control`) znajduje się od teraz idealnie pośrodku nad dolną kapsułą zasilania (`align-self: center`).
- [x] **Dokownica Dolna Pigułek Sesji (`src/controller/web/`)**:
  - Przeniesiono przełącznik pigułkowy sesji (`.session-segmented-control`) do dokownicy dolnej `.chat-bottom-dock` zakotwiczonej tuż nad kapsułą wpisywania wiadomości.
- [x] **Sekcja Powitalna Hero Section z Sugestiami (`src/controller/web/`)**:
  - Dla pustego czatu wdrożono bogatą sekcję Hero Section (`🤖 REGIS AI`, podtytuł oraz 3 klikalne pigułki sugerowanych komend).
  - Kliknięcie w dowolną sugestię automatycznie wkleja prompt i uruchamia komendę w czacie.
- [x] **Maskowanie Przezroczystości (CSS Scroll Fade-Out) (`src/controller/web/css/chat.css`)**:
  - Wdrożono natywną maskę przezroczystości CSS (`mask-image: linear-gradient(...)`) dla kontenera wiadomości `.chat-messages-body`.
  - Wiadomości podwijające się pod góry ekranu płynnie rozmywają się (fade-out) tuż przed pigułkami bez zderzania się z przyciskami.
- [x] **Wycentrowany Nagłówek w Osi 860px (`src/controller/web/views/chat.html` & `chat.css`)**:
  - Przeniesiono nagłówek czatu (`Czat & Monitor` + pigułki sesji) do kontenera `.chat-header-inner` o stałej szerokości `max-width: 860px` z marginesem automatycznym.
  - Nagłówek leży od teraz w dokładnie tej samej wycentrowanej osi co linia czasu wiadomości i dolna kapsuła zasilania.
- [x] **Usunięcie Przycisków Niszczycielskich (`src/controller/web/`)**:
  - Całkowicie wyeliminowano zbędny przycisk *"Wyczyść tę sesję"*, oczyszczając nagłówek ze zbędnego szumu i usuwając niepotrzebne kursory zakazu.
- [x] **Dopracowanie Stanu Pustego i Przycisków Czatu (`src/controller/web/`)**:
  - Usunięto przerywaną ramkę `border: 1px dashed` z `.empty-state` na rzecz gładkiej, wyśrodkowanej typografii.
  - Wdrożono dynamiczne wygaszanie (`disabled`) dla przycisku *"Wyczyść tę sesję"* (`.btn-ghost-danger:disabled`), gdy sesja nie zawiera wiadomości.
  - Wykonano symetryczne wyrównanie elementów w nagłówku czatu (`align-items: center`).
- [x] **Modularyzacja Stylów CSS (`src/controller/web/css/`)**:
  - Rozbito napuchnięty `style.css` na 5 czytelnych modułów w katalogu `css/` (`tokens.css`, `layout.css`, `components.css`, `chat.css`, `modals.css`).
  - Sprowadzono `style.css` do natywnego punktu wejścia z instrukcjami `@import`.
- [x] **Modularyzacja Plików Web UI (`src/controller/web/`)**:
  - Rozbito monolityczny `index.html` na odrębne szablony w `views/` (`dashboard.html`, `logs.html`, `chat.html`) oraz `modals/` (`node_config.html`, `cloud_provider.html`).
  - Wdrożono dynamiczny loader `loadViewComponents()` w `src/controller/web/app.js`, który przy starcie asynchronicznie dociąga szablony bez potrzeby użycia Node.js/npm.
- [x] **Redesign Nagłówka i Kapsuły Wejściowej Czatu (`src/controller/web/index.html` & `style.css`)**:
  - Usunięto błąd nakładania się tekstu typografii nagłówka (czysty Flexbox `space-between`).
  - Przekształcono przycisk czyszczenia sesji w elegancki **Ghost Button** (`.btn-ghost-danger`).
  - Połączono dolny pasek wprowadzania tekstu i przycisk wysyłania w **jedną płynną kapsułę** (`.chat-input-capsule`).
- [x] **Zunifikowany Przesył Komend do Klienta (`src/controller/messages.py` & `clients.py`)**:
  - Utworzono nową silnie typowaną wiadomość `SendClientCommandMessage`.
  - Endpointy `POST /v1/clients/{client_id}/config` oraz `POST /v1/clients/{client_id}/command` wycinają bezpośrednie wywołania obiektowe na rzecz publikacji `SendClientCommandMessage` na `message_bus`.
- [x] **Naprawa Przeładowywania Podprocesów w Kliencie (`src/client/network/ws_dispatcher.py`)**:
  - Zmieniono przekazywanie flagi `from_registration=False` przy odbiorze komendy `config` z Kontrolera.
  - Klient `RegisDesktop` automatycznie restartuje podproces `ollama_worker` z nowymi parametrami, wyładowuje stary model z VRAM i natychmiast odświeża ramkę `register()` do Kontrolera.
- [x] **Elastyczne Pole Wprowadzania Nazwy Modelu (`src/controller/web/index.html` & `modals.js`)**:
  - Zamieniono sztywny `<select>` wyboru modelu na otwarte pole tekstowe `<input type="text">` połączone z listą podpowiedzi `<datalist>`.
  - Rozszerzono `SUPPORTED_REGIS_MODELS` w `src/controller/agent/models.py` o warianty 27B/32B.
- [x] **Odblokowanie Pętli AsyncIO przy Strumieniowaniu (`src/controller/agent/engine.py`)**:
  - Wydzielono synchroniczną konsumpcję generatorów HTTP `requests.post` w `_consume_sync_stream`.
  - Uruchomiono iterację w osobnym wątku za pomocą `asyncio.to_thread(_consume_sync_stream, ...)` z zachowaniem bezpiecznej emisji `loop.call_soon_threadsafe(q.put_nowait, ev)`.
  - Rozwiązano problem zamrażania pętli zdarzeń asyncio — zdarzenia `tool_call`, `tool_result` oraz tokeny `content` płyną natychmiast przez SSE w czasie rzeczywistym.
- [x] **Płaska Oś Czasu dla Wszystkich Ról (`src/controller/web/chat.js`)**:
  - Usunięto zagnieżdżanie wyników `role: "tool"` w głąb obiektów `role: "assistant"`.
  - Każda rola (`user`, `assistant: tool_call`, `tool: result`, `assistant: text`) renderowana jest 1:1 jako osobny, płaski krok w osi czasu.
  - Dostosowano strumieniowanie SSE (`_bindChatForm`) tak, aby zdarzenia `tool_call` i `tool_result` generowały osobne wiersze na żywo.
- [x] **Nowoczesna Typografia i Frameless Design (`src/controller/web/style.css`)**:
  - Przejście z powszechnego fontu monospace na gładki font sans-serif w czacie.
  - Usunięcie ostrawo-czarnych obramowań `border` i ciężkiego tła pudełkowego wokół odpowiedzi i akcji.
  - Wdrożenie zaokrąglonej pigułki komendy użytkownika (`.msg-user-card`, `background: #1c1c1c`, `border-radius: 12px`).
- [x] **Wyciszenie Kolorystyki i Usunięcie Emotek (`src/controller/web/chat.js` & `style.css`)**:
  - Wyeliminowanie emotek `⚡` i `⚙️` na rzecz czystego symbolu kodu `{}` (`.tool-call-symbol`).
  - Zastąpienie krzykliwego błękitu (`#60a5fa`) stonowanym matowym odcieniem szarości (`#d4d4d8` / `#888888`).
- [x] **Ukrycie Stopek Telemetrii (`src/controller/web/style.css`)**:
  - Zastosowanie `display: none` dla klas `.msg-meta` w czacie, eliminując szum informacyjny pod każdą linią konwersacji.

---

## Rejestr Zrealizowanych Zadań (Sesja 2026-08-09 - Strumieniowanie Wywołań Narzędzi w UI i Satelicie)

- [x] **Dedykowana Wiadomość Akcji (`src/controller/messages.py`)**:
  - Utworzono klasę `AgentActionMessage` opisującą start oraz wynik wywołania narzędzia.
- [x] **Propagacja Zdarzeń SSE (`src/controller/core/telemetry.py`)**:
  - Zarejestrowano w magistrali subskrybenta `AgentActionMessage` i udostępniono event SSE `agent_action`.
- [x] **Emisja Akcji i Ustrukturyzowany Log (`src/controller/orchestrator.py`)**:
  - Zaktualizowano pętlę Orkiestratora tak, by przesyłała obiekty `tool_call` i `tool_result` oraz publikowała `AgentActionMessage`.
- [x] **Zabezpieczenie Strumienia w Czacie (`src/controller/web/chat.js`)**:
  - Dodano flagę `isChatStreaming` i naprawiono parsujące renderowanie kafelków narzędzi na żywo (`renderToolsBlock`).
- [x] **Reaktywne Aktualizacje dla Satelity (`src/controller/web/events.js`)**:
  - Dodano odświeżanie sesji po zdarzeniu `agent_action` (tylko przy `!isChatStreaming`), umożliwiając natychmiastowe widzenie narzędzi przy komunikacji głosowej.
- [x] **Optymalizacja Zapytania o Historię (`store.py`, `interaction.py`)**:
  - Dodano parametr `create_if_missing=False` zapobiegający bezpotrzebnemu tworzeniu pustych sesji.

---

## Rejestr Zrealizowanych Zadań (Sesja 2026-08-08 - Unifikacja MessageBus, Katalog Wiadomości i Eliminacja Tight Coupling)

- [x] **Uniwersalna Magistrala Wiadomości (`src/controller/core/message_bus.py`)**:
  - Usunięto rozczłonkowane `command_bus.py` oraz `event_bus.py`. Stworzono lekki (~35 linii) agnostyczny `MessageBus`.
  - Utworzono `telemetry.py` z buforem historii SSE (500 zdarzeń) podłączonym do `message_bus`.
- [x] **Pełny Katalog Silnie Typowanych Wiadomości (`src/controller/messages.py`)**:
  - Stworzono i posegregowano w 4 sekcje klasy wiadomości: `TextMessage`, `AudioMessage` (ze spójnym polem `sender`), `PlayAudioMessage`, `PauseSatelliteMessage`, `ResumeSatelliteMessage`, `ClearHistoryMessage`, `ClientRegisteredMessage`, `ClientUnregisteredMessage`, `ClientUpdatedMessage`, `ClientCommandResultMessage`, `SatelliteEventMessage`, `ConversationTurnMessage`, `SystemLogMessage`.
- [x] **Eliminacja Ciasnych Powiązań (Tight Coupling)**:
  - Usunięto bezpośrednie importy `client_manager` w `interaction.py`, zastępując je publikacją `PlayAudioMessage` i `ResumeSatelliteMessage`.
  - Wdrożono reaktywne słuchacze w `clients.py` sterujące Satelitami przez gniazda WebSocket.
  - Przeniesiono czyszczenie historii w `manager.py` na asynchroniczne wywołania `asyncio.to_thread` reagujące na `ClearHistoryMessage`.
- [x] **Maksymalne Uproszczenie Orkiestratora (`src/controller/orchestrator.py`)**:
  - Usunięto klasę `TurnContext` i funkcję `_build_context`. `handle_text_message` oraz `handle_audio_message` przekazują treść i `sender` bezpośrednio do `_execute_turn_stream`.
  - Odspawano silnik agenta `engine.py` od globalnego `app_state`, wstrzykując `tools_registry` bezpośrednio z Orkiestratora.

---

## Rejestr Zrealizowanych Zadań (Sesja 2026-08-08 - Refaktoryzacja Warstwy Stanu i EventBus SSE)

- [x] **Eliminacja Katalogu `src/controller/core/state/`**:
  - Usunięto cały folder `state/` usuwając zbędny bloatware.
- [x] **Dostawcy Chmury w Config i Endpoints (`endpoints/cloud.py`)**:
  - Przeniesiono `cloud_store.py` do `endpoints/cloud.py` używając schematu `CloudProvidersConfig` i `config.load()` / `config.save()`.
- [x] **Zarządzanie Klientami (`endpoints/clients.py` & `core/client_registry.py`)**:
  - Zmigrowano obsługę połączeń WS, rejestrację i zapis konfiguracji `ClientsConfig` do `endpoints/clients.py`.
  - Stworzono lekki rejestr w pamięci RAM `core/client_registry.py`.
- [x] **Wyniesienie EventBus i SSE (`core/event_bus.py` & `/api/events`)**:
  - Przeniesiono `event_bus.py` do `core/event_bus.py`.
  - Dodano endpoint SSE `/api/events` w `endpoints/system.py`.
- [x] **Przeniesienie Stanu Runtime (`core/state.py`)**:
  - Przeniesiono zmienne stanu runtime z `app_state.py` do `core/state.py`.
- [x] **Aktualizacja Importów i Testów**:
  - Zaktualizowano wszystkie ścieżki w kodzie oraz poprawiono zestaw testów w `tests/test_llm_backends.py`.

---

## Rejestr Zrealizowanych Zadań (Sesja 2026-08-08 - Restrukturyzacja Architektoniczna Kontrolera)

- [x] **Rozdzielenie Orkiestratora i Konsolidacja Pamięci Sesji**:
  - Przeniesiono zarządcę sesji i czyszczenie historii do `src/controller/core/session/` (`store.py`, `history.py`, `manager.py`).
  - Usunięto stary plik `session_store.py`.
- [x] **Wydzielenie Czystego Mózgu Agenta ReAct (`src/controller/agent/`)**:
  - Utworzono pętlę agenta ReAct w `agent/engine.py`.
  - Przeniesiono prompt systemowy do `agent/prompt/` oraz definicje modeli do `agent/models.py`.
- [x] **Hermetyzacja Rąk Agenta (`src/controller/agent/tools/`)**:
  - Przeniesiono `tools_registry.py` oraz `schemas.py` z top-level `tools/` do `agent/tools/`.
  - Usunięto stary katalog `src/controller/tools/`.
- [x] **Ujednolicenie Dostawców Zmysłów w Warstwie 2 (`src/controller/providers/`)**:
  - Skonsolidowano dostawców LLM pod `providers/llm/` (`openrouter.py`, `ollama.py`, `client_app.py`, `base.py`, `resolver.py`).
  - Utworzono `providers/audio/service.py` realizujący niskopoziomowe zapytania HTTP do STT/TTS.
  - Usunięto katalogi `src/controller/llm/` oraz `src/controller/audio/`.
- [x] **Przemianowanie i Uporządkowanie Endpointów (`src/controller/endpoints/`)**:
  - Przeniesiono dawne `api/` do `src/controller/endpoints/` (`interaction.py`, `clients.py`, `cloud.py`, `system.py`, `tools.py`).
  - Usunięto martwy endpoint `POST /api/satellite/event`.
  - Przeniesiono i zrefaktoryzowano komendy do klienta na `POST /v1/clients/{client_id}/command`.
  - Zrefaktoryzowano pętlę WebSocket w `clients.py` na słownikową mapę handlerów zdarzeń.

---

## Zadania Przyszłe

- [ ] **FastAPI Dependency Injection**:
  - `state.py` jako moduł z globalnymi zmiennymi jest krokiem przejściowym. Docelowo `AppState` przez `Depends()` w routerach.
- [ ] **Wdrożenie Dwuwarstwowych Sub-Agentów**:
  - Implementacja wzorca Mixture of Specialist Sub-Agents opisanego w `docs/hierarchical_subagents_rfc.md`.
- [ ] **Pamięć Długoterminowa** `[ARCH]`:
  - Kluczowy brakujący feature odróżniający Regisa od HA AI. Nowe rozwiązanie wymaga osobnej sesji architektonicznej.
- [ ] **Scheduler Zadań Agenta** `[ARCH]`:
  - Mechanizm odroczonych "szturchnięć" agenta. Niezaprojektowany, wymaga sesji architektonicznej.
- [ ] **Docker Deployment** `[DIST]`:
  - Cel dystrybucyjny: Regis jako obraz Docker na mini PC.
