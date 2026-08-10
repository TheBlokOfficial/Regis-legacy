# Open/Close Application Paradigm — Dynamiczna Subskrypcja Kontekstu (Qwen 2.5 32B)

## Kontekst

Blackboard rozwiązał ReAct Drift, ale bezwarunkowe wstrzykiwanie całego stanu (150 żarówek, logi routera) nie skaluje się. Proponowany wzorzec: pary narzędzi `open_X`/`close_X` — model "otwiera aplikację", Python zaczyna wstrzykiwać jej stan co turę, model "zamyka", wstrzykiwanie ustaje.

To naturalna ewolucja Blackboardu — dodaje mechanizm *zakresu* (scoping), rozwiązując problem "co właściwie powinno leżeć na tablicy w danym momencie", którego sam Blackboard nie adresował.

## 1. Czy to dobra droga w inżynierii agentów?

**Tak, i to nie jest pomysł odosobniony — to rozpoznana rodzina wzorców, z ważnym zastrzeżeniem produkcyjnym.**

Koncepcja "kontekst jako RAM, trwały magazyn jako dysk, model zarządza własnym stronicowaniem" ma swoją genezę w architekturze MemGPT — dokładnie ta sama metafora, którą sami wymyśliliście niezależnie. To dobry znak: trafiliście na wzorzec, do którego branża dochodziła już wcześniej z innej strony. Nowsze prace formalizują to dalej — jedna z niedawnych propozycji architektonicznych opisuje harness jako <cite index="24-1">naturalny punkt egzekwowania reguł, ponieważ to on i tak składa prompty, pośredniczy w narzędziach i obserwuje zdarzenia cyklu życia</cite>, proponując zarządzanie stanem jako "wirtualną pamięć" z jawnymi gwarancjami rezydencji i trwałości. Podobny kierunek reprezentuje praca nad dynamicznym "wyposażaniem" agenta w narzędzia i konteksty w rozmowach wieloturowych, zamiast trzymania wszystkiego dostępnego na stałe.

**Ważne zastrzeżenie, które warto potraktować poważnie, bo dotyka wprost Waszego pytania 2.** Jedna z analiz praktycznych wdrożeń tego typu architektury zauważa, że narzut utrzymania osobnych warstw pamięci bywa na tyle duży, że <cite index="25-1">tego typu podejścia mają tendencję do zawodzenia w praktyce, a mimo kilku lat istnienia koncepcji trudno znaleźć jej rzeczywiste zastosowania produkcyjne</cite>. To nie dyskwalifikuje pomysłu — ale konkretyzuje, gdzie leży ryzyko: nie w samej idei podziału na "otwarte" i "zamknięte", tylko w tym, **kto odpowiada za cykl życia**. Wersje, w których to wyłącznie model decyduje, kiedy coś otworzyć i zamknąć, są tymi, które najczęściej zawodzą w praktyce. Do tego wracam w punkcie 2 — to najważniejszy wniosek z całej odpowiedzi.

**Druga rzecz warta odnotowania: ten wzorzec rozwiązuje skalowanie *czasowe*, nie *przestrzenne*.** Open/Close zapewnia, że nie wszystko jest wstrzykiwane naraz przez cały czas — ale gdy `open_home_dashboard` faktycznie się otworzy przy 150 żarówkach, sam ten pojedynczy widok może być ogromny. Wzorzec sam w sobie nie chroni przed tym, że pojedyncza "aplikacja" będzie zbyt duża, gdy jest otwarta. Rekomendacja: każdy widok stanu powinien mieć własną wewnętrzną redukcję (np. `open_home_dashboard` nie zrzuca surowego stanu 150 żarówek, tylko podsumowanie — "142 zgaszone, 8 zapalonych w kuchni i salonie" — z możliwością doprecyzowania na żądanie). Open/Close jest warunkiem koniecznym skalowania, nie wystarczającym.

**Trzecia rzecz: wiele otwartych aplikacji naraz odtwarza problem w mniejszej skali.** Jeśli użytkownik przechodzi między tematami, a model otwiera nowe "aplikacje" bez zamykania starych, po kilkunastu turach macie z powrotem kilka bloków stanu wstrzykiwanych jednocześnie — mniej dramatyczne niż wstrzykiwanie całego świata, ale ten sam mechanizm w miniaturze. Potrzebny jest twardy limit liczby jednocześnie otwartych aplikacji (patrz punkt 2).

## 2. Ryzyka Open/Close przy 32B

