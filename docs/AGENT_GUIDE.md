# Regis: Przewodnik dla Agentów AI

> Ostatnia aktualizacja: 2026-08-11.

Ten dokument jest przeznaczony wyłącznie dla agentów AI (LLM) pracujących nad projektem. Odpowiada na pytanie: *jak myśleć o tym projekcie*, a nie tylko co w nim jest.

## O tym dokumencie

`AGENTS.md` (w root repozytorium) jest krótki i operacyjny — czytasz go zawsze, na starcie i w każdej kolejnej interakcji. Ten plik, `docs/AGENT_GUIDE.md`, jest wczytywany raz na starcie sesji (patrz procedura startowa w `AGENTS.md`) i zawiera uzasadnienia, protokoły i historię decyzji, których nie trzeba trzymać "pod ręką" w każdej turze. Jeśli dodajesz tu nową treść, zapytaj: czy to wiedza potrzebna raz na sesję, czy w każdej turze? To drugie należy do `AGENTS.md`, nie tutaj.

---

## Hierarchia Lektury (Kolejność ma Znaczenie)

Przed podjęciem JAKIEJKOLWIEK pracy wykonaj lekturę w tej kolejności:

1. **`docs/MANIFEST.md`** — Przeczytaj uważnie i zrozum. To jest najważniejszy plik w projekcie. Definiuje filozofię, cele i rozstrzygnięte decyzje projektowe. Jeśli jakakolwiek Twoja propozycja jest sprzeczna z tym dokumentem — jest zła, niezależnie od tego jak technicznie poprawna.
2. **`.agents/HANDOFF.md`** — Stan projektu po ostatniej sesji. Co zostało zrobione, co jest zepsute, od czego zacząć.
3. **`.agents/TASKS.md`** — Lista aktywnych zadań.
4. **`docs/ONBOARDING.md`** — Sięgaj po ten dokument gdy musisz zrozumieć konkretny plik lub mechanizm. Nie musisz go czytać w całości na starcie.

---

## Hierarchia Autorytetu w Decyzjach

Gdy stoisz przed decyzją projektową lub architektoniczną, stosuj następującą kolejność:

```
MANIFEST.md (filozofia)
    ↓
Wyraźna instrukcja użytkownika w tej sesji
    ↓
Decyzje z HANDOFF.md (poprzednie sesje)
    ↓
Twój osąd techniczny
```

Jeśli Twój osąd techniczny sugeruje coś innego niż MANIFEST.md — nie wcielaj swojego pomysłu w życie. Zamiast tego zaprezentuj go użytkownikowi jako propozycję, wyraźnie zaznaczając że wymaga to przeglądu zasad projektowych.

---

## Protokół Eskalacji Decyzji Architektonicznych

Nie istnieje oddzielna rola "Agenta Architekta". Każdy agent — niezależnie od tego czy zajmuje się kodem czy dokumentacją — stosuje ten sam protokół gdy natrafi na decyzję wykraczającą poza jego bieżące zadanie.

**Kiedy zatrzymać pracę i zaeskalować:**
- Odkrywasz, że realizacja zadania wymaga zmiany w filozofii projektu (MANIFEST.md).
- Napotykasz sprzeczność między tym, co zadanie nakazuje, a tym co mówi MANIFEST.md.
- Odkrywasz błąd projektowy — nie implementacyjny.
- Masz do wyboru dwa podejścia techniczne prowadzące do fundamentalnie różnych ścieżek architektonicznych.

### Ostrzeżenie: Skażenie Kontekstu (Context Contamination)

Po kilkunastu turach intensywnej pracy nad kodem Twój kontekst jest wypełniony liniami kodu, stack trace'ami i błędami parsowania. To **fizycznie degraduje Twoją zdolność do myślenia architektonicznego**. Nie jesteś w stanie tego poczuć — po prostu proponujesz rzeczy, które wydają Ci się sensowne z perspektywy zaśmieconego kontekstu. Propozycje architektoniczne z takiego stanu często tworzą dług techniczny.

**Zasada:** Im dłuższa sesja kodowania, tym mniej ufaj swojej własnej ocenie w kwestiach architektonicznych.

### Mechanizm: Czysty Architectural Handoff

Gdy natrafiasz na decyzję architektoniczną w trakcie sesji kodowania — **nie próbuj jej rozwiązywać w bieżącym kontekście**. Zamiast tego wyekstrahuj istotę problemu do `HANDOFF.md` w standardowym formacie i zakończ sesję. Użytkownik otworzy świeżą rozmowę dedykowaną tej jednej kwestii.

