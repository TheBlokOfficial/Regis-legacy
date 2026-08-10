# Biblioteka Wiedzy — Regis

Ten katalog zawiera **bazę wiedzy zdobytej w trakcie rozwoju projektu** — analizy konkretnych problemów inżynieryjnych napotkanych przy pracy z modelami LLM w pętli ReAct, architekturą agentową i pamięcią długoterminową.

Dokumenty tutaj **nie są planami do wdrożenia** — to diagnozy przyczyn źródłowych, oceny opcji i rekomendacje architektoniczne. Stanowią rozszerzenie `docs/PROMPT_ENGINEERING.md` o szczegółowe case studies.

---

## Zawartość

### Pętla ReAct i Tool Calling

| Plik | Zagadnienie |
|---|---|
| [`react_parallel_tool_calling.md`](react_parallel_tool_calling.md) | Wymuszanie liniowości pętli ReAct — dlaczego stop token `</tool_call>` jest silniejszą gwarancją niż reguła w prompcie |
| [`react_few_shot_anchoring.md`](react_few_shot_anchoring.md) | Dlaczego few-shot bije regułę deklaratywną — jak projektować kontrastujące przykłady żeby model rozróżniał sytuacje |
| [`react_tool_scaling_context_bloat.md`](react_tool_scaling_context_bloat.md) | Jak rosnąca liczba narzędzi degraduje jakość ReAct — progi degradacji, koszt tokenowy, dynamiczne odkrywanie narzędzi |
| [`react_state_drift_metadata_confusion.md`](react_state_drift_metadata_confusion.md) | ReAct Drift i mylenie warstw danych z metadanymi schematu narzędzi — diagnoza i opcje naprawy |
| [`react_tool_response_formatting.md`](react_tool_response_formatting.md) | Jak formatować `tool_result` żeby model nie traktował pustej odpowiedzi jako "brak wyników" — wzorzec potwierdzenia hybrydowego |

### Architektura i Uprawnienia

| Plik | Zagadnienie |
|---|---|
| [`architecture_tier_permissions_staging.md`](architecture_tier_permissions_staging.md) | Desynchronizacja uprawnień tier vs. promptu — wzorzec staging/proposal jako izolacja operacji nieodwracalnych |

### Pamięć Długoterminowa

| Plik | Zagadnienie |
|---|---|
| [`memory_hitl_consolidation.md`](memory_hitl_consolidation.md) | Human-in-the-Loop konsolidacja pamięci — pattern do przetwarzania surowych faktów przez Regisa z zatwierdzeniem użytkownika |
| [`memory_context_subscription_pattern.md`](memory_context_subscription_pattern.md) | Open/Close Application Paradigm — dynamiczna subskrypcja kontekstu (paginacja pamięci roboczej agenta) i zabezpieczenia przed "zombie state" |

### Modele i Prompt Engineering

| Plik | Zagadnienie |
|---|---|
| [`nlu_qwen_small_model_guide.md`](nlu_qwen_small_model_guide.md) | Praktyczny przewodnik po konfiguracji Qwen 1.5B jako parsera NLU — JSON Schema, few-shot, parametry samplingu, kwantyzacja |

---

## Jak korzystać z tej biblioteki

Sięgaj po konkretny plik gdy:
- Napotykasz problem podobny do opisanego w tytule
- Projektujesz nową funkcję dotyczącą pamięci lub pętli ReAct
- Chcesz zrozumieć "dlaczego tak" za decyzją odnotowaną w `AGENT_GUIDE.md`

Dokumenty są wzajemnie niezależne — możesz czytać każdy osobno bez kontekstu pozostałych.
