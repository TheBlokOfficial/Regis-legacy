# Regis: Manifest Projektu

Ten dokument definiuje duszę projektu Regis. Służy jako najwyższy kompas dla programistów oraz agentów AI pracujących przy kodzie. Jeśli jakakolwiek nowa funkcja, narzędzie lub decyzja architektoniczna jest sprzeczna z tym dokumentem — należy ją odrzucić.

---

## 1. Czym jest Regis?

Regis to **autonomiczne oprogramowanie agenta** — instalujesz je na dedykowanej maszynie (mini PC) i od razu otrzymujesz działający system z własnym panelem webowym. Otwierasz przeglądarkę, widzisz dashboard: aktualny status agenta, kanału głosowego, satelitów i integracji. Integracje dodajesz **do Regisa** — nie na odwrót.

Regis nie jest frameworkiem ani biblioteką. Jest produktem — tak jak Home Assistant jest produktem do smart home, Regis jest produktem do prowadzenia agenta w złożonym środowisku osobistym i domowym. Jego rdzeń to pełnoprawny agent (pętla ReAct, zarządzanie sesjami, rejestr narzędzi) z pluginowalną warstwą zmysłów (LLM, STT, TTS, kanały komunikacji) i opcjonalnymi integracjami narzędziowymi (HA, web, kamery). Możesz go rozszerzyć — ale działa i bez żadnych rozszerzeń.

**Istota projektu:** Regis to oprogramowanie które interaktuje z innymi oprogramowaniami w dokładnie taki sam sposób jak człowiek. Nie interesuje go low-level — protokoły, sterowniki, sposób w jaki żarówka Zigbee negocjuje połączenie z koncentratorem. Regis widzi to co widzi człowiek patrzący na dashboard: włączona lub wyłączona. Dlatego Home Assistant — platforma z setkami integracji i całym ekosystemem community — jest z perspektywy Regisa po prostu jedną integracją w katalogu `integrations/`. Regis nie zarządza urządzeniami. Pyta systemy które to robią. To jest właściwy poziom abstrakcji, nie ograniczenie.

Regis jest projektem osobistym — zaprojektowanym do poruszania się w złożonym środowisku domowym i osobistej przestrzeni użytkownika. Nie jest narzędziem enterprise. Nie służy do scrapowania internetu, przetwarzania tysięcy dokumentów ani obsługi korporacyjnych procesów — choć agent ReAct technicznie byłby do tego zdolny. Fakt że coś jest możliwe, nie znaczy że powinno tu trafić. Regis to asystent z osobowością, nie platforma do automatyzacji.

**Tryb podstawowy — głosowy:** Regis komunikuje się z użytkownikiem przez satelity głosowe (ESP32, RegisDesktop). Interakcja głosowa jest trybem prymarnym dla użytkownika końcowego. Panel webowy i czat tekstowy pełnią rolę narzędzi deweloperskich (podgląd wywołań agenta, debugowanie, konfiguracja) — nie są przeznaczone do codziennej interakcji z systemem.

Projekt jest hobby — jakość, spójność i czystość architektury są ważniejsze niż szybkie dostarczanie funkcji.

---

## 2. Złota Zasada: Przezroczystość (Zasada "Nie Przeszkadzaj")

**System musi być organiczny i nigdy nie może wchodzić użytkownikowi w drogę.**

Największym grzechem w tym projekcie jest implementacja funkcji "na siłę", tylko dlatego, że technologia na to pozwala. Jeśli nowa funkcjonalność (nawet najbardziej zaawansowana technologicznie) sprawia, że system staje się uciążliwy, wolny lub irytujący — należy ją usunąć lub całkowicie przeprojektować. W najgorszym scenariuszu Regis ma być po prostu **niewidzialny i bezkolizyjny** dla domowników.

---

## 3. Podział Systemu i Hierarchia Komponentów

Podział elementów w systemie jest prosty i jednoznaczny:

