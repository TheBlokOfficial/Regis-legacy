# Regis Project Handoff

**Data sesji**: 2026-08-10

## 1. Co Zostało Wykonane w Ostatniej Sesji
- **Przebudowa Układu Dashboardu (3 Symetryczne Kafelki)**:
  - Przekształcono widok Pulpitu (`src/controller/web/views/dashboard.html`) w 3 symetryczne, jednakowe kafelki w jednym rzędzie:
    1. **Agent & Kanał Audio** (Mózg LLM + Bundle Mowy STT/TTS)
    2. **Satelity** (Punkty stykowe audio/interakcji z VAD)
    3. **Integracje** (Mostki zewnętrzne, np. Home Assistant)
  - Wycentrowano obszar roboczy w CSS (`max-width: 1320px; margin: 0 auto;` w `layout.css`).
- **Dopracowanie UX & Statusów LED w Kafelku Agenta**:
  - Podzielono Kafelek 1 na 2 czyste podsekcje: **Agent** oraz **Kanał głosowy**, każda z własną pulsującą diodą LED (🟢 `.dot.online` / 🔴 `.dot.offline`) w nagłówku.
  - Usunięto zbędny żółty banner "TRYB FALLBACK" oraz wyeliminowano powielone zielone kropki wewnątrz wierszy elementów na rzecz ascetycznego wyglądu (`renderer.js`).
  - Usunięto etykietę `[• Tryb awaryjny]` z prawego rogu górnego paska statusu (`status-strip`), oczyszczając go do czystej telemetrii liczbowej (`Uptime`, `Agent (LLM)`, `Satelity`, `Integracje`).
- **Rozstrzygnięcie ws. Refaktoryzacji Backendowo-Klientowej (Spłacenie Długu Technicznego)**:
  - Uzgodniono zaniechanie pisania skomplikowanych hybrydowych modalów pod tymczasowy monolit dev.
  - Użytkownik przeprowadza backendową refaktoryzację:
    1. `RegisDesktop` staje się wyłącznie czystą satelitą (`ISatellite`).
    2. Kontroler komunikuje się z Ollamą bezpośrednio po HTTP (`localhost:11434`), wycinając wrapper `ollama_worker`.
    3. Tworzony jest osobny daemon `Audio Service` dla STT (Faster-Whisper) i TTS (Piper).

## 2. Aktualny Stan Kodu & Architektura
- Szablony HTML i pliki CSS/JS dla dashboardu (`views/dashboard.html`, `css/layout.css`, `css/components.css`, `renderer.js`) są w 100% zaktualizowane i gotowe pod nowy podział.
- Kod Kontrolera i Klienta oczekuje na zakończenie refaktoryzacji `RegisDesktop` oraz bezpośredniej integracji Kontrolera z API Ollamy / Audio Service.

## 3. Kroki Startowe Dla Następnego Agenta
1. Wykonaj obowiązkową procedurę startową czytania plików (`docs/MANIFEST.md`, `docs/AGENT_GUIDE.md`, `.agents/HANDOFF.md`, `.agents/TASKS.md`).
2. Potwierdź z użytkownikiem stan refaktoryzacji `RegisDesktop` (czy przeszedł w tryb 100% Satelity i czy Ollama/Audio Service są podłączone bezpośrednio pod Kontroler).
3. Podłącz akcje edycyjne na frontendzie pod nowe endpointy Kontrolera (LLM, Audio Service, Satelity).
