# ReAct Drift przy Konsolidacji Pamięci (Qwen 2.5 32B, Ollama)

## Kontekst

`read_queue()` zwraca 3 notatki. Model prawidłowo przetwarza pierwszą i zapisuje ją przez `save_note()`. Przy przejściu do drugiej — zamiast spojrzeć wstecz na oryginalny wynik `read_queue()` — zaczyna halucynować kolejne notatki na podstawie przykładowych wartości z pola `description` w schemacie JSON narzędzia `save_note` (np. "ulubiony_kolor" z przykładu w opisie stało się rzekomą treścią notatki).

## Diagnoza: to nie jest zwykłe "lost in the middle"

Warto rozdzielić dwa zjawiska, które w opisie zlewają się w jedno, bo mechanizm jest bardziej specyficzny niż zwykłe rozmycie uwagi na długim kontekście.

**Rozmycie sygnału.** Negocjacja pierwszej notatki z użytkownikiem to kilka dodatkowych tur konwersacyjnych (propozycja, poprawki, potwierdzenie) — każda z nich odsuwa oryginalny wynik `read_queue()` dalej w głąb kontekstu, dokładnie w mechanizm "lost in the middle" omawiany już przy okazji sandwichingu reguł w długich pętlach.

**Konflacja poziomów: dane vs metadane.** To jest specyficzny i bardziej interesujący element tego przypadku. Model nie "milczy" ani nie mówi "nie wiem" w obliczu osłabionego sygnału — sięga po najsilniejszy dostępny w pobliżu sygnał tekstowy. A modele instrukcyjne są trenowane na danych function-calling tak, by bardzo silnie ważyć pole `description` schematu jako źródło semantyki wywołania (pisałem o tym przy okazji cheat-code'u z opisami narzędzi). Gdy prawdziwy sygnał o stanie kolejki się osłabia, model nie zgłasza niepewności — podstawia w jego miejsce najbliższy silny sygnał tekstowy, jaki zna, czyli przykładowe wartości ze schematu. To nie przypadkowa halucynacja "znikąd" — to pomylenie warstwy metadanych (przykład w opisie narzędzia) z warstwą danych (rzeczywista treść notatki).

## Dlaczego obie dotychczasowe próby zawiodły — to nie było wybieranie punktu na osi "sztywność ↔ swoboda"

To kluczowy wniosek, zanim przejdę do oceny opcji A-D: Kaganiec i Empowerment nie są dwoma końcami jednej skali, które trzeba wyważyć kompromisem. To dwie różne rzeczy pomylone pod wspólną etykietą "reguły w prompcie".

- **Kaganiec dusił 32B**, bo mieszał w jednym zestawie reguł dwie różne kategorie: *śledzenie stanu* (twarde, powinno być deterministyczne) i *ton rozmowy* (miękkie, powinno zostać swobodne). Silniejszy model, lepiej wyczuwający kontekst konwersacyjny, faktycznie napotykał sprzeczność — instrukcja każe mu być uprzejmym i naturalnym, a jednocześnie sztywno trzymać się kroku po kroku, co przy naturalnej rozmowie z użytkownikiem bywa nienaturalne.
- **Empowerment nasilił drift**, bo razem ze zdjęciem sztywności konwersacyjnej zdjęliście też *całe* śledzenie stanu — łącznie z tą częścią, która faktycznie musiała zostać twarda. Wylaliście dziecko z kąpielą.

Właściwe rozwiązanie nie leży gdzieś pomiędzy tymi dwoma próbami. Leży w **rozdzieleniu odpowiedzialności**: śledzenie stanu kolejki to zadanie dla kodu (deterministyczne, zawsze musi być sztywne, niezależnie od wielkości modelu), a prowadzenie rozmowy o treści każdej notatki to zadanie dla modelu (powinno zostać w pełni swobodne, zgodnie z podejściem Empowerment). Obie wasze próby stosowały tę samą dźwignię — sztywność promptu — do obu zadań naraz, zamiast zastosować różne narzędzie do każdego z nich.

## Ocena opcji A/B/C/D

**A) Przypinanie `read_queue` jako "Bieżący Stan" w Pythonie** — to właściwy kierunek, ale w wersji z pytania niedopracowany. Samo ponowne wklejanie *oryginalnego, surowego* wyniku `read_queue()` każe modelowi nadal samodzielnie wyliczać, co już zostało zrobione, a co zostało — czyli przenosi problem, zamiast go usunąć. Właściwa wersja to nie "przypnij historyczny wynik", tylko "za każdą turą zapytaj dysk na nowo o aktualny stan i wstrzyknij świeżą, przetworzoną odpowiedź" — patrz opcja D.