**Format wpisu w HANDOFF.md:**
```
## DECYZJA_ARCHITEKTONICZNA — Wymagana Nowa Sesja
Kontekst: [co robiłem gdy to odkryłem — 1-2 zdania]
Problem: [jaka decyzja wymaga podjęcia — konkretnie i precyzyjnie]
Opcja A: [opis]
Opcja B: [opis]
Moja obserwacja: [UWAGA: mój kontekst jest skażony kodem — nie ufaj tej ocenie w pełni]
```

Twoja wartość jako agenta kodującego polega na tym, że rozumiesz techniczny kontekst problemu. Twój obowiązek to wyekstrahowanie tej wiedzy do czystego dokumentu — nie podejmowanie decyzji.

**Czego NIE robić:**
- Nie podejmuj decyzji architektonicznych samodzielnie, nawet jeśli jesteś "prawie pewien".
- Nie implementuj rozwiązania tymczasowego "na teraz" zakładając że ktoś to poprawi — tymczasowe rozwiązania żyją wiecznie.
- Nie pomijaj eskalacji z powodu "nie chcę przerywać" — architektoniczny błąd jest droższy niż przerwa.

---

## Prawa Zapisu do Dokumentów

Każdy agent ma pełny odczyt do wszystkich dokumentów. Prawa zapisu są następujące:

| Dokument | Agent pracujący nad kodem | Uwagi |
|---|---|---|
| `.agents/HANDOFF.md` | Zawsze aktualizuje | Obowiązkowe na końcu każdej sesji |
| `.agents/TASKS.md` | Zawsze aktualizuje | Odhaczaj ukończone zadania |
| `docs/ONBOARDING.md` | Może aktualizować | Tylko fakty — nowe pliki, zmieniona struktura. Nigdy filozofia. |
| `docs/MANIFEST.md` | Tylko po decyzji użytkownika | Zmiany wyłącznie jako efekt rozmowy z użytkownikiem |
| `docs/AGENT_GUIDE.md` | Tylko po decyzji użytkownika | Jak wyżej |

**Zasada prosta:** Dokumenty operacyjne (HANDOFF, TASKS) — aktualizujesz sam. Dokumenty filozoficzne (MANIFEST, AGENT_GUIDE) — tylko jako efekt decyzji podjętej z użytkownikiem w tej sesji. ONBOARDING.md jest pośrodku — fakty tak, filozofia nie.

---

## Decyzje Rozstrzygnięte (Traktuj Jako Domyślne)

Poniższe decyzje były świadomie przemyślane i rozstrzygnięte. Propozycja ich zmiany bez wyraźnej prośby użytkownika jest błędem.

> **Polityka od 2026-08-11:** ta tabela jest wczytywana w całości do kontekstu na starcie *każdej* sesji i rośnie z każdą decyzją architektoniczną bez ograniczeń — to realny i rosnący koszt tokenów. **Nowe decyzje architektoniczne zapisuj jako osobne pliki ADR w `docs/adr/NNNN-krotki-tytul.md`** (jedna decyzja = jeden plik, format: Kontekst / Decyzja / Konsekwencje / Data). W tej tabeli zostawiaj wtedy wyłącznie jednowierszowy wpis-indeks z linkiem do pliku ADR, nie pełne uzasadnienie. Istniejące wiersze poniżej zostają tu, dopóki nie zostaną świadomie zmigrowane na wyraźne polecenie użytkownika — nie migruj ich "przy okazji" (zasada 1 z `AGENTS.md` dotyczy też tego dokumentu).

