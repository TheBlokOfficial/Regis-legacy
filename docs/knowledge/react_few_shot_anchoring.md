# Rozwiązanie: Prompt Anchoring / "Nadgorliwość" persony (Qwen 2.5 7B, asystent domowy "Lokaj")

## Problem

Persona: skrajnie powściągliwy Lokaj, pozbawiony sztucznych uprzejmości. W `base_system.md` zakazano powitań ("pomijaj uprzejmości, przechodź do konkretów"), a w bloku Few-Shot pokazano jedną perfekcyjną iterację: zapytanie o czas → wywołanie `get_current_time()`.

Efekt: gdy użytkownik pisze samo "Cześć", model — zablokowany przed odpowiedzią grzecznościową, a nie mając żadnego zlecenia — chwyta się jedynego znanego mu wzorca działania w próżni: proaktywnie wywołuje `get_current_time()` i odpowiada konkretem ("Godzina to 11:51").

## Diagnoza

To pokazuje realną hierarchię siły sygnałów u 7B: **few-shot bije regułę deklaratywną.** Zakaz "pomijaj uprzejmości" to tekst instrukcyjny, rozumiany przez model tylko abstrakcyjnie. Jedyny konkretny wzorzec zachowania, jaki model dostał, to: *brak jasnego zlecenia → sięgnij po narzędzie → odpowiedz konkretem*. Gdy przychodzi wiadomość bez zlecenia ("Cześć"), model nie ma wzorca na tę sytuację — ma tylko jeden nauczony schemat działania w próżni i go stosuje.

Wniosek: problem nie leży w regule zakazującej uprzejmości — leży w luce w tym, czego few-shot *nauczył* model robić, gdy zlecenia nie ma. Łatanie samą regułą leczy objaw, nie przyczynę.

## Ocena rozważanych opcji

**1. Furtka dla powitań w prompcie** ("jeśli użytkownik wysyła wyłącznie powitanie, nie wywołuj narzędzi") — działa punktowo, ale to łata na jeden konkretny trigger. Nie obejmuje innych wiadomości bez zlecenia ("hmm", "no dobra", "jest ktoś?"). Reguła się nie uogólnia.

**2. Twardy zakaz ogólny** ("nigdy nie wywołuj narzędzi, jeśli użytkownik jawnie nie poprosi") — szerszy niż 1, ale ma dwie słabości:
- to czysta negacja bez afirmatywnej alternatywy — model wie, czego nie robić, ale nie ma nauczonego wzorca, co robić zamiast tego (ten sam mechanizm próżni, przesunięty o poziom wyżej);
- sformułowanie "jawnie nie poprosi" jest ryzykowne w kontekście domowym, gdzie dużo poleceń jest *implicit* ("zimno mi" → termostat, bez dosłownego "ustaw termostat"). Zbyt dosłowna reguła może wyłączyć pożądane wnioskowanie kontekstowe, nie tylko halucynację przy powitaniu.

**3. Zmiana w Few-Shot** — jedyna opcja trafiająca w rzeczywistą przyczynę. Uwaga: samo *zastąpienie* przykładu z `get_current_time` innym narzędziem (np. `set_thermostat`) nie rozwiązuje problemu — tylko przenosi anchor gdzie indziej, bo model nadal ma jeden wzorzec "brak zlecenia → wywołaj coś". Właściwy ruch to **dodanie drugiego, kontrastującego przykładu**: wiadomość bez zlecenia → brak wywołania narzędzia → krótka odpowiedź gotowościowa. Dopiero dwa kontrastujące przykłady uczą model *rozróżniania*, nie tylko jednej ścieżki działania.

**4. Przechwycenie w Pythonie (frontend intercept)** — najbardziej deterministyczne, ale kosztowne architektonicznie:
- zasięg: trzeba pattern-matchować warianty ("cześć", "hej", "witam", literówki, wielkość liter), a zbite w jednej wiadomości powitanie + zlecenie ("cześć, mam pytanie o pogodę") wymaga już logiki, nie prostego przechwycenia;
- tworzy dwa niezależne źródła "głosu" Lokaja — twardo zakodowany string w Pythonie i styl generowany przez model. Przy każdej przyszłej korekcie persony trzeba pamiętać o synchronizacji dwóch miejsc w kodzie, co naturalnie się rozjeżdża z czasem.

Sensowne jako optymalizacja kosztowa (oszczędność round-tripu do backendu przy dosłownym, jednoznacznym powitaniu), niebezpieczne jako jedyna linia obrony — nie generalizuje.

## Rekomendowana architektura

| Warstwa | Rola | Dlaczego |
|---|---|---|
| **Few-shot (3, rozszerzony)** | Uczy rozróżniania: zlecenie → narzędzie, brak zlecenia → gotowość bez narzędzia | Silniejszy sygnał dla 7B niż reguła tekstowa; usuwa przyczynę, nie objaw |
| **Reguła ogólna (2, przeformułowana)** | Boundary dla przypadków spoza few-shot (np. "hmm", cisza kontekstowa) | Sieć bezpieczeństwa dla wariantów, których few-shot fizycznie nie pokrył |
| **Frontend intercept (4)** | Opcjonalna optymalizacja kosztowa dla dosłownego, jednoznacznego "Cześć" bez dodatkowej treści | Tylko jako skrót wydajnościowy, nigdy jako jedyne zabezpieczenie |

## Przeformułowanie reguły 2

Tak, by nie kolidowała z implicit commands:

> "Wywołuj narzędzie tylko wtedy, gdy w wiadomości użytkownika jest zlecenie lub pytanie wymagające danych z narzędzia — wprost lub w sposób jednoznacznie dorozumiany (np. skarga na temperaturę implikuje termostat). Samo powitanie lub brak treści zleceniowej nie jest podstawą do żadnej akcji — wtedy ograniczasz się do krótkiej gotowości."

## Kluczowy krok wykonawczy

Dokładnie ta granica ("powitanie → gotowość bez narzędzia") musi mieć swój odpowiednik jako **drugi przykład w bloku few-shot**, obok istniejącego przykładu z `get_current_time`. Bez tego reguła tekstowa ponownie przegra z jedynym wzorcem behawioralnym, jaki model faktycznie zna.
