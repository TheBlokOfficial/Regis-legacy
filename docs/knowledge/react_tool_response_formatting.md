# Puste Potwierdzenie vs Duplikacja Danych (`open_notes()`, Qwen 2.5 32B)

## Diagnoza — dlaczego model faktycznie "panikuje"

To nie jest kaprys ani "głupota" modelu — to precyzyjne, przewidywalne zachowanie wynikające z tego, jak model został wytrenowany do interpretowania wywołań narzędzi. Fine-tuning function-callingowy uczy model bardzo silnego wzorca: odpowiedź na wywołanie narzędzia znajduje się **w sparowanym z nim `tool_result`**, powiązanym konkretnym identyfikatorem wywołania. To ta sama zasada, o której pisałem przy okazji cheat-code'u z opisem narzędzia — model jest trenowany, by bardzo mocno ważyć konkretne, strukturalnie oczekiwane miejsca w kontekście. Tutaj działa to na Waszą niekorzyść: dla narzędzia, które semantycznie jest operacją odczytu ("otwórz i pokaż mi zawartość"), pusty `{"status": "Sukces"}` w tym dokładnie miejscu pasuje do wzorca, który model widział tysiące razy w danych treningowych jako sygnał "brak wyników / operacja nic nie zwróciła". Model nie ignoruje `<desk_state>` przez nieuwagę — on w ogóle nie traktuje go jako odpowiedzi na to konkretne wywołanie, bo strukturalnie nim nie jest. To osobny blok, w innym miejscu, bez formalnego powiązania z `tool_call_id`.

## Czy Opcja B jest niezawodna? Nie — i nie dlatego, że 32B jest "za słaby"

Drogowskaz tekstowy w Opcji B każe modelowi zignorować silny, wytrenowany priorytet (odpowiedź żyje w `tool_result`) na rzecz instrukcji słownej wskazującej gdzie indziej. To dokładnie ten sam mechanizm, który już raz zawiódł w tym projekcie: czysto deklaratywna instrukcja tekstowa przegrywa ze strukturalnym/wytrenowanym wzorcem, tak jak wcześniej reguła "nie wywołuj narzędzi równolegle" przegrywała z jedynym wzorcem behawioralnym, jaki model znał z few-shota. Silniejszy model (32B) może częściej poprawnie zastosować taki drogowskaz niż słabszy, ale "częściej" to nie "niezawodnie" — a to przecież tego szukacie w architekturze, którą chcecie skalować do dziesiątek "aplikacji".

**Jest też druga wada Opcji B, której nie uwzględniliście w bilansie DRY, a która odwraca argument o "czystości architektonicznej".** Ten sztywny komunikat sterujący pojawi się w `tool_result` **za każdym razem**, gdy model wywoła `open_notes()` w ciągu sesji — a w historii konwersacji pozostaje jako trwały zapis. Po kilkunastu turach macie w transkrypcie kilka kopii tego samego, statycznego tekstu, który w chwili, gdy pojawia się w historii po raz drugi czy trzeci (a `<desk_state>` dawno przesunął się gdzie indziej i zaktualizował), **nie niesie już żadnej informacji** — to czysty szum. Duplikacja danych w Opcji A przynajmniej ma wartość: to zrzut stanu z konkretnego momentu w czasie. Duplikacja tekstu sterującego w Opcji B nie ma żadnej — to jest gorszy rodzaj powtórzenia, nie lepszy.

## Czy warto pogodzić się z duplikacją danych (Opcja A)? Częściowo — ale w pełnej formie to niepotrzebny koszt

Warto policzyć to uczciwie: duplikacja w Opcji A jest **jednorazowa i ograniczona w czasie** — pojawia się dokładnie w turze, w której `open_notes()` zostało wywołane, i nie powtarza się przy kolejnych turach negocjacji (bo `<desk_state>` na dole odświeża się co turę, ale `tool_result` z konkretnego wywołania `open_notes()` zostaje w historii jako jednorazowy wpis, stopniowo oddalający się w głąb kontekstu jak każda inna wiadomość). To realny koszt tokenowy, ale ograniczony i policzalny — w przeciwieństwie do kosztu porażki Opcji B: niepotrzebne wywołania narzędzi poszukiwawczych to dodatkowe rundy w pętli ReAct, dodatkowa latencja i więcej zużytych tokenów niż wyniosłaby jednorazowa duplikacja. Na czystym rachunku kosztów Opcja A wygrywa z Opcją B.