1. **Klienci (Satelity)** — urządzania stykowe w pokojach (ESP32, Satelita Desktopowa) będące cienkimi klientami I/O (audio/tekst).
2. **Providerzy (Dostawcy Zmysłów)** — dzielą się na dwie grupy:
   - **Agent (LLM Provider)** — najwyżej w hierarchii. To sam agent (mózg) i jego pętla ReAct (OpenRouter w chmurze, Ollama lokalnie). Bez aktywnego LLM agent nie istnieje (fallback: Parser offline).
   - **Kanał Głosowy (`voice_channel`)** — logiczny stan gotowości interakcji głosowej, budowany dynamicznie z niezależnych providerów **STT** (transkrypcja mowy) oraz **TTS** (synteza głosu) dobieranych z worka dostępnych zmysłów.

### Zasady Kanału Głosowego:
- **Brak Sztywnego Bundlowania**: Nie robimy żadnego wiązania konkretnego providera STT z konkretnym providerem TTS. Provider STT (np. Faster-Whisper, Cloud STT) oraz provider TTS (np. Piper, ElevenLabs) są całkowicie niezależnymi usługami dobieranymi z ogólnego "worka".
- **Warunek Aktywności**: Kanał głosowy jest uznawany za **aktywny** (`voice_channel_ready = STT_active AND TTS_active`), gdy w worku aktywnych providerów znajduje się przynajmniej jeden aktywny dostawca STT i przynajmniej jeden aktywny dostawca TTS.
- **Infrastruktura I/O**: STT i TTS nie są narzędziami w rozumieniu `ToolRegistry` — agent ich nie wywołuje. Są przezroczystą infrastrukturą I/O satelitów (STT konwertuje głos przed agentem, TTS tekst po agencie).

### 3.1 Rdzeń Systemu (Core)

Core to wszystko, co stanowi samego agenta. Instalując Regisa, dostajesz kompletny mózg i układ nerwowy — gotowy do działania po podłączeniu zmysłów. Core nie wymaga konfiguracji, żeby *istnieć* — wymaga podłączonych providerów, żeby *działać*.

**Zawartość:**
- **Pętla ReAct** — wewnętrzny monolog `<thought>`, routing narzędzi, obsługa tury konwersacji
- **Session Manager** — historia konwersacji per sesja, przechowywanie i odtwarzanie kontekstu
- **Tool Registry** — mechanizm rejestracji i wywoływania narzędzi (nie konkretne narzędzia — tylko mechanizm)
- **Abstrakcyjne interfejsy dla zmysłów:**
  - `ILLMProvider` — gniazdo na model językowy (agent, rdzeń systemu)
  - `ISTTProvider` — gniazdo na transkrypcję mowy (wejście Kanału Głosowego)
  - `ITTSProvider` — gniazdo na syntezę mowy (wyjście Kanału Głosowego)
  - `ISatellite` — gniazdo na kanał komunikacji z użytkownikiem
- **Protokół wewnętrzny** — schematy i kontrakty komunikacyjne między komponentami

**Zasada:** Core nie zawiera żadnych referencji do konkretnych providerów, satelit ani narzędzi. Wie tylko, że *coś* implementuje dany interfejs.

**Walidacja przy starcie:** Przynajmniej jedno `ILLMProvider` musi być podłączone. Bez LLM agent nie funkcjonuje — to fundamentalne wymaganie, inaczej niż brak narzędzi (bez integracji HA agent po prostu nic nie może *zrobić* w smart home, ale nadal istnieje).

### 3.2 Dostawcy Zmysłów i Satelity (Providers & Satellites)

Konkretne implementacje podłączane do interfejsów przy starcie. Zmiana providera STT/TTS nie wymaga dotknięcia Core — wymaga jedynie zamiany implementacji.

| Interfejs | Przykładowe implementacje |
|---|---|
| `ILLMProvider` | OpenRouter, Ollama, Anthropic API |
| `ISTTProvider` | Faster-Whisper (lokalny Audio Service), Cloud STT API |
| `ITTSProvider` | Piper (lokalny Audio Service), Cloud TTS API |
| `ISatellite` | ESP32, Satelita Desktopowa, HTTP API |

**Regis Desktop** to czysta implementacja satelity dla systemu Windows (VAD, WakeWord lokalne, audio I/O). Usługi LLM, STT i TTS działają na dedykowanej maszynie (mini PC) jako osobne procesy (Ollama + Audio Service).

