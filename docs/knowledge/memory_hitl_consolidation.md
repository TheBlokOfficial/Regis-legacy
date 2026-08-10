# Human-in-the-Loop Konsolidacja Pamięci (Regis 14B, `read_queue` / `clear_queue`)

## Kontekst

`queue_note` (Lokaj, 7B) zrzuca do `pending_notes.json` surowe, często jednowyrazowe fakty ('Polska', 'Nysa', 'czerwony'). Nowy pomysł: Regis (14B) dostaje `read_queue` i `clear_queue`, a na życzenie użytkownika ("Szefie, zróbmy porządek") odczytuje brudnopis, komentarzem kwituje ubóstwo kontekstu małego modelu, wnioskuje pełne zdania, proponuje je użytkownikowi, po zatwierdzeniu zapisuje przez `save_note` i czyści kolejkę.

## 1. Czy Human-in-the-Loop to dobry pattern tutaj?

**Tak, i to z dobrego powodu — ale nie z powodu, który jest najczęściej podawany.** HITL zwykle broni się jako ogólna zasada ostrożności. Tu jest coś bardziej konkretnego: interpretacja fragmentu typu 'czerwony' niesie ryzyko **halucynacji pewności kontekstu**, a nie halucynacji faktu. Model nie zmyśla danych znikąd — zmyśla *przekonujące, brzmiące sensownie otoczenie* wokół prawdziwego fragmentu ("użytkownik preferuje kolor czerwony w oświetleniu" — a może to był ulubiony kolor samochodu, ściany, albo coś zupełnie innego). To gorszy rodzaj błędu niż czysta halucynacja faktu, bo brzmi wiarygodnie i trudniej go wychwycić przy późniejszym przeglądzie pamięci. HITL jako bramka zatwierdzenia trafia dokładnie w ten problem — dobry wybór.

Dodatkowy plus: to naturalnie wzmacnia ustaloną wcześniej personę Regisa (boss mode, komentujący ograniczenia mniejszego modelu) — zadanie utrzymania pamięci staje się częścią charakteru agenta, nie suchą operacją systemową.

**Ale sam pomysł ma dwie słabości warte odnotowania, zanim przejdziemy do zagrożeń technicznych:**

- **Trigger wyłącznie pull-based** ("Szefie, zróbmy porządek") oznacza, że kolejka rośnie bez ograniczeń, dopóki użytkownik sam nie zainicjuje porządków. To nie jest jeszcze błąd krytyczny, ale warto rozważyć dyskretny, nienachalny sygnał ze strony Regisa przy okazji innej rozmowy ("swoją drogą, mam kilka nieprzetworzonych notatek, zajmiemy się nimi?"), zamiast czekać w nieskończoność — z zachowaniem ostrożności, by nie powtórzyć błędu nadgorliwości omawianego wcześniej przy Lokaju.
- **Sufit jakości interpretacji jest ustalany w momencie zapisu do `pending_notes.json`, nie w momencie odczytu.** Jeśli `queue_note` zapisuje wyłącznie goły token ('czerwony') bez żadnego śladu kontekstu rozmowy, w którym padł, to żadna spryt Regisa przy odczycie tego nie odzyska — po tygodniach kontekst jest już nieodwracalnie utracony i Regis będzie zgadywał tak samo w ciemno jak wy teraz. Warto rozważyć rozszerzenie `queue_note` o krótki fragment kontekstu (np. ostatnie 1-2 zdania rozmowy) lub prostą kategorię/tag zapisywane w momencie ekstrakcji przez Lokaja — to inwestycja tańsza niż próba odtworzenia kontekstu później.

## 2. Ukryte zagrożenia — inżynieria promptów i limit kontekstu

**A. `clear_queue` jako operacja "wszystko albo nic" — to największe ryzyko w całym projekcie.** Jeśli Regis proponuje np. 15 faktów, użytkownik zatwierdza 10, odrzuca 3, a 2 pozostają bez odpowiedzi (rozmowa zbacza na inny temat), a `clear_queue` czyści cały plik na końcu — tracicie bezpowrotnie te niezatwierdzone pozycje. To dokładnie ten sam wzorzec błędu, który omawialiśmy przy okazji `delete_note`: operacja nieodwracalna wykonana w granulacji niezgodnej z tym, co faktycznie zostało potwierdzone. Rekomendacja: zmienić sygnaturę na `clear_queue(ids=[...])`, przyjmującą wyłącznie identyfikatory pozycji faktycznie zapisanych, nigdy blankietowe czyszczenie całego pliku.