Ale pełna duplikacja całej zawartości też nie jest konieczna, żeby zaspokoić wytrenowany wzorzec modelu — potrzebny jest tylko sygnał, że coś realnego zostało zwrócone, nie koniecznie wszystko.

## Trzecia droga: potwierdzenie hybrydowe (rekomendacja)

Prawdziwym problemem nie jest brak pełnych danych w `tool_result` — jest nim **strukturalna pustka**, która wygląda jak sygnał "nic nie znaleziono". Rozwiązaniem nie jest więc "wszystko" (A) ani "nic, tylko wskazówka" (B), tylko lekkie, ale treściwe potwierdzenie:

```json
{
  "status": "sukces",
  "znaleziono": 3,
  "podglad": "notatki dot.: preferowany kolor, miasto, godziny ciszy nocnej"
}
```

To satysfakcjonuje wytrenowany priorytet modelu (w sparowanym `tool_result` jest coś konkretnego, nie pustka przypominająca błąd), a jednocześnie koszt duplikacji jest minimalny — kilka słów podglądu, nie pełny zrzut JSON. Pełna, aktualna treść nadal żyje wyłącznie w `<desk_state>`, zgodnie z zasadą jednego źródła prawdy, którą ustaliliśmy poprzednio.

Warto zauważyć, że to nie jest rozwiązanie ad hoc wymyślone na potrzeby tego problemu — to zbieżne z tym, jak działa nawet architektura MemGPT, na którą się powołujecie: funkcje edytujące pamięć zwracają bezpośrednie, konkretne potwierdzenie w odpowiedzi na wywołanie (np. potwierdzenie zapisu), natomiast pełna, aktualna treść trwałej pamięci żyje osobno, w bloku wstrzykiwanym do kontekstu przy każdej turze. Wzorzec "konkretne potwierdzenie w `tool_result` + pełny stan gdzie indziej" jest już częścią architektury, do której się odwołujecie — nie trzeba go wymyślać od nowa, wystarczy zastosować konsekwentnie.

## Ranking rekomendacji

1. **Potwierdzenie hybrydowe (podgląd + licznik)** — najlepszy stosunek niezawodności do kosztu; zgodne z wytrenowanym wzorcem, minimalna duplikacja.
2. **Opcja A (pełna duplikacja)** — bezpieczny wybór zapasowy, jeśli budowanie logiki podglądu dla każdego narzędzia wydaje się nieproporcjonalnym nakładem pracy na tym etapie. Koszt jest realny, ale ograniczony i przewidywalny.
3. **Opcja B (czysty drogowskaz)** — odradzam. Wygląda na najczystszą architektonicznie na papierze, ale w praktyce działa pod prąd wytrenowanego wzorca modelu, a jej rzekoma oszczędność tokenowa nie utrzymuje się w całej historii sesji.

## Tabela podsumowująca

| Opcja | Zgodność z wytrenowanym wzorcem | Koszt tokenowy | Ryzyko fałszywego alarmu |
|---|---|---|---|
| A — pełna duplikacja | Wysoka | Umiarkowany, jednorazowy | Niskie |
| B — sam drogowskaz | Niska — działa wbrew priorytetowi modelu | Pozornie niski, w praktyce rośnie w historii (bezwartościowy szum) | Wysokie |
| **Hybryda — podgląd + licznik** | **Wysoka** | **Minimalny** | **Niskie** |

## Podsumowanie

To nie jest w gruncie rzeczy spór DRY kontra UX modelu — to spór między dwoma rodzajami kosztu: policzalnym, jednorazowym kosztem tokenowym (duplikacja) a nieprzewidywalnym, powtarzalnym kosztem błędu (niepotrzebne wywołania poszukiwawcze wywołane strukturalną pustką, która wygląda jak porażka). Hybrydowe potwierdzenie unika obu — daje modelowi coś konkretnego dokładnie tam, gdzie trenowanie każe mu tego szukać, bez płacenia pełnej ceny duplikacji całej zawartości notatnika.
