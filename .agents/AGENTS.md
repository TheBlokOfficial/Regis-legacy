# Regis Workspace Rules

> Ostatnia aktualizacja: 2026-08-11. Ten plik jest wczytywany automatycznie przez każde narzędzie zgodne ze standardem AGENTS.md (Antigravity, Claude Code, Cursor i inne). Ma pozostać krótki i operacyjny — instrukcje "co robić teraz", nie "dlaczego". Uzasadnienia, historia decyzji i głębsza filozofia projektu żyją w `docs/AGENT_GUIDE.md`, który wczytujesz raz, na starcie sesji, w ramach procedury poniżej.

## 1. Zasady Obowiązujące Zawsze

- **Zmiany w kodzie wymagają wyraźnego polecenia użytkownika.** Modyfikuj pliki źródłowe wyłącznie wtedy, gdy użytkownik jawnie i jednoznacznie o to poprosi w bieżącej sesji. Gdy nie masz pewności, czy polecenie obejmuje konkretną zmianę — zapytaj, zanim zaczniesz edytować.
- **Każda edycja jest poprzedzona analizą.** Zanim użyjesz narzędzi do edycji plików lub zaproponujesz zmiany, przeprowadź cichą analizę planu i sprawdź jego zgodność z `docs/MANIFEST.md`. Modele z natywnym trybem rozumowania realizują to automatycznie; pozostałe generują ten namysł jako tekst przed akcją. Pełne zasady i ważny wyjątek dla modeli reasoning (np. Gemini 3.x) — w `docs/AGENT_GUIDE.md`.
- **Refaktoryzacja sięga logiki, nie tylko nazewnictwa.** Gdy zadanie wymaga refaktoryzacji, stosuj KISS / YAGNI / DRY (pełny opis w `docs/AGENT_GUIDE.md`) — sama zmiana nazw zmiennych nie spełnia zadania.
- **Interfejs CLI jest ascetyczny.** Stosuj minimalizm barwny i oszczędne, celowe użycie emotikonów. Pełne zasady i przykłady biblioteki `rich` w `docs/AGENT_GUIDE.md`.

## 2. Procedura Startowa (wykonaj po cichu, bez pytania o zgodę)

Zanim zrealizujesz pierwsze polecenie w nowej sesji, wczytaj kolejno:

1. `docs/MANIFEST.md` — filozofia i rozstrzygnięte decyzje projektowe. Nadrzędne wobec wszystkiego poniżej.
2. `docs/AGENT_GUIDE.md` — wskazówki techniczne, architektoniczne i protokoły pracy.
3. `.agents/HANDOFF.md` — stan prac po ostatniej sesji.
4. `.agents/TASKS.md` — lista aktywnych zadań.

## 3. Planowanie

Przed utworzeniem lub aktualizacją `implementation_plan.md` / `task.md` wczytaj i zastosuj skill `.agents/skills/regis-planning/SKILL.md`.

## 4. Komendy i Środowisko

- **Testy:** `pytest` — uruchamiaj przed zgłoszeniem zakończenia zadania.
- **Powłoka:** PowerShell (Windows) — łącz komendy przez `;`, nigdy przez `&&`.

## 5. Zamknięcie Sesji

Gdy użytkownik zasygnalizuje koniec pracy (np. "kończymy", "to wszystko na dziś"), wykonaj po cichu poniższe kroki, zanim się pożegnasz:

1. Zastąp treść `.agents/HANDOFF.md` nowym opisem aktualnego stanu prac i jasnym punktem startowym dla kolejnej sesji. Historia zostaje w Git — nie musisz jej powielać.
2. Zaktualizuj `.agents/TASKS.md`: odznacz ukończone zadania, zachowaj je na liście.
3. Sprawdź `git status` i upewnij się, że nie zostają niezamierzone pliki tymczasowe (zignoruj te, które są tam celowo).
4. Zapisz zmiany:
   ```
   git add . ; git commit -m "Auto-zapis sesji agenta: [krótki, rzeczywisty opis prac]" ; git push
   ```
5. Dopiero po udanym push krótko opisz użytkownikowi, co zaktualizowałeś, i wtedy się pożegnaj.

> **Rekomendacja:** rozważ przeniesienie kroków 1–4 do `.agents/workflows/zamkniecie-sesji.md` jako Workflow Antigravity, wywoływany np. komendą `/koniec-sesji`. Wykonanie stanie się deterministyczne (jedna komenda) zamiast zależeć od rozpoznania frazy w kontekście, który po długiej sesji kodowania bywa zaśmiecony.