**Ryzyko główne: "zombie state" — otwarte aplikacje pozostawione w tle.** To dokładnie ten typ awarii, który udokumentowano w analizach produkcyjnych harnessów agentowych — <cite index="24-1">utrata stanu po kompresji kontekstu, pominięte operacje domykające przy resecie sesji i destrukcyjne nadpisania</cite> pojawiają się właśnie tam, gdzie zarządzanie cyklem życia stanu było pozostawione jako "najlepszy wysiłek" modelu, a nie twarda gwarancja harnessu. Branżowa terminologia dla tego zjawiska to wprost <cite index="20-1">"zombie memory" — stan, który logicznie powinien być zamknięty/wygaszony, ale mechanicznie pozostaje aktywny</cite>, co argumentuje się rozwiązywać przez oddzielenie zarządzania cyklem życia pamięci od samego modelu.

**Dlaczego nie warto ufać samej dyscyplinie modelu — nawet przy 32B.** Jest ku temu konkretny, zbadany powód, a nie tylko ostrożność: świeże badania nad zarządzaniem kontekstem pokazują, że modele frontierowe są <cite index="23-1">"proprioceptywnie ślepe" na własny kontekst — nie potrafią samodzielnie ocenić, jak duża, stara czy wykorzystana jest dana część ich pamięci roboczej</cite>. Innymi słowy: nie chodzi o to, że 32B jest "za mało inteligentny", żeby pamiętać o zamknięciu — chodzi o to, że modele generalnie nie mają wbudowanego zmysłu własnego zużycia kontekstu, więc poleganie na tym, że model "zauważy", że coś zostało otwarte za długo, jest strukturalnie słabym założeniem, niezależnie od wielkości modelu.

**Ryzyko odwrotne: przedwczesne zamknięcie.** Model zamyka aplikację, zanim wątek faktycznie się skończył, co odtwarza dokładnie ten sam ReAct Drift, który właśnie naprawiliście. Mitygacja: `close` nie powinno być operacją destrukcyjną — dane źródłowe (np. `pending_notes.json`) istnieją niezależnie od flagi w Pythonie. Jeśli model błędnie zamknie, a potem spróbuje odwołać się do czegoś z tej domeny, harness powinien po cichu ponownie otworzyć widok, zamiast pozwolić modelowi zgadywać lub zwracać błąd — koszt pomyłkowego zamknięcia powinien być bliski zeru.

**Ryzyko: flaga skopowana globalnie zamiast per-sesja.** Nazwa problemu, który rozwiązujecie ("Global State Injection"), jest dobrym przypomnieniem, żeby flaga otwarcia/zamknięcia była jednoznacznie przypięta do konkretnej sesji/konwersacji, nie do procesu jako całości — inaczej ryzykujecie nowy, poważniejszy błąd: przeciek stanu jednej rozmowy (np. czyjeś otwarte notatki) do kontekstu innej.

**Ryzyko: nadgorliwe otwieranie przez "pomocny" model.** To wariant znanego już problemu nadgorliwości — jeśli otwarcie aplikacji wygląda dla modelu jak działanie bez kosztu, silny, zorientowany na cel 32B może zacząć otwierać "na wszelki wypadek". Prompt musi jawnie ramować otwarcie jako coś, co ma realny koszt (patrz punkt 3).

**Mitygacje — wszystkie po stronie kodu, nie promptu:**
- **TTL / automatyczne wygaszanie.** Standardowa, najprostsza linia obrony w zarządzaniu pamięcią agentów to <cite index="27-1">wygaszanie oparte na wieku (time-to-live)</cite> — po N turach bez odniesienia do danej domeny, flaga gaśnie automatycznie, niezależnie od tego, czy model wywołał `close`.
- **Wykrywanie dryfu tematu** — ten sam lekki, deterministyczny moduł słów kluczowych, który już macie z poprzedniego zadania (routing reguł biznesowych), może dodatkowo służyć jako sygnał "użytkownik zmienił temat" i wymuszać zamknięcie niezwiązanej aplikacji.
- **Twardy limit liczby jednocześnie otwartych aplikacji** (np. 2-3) z wymuszonym zamknięciem najdawniej używanej przy przekroczeniu limitu (LRU) — to ostatnia linia obrony, działająca nawet jeśli TTL i wykrywanie dryfu zawiodą.
- **Idempotentne zamknięcie/otwarcie** — wywołanie `close_notes`, gdy notatki już są zamknięte, nigdy nie powinno być błędem; to bezpieczny no-op.

## 3. Konstrukcja promptu — dyscyplina jako wsparcie, nie jako gwarancja