### 3.3 Integracje (Narzędzia)

Konkretne zdolności agenta do działania w świecie zewnętrznym. W fully opcjonalne — agent funkcjonuje bez żadnej integracji, po prostu nie może nic *zrobić* poza rozmową.

**Mechanizm:** Każda integracja rejestruje swoje narzędzia w `ToolRegistry` przy starcie. Core nie wie skąd narzędzia pochodzą — widzi tylko ich sygnatury i wywołuje je przez abstrakcję (np. Home Assistant, przeglądarka internetowa, kamery IP, MQTT).

---

## 3.5 Referencyjna Implementacja (Docelowy Deployment)

> Poniższe sekcje opisują **docelową implementację referencyjną** — nie definicję systemu. Mini PC, RegisDesktop i ESP32 to konkretny deployment. Architektura Regisa jest od nich niezależna i może być wdrożona na innym sprzęcie lub z innymi kanałami komunikacji.

### Centrum Systemu: Mini PC (24/7)

Mini PC (np. Minisforum lub podobny x86) działa nieprzerwanie jako centrum systemu. Hostuje trzy procesy:

| Proces | Rola | Technologia |
|---|---|---|
| **Controller** | Lekki daemon: routing sesji, rejestr narzędzi, Tool Registry, proxy HA | Python (Twój kod). Nigdy nie hostuje LLM ani audio. |
| **Ollama** | LLM inference, HTTP API na `localhost:11434` | Zewnętrzny daemon Go. Controller rozmawia z nim bezpośrednio przez HTTP — bez wrappera. |
| **Audio Service** | STT (Faster-Whisper) + TTS (Piper), HTTP API | Python (Twój kod). Osobny daemon — satelity strumieniują audio przez sieć. |

**Zasady deploymentu:**
- Controller pozostaje lekkim daemonem — nie hostuje LLM, nie przetwarza audio.
- Ollama zarządza sobą jako zewnętrzny daemon. Controller jedynie wywołuje jego HTTP API.
- Audio Service musi być osobnym procesem: satelity (ESP32, RegisDesktop) strumieniują do niego audio przez sieć — wymaga sieciowego endpointu.

### Bezpieczeństwo Systemu: RPi5 (opcjonalnie)

RPi5 pełni rolę ostatniej linii obrony gdy system przechodzi w Tryb Awaryjny. Hostuje:
1. **Parser offline** — lekki model ze Structured Outputs obsługujący proste komendy urządzeń.
2. **Awaryjny STT** — lekki model Whisper do transkrypcji audio.

RPi5 nie jest wymagany w podstawowym deploymencie na mini PC. Aktywowany wyłącznie gdy brakuje LLM lub Kanału Głosowego.

### Satelity (Cienkie Klienty)

Każde urządzenie interaktywne jest satelitą — rejestruje się w Kontrolerze i strumieniuje audio do Audio Service:

| Satelita | Rola |
|---|---|
| **RegisDesktop** | Windows PC użytkownika: VAD, WakeWord lokalne, audio I/O |
| **ESP32** | Dedykowany sprzęt w domu: VAD, strumieniowanie audio |

### Faza Przejściowa (Aktualny Stan Dev)

Dopóki mini PC nie jest skonfigurowany, RegisDesktop pełni podwójną rolę: satelita + lokalne usługi (Ollama, Faster-Whisper, Piper). Jest to stan tymczasowy. W tej fazie nie ma Audio Service jako osobnego procesu — RegisDesktop dostarcza te usługi bezpośrednio.

### Pipeline Przetwarzania Audio

**Dla ESP32 (ograniczony sprzęt):**
```
[ESP32]              [Audio Service]     [Controller]
VAD wykrywa mowę
→ stream audio ─────→ WakeWord detection
                       → brak WakeWord → odrzuć
                       → WakeWord! → STT (Whisper)
                       → tekst ────────────────────→ LLM (ReAct + narzędzia)
                       ←──────────────────────────── odpowiedź tekst
                     TTS (Piper) → audio
←────────────────────
→ odgrywa odpowiedź
```