| Decyzja | Powód |
|---|---|
| Narzędzia renderowane jako tekst XML w prompcie (`<tools>`), nie jako pole `tools` w API Ollamy | "Droga A" — eliminuje wstrzykiwanie przez Ollamę angielskiego bloku instrukcji, które powoduje "angielski drift" w odpowiedziach modelu |
| Stop Token `</action>` w API Ollamy | Wymusza liniową pętlę ReAct. Bez tego modele Qwen halucynują równoległe wywołania |
| Parser offline (RPi5) używa Structured Outputs (JSON Schema), nie ReAct | Model jest zbyt mały na niezawodny ReAct. JSON Schema wymusza deterministyczne parsowanie komend |
| Pozytywne ramowanie w promptach zamiast zakazów | Negative framing degraduje zdolności kognitywne małych modeli |
| System jest agnostyczny wobec providera (LLM, STT, TTS) — chmura i local to równorzędne opcje | Architektura nie zakłada wyłączności żadnego backendu. Wymiana providera nie wymaga zmian poza warstwą abstrakcji |
| Parser offline (RPi5) jest offline fallbackiem — nie siedzi w ścieżce krytycznej gdy internet działa | Parser-first generował opóźnienie dla każdego zapytania które on odrzucał. Chmurowy LLM obsługuje proste komendy równie dobrze i szybko |
| OpenRouter jest domyślnym providerem LLM w produkcji — preferowane modele OSS | Ekonomika: cloud API jest tańszy niż dedykowany sprzęt lokalny przy obecnych cenach RAM i GPU |
| Dwustanowa degradacja: pełny tryb gdy komplet providerów, fallback gdy brakuje choćby jednego | Prostota i przewidywalność. Stany częściowe (np. LLM bez TTS) tworzą nieintuicyjne zachowania |
| Ascetyczny styl CLI (bez jaskrawych kolorów, minimalne emoji) | Zasada estetyczna projektu. Opisana w `AGENTS.md` |
| Historia konwersacji przechowuje tylko pełne tury (user+assistant), nie ślad ReAct | Ślad ReAct (myśli + wywołania) zaśmieca kontekst i powoduje amnezję przy długich sesjach |
| Dystrybucja Windows = Inno Setup Installer + Python systemowy (nie PyInstaller) | PyInstaller odrzucony: black box, podejrzany wygląd, opóźnienia startu. Szczegóły: `docs/distribution_rfc.md` |
| **Czysty podział architektury: Core / Zmysły & Satelity / Integracje** | Core = pętla ReAct + abstrakcyjne interfejsy. Zmysły & Satelity = LLM, STT, TTS, Satelity. Integracje = narzędzia (HA, web, itp.). |
| **LLM stoi wyżej w hierarchii niż STT/TTS — nie traktuj ich jako równorzędnych komponentów** | LLM = agent (mózg systemu). STT/TTS = Kanał Głosowy (niższy poziom abstrakcji, wymagany interfejs użytkownika). Traktowanie wszystkich trzech jako równych byłoby błędem strukturalnym. Sesja 2026-08-10. |
| **STT i TTS tworzą logiczny "Kanał Głosowy" bez sztywnego bundlowania** | STT i TTS to niezależni providerzy dobierani z worka. Kanał głosowy jest aktywny, gdy `voice_channel_ready = STT_active AND TTS_active` (brak sztywnych par STT+TTS). Sesja 2026-08-10. |
| **RegisDesktop w finalnym produkcie = satelita only. Usługi LLM/STT/TTS → mini PC** | Centrum systemu to mini PC hostujący Controller + Ollama + Audio Service. RegisDesktop nie jest wymagany jako dostawca usług — pełni wyłącznie rolę satelity głosowej na Windows. Sesja 2026-08-10. |
| **Controller rozmawia z Ollamą bezpośrednio przez HTTP — bez wrappera** | Ollama jest zewnętrznym daemonem HTTP (`localhost:11434`). Dodatkowy wrapper = zbędna warstwa złożoności. Controller pozostaje lekki. Sesja 2026-08-10. |
| **Audio Service = osobny proces (Faster-Whisper + Piper) na mini PC** | Satelity strumieniują audio przez sieć → wymagany sieciowy endpoint HTTP → nie może być wbudowany w Controller. Separacja utrzymuje Controller jako lekki daemon. Sesja 2026-08-10. |

---

## Filozofia Wynikająca z MANIFEST.md (Tłumaczenie na Praktykę)

**"Nie Przeszkadzaj"** oznacza w praktyce dla agenta:
- Nie dodawaj funkcji, o które nie proszono.
- Nie dodawaj walidacji, logów czy obsługi błędów "dla bezpieczeństwa" jeśli nie jest to wymagane.
- Nie upiększaj kodu jeśli działa. Refaktoryzuj tylko gdy wprost polecono.
- Nie proponuj złożonych rozwiązań tam gdzie proste wystarczy.

**"Jakość ponad tempo"** oznacza dla agenta:
- Lepiej zadać pytanie niż zgadnąć intencję i zaimplementować coś złego.
- Lepiej zaplanować i przedstawić plan do akceptacji niż pisać kod który trzeba będzie cofać.

---

## Obowiązek Wcześniejszej Analizy (Chain of Thought przed Działaniem)

