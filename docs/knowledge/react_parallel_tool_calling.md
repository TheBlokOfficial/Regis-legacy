# Rozwiązanie: Parallel Tool Calling Hallucination (Qwen 2.5 7B, pętla ReAct)

## Problem

Model w jednym ciągu generacji wywołuje więcej niż jedno narzędzie naraz, np. `read_notes()` i od razu `get_weather(location=Warszawa)`, nie czekając na odczytanie faktycznego miasta z notatek. Powoduje to halucynację parametru `location`.

Cel: wymusić ściśle liniową pracę pętli — **Myśl → Jedno Narzędzie → Stop → Zasilenie wynikiem**.

## Rekomendacja: hierarchia warstw, nie wybór jednej opcji

Stop token (2) i parser (3) jako twarde warstwy wykonawcze, prompt (1) jako lekkie dopełnienie jakości myślenia. To rozdzielenie odpowiada ogólnej zasadzie: prompt ustawia *intencję* modelu, a twarde gwarancje formatu i wykonania daje warstwa infrastruktury poniżej promptu.

## Dlaczego sam prompt (1) nie wystarcza

Reguła "nie wywołuj narzędzi równolegle" w system prompcie jest probabilistyczna, nie deterministyczna. 7B już teraz łamie logiczną kolejność (woła `get_weather` zanim zna wynik `read_notes`) — dopisanie zakazu zmniejszy częstotliwość zjawiska, ale nic fizycznie nie blokuje modelu przed wygenerowaniem drugiego `<tool_call>` w tym samym przejściu. Prompt sam w sobie jest za słaby jako jedyna linia obrony.

## Dlaczego stop token (2) to właściwy silnik rozwiązania

To najmocniejsza warstwa, bo działa na poziomie samplera, a nie "dobrej woli" modelu.

**Mechanika:** natywny format tool-callingu Qwena (styl Hermes/ChatML) przy równoległych wywołaniach generuje kolejne, osobne bloki `<tool_call>{...}</tool_call>`, jeden po drugim, bez wspólnego wrappera JSON-array. Ustawienie stop sequence na `</tool_call>` fizycznie ucina generację zaraz po zamknięciu pierwszego bloku — model nie zdąży nawet zacząć drugiego, bo backend przestaje samplingować tokeny w tym momencie. To twarda granica na poziomie inferencji, nie prośba.

**Pułapki do przetestowania:**

- **`include_stop_str_in_output`** — sprawdzić, czy backend (vLLM, Ollama itp.) domyślnie wycina samą sekwencję stop z outputu, czy ją zostawia. Jeśli wycina, trzeba ręcznie doklejać `</tool_call>` z powrotem przy rekonstrukcji wiadomości, inaczej w historii zostaje niedomknięty tag.
- **Warianty białych znaków** — np. `</tool_call >` (spacja przed `>`) ominie stop sequence. Warto dodać kilka wariantów jako dodatkowe stop sequences.
- **Rzadki false-positive** — gdyby argument narzędzia zawierał dosłowny string `</tool_call>` jako dane tekstowe, sekwencja ucięłaby generację przedwcześnie. Przy obecnym zestawie narzędzi (smart home) skrajnie mało prawdopodobne, ale warto pamiętać przy dodawaniu nowych narzędzi.

## Dlaczego parser (3) zostaje, ale jako fallback

Parser-only jest najsłabszym z trzech rozwiązań w izolacji — model i tak generuje pełną halucynowaną parę wywołań, płacicie tokenami/latencją, a efekt wyrzucacie do kosza. Ale jako drugi bezpiecznik ma sens: jeśli mimo stop tokena coś się prześlizgnie (np. wariant białych znaków), parser wykonuje tylko pierwsze wywołanie i ucina resztę przed wykonaniem — nawet failure warstwy 2 nie prowadzi do wykonania halucynowanego narzędzia.

**Ważne:** przy przycinaniu odpowiedzi zrekonstruować wiadomość assistant w historii tak, by pokazywała tylko to, co faktycznie się wykonało (thought + jedno tool_call, czysto domknięte). Surowy fragment obciętego drugiego wywołania w kontekście może w kolejnej turze zdezorientować model, który "pamięta", że coś zaczął, czego nigdy nie dokończył.

## Rola promptu (1) w tym mixie

Nie jako blokada, tylko jako poprawa jakości `<thought>`, żeby plan modelu był spójny z rzeczywistą, liniową egzekucją:

> "W każdej iteracji planujesz i wywołujesz dokładnie jedno narzędzie. Jeśli do wykonania zadania potrzebujesz wielu narzędzi, w `<thought>` zaznacz, którego użyjesz teraz, a które będą potrzebne w kolejnych krokach, po otrzymaniu wyniku."

## Podsumowanie architektury

| Warstwa | Rola | Gwarancja |
|---|---|---|
| Prompt (1) | Spójność `<thought>` z liniową egzekucją | Miękka, brak |
| Stop token (2) | Fizyczne ucięcie generacji po 1. narzędziu | Twarda, na poziomie samplera |
| Parser (3) | Siatka bezpieczeństwa + higiena historii konwersacji | Twarda, na poziomie aplikacji |

## Ewentualny krok czwarty (przyszłość)

Grammar-constrained decoding ograniczający region `<tool_call>...</tool_call>` do dokładnie jednego obiektu JSON zgodnego ze schematem — teoretycznie najmocniejsza gwarancja. Przy hybrydowym formacie (wolny tekst `<thought>` + XML tagi + osadzony JSON) trudniejsze do poprawnego wdrożenia niż w czystym trybie function-calling z JSON-only outputem. Stop token przy obecnej architekturze daje praktycznie ten sam efekt dużo mniejszym kosztem inżynieryjnym.
