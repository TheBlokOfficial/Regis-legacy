# Regis Project Handoff

**Data sesji**: 2026-08-10

## 1. Co Zostało Wykonane w Ostatniej Sesji
- **Dyskusja Architektoniczna i Przebudowa Dokumentów Fundamentowych**:
  - **Hierarchia Komponentów**: Doprecyzowano, że LLM to mózg systemu (agent ReAct, najwyższy poziom), a STT i TTS tworzą **Kanał Głosowy** (infrastruktura I/O satelitów na niższym poziomie abstrakcji, nie narzędzia agenta).
  - **Kanał Głosowy (`voice_channel`)**: Działa jako spójny bundle logiczny: `voice_channel_ready = STT_active AND TTS_active`. Brak któregokolwiek oznacza niedostępność komunikacji głosowej.
  - **Trójstanowy Model Degradacji**:
    - **Operacyjny Pełny** (LLM + Kanał Głosowy): pełna interakcja mowa/tekst.
    - **Operacyjny Cichy** (LLM aktywny, Kanał Głosowy nieaktywny): agent działa autonomicznie (scheduler, HA, narzędzia), satelity mają czerwoną diodę (offline), brak głosu.
    - **Awaryjny** (Brak LLM): deterministyczny parser offline na RPi5.
  - **Turn Context (`TurnContext`) & Ujednolicony Pipeline**: Introduced `TurnContext` carrying execution metadata (`source`, `room`, `input_modality`, `output_modality`, `response_target`). Injected into prompt so agent is context-aware (e.g. responds differently when triggered by scheduler vs user).
  - **Rola RegisDesktop i Architektura Mini PC**: W docelowym produkcie RegisDesktop staje się wyłącznie satelitą głosową na Windows. Na centralnym Mini PC działają 3 procesy: Controller (lekki daemon Python), Ollama (zewnętrzny daemon Go, komunikacja HTTP bezpośrednio) oraz Audio Service (nowy daemon Python: Faster-Whisper + Piper).
  - **Zachowanie Konserwatywne Agenta**: Zapisano regułę behawioralną — w przypadku braku komunikacji z użytkownikiem, inwazyjne/wymagające zgody akcje są wstrzymywane i zapisywane do przypomnienia.
- **Aktualizacja Dokumentacji**:
  - **`docs/MANIFEST.md`**: Przebudowano §3.0, §3.2, §3.5, §5, dodano nowy §5.1 (`TurnContext`), zaktualizowano §6 oraz §7.
  - **`docs/AGENT_GUIDE.md`**: Dodano 5 nowych wpisów w tabeli decyzji architektonicznych.
  - **`.agents/TASKS.md`**: Dodano wpisy dla `Audio Service` oraz `Formalnego oddzielenia ról RegisDesktop`.

## 2. Aktualny Stan Kodu & Architektura
- Dokumentacja w `docs/MANIFEST.md` i `docs/AGENT_GUIDE.md` jest w 100% spójna z ustaleniami z dnia 2026-08-10.
- Kod źródłowy (Controller/Web UI) oczekuje na wdrożenie panelu "Aktualny Pipeline" na dashboardzie lub dalsze prace architektoniczne/backendowe według priorytetów z `.agents/TASKS.md`.

## 3. Kroki Startowe Dla Następnego Agenta
1. Przeczytaj pliki w obowiązkowej kolejności startowej (`docs/MANIFEST.md`, `docs/AGENT_GUIDE.md`, `.agents/HANDOFF.md`, `.agents/TASKS.md`).
2. Sprawdź z użytkownikiem cel kolejnej sesji — np. implementacja panelu dashboardu "Aktualny Pipeline" (zgodnie z zaprojektowanym w tej sesji widokiem operacyjnym summary/detail) lub prace nad backendem.