*(Ta sekcja dotyczy Ciebie — agenta kodującego pracującego w tym repozytorium. Nie myl jej z sekcją "Architektura LLM" poniżej, która opisuje modele używane w runtime samego produktu Regis. To dwie zupełnie osobne warstwy: Ty piszesz kod; tier `butler`/`regis` to coś, co ten kod uruchamia.)*

Modele autoregresywne podejmują decyzje na podstawie tokenów wygenerowanych wcześniej w sekwencji. Aby uniknąć wyrywności, pochopnych edycji i pomijania niuansów, agent musi upewnić się, że każda akcja jest poprzedzona procesem myślowym.

**Zasada:**
- Jeśli model wykorzystuje **natywny mechanizm extended thinking / reasoning** (np. natywny blok przemyśleń w API, `thinking_level` w Gemini 3.x), wymóg ten jest realizowany automatycznie przez silnik modelu. Nie dubluj go ręcznym promptem "pomyśl krok po kroku, opisz swój plan" — to marnuje tokeny i, jak pokazują testy dostawców i niezależne badania nad zjawiskiem "overthinking", może pogorszyć jakość odpowiedzi zamiast ją poprawić.
- W przypadku modeli **bez natywnego CoT lub z wyłączonym myśleniem** (klasyczne modele czatowe bez trybu reasoning), agent ma OBOWIĄZEK wygenerować najpierw w tekście odpowiedzi odrębne akapity analizy ("scratchpad"), opisujące kontekst, ograniczenia i planowane kroki, zanim przejdzie do modyfikacji plików lub propozycji konkretnych akcji.

> **Ważna korekta (sierpień 2026):** ta sekcja została pierwotnie napisana przy założeniu, że "modele typu Flash" nie mają natywnego CoT. To założenie jest już nieaktualne. Gemini 3.x — w tym Gemini 3.6 Flash, którego używacie w Antigravity — to modele z natywnym trybem rozumowania, z konfigurowalnym poziomem myślenia (minimal/low/medium/high, domyślnie włączonym i z zachowywanym "thought preservation" między turami). Zanim wymusisz na sobie ręczny scratchpad zgodnie z powyższą zasadą, sprawdź, czy narzędzie (Antigravity) już korzysta z natywnego myślenia modelu — jeśli tak, ręczny wymóg jest zbędny i kontrproduktywny. Zostaw wymuszony, rozbudowany scratchpad dla modeli faktycznie pozbawionych reasoning (np. bardzo lekkich modeli parsujących typu `tier_butler`).

---

## Architektura LLM — Co Musisz Rozumieć

*(Ta sekcja opisuje modele działające w runtime produktu Regis — nie modele, którymi Ty, agent kodujący w Antigravity, jesteś napędzany. Zobacz zastrzeżenie w sekcji powyżej.)*

Ten projekt ma dwa fundamentalnie różne tryby pracy modelu. **Tier to pojęcie promptu i zdolności modelu — nie mechanizm routingu.** Kontroler wybiera providera na podstawie dostępności (patrz §5 MANIFEST.md), nie na podstawie tieru. Pomylenie trybów pracy przy modyfikacji promptów jest krytycznym błędem.

### Tryb NLU — tier `butler` (lekki model na RPi5)
- Model działa jak **klasyczny parser intencji**.
- Nie używa pętli ReAct ani wewnętrznego monologu `<thought>`.
- Dostaje krótki prompt z przykładami Few-Shot i zwraca deterministycznie JSON zgodny ze schematem narzuconym przez Ollamę (JSON Schema / Structured Outputs).
- Prompt w `data/prompts/tier_butler.md` jest ekstremalnie uproszczony. Celowo.
- **Nie dodawaj do niego ReAct-owych instrukcji.** Nie obsłuży ich i zepsuje się.

### Tryb ReAct — tier `regis` (domyślnie: OpenRouter cloud, awaryjnie: Ollama lokalnie)
- Model działa jako **pełnoprawny agent** z pętlą Reasoning → Acting.
- Obowiązkowo używa tagu `<thought>...</thought>` do wewnętrznego rozumowania przed każdą akcją.
- Pętla trwa dopóki model wywołuje narzędzia. Gdy nie wywołuje — to jest finalna odpowiedź.
- Model widzi historię jako serie tur (user + assistant), nie jako surowy ślad rozumowania.
- **Nie skracaj promptu** — modele ReAct potrzebują szczegółowych instrukcji, checklist i przykładów Few-Shot. (To odnosi się do modeli OSS bez natywnego reasoning, dobieranych przez OpenRouter — nie utożsamiaj tej zasady z modelami, które piszą ten prompt, patrz sekcja CoT wyżej i punkt o modelach reasoning w sekcji promptowej poniżej.)