**Dla RegisDesktop (pełny sprzęt):**
```
[RegisDesktop]       [Audio Service]     [Controller]
VAD + WakeWord (lokalnie)
→ stream audio ─────→ STT (Whisper)
                       → tekst ────────────────────→ LLM (ReAct + narzędzia)
                       ←──────────────────────────── odpowiedź tekst
                     TTS (Piper) → audio
←────────────────────
→ odgrywa odpowiedź
```

**Kluczowe decyzje projektowe (niezmienione):**
- VAD zawsze na Satelicie — lekki algorytm energetyczny, radykalnie redukuje niepotrzebne strumieniowanie.
- WakeWord na ESP32 zbyt kosztowny — delegowany do Audio Service. Na desktopie działa lokalnie.
- STT zawsze w Audio Service — standaryzuje jakość transkrypcji niezależnie od Satelity.

---

## 3.6 Warstwa Integracji (Rozstrzygnięta Zasada Architektoniczna)

**Home Assistant jest jedną z możliwych integracji — nie jedyną.**

Katalog `integrations/` to granica między logiką systemu a światem zewnętrznym. HA jest pierwszą i prawdopodobnie największą integracją (żarówki, przełączniki, klimatyzacja, odtwarzacze — wszystko co najłatwiej podłączyć przez HA), ale architektura nie zakłada jego wyłączności.

Przyszłe integracje mogą obejmować m.in.:
- Bezpośrednia komunikacja MQTT
- Inne platformy Smart Home (np. Zigbee2MQTT)
- Własne skrypty i usługi sieciowe
- Dowolny inny endpoint, który ma sens w kontekście sterowania domem

**Konsekwencja dla kodu:** `ToolsRegistry` i `RemoteToolsRegistry` są agnostyczne wobec źródła narzędzi — rozmawiają z `integrations/` przez abstrakcyjny interfejs, nie bezpośrednio z HA. Dodanie nowej integracji oznacza: nowy plik w `integrations/`, nowe narzędzie w `protocol/schemas.py` i nowy handler w `protocol/tools_registry.py`. Żadne inne warstwy nie wymagają zmian.

---

## 3.7 Wizja Docelowa

Cel projektu: **mini PC jako centrum systemu** z chmurą jako domyślnym dostawcą LLM lub Ollamą lokalnie gdy chmura jest droga lub niedostępna.

```
┌──────────────────────────────────────────┐
│           CENTRUM (Mini PC, 24/7)        │
│                                          │
│  [Controller]  ←──→  [Ollama (LLM)]     │
│   routing              inference         │
│   rejestr        ←──→  [Audio Service]  │
│   proxy HA              STT + TTS        │
└──────────────────────────────────────────┘
           ↑                    ↑
        [ESP32]           [RegisDesktop]
     VAD+stream            satelita PC
                          ↕
          ┌───────────────────────────────┐
          │     PROVIDERY (dynamiczne)    │
          │                               │
          │  LLM:  OpenRouter / Ollama    │
          │  STT:  Cloud API / Whisper    │
          │  TTS:  Cloud API / Piper      │
          └───────────────────────────────┘
```

**Kluczowe właściwości docelowego układu:**
- Mini PC jest zawsze włączony. Hostuje Controller, Ollama i Audio Service.
- Chmura (OpenRouter + cloud STT/TTS) jest domyślnym providerem LLM — bez zakupu dodatkowego GPU.
- Gdy chmura podrożeje lub pojawi się sensowny sprzęt lokalny — podmiana providera nie wymaga zmian w architekturze.
- RegisDesktop rejestruje się jako satelita głosowa gdy uruchomiony. Nie dostarcza usług LLM/STT/TTS w docelowym produkcie.

---

## 4. Rejestr Encji (Entity Registry)

Kontroler jest jedynym źródłem prawdy. Wszystkie procesy w systemie — Satelity i Węzły Robocze — **rejestrują się** w Kontrolerze przy starcie oraz cyklicznie odnawiają swą rejestrację w tle (Continuous Registration). Dostarczają mu w ten sposób metadanych o sobie, a dzięki pętli ponawiania uodpornione są na restarty Kontrolera. Kontroler używa tych metadanych do podejmowania decyzji routingowych i budowania kontekstu dla modelu.

