# Poradnik: Qwen2.5 1.5B Instruct jako parser poleceń oświetlenia (PL, RPi5)

Poradnik opisuje jak przygotować lokalnie hostowany model **Qwen2.5 1.5B Instruct** (RPi5, 8GB RAM), aby błyskawicznie i bezbłędnie interpretował polskie polecenia głosowe/tekstowe dotyczące włączania, wyłączania i regulacji jasności światła.

---

## 1. Zasada nadrzędna: wymuszaj strukturę wyjścia

Model 1.5B potrafi poprawnie rozpoznać intencję, ale bez ograniczeń chętnie doda zbędny tekst, złamie format JSON albo "dopowie" coś od siebie. Dlatego **prompt engineering to tylko połowa rozwiązania** — druga połowa to wymuszenie formatu na poziomie silnika inferencji.

- **llama.cpp** — użyj gramatyki GBNF albo `response_format` z JSON Schema
- **Ollama** — użyj parametru `"format"` z podanym JSON Schema w zapytaniu
- **llama-cpp-python** — `grammar=JsonSchemaGrammar(schema)`

Przykładowy schemat wyjścia:

```json
{
  "type": "object",
  "properties": {
    "action": { "enum": ["light_on", "light_off", "set_brightness", "unknown"] },
    "room": { "type": ["string", "null"] },
    "brightness_value": { "type": ["integer", "null"] },
    "brightness_direction": { "enum": ["up", "down", null] }
  },
  "required": ["action", "room", "brightness_value", "brightness_direction"]
}
```

> Wymuszenie gramatyki JSON eliminuje zdecydowaną większość błędów formatu u małych modeli — to najbardziej opłacalna zmiana, jaką możesz wprowadzić.

---

## 2. System prompt — krótki i jednoznaczny

Mniejsze modele mają ograniczoną "pojemność uwagi" na długie instrukcje. Zamiast rozbudowanych opisów, daj krótkie, twarde reguły + przykłady (few-shot działa u małych modeli mocniej niż opis słowny).

```
Jesteś modułem NLU sterującym oświetleniem w domu. Analizujesz polecenie użytkownika
i zwracasz WYŁĄCZNIE jeden obiekt JSON, bez żadnego dodatkowego tekstu.

Pola:
- action: "light_on" | "light_off" | "set_brightness" | "unknown"
- room: nazwa pomieszczenia (np. "salon", "kuchnia") albo null, jeśli nie podano
- brightness_value: liczba 0-100, jeśli podano konkretną wartość, inaczej null
- brightness_direction: "up" albo "down", jeśli polecenie jest względne
  (przyciemnij/rozjaśnij bez liczby), inaczej null

Jeśli polecenie nie dotyczy światła, zwróć action: "unknown".
Nie tłumacz, nie komentuj, nie dodawaj markdown.
```

**Guideline:** trzymaj system prompt pod ~150-200 tokenów. Każdy dodatkowy akapit "rozmywa" uwagę modelu na kluczowych regułach.

---

## 3. Few-shot examples — pokryj realne warianty językowe

Dodaj 6-10 przykładów bezpośrednio w promptcie, obejmujących różne rejestry języka:

```
Użytkownik: zapal światło
{"action":"light_on","room":null,"brightness_value":null,"brightness_direction":null}

Użytkownik: zgaś światło w kuchni
{"action":"light_off","room":"kuchnia","brightness_value":null,"brightness_direction":null}

Użytkownik: czy mógłbyś zaświecić światło w pokoju?
{"action":"light_on","room":"pokój","brightness_value":null,"brightness_direction":null}

Użytkownik: ustaw jasność na 30 procent
{"action":"set_brightness","room":null,"brightness_value":30,"brightness_direction":null}

Użytkownik: przyciemnij trochę światło w salonie
{"action":"set_brightness","room":"salon","brightness_value":null,"brightness_direction":"down"}

Użytkownik: jak się masz?
{"action":"unknown","room":null,"brightness_value":null,"brightness_direction":null}
```

### Warianty warte uwzględnienia:
- polecenia bezpośrednie: "zapal światło", "zgaś światło"
- pytania grzecznościowe: "czy mógłbyś...", "czy możesz..."
- polecenia z pokojem i bez pokoju
- polecenia względne bez liczby: "przyciemnij", "rozjaśnij nieco", "zrób ciemniej"
- polecenia z konkretną wartością: "ustaw na 50%", "50 procent jasności"
- literówki / potoczne formy: "zapl światło", "wyłącz to światło"