Zanim przejdę do konkretów, jedno zastrzeżenie zgodne z tym, co ustaliliśmy poprzednio: prompt nie powinien być głównym mechanizmem egzekwowania zamykania — to zadanie należy do warstwy kodu (punkt 2). Rola promptu to zwiększenie *prawdopodobieństwa*, że model zrobi to poprawnie sam z siebie, nie zagwarantowanie tego.

- **Utrzymajcie metaforę biurka konsekwentnie w prompcie** — to już dobrze działająca kotwica dla modelu, warto ją rozwinąć wprost: "Masz ograniczone miejsce na biurku. Możesz mieć otwarte tylko kilka rzeczy naraz."
- **Powiążcie porządek z tożsamością, nie z arbitralną zasadą.** Zamiast suchego nakazu, wpleć sprzątanie w charakter persony (np. Archiwista/Regis, dla którego dbałość o porządek jest naturalnym elementem roli) — to spójne z zasadą kotwiczenia roli, o której pisałem w pierwszym dokumencie: afirmatywna instrukcja związana z tożsamością działa silniej niż goły zakaz.
- **Dajcie konkretny, sytuacyjny wyzwalacz zamknięcia, nie abstrakcyjne przypomnienie.** "Pamiętaj o zamykaniu aplikacji" to zbyt ogólne. Skuteczniejsze: "Gdy użytkownik jednoznacznie zmienia temat na coś niezwiązanego z otwartą aplikacją, zamknij ją, zanim przejdziesz dalej" — konkretny moment decyzyjny, nie ciągły obowiązek do pamiętania.
- **Nadajcie otwarciu jawny koszt w tekście promptu.** Coś w rodzaju: "Otwieranie aplikacji zajmuje miejsce w Twojej pamięci roboczej — otwieraj tylko to, czego aktualnie potrzebujesz." To bezpośrednia przeciwwaga dla ryzyka nadgorliwego otwierania.
- **Few-shot pełnego cyklu** — jeden kompletny przykład: otwarcie → kilka tur negocjacji → rozpoznanie zmiany tematu → zamknięcie, pokazany jako spójna sekwencja, zgodnie z zasadą, że przykład uczy skuteczniej niż sama reguła opisowa.
- **Rozważcie dać modelowi widoczność tego, co ma aktualnie otwarte** — jeden z nowszych kierunków badawczych nad zarządzaniem kontekstem pokazuje, że dawanie modelowi wprost informacji o stanie jego własnej pamięci roboczej (ile jest otwarte, jak długo) poprawia jego zdolność do samodzielnego zarządzania nią, skoro modele domyślnie nie mają takiej percepcji. Praktycznie: krótka linijka statusu w samym bloku stanu, np. "Otwarte: notatki (od 6 tur), oświetlenie (od 1 tury)" — nie jako zamiennik mechanizmów z punktu 2, ale jako uzupełnienie zwiększające szansę, że model sam zamknie coś w porę.

## Tabela podsumowująca

| Element | Odpowiedzialność | Uzasadnienie |
|---|---|---|
| Decyzja "otwórz/zamknij" w normalnym toku | Model (prompt) | To zadanie oceny sytuacyjnej — dobre pole dla silnego 32B |
| Gwarancja, że nic nie zostanie otwarte na zawsze | Kod (TTL, limit, LRU) | Modele nie mają wglądu we własne zużycie kontekstu — nie można polegać na samej pamięci modelu |
| Bezpieczeństwo błędnego zamknięcia | Kod (miękkie zamknięcie, auto-reopen) | Dane źródłowe nie giną wraz z flagą — pomyłka musi być tania |
| Zakres flagi | Kod (per-sesja, nie globalnie) | Zapobiega przeciekowi stanu między rozmowami |
| Widoczność stanu własnej pamięci | Prompt + wstrzykiwany status | Model nie "czuje" swojego zużycia kontekstu z natury — trzeba mu to pokazać jawnie |

## Podsumowanie

Kierunek jest dobry — to rozpoznana rodzina wzorców (paging kontekstu, dynamiczne "wyposażanie" w stan), nie improwizacja. Największe ryzyko nie leży w samej koncepcji otwierania/zamykania, tylko w pokusie, by potraktować dyscyplinę modelu jako wystarczające zabezpieczenie przed "zombie state" — dokumentacja produkcyjna pokazuje, że to najczęstszy powód, dla którego tego typu architektury zawodzą w praktyce. Prompt zwiększa prawdopodobieństwo poprawnego zachowania; twarda gwarancja (TTL, limit jednoczesnych aplikacji, miękkie/odwracalne zamknięcie, zakres per-sesja) musi siedzieć w kodzie, nie w nadziei, że model o tym pamięta.