### Metadane Satelity
Każda Satelita przy rejestracji podaje:
- `id` — unikalny identyfikator urządzenia
- `room` — pomieszczenie, w którym fizycznie się znajduje (np. `"salon"`, `"sypialnia"`)
- `type` — typ Satelity (`esp32`, `desktop`, `terminal`)
- `capabilities` — co potrafi robić (`audio_in`, `audio_out`, `text`)
- `wakeword_local` — czy obsługuje WakeWord lokalnie (prawda dla desktopów, fałsz dla ESP32)

### Metadane Węzła Roboczego
Każdy Węzeł Roboczy przy rejestracji podaje:
- `id` — unikalny identyfikator
- `host` / `port` — adres sieciowy węzła
- `model_name` — konkretny model Ollamy (np. `qwen3.5:9b`)
- `tier` — klasa modelu (`butler` lub `regis`)

### Kontekst Przestrzenny (Spatial Context Filtering)

To jest kluczowy mechanizm umożliwiający efektywną pracę małych modeli.

Gdy Satelita z pomieszczenia `salon` wysyła żądanie, Kontroler **nie podaje modelowi pełnej listy urządzeń domowych**. Zamiast tego filtruje ją do urządzeń przypisanych do pokoju `salon` i buduje dla modelu wąski, precyzyjny kontekst. Lekki parser operuje wtedy na liście 5 urządzeń zamiast 50 — to nie jest ograniczenie, to jest precyzja.

**Otwarta kwestia — cross-room commands:** Co gdy użytkownik w salonie mówi "wyłącz światło w sypialni"? Propozycja: model dostaje domyślnie swój pokój, ale posiada narzędzie `get_devices(room=...)` pozwalające mu sięgnąć po inne pomieszczenie gdy wyraźnie o to prosi. Większy model na desktopie może od razu otrzymywać pełną listę urządzeń. **Nierozstrzygnięte — wymaga dalszej dyskusji.**

### Co Kontroler synchronizuje do Węzłów
Kontroler przechowuje i dystrybuuje:
- **Prompty systemowe** — tożsamość Regisa, instrukcje behawioralne (rdzeń persony)
- **Historia konwersacji** — aktywne sesje, umożliwia migrację kontekstu między węzłami
- **Rejestr wszystkich encji** — lista aktywnych Satelit i Węzłów z metadanymi

---

## 5. System Providerów i Degradacja

System ma dwa niezależne wymagania o różnych konsekwencjach dla działania:

| Komponent | Rola | Konsekwencja braku |
|---|---|---|
| **LLM** | Agent (mózg) — bez niego system nie istnieje jako agent | Tryb Awaryjny: tylko Parser offline |
| **Kanał Głosowy (STT+TTS)** | Infrastruktura I/O satelitów — przezroczysta konwersja głos↔tekst | Tryb Cichy: agent działa, satelity offline |

STT i TTS tworzą razem **Kanał Głosowy** (`voice_channel`). Ich dostępność oceniana jest łącznie: `voice_channel_ready = STT_active AND TTS_active`. Stan częściowy = kanał niedostępny.

### Model Trzystanowy

**Tryb Operacyjny Pełny** — LLM i Kanał Głosowy aktywne:
```
LLM: [≥1] AND STT: [≥1] AND TTS: [≥1]
→ pełny agent ReAct, rozmowa głosowa przez satelity
```

**Tryb Operacyjny Cichy** — LLM aktywny, Kanał Głosowy niedostępny:
```
LLM: [≥1] AND voice_channel: [0]
→ agent myśli i działa (scheduler, narzędzia, HA)
→ satelity offline (czerwona dioda), użytkownik nie może inicjować rozmowy głosowej
```

**Tryb Awaryjny** — brak LLM:
```
LLM: [0]
→ Parser offline (RPi5), tylko proste deterministyczne komendy urządzeń
```

Przejście między trybami jest atomowe. Użytkownik zawsze wie czego oczekiwać: zielona dioda = tryb pełny, czerwona dioda = brak głosu (agent nadal pracuje autonomicznie), brak reakcji = tryb awaryjny.