**B. Ryzyko kolejności/atomowości między `save_note` a `clear_queue`.** Jeśli sesja zostanie przerwana (zerwane połączenie, użytkownik zamyka aplikację) między wywołaniem `save_note` a `clear_queue`, bezpieczny stan awaryjny to: *notatka zapisana, kolejka nie wyczyszczona* — najwyżej przy następnych porządkach Regis zobaczy duplikat i go pominie. Odwrotna kolejność (kolejka wyczyszczona przed potwierdzonym zapisem) jest nie do przyjęcia — utrata danych bez możliwości odzyskania. Prompt musi wymuszać: `clear_queue` dla danej pozycji wolno wywołać dopiero **po otrzymaniu wyniku** potwierdzającego sukces `save_note`, nigdy w tej samej turze bez czekania na `tool_result`. To ta sama dyscyplina "czekaj na wynik przed kolejnym krokiem", o której pisałem przy okazji pętli ReAct — tu stosowana na poziomie całego workflow, nie pojedynczego wywołania.

**C. Wzrost kontekstu przy odczycie całej kolejki naraz.** Jeśli `pending_notes.json` narosło do kilkudziesięciu pozycji, wczytanie ich wszystkich jednym `read_queue` plus cała późniejsza wymiana propozycja-zatwierdzenie dla każdej z nich w jednej sesji konwersacyjnej może zapchać kontekst, zwłaszcza przy lokalnym wdrożeniu 14B z ograniczonym oknem. To nie jest tylko kwestia wydajności — jeśli propozycje dla pozycji 1-5 "wypadną" z okna kontekstu, zanim dojdzie do pozycji 20, ryzykujecie niespójność między tym, co model "pamięta" jako zatwierdzone, a rzeczywistym stanem zatwierdzeń.

**D. Duplikaty względem istniejącej pamięci.** Przy drugich i kolejnych porządkach Regis może zaproponować notatkę semantycznie tożsamą z czymś, co już jest w `memory.json`, tylko innymi słowami. Warto, by przed każdą propozycją Regis sprawdzał istniejącą pamięć przez `read_notes()` i pomijał lub łączył pozycje już pokryte, zamiast bezrefleksyjnie mnożyć wpisy.

**E. Niejednoznaczne "tak".** Użytkownik mówiący "tak" po serii propozycji może mieć na myśli "tak, ta jedna" albo "tak, wszystkie". Prompt musi rozstrzygać to jednoznacznie i konserwatywnie — domyślnie traktować potwierdzenie jako dotyczące pojedynczej, ostatnio zaproponowanej pozycji, chyba że użytkownik explicite powie "wszystkie" / "zatwierdzam całość".

**F. Przeciek tonu żartobliwego do warstwy wykonawczej.** Instrukcja "wyśmiej braki kontekstu u Lokaja" jest dobrym elementem charakteru, ale musi być wyraźnie odseparowana od `<thought>` i logiki wywołań narzędzi — żart ma żyć wyłącznie w tekście konwersacyjnym do użytkownika, nigdy nie zastępować ani nie zaburzać precyzyjnego wykonania kroków.

**G. "Wyciek tokenów" w sensie budżetu kontekstu.** Jeśli `read_queue` wrzuca do kontekstu wszystkie surowe, częściowo zduplikowane wpisy bez wstępnego czyszczenia, Regis zużywa tokeny na odkrywanie duplikatów i szumu, które backend mógłby odfiltrować deterministycznie *przed* wstrzyknięciem do promptu. Model powinien dostawać already-wstępnie odszumioną listę, a swój "budżet rozumowania" poświęcać na to, w czym jest faktycznie dobry — interpretację znaczenia, nie mechaniczną deduplikację.

## 3. Optymalizacja promptu dla Regisa

**Model procesu jako maszyna stanów, jedna pozycja na raz — nie batch.** Dla przepływu tak nowego i wieloturowego jak ten, jawna sekwencja stanów w prompcie jest bezpieczniejsza niż ogólna instrukcja opisowa:

```
ODCZYT (read_queue) 
  → PROPOZYCJA (jedna pozycja, tekst konwersacyjny, bez wywołania narzędzia) 
  → CZEKANIE na odpowiedź użytkownika 
  → jeśli zatwierdzone: save_note → czekaj na tool_result sukcesu → clear_queue(id=X)
  → jeśli odrzucone: przejdź do kolejnej pozycji, nie wywołuj żadnego narzędzia dla tej
  → jeśli niejednoznaczne/za mało kontekstu: zapytaj użytkownika wprost, nie zgaduj
  → NASTĘPNA POZYCJA lub KONIEC (gdy kolejka pusta lub użytkownik zmienia temat)
```