**B) State Tracker w `<thought>`** — słabszy wybór niż A/D, i to z konkretnego powodu: to każe systemowi probabilistycznemu (model) rekonstruować coś, co system deterministyczny (kod, `pending_notes.json` na dysku) już zna z absolutną precyzją. Jeśli sygnał, z którego model miałby to "wypisać", już jest skażony (jak w opisanym przypadku), samo kazanie mu spisać to, co "pamięta", nie naprawia skażenia — tylko każe mu artykułować błędne przekonanie z większą pewnością siebie. Sensowne wyłącznie jako dodatkowa, wtórna warstwa kontroli spójności ("czy to, co zamierzam zrobić, zgadza się z tym, co dostałem w bieżącej turze") — nigdy jako główne źródło prawdy o stanie.

**C) Zarządzanie listą `messages` / rolą "tool"** — realna, warta sprawdzenia higiena, ale nie samodzielna naprawa. Dwie rzeczy do zweryfikowania:
- Czy wynik `read_queue()` trafia do modelu w formacie zgodnym z natywnym szablonem Qwena dla wyników narzędzi (Hermes/ChatML `<tool_response>`), czy jest spłaszczany do zwykłego tekstu — jeśli to drugie, model może nie ważyć go tak silnie, jak został wytrenowany, by ważyć poprawnie sformatowany wynik narzędzia.
- Czy w Waszym silniku dzieje się jakakolwiek kompresja/podsumowanie historii przy rosnącym kontekście (context compaction) — jeśli tak, to prawdopodobny dodatkowy winowajca: podsumowanie mogło po cichu zgubić lub spłycić oryginalny JSON z `read_queue()`, zanim model w ogóle dotarł do drugiej notatki.

Warto to sprawdzić niezależnie od wybranej architektury, ale nawet przy poprawnym formacie i braku kompresji, dylucja przez tury negocjacyjne (patrz diagnoza) i tak wystąpi — C usuwa jedną potencjalną przyczynę dodatkową, nie usuwa przyczyny głównej.

**D) Rekomendowany wzorzec: autorytatywny, ustrukturyzowany stan zewnętrzny ("blackboard"), odświeżany co turę, jawnie odseparowany od metadanych schematów.**

To formalizacja i dopracowanie opcji A. Konkretnie:

- Python **nie** przypina oryginalnego wyniku `read_queue()`. Zamiast tego, w każdej turze pętli, w której trwa proces konsolidacji, kod **na nowo odpytuje** `pending_notes.json` (nie historię konwersacji) i buduje świeży, ustrukturyzowany blok stanu — np. `{"pozostało": [...], "właśnie_zapisano": {...}, "krok": "2 z 3"}`.
- Ten blok jest wstrzykiwany jako osobna, wyraźnie oznaczona sekcja (np. w dedykowanym tagu `<queue_state>`), umieszczona **blisko punktu generacji** w każdej turze — nie zakopana w historii tur negocjacyjnych sprzed kilku wymian.
- Prompt zawiera jedno jawne zdanie rozstrzygające konflikt poziomów, który spowodował oryginalny błąd: *"Jedynym źródłem prawdy o zawartości kolejki jest blok `<queue_state>` w bieżącej turze. Przykładowe wartości w opisach narzędzi (np. w `description` `save_note`) nigdy nie są danymi użytkownika — służą wyłącznie do ilustracji formatu."* To bezpośrednio adresuje przyczynę źródłową: strukturalne, jawne rozróżnienie między warstwą danych a warstwą metadanych, którego wcześniej model nie miał.
- Jeśli zaimplementowaliście rekomendowaną wcześniej granularną zmianę `clear_queue(ids=[...])`, ten wzorzec współgra z nią naturalnie: skoro `pending_notes.json` na dysku zawsze dokładnie odzwierciedla to, co faktycznie zostało zapisane i wyczyszczone, świeże odpytanie dysku co turę **automatycznie** pokazuje właściwą "pierwszą" pozostałą notatkę — model nie musi liczyć "zrobiłem 1 z 3", bo dysk zawsze pokazuje aktualny stan, nie licznik do samodzielnego śledzenia.
- Warstwa konwersacyjna (ton, negocjacja treści notatki, persona Archiwisty) zostaje w pełni swobodna, zgodnie z podejściem Empowerment, które słusznie chcieliście zachować — bo to zadanie, w którym silniejszy model faktycznie błyszczy, i nie ma potrzeby go tam ograniczać.

To rozwiązuje problem u źródła, nie łata objawów: model nigdy nie jest zmuszony samodzielnie rekonstruować stanu z rozmytego lub skażonego sygnału, bo w każdej turze dostaje świeżą, jednoznacznie oznaczoną prawdę.

## Praktyczne uzupełnienie: uprawnienie do niepewności jako druga linia obrony

Nawet przy poprawnie wdrożonym D warto dodać jawne uprawnienie: *"Jeśli mimo bloku `<queue_state>` nie jesteś pewien, czy dana treść pochodzi z rzeczywistej kolejki, zapytaj użytkownika lub wywołaj `read_queue()` ponownie, zamiast zgadywać."* To ta sama zasada, którą ustaliliśmy przy okazji interpretacji surowych fragmentów w konsolidacji pamięci — model dostaje afirmatywną alternatywę do zgadywania. Nie jest to substytut D (bezpieczeństwo musi tkwić w architekturze, nie w nadziei, że model skorzysta z furtki), ale dobra siatka bezpieczeństwa na wypadek nieprzewidzianych luk.

## Tabela podsumowująca

| Opcja | Rozwiązuje przyczynę czy objaw | Ryzyko pozostawione |
|---|---|---|
| A (surowe przypinanie) | Częściowo — właściwy kierunek, niedopracowana implementacja | Model nadal musi wyliczać "co zostało" |
| B (self-report w `<thought>`) | Objaw — każe modelowi artykułować, nie naprawia sygnału | Może utrwalać błędne przekonanie z większą pewnością |
| C (higiena `messages`/`tool`) | Częściowa przyczyna dodatkowa (format, kompresja) | Nie usuwa dylucji przez tury negocjacyjne |
| **D (blackboard + jawna separacja danych/metadanych)** | **Przyczynę źródłową** | Wymaga dyscypliny w Pythonie (świeże zapytanie co turę) |

## Podsumowanie

Błąd nie bierze się z tego, że model "zapomina" w sensie ogólnym — bierze się z tego, że gdy prawdziwy sygnał o stanie się osłabia, model podstawia w jego miejsce najbliższy silny sygnał tekstowy, jaki zna, którym w tym przypadku były metadane schematu, nie dane. Naprawa nie polega na tym, by kazać modelowi pamiętać lepiej (B) ani łatać pojedynczy objaw (usuwanie mylących słów ze schematów, jak sami zauważyliście) — polega na tym, by nigdy nie zostawiać modelu bez świeżego, jednoznacznie oznaczonego źródła prawdy o stanie w danej turze, i na jawnym rozdzieleniu warstwy danych od warstwy metadanych w samym prompcie. Sztywność należy do kodu; swoboda należy do rozmowy — problem obu dotychczasowych prób polegał na tym, że nie rozdzieliliście tych dwóch odpowiedzialności.
