# Rozwiązanie: Desynchronizacja Uprawnień Tier vs Instrukcji Promptu (Notatnik, Lokaj 7B / Regis 14B)

## Problem

`base_system.md` (wspólny dla obu tierów) zawiera kategoryczny nakaz: "ZAWSZE używaj `save_note`, aby trwale zapisać nowy fakt o użytkowniku". Jednocześnie `schemas.py` rezerwuje `save_note` i `delete_note` wyłącznie dla tieru "regis". Gdy użytkownik mówi do Lokaja "Mieszkam w Nysie", model perfekcyjnie realizuje instrukcję z promptu, halucynuje wywołanie `save_note`, backend je odrzuca (brak uprawnień), a surowy JSON wylewa się do interfejsu.

## Diagnoza — to dwa oddzielne błędy, nie jeden

**Błąd 1 (przyczyna źródłowa): prompt nie jest świadomy uprawnień tieru.** `base_system.md` opisuje narzędzia tak, jakby były jednolicie dostępne dla obu modeli, podczas gdy faktyczna autoryzacja żyje wyłącznie w `schemas.py`. To niezgodność między tym, co prompt *obiecuje* modelowi, a tym, co backend *pozwala* wykonać — niezależnie od wyboru A/B/C, ten fundamentalny brak spójności trzeba naprawić.

**Błąd 2 (defekt harnessu): nieautoryzowane wywołanie nie powinno nigdy dotrzeć do UI jako surowy tekst.** To, że odrzucone wywołanie "wylewa się" do interfejsu, to osobna usterka w warstwie parsera/harnessu — wymaga naprawy niezależnie od wybranej strategii uprawnień.

## Ocena rozważanych opcji

**A) Spłaszczenie uprawnień** — ryzyko nie jest symetryczne między dwoma narzędziami. `save_note` przy błędzie 7B (krzywy JSON, nadpisanie pola) jest odwracalne — można nadpisać ponownie. `delete_note` jest **nieodwracalne** — raz wykonana halucynowana kasacja notatki nie ma cofnięcia. Nadanie 7B uprawnień do operacji destrukcyjnej i bezpowrotnej stoi w sprzeczności z zasadą, że twarde ograniczenia bezpieczeństwa nie powinny być łagodzone dla wygody. Odrzucam dla `delete_note` bez wyjątków; dla `save_note` ryzykowne bez dodatkowej walidacji.

**B) Ścisła separacja w promptach** — usuwa halucynację, ale tworzy poważniejszy problem: **trwałą utratę danych**. Lokaj jako recepcjonista 24/7 to główny punkt kontaktu przy small-talku — jeśli w ogóle przestanie "wiedzieć", że zapisywanie istnieje, fakt wypowiedziany mimochodem ("Mieszkam w Nysie") przepada bezpowrotnie, chyba że użytkownik powtórzy go później bezpośrednio Regisowi. Rozwiązuje objaw kosztem funkcjonalności, którą sami wskazujecie jako wartościową (proaktywność przy small-talku).

**C) Delegacja przez `call_boss`** — właściwy kierunek koncepcyjnie (rozdzielenie wykrycia od wykonania), ale kosztowna implementacja: pełne wywołanie 14B do zapisania trywialnego faktu o mieście to nieproporcjonalny koszt obliczeniowy i latencja względem wagi zadania.

## Rekomendacja: opcja D — rozdzielenie "wykrycia" od "zapisu" (wzorzec staging/proposal)

Żadna z A/B/C nie rozwiązuje problemu w całości, bo każda miesza dwie różne odpowiedzialności: *rozpoznanie, że warto coś zapamiętać* (to Lokaj robi dobrze — to zwykłe rozumienie języka) i *fizyczny, zwalidowany zapis* (to wymaga ostrożności, niezależnie od tego, który model go inicjuje).

**Mechanika:**

- Lokaj (tier "lokaj") dostaje nowe, wąsko zakresowane narzędzie, np. `queue_note(fact="Mieszka w Nysie")` — **nie** `save_note`. To narzędzie nie zapisuje do trwałego magazynu notatek, tylko do lekkiej kolejki/tabeli staging (`pending_notes`).
- Zapis do kolejki jest tani i bezpieczny — nawet jeśli 7B źle sformatuje treść faktu, nie dotyka to właściwego magazynu notatek, więc nie ma ryzyka nadpisania czy utraty istniejących danych.
- Z kolejki fakty trafiają do właściwego `save_note` jednym z dwóch sposobów, zależnie od złożoności:
  - **prosty przypadek** (pojedynczy, jednoznaczny fakt) — deterministyczna walidacja po stronie backendu (zwykły kod Python, bez LLM) promuje wpis automatycznie;
  - **złożony/niejednoznaczny przypadek** — trafia do Regisa asynchronicznie, przy najbliższej okazji, gdy 14B i tak jest już wywołany do innego zadania, zamiast generować osobny, kosztowny round-trip tylko dla tej notatki.