**Twarda reguła kolejności** (wpisana explicite w prompt, nie domyślna): *"Nigdy nie wywołuj `clear_queue` dla pozycji, dla której nie otrzymałeś jeszcze potwierdzenia sukcesu z `save_note`. Jeśli sesja zostanie przerwana przed zapisem, pozycja musi pozostać w kolejce."*

**Uprawnienie do niepewności zamiast zgadywania.** Dla fragmentów bez wystarczającego kontekstu prompt powinien explicite pozwalać na: *"Jeśli nie potrafisz z rozsądną pewnością zinterpretować zapisanego fragmentu, powiedz to wprost i zapytaj użytkownika o doprecyzowanie, zamiast proponować domysł jako fakt."* To bezpośrednio adresuje ryzyko z punktu 1 (halucynacja pewności kontekstu) — dajemy modelowi afirmatywną alternatywę do zgadywania, zgodnie z zasadą, że reguła bez alternatywy zostawia model w próżni decyzyjnej.

**Few-shot pojedynczego cyklu.** Podobnie jak przy problemie nadgorliwości Lokaja, sama reguła tekstowa może przegrać z brakiem konkretnego wzorca. Warto dołączyć pełny przykład jednej iteracji: odczyt → propozycja w naturalnym tekście → symulowana odpowiedź użytkownika "tak" → `save_note` → oczekiwanie na wynik → `clear_queue(id=...)` — pokazany jako kompletna, zamknięta sekwencja, nie opisany słownie.

**Jawna obsługa odrzucenia.** Zdefiniować osobno: co się dzieje, gdy użytkownik mówi "nie, to nieprawda" — pozycja zostaje w kolejce (domyślnie, bezpieczniej) czy zostaje trwale odrzucona (`clear_queue(id=X)` bez poprzedzającego `save_note`)? To musi być jawna, świadoma decyzja użytkownika za każdym razem, nie zachowanie domyślne.

**Warstwa backendowa, nie tylko prompt.** Deduplikacja i wstępne czyszczenie kolejki (punkt 2G) powinny dziać się w `read_queue` po stronie kodu, zanim treść trafi do kontekstu Regisa — to tańsze i bardziej niezawodne niż poleganie na modelu, by sam wychwycił duplikaty w rozumowaniu.

## Tabela: zagrożenie → mitygacja

| Zagrożenie | Warstwa | Mitygacja |
|---|---|---|
| `clear_queue` czyści więcej niż zatwierdzono | Schemat narzędzia | `clear_queue(ids=[...])` zamiast blankietowego czyszczenia |
| Kolejka wyczyszczona przed potwierdzonym zapisem | Prompt (dyscyplina ReAct) | `clear_queue` tylko po otrzymanym `tool_result` sukcesu z `save_note` |
| Przepełnienie kontekstu przy dużej kolejce | Architektura procesu | Jedna pozycja na raz, nie batch |
| Duplikaty względem `memory.json` | Prompt + narzędzie | `read_notes()` przed każdą propozycją |
| Niejednoznaczne "tak" | Prompt | Domyślnie dotyczy jednej, ostatniej pozycji, chyba że jawne "wszystkie" |
| Halucynacja pewności kontekstu | Prompt | Jawne uprawnienie do pytania zamiast zgadywania |
| Szum/duplikaty zużywające tokeny | Backend | Deduplikacja w `read_queue` przed wstrzyknięciem do kontekstu |
| Przeciek żartobliwego tonu do wykonania | Prompt | Humor tylko w tekście do użytkownika, nigdy w `<thought>` |

## Podsumowanie

HITL to dobry wybór, bo trafia w realny problem — nie zmyślanie faktów, tylko zmyślanie wiarygodnie brzmiącego kontekstu wokół prawdziwych fragmentów. Największe ryzyko techniczne nie leży jednak w warstwie promptu, tylko w granulacji `clear_queue` — dopóki to operacja blankietowa, żadna dyscyplina promptowa nie ochroni przed cichą utratą niezatwierdzonych danych. Zmiana sygnatury na czyszczenie po identyfikatorach, w połączeniu z regułą "nie czyść przed potwierdzonym zapisem" i przetwarzaniem jednej pozycji na raz, usuwa większość zagrożeń u źródła — reszta to kwestia dobrego few-shota i jawnego uprawnienia do niepewności zamiast wymuszonego zgadywania.