**Uwaga architektoniczna:** Parser (RPi5) jest osobnym, zawsze dostępnym mechanizmem bezpieczeństwa — nie jest częścią systemu providerów i nie wymaga rejestracji.

---

## 5.1 Turn Context — Kontekst Tury Agenta

Każde wywołanie agenta niesie ze sobą `TurnContext` — lekki obiekt metadanych opisujący okoliczności tury. Orchestrator buduje go przed wywołaniem agenta i używa do zarządzania pipeline'em pre/post-processing (STT, TTS). Agent otrzymuje go jako część promptu systemowego — dzięki temu wie w jakiej sytuacji się znajduje i może dostosować zachowanie.

### Pola TurnContext

| Pole | Wartości | Opis |
|---|---|---|
| `source` | `user` / `scheduler` / `system_event` | Kto wywołał agenta |
| `satellite_id` | `"esp32-salon"` / `null` | Satelita źródłowa (jeśli user) |
| `room` | `"salon"` / `null` | Pokój użytkownika (jeśli user) |
| `input_modality` | `voice` / `text` / `none` | Jak wejście dotarło do agenta |
| `output_modality` | `voice` / `text` / `silent` | Jak odpowiedź ma być dostarczona |
| `response_target` | `satellite_id` / `null` | Gdzie wysłać odpowiedź |

### Jak Agent Widzi Kontekst

Orchestrator wstrzykuje opis do promptu systemowego:

```
[Wywołanie przez użytkownika]
<turn_context>
  Wywołanie: użytkownik, satelita ESP32-salon (pokój: Salon)
  Tryb wyjścia: głosowy — Twoja odpowiedź zostanie odtworzona w pokoju Salon
</turn_context>
```

```
[Wywołanie przez scheduler]
<turn_context>
  Wywołanie: scheduler systemowy
  Tryb wyjścia: brak — odpowiedź nie zostanie odtworzona. Wykonaj działanie i zakończ.
</turn_context>
```

### Ujednolicony Pipeline

`TurnContext` sprawia że pipeline jest jeden — różne konfiguracje, ten sam kod:

```
[Trigger] → [TurnContext]
          → [Preprocessing: STT jeśli input_modality=voice, pass-through jeśli text/none]
          → [Agent (LLM, ReAct) — zawsze identyczny, zawsze tekst in/out]
          → [Postprocessing: TTS→satellite jeśli output_modality=voice, log jeśli silent]
```

Nie ma osobnych pipeline'ów dla użytkownika i schedulera. Jest jeden pipeline z dynamicznym kontekstem. TurnContext łączy się ze Spatial Context Filtering (§4) — agent dostaje zarówno kontekst przestrzenny (pokój, urządzenia) jak i kontekst interakcji (skąd pochodzi, jak odpowiedzieć).

**Stan Trybu Cichego a TurnContext:** Gdy `voice_channel` jest niedostępny, Orchestrator ustawia `output_modality = silent` dla wszystkich tur — nawet tych wywołanych przez użytkownika (który widzi czerwoną diodę i wie że nie może rozmawiać). Agent wie że jego odpowiedź nie zostanie odtworzona i może dostosować zakres działań.

---

## 6. Persona Agenta

### Persona jest user-defined

System Regis nie narzuca konkretnego charakteru, tonu ani stylu agenta — to jest konfiguracja użytkownika. Użytkownik definiuje personę w pliku konfiguracyjnym (imię, charakter, instrukcje behawioralne). Regis dostarcza mechanizm — nie treść.

**Zasada spójności:** Cokolwiek użytkownik skonfiguruje jako personę, system musi ją utrzymywać konsekwentnie we wszystkich trybach pracy i na wszystkich węzłach. Persona zdefiniowana przez użytkownika nie może się zmieniać w zależności od tego, który model LLM aktualnie pracuje pod spodem.

### Cele projektowe systemu (nie persony)

Regis jako oprogramowanie ma następujące **cele projektowe** — nie są to twierdzenia o aktualnym stanie, lecz intencje które powinny kierować każdą decyzją architektoniczną i UX:

- **Szybkość** — minimalne opóźnienia między wejściem użytkownika a odpowiedzią systemu
- **Bezpośredniość** — brak zbędnych kroków pośrednich, warstw abstrakcji które nie wnoszą wartości
- **Niezawodność** — system działa albo jawnie informuje o problemie; stany częściowe i ciche błędy są niedopuszczalne

### Implementacja spójności persony między trybami
- **Konfigurowalny rdzeń persony:** W każdym prompcie, niezależnie od trybu i tieru, osadzony jest opis persony zdefiniowanej przez użytkownika. Tryb pracy (NLU vs ReAct) zmienia się — persona nie.
- **Graceful Degradation:** Agent nigdy nie udaje, że potrafi czegoś, czego nie potrafi. Odpowiada zwięźle i bez przepraszania. Brak tłumaczeń technicznych.
- **Zachowanie Konserwatywne (gdy komunikacja niemożliwa):** Jeśli agent nie może skomunikować się z użytkownikiem a działanie wymaga potwierdzenia lub jest potencjalnie inwazyjne — nie wykonuje go. Zapisuje zamiar do późniejszego przypomnienia gdy komunikacja wróci. Działania bezpieczne i nieodwracalnie pozytywne może wykonać bez ogłaszania.
- **Capability Layer (Warstwa Możliwości):** Prompty pisane są warstwowo. Rdzeń persony jest stały. Zestaw narzędzi i tryb pracy zmienia się w zależności od dostępnych providerów.

---

## 7. Aktualny Dług Architektoniczny

**Zrealizowano (historycznie):**
- Rozbicie monolitu na trzy niezależne usługi (`controller`, `controller.worker`, `node`)
- Izolacja konfiguracji na profile per instancja (pliki `.env`)
- Auto-Discovery węzłów (UDP Broadcast Zero-Conf, `protocol/discovery.py`)
- Rejestr Encji (Satelity i Węzły rejestrują się w Kontrolerze)
- **Izolacja usług (monorepo):** `src/protocol/` oczyszczony do roli chudego kontraktu sieciowego. Każda usługa (`controller`, `node`, `worker`) ma własne kopie `config.py`, `logger.py`, `exceptions.py`, `history_utils.py`, `llm_backends/`. Zero cross-importów między usługami.
- **Warstwa abstrakcji LLM (`llm_backends/`)** w Kontrolerze zaimplementowana (`controller/llm_backends/`). OpenRouter i Ollama jako oddzielne backendy z wspólnym interfejsem `LLMBackend`.

**Aktualny dług (oczekuje realizacji):**
- **Audio Service** — nowy komponent (Python daemon: Faster-Whisper + Piper) do zaimplementowania jako osobny proces na mini PC. Aktualnie jego rolę pełni RegisDesktop (tymczasowo, faza dev). Wymagany do osiągnięcia docelowej architektury z mini PC jako centrum.
- **Formalne oddzielenie ról RegisDesktop** — podział na "tryb dev" (usługi + satelita) i "tryb prod" (tylko satelita). Wymaga refaktoryzacji RegisDesktop po wdrożeniu Audio Service.
- **Dystrybucja Windows:** Inno Setup (`RegisNodeSetup.exe`) jest zaprojektowany (`docs/distribution_rfc.md`) ale instalator nie jest jeszcze zbudowany produkcyjnie — patrz `TASKS.md`.
- **Pamięć Długoterminowa:** Stary system Notatnika wycięty. Nowe rozwiązanie (np. wektorowe) nie zostało jeszcze zaprojektowane — patrz `TASKS.md`.
- **System Providerów (STT/TTS):** Warstwa abstrakcji dla STT i TTS nie jest jeszcze zaimplementowana jako formalne klasy bazowe w kodzie. Implementacja jest częścią `[ARCH — Phase 2]`.
- **Formalne interfejsy warstwy 2:** Abstrakcyjne interfejsy `ILLMProvider`, `ISTTProvider`, `ITTSProvider`, `ISatellite` istnieją jako koncepcja architektoniczna (§3.1) — nie są jeszcze sformalizowane jako klasy bazowe w kodzie.