---

## 4. Regulacja jasności — nie każ modelowi liczyć

Model 1.5B łatwo popełnia błędy matematyczne. Dla poleceń względnych ("przyciemnij trochę") **nie proś go o wyliczenie konkretnej wartości procentowej** — niech zwraca tylko `brightness_direction: "up"/"down"`, a stały krok (np. ±15%) niech oblicza już logika Twojej aplikacji sterującej, nie model.

---

## 5. Parametry samplingu

| Parametr | Wartość | Dlaczego |
|---|---|---|
| `temperature` | 0 – 0.1 | zadanie deterministyczne/klasyfikacyjne, nie kreatywne |
| `top_p` | 0.9 (przy temp > 0) | ogranicza losowe "dryfowanie" |
| `max_tokens` | 60–80 | tyle wystarcza na JSON; dodatkowo przyspiesza odpowiedź na RPi5 |

---

## 6. Kwantyzacja modelu

Przy 8GB RAM nie musisz iść w agresywną kwantyzację modelu 1.5B:

- **Q5_K_M lub Q6_K** — zalecane; zauważalnie lepsza wierność instrukcjom niż Q4, niewielki koszt prędkości/pamięci
- Q4_K_M — użyj tylko jeśli zależy Ci na maksymalnej prędkości kosztem drobnych błędów klasyfikacji

Warto przetestować oba warianty na własnym zestawie przykładów i porównać dokładność.

---

## 7. Warstwa bezpieczeństwa przed wykonaniem akcji

Nawet z wymuszoną gramatyką JSON model czasem błędnie dopasuje pole. Zanim wykonasz akcję na urządzeniu:

- **Waliduj `room`** względem listy znanych pomieszczeń (np. fuzzy matching biblioteką typu `rapidfuzz`); jeśli nie pasuje — potraktuj jako pokój domyślny albo poproś o doprecyzowanie
- **Jeśli `action == "unknown"`** lub pole nie daje się dopasować do żadnego znanego urządzenia — nie wykonuj żadnej akcji
- Rozważ log poleceń nierozpoznanych, żeby później rozszerzać few-shot examples o realne przypadki, które model źle sklasyfikował

---

## 8. Testowanie i iteracja

1. Zbuduj zestaw testowy 50-100 przykładowych poleceń (w tym potoczne, pytające, z literówkami) wraz z oczekiwanym JSON-em
2. Uruchamiaj ten zestaw po **każdej** zmianie system promptu — poprawka jednego przypadku potrafi zepsuć inny, zwłaszcza przy modelu tej wielkości
3. Śledź dokładność (accuracy) jako główną metrykę; przy < 95% na Twoim zbiorze rozważ krok 9

---

## 9. Kiedy sięgnąć po fine-tuning

Jeśli prompt engineering + wymuszona gramatyka JSON nie dają wystarczającej dokładności, kolejny krok to lekki **fine-tuning LoRA** na kilkuset przykładach tego konkretnego zadania. Model 1.5B jest na tyle mały, że taki fine-tuning jest tani obliczeniowo i bardzo skuteczny dla wąskiego, powtarzalnego zadania jak klasyfikacja poleceń świetlnych. Trenowanie odbywa się poza RPi5 (na mocniejszej maszynie/w chmurze), a gotowy model wdraża się z powrotem na Raspberry Pi.

---

## Checklista szybkiego wdrożenia

- [ ] Wymuszona gramatyka JSON / JSON Schema na poziomie silnika inferencji
- [ ] Krótki, jednoznaczny system prompt (~150-200 tokenów)
- [ ] 6-10 przykładów few-shot pokrywających realne warianty językowe
- [ ] `brightness_direction` zamiast liczenia wartości przez model dla poleceń względnych
- [ ] `temperature` ≈ 0, ograniczony `max_tokens`
- [ ] Kwantyzacja Q5_K_M/Q6_K przetestowana względem Q4
- [ ] Walidacja `room` i `action` przed wykonaniem akcji na urządzeniu
- [ ] Zestaw testowy 50-100 poleceń do regresyjnego sprawdzania po każdej zmianie