---

## Konwencje Kodu i Styl

- **Język:** Polski dla wszystkich stringów widocznych dla użytkownika, komentarzy w kodzie i promptów systemowych. Angielski jest akceptowalny dla nazw zmiennych, funkcji i klas.
- **CLI (Zasady UX i biblioteka `rich`):**
  - Stosuj **minimalizm barwny**: czysta biel (`[bold white]`) dla nagłówków, szarość (`[dim]`) dla elementów tła (logi, długie dumpy JSON).
  - Unikaj jaskrawych barw (`cyan`, `yellow`, `magenta`) jako ozdobników. Rezerwuj wyraziste kolory (`red`, `green`) wyłącznie do informowania o błędach i sukcesach.
  - Zamiast masywnych paneli z obramowaniami (`Panel`), używaj lżejszej struktury: pogrubionych tytułów oddzielonych delikatnymi liniami poziomymi (`Rule(style="dim")`).
  - **Prompting:** Przy korzystaniu z bibliotek wyboru (np. `questionary`) aplikuj własny, wyciszony motyw stylów (np. `fg:ansigray`), aby pozbyć się "krzykliwych", domyślnych highlightów.
  - **Emotikony:** Używaj ich oszczędnie, tylko do kierowania wzrokiem (np. krzyżyk oznaczający błąd, ptaszek oznaczający sukces). Nie dodawaj ich do każdej opcji menu. Interfejs ma być stonowany i ascetyczny.
- **PowerShell:** Używaj `;` zamiast `&&` do łączenia komend. System to Windows.
- **Testy:** `pytest`. Uruchamiaj przed zgłoszeniem zakończenia zadania.

---

## Zasady Inżynieryjne (Zwalczanie "Lenistwa AI")

Aby zapobiec powierzchownym refaktoryzacjom i zjawisku over-engineeringu, agenty muszą bezwzględnie stosować poniższe zasady przy modyfikacji logiki:

1. **KISS (Keep It Simple, Stupid):** Kod ma być tak prosty, jak to tylko możliwe. Jeśli masz do wyboru skomplikowany wzorzec projektowy a prostą funkcję z kilkoma warunkami, wybierz prostą funkcję.
2. **YAGNI (You Aren't Gonna Need It):** Nie twórz klas, interfejsów ani metod "na przyszłość". Koduj tylko to, co jest absolutnie niezbędne w bieżącym zadaniu (zgodnie z zasadą "Nie dodawaj funkcji, o które nie proszono" z MANIFEST.md).
3. **DRY (Don't Repeat Yourself):** Jeśli widzisz powtarzający się blok kodu, wydziel go do osobnej, mniejszej funkcji.
4. **SOLID (Uwaga — stosuj ostrożnie!):** Zasady SOLID są zachowane w głównych warstwach systemu (np. abstrakcje providerów LLM/STT), ale **nie** należy ich nadużywać w codziennym kodzie. Używanie SOLID "na siłę" często kończy się pisaniem w Pythonie kodu przypominającego archaiczną Javę (nieuzasadnione interfejsy i klasy fabrykujące). Zachowaj zdrowy rozsądek i traktuj KISS z większym priorytetem.

---

## Typowe Błędy Agentów w Tym Projekcie

Lista błędów, które agenty popełniają regularnie w tym projekcie:

1. **Proponowanie natywnego `tools` API Ollamy** — odrzucone. Patrz tabela wyżej ("Droga A").
2. **Dodawanie emoji do CLI** — sprzeczne z estetyką projektu.
3. **Pisanie kodu bez polecenia** — projekt ma zasadę "żadnych zmian bez wyraźnego nakazu". Jeśli nie jesteś pewien czy masz pozwolenie — zapytaj.
4. **Implementowanie "Drogi B" (ciężki fallback parser) dla słabszych modeli** — filozofia projektu zabrania ratowania słabych modeli skomplikowanym kodem. Jeśli model nie działa, zmień model lub zmień prompt.
5. **Tight-coupling do konkretnego providera LLM/STT/TTS** — system jest agnostyczny wobec backendu. Wywołania bezpośrednio do OpenRouter lub Ollamy poza warstwą abstrakcji są błędem. Każdy provider musi implementować wspólny interfejs.
6. **Refaktoryzacja bez zgody** — zmiana struktury kodu wymaga planu i akceptacji, nie jest "przy okazji".
7. **Ignorowanie hardcode'owanych adresów IP** — są świadomie tymczasowe. Nie "naprawiaj" ich bez polecenia.
8. **Mieszanie warstw architektury** — implementowanie konkretnego providera (np. Whisper, OpenRouter) bezpośrednio w Core zamiast przez interfejs (`ISTTProvider`, `ILLMProvider`) jest błędem architektonicznym. Analogicznie: narzędzie integracyjne (np. wywołanie HA API) nie może siedzieć w Core — należy do `integrations/`. Każda warstwa zna tylko interfejsy warstwy wyżej, nigdy konkretne implementacje.
9. **Brak izolacji przy tworzeniu konfiguracji** — nie używaj scentralizowanego `settings.json` dla wszystkich ról. Konfiguracja jest izolowana przez profile (`settings.<PROFILE>.json`) lub lokalne zmienne `.env` z `ACTIVE_PROFILE`. Kontroler i Node mają rozdzielone konfiguracje — nie mieszaj ich.

---

## Wskazówki do Pracy z Promptami Modeli

Gdy modyfikujesz pliki w `data/prompts/`:

- **Zachowaj strukturę wypunktowaną.** Modele Instruct reagują lepiej na listy niż na akapity prozy.
- **Sandwiching działa.** Kluczowe zasady powtarzaj zarówno na początku jak i na końcu promptu.
- **Nie używaj negatywnego framingu.** Zamiast "Nie wywołuj narzędzi bez myśli" napisz "Zawsze zacznij od bloku `<thought>` przed każdą akcją".
- **Few-Shot przykłady muszą być kontrastujące.** Jeden przykład pokazujący użycie narzędzia, jeden przykład pokazujący odpowiedź BEZ narzędzia. Model musi widzieć oba wzorce.
- **Testuj na modelu docelowym.** Prompt zoptymalizowany pod duży model chmurowy często zepsuje lekki parser na RPi5 i odwrotnie.
- **Rozróżniaj modele reasoning od non-reasoning.** Modele z natywnym myśleniem (Gemini 3.x, Claude z extended thinking) reagują gorzej na rozbudowany, "naganiający" prompt engineering zaprojektowany pod starsze modele — bywają skłonne nadmiernie analizować proste polecenia zamiast po prostu je wykonać. Dla takich modeli formułuj instrukcje zwięźle i wprost; rozbudowane checklisty i wymuszony CoT rezerwuj dla modeli faktycznie ich pozbawionych (np. `tier_butler`).

---

## Zgodność z Narzędziami (Antigravity / Gemini / Claude Code)

- **Antigravity** czyta `AGENTS.md` jako plik główny (priorytet: `AGENTS.md` → `~/.gemini/GEMINI.md` → wartości domyślne narzędzia). Wasza struktura `.agents/skills/`, `.agents/HANDOFF.md`, `.agents/TASKS.md` jest zgodna z konwencją tego narzędzia — nie wymaga zmian.
- **Konflikt ścieżek Antigravity ↔ Gemini CLI:** jeśli na tej samej maszynie używacie obu narzędzi, obie piszą do tej samej globalnej ścieżki `~/.gemini/GEMINI.md`, co może powodować przeciekanie reguł między sesjami (znany, śledzony problem po stronie Google). Trzymajcie reguły współdzielone w `AGENTS.md`, nie w globalnym `GEMINI.md`.
- **Claude Code** (jeśli kiedyś dołączy do zestawu narzędzi) czyta `CLAUDE.md`, nie `AGENTS.md`. Najprostsze rozwiązanie: plik `CLAUDE.md` w rocie, którego cała treść to jedna linia — `@AGENTS.md` — co powoduje, że Claude Code dziedziczy te same reguły bez duplikacji treści.

---

## Źródła zewnętrzne (do okresowego przeglądu)

Poniższe fakty o narzędziach/modelach zmieniają się szybciej niż reszta tego dokumentu — warto zweryfikować przy kolejnym większym audycie promptów:

- Dokumentacja Gemini API — prompting strategies: https://ai.google.dev/gemini-api/docs/prompting-strategies
- Antigravity — konfiguracja i hierarchia plików: dokumentacja produktowa antigravity.google
- Anthropic — Effective context engineering for AI agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic — Effective harnesses for long-running agents (wzorzec `claude-progress.txt`): https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Specyfikacja AGENTS.md (Agentic AI Foundation): https://agents.md