- `delete_note` pozostaje wyłącznie w gestii Regisa, bez żadnej ścieżki delegacji — nawet pośredniej przez staging. Operacje nieodwracalne nie zasługują na skrót, niezależnie od tego, jak bardzo "oczywisty" wydaje się przypadek.

To rozwiązuje wszystkie trzy problemy jednocześnie: 7B nigdy nie dotyka trwałego magazynu (bezpieczeństwo z A), fakt jest przechwytywany natychmiast, nie tracony (funkcjonalność z B), a koszt pozostaje niski, bo nie wymaga synchronicznego wywołania 14B dla trywialnych przypadków (efektywność, której brakowało w C).

## Naprawa źródłowa: `base_system.md` musi być świadomy tieru

Niezależnie od wybranej strategii uprawnień, wspólny prompt bazowy nie powinien opisywać narzędzi w sposób jednolity dla obu modeli. Dwa podejścia:

- **Dynamiczne wstrzykiwanie listy narzędzi** — sekcja "Twoje dostępne narzędzia" w prompcie jest generowana programowo na podstawie faktycznych uprawnień tieru, a nie wpisana na sztywno w statycznym pliku.
- **Nakładki tierowe** (spójne z istniejącym już `tier_regis.md``) — instrukcje specyficzne dla narzędzi (w tym `save_note`/`queue_note`) przenosimy do `tier_lokaj.md` i `tier_regis.md`, a `base_system.md` zawiera wyłącznie to, co faktycznie wspólne (persona, ton, format `<thought>`).

Zasada ogólna: model powinien mieć w prompcie świadomość wyłącznie tych narzędzi, które faktycznie posiada — inaczej sam prompt staje się źródłem halucynacji, niezależnie jak dobrze napisana jest reszta instrukcji.

## Naprawa równoległa: wyciek surowego JSON do UI

To błąd niezależny od wyboru strategii uprawnień i wymaga naprawy niezwłocznie. Harness powinien sprawdzać autoryzację tieru **przed** wykonaniem, a nie polegać na tym, że backend narzędzia po prostu "zignoruje" nieuprawnione wywołanie:

- Parser przechwytuje próbę wywołania narzędzia spoza uprawnień danego tieru **przed** jej wykonaniem.
- Zamiast przepuszczać surowy tekst do interfejsu, zwraca do pętli ReAct czytelny komunikat błędu (np. "Narzędzie `save_note` niedostępne w tym tierze — użyj `queue_note`"), pozwalając modelowi się skorygować w kolejnej iteracji.
- To ten sam mechanizm tolerancyjnego parsera jako siatki bezpieczeństwa, o którym pisałem przy okazji problemu równoległego tool-callingu — nieautoryzowane czy źle sformułowane wywołanie nigdy nie powinno docierać do użytkownika w surowej postaci.

## Tabela podsumowująca

| Opcja | Ryzyko bezpieczeństwa | Koszt obliczeniowy | Utrata danych | Werdykt |
|---|---|---|---|---|
| A — spłaszczenie uprawnień | Wysokie (zwł. `delete_note` — nieodwracalne) | Niskie | Brak | Odrzucić dla `delete_note`; ryzykowne dla `save_note` |
| B — ścisła separacja promptów | Niskie | Niskie | Wysokie (fakty tracone przy small-talku) | Niewystarczające samodzielnie |
| C — handoff (`call_boss`) | Niskie | Wysokie (zbędny round-trip 14B) | Brak | Słuszny kierunek, zbyt kosztowna implementacja |
| **D — staging/proposal (rekomendacja)** | Niskie | Niskie | Brak | **Rekomendowane** |

## Podsumowanie

Problem nie jest wyborem między A, B i C — to sygnał, że te trzy opcje próbują wcisnąć dwie różne odpowiedzialności (wykrycie faktu i jego trwały zapis) w jedno narzędzie i jeden poziom uprawnień. Rozdzielenie ich (opcja D) usuwa konflikt u źródła, zamiast negocjować kompromis między bezpieczeństwem, kosztem i utratą danych. Dodatkowo: (1) `base_system.md` musi stać się tier-aware, i (2) harness musi przechwytywać nieautoryzowane wywołania przed wykonaniem, a nie po fakcie — oba te punkty są konieczne niezależnie od wybranej architektury uprawnień.
