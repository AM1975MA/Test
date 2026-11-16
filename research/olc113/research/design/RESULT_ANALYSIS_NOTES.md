# OLC113 — lettura indipendente dei risultati

**PRICE_RESET non soddisfa il criterio prefissato di miglioramento materiale.** Il CAGR completo è 24.16% contro 22.57% di BASE (+1.59 punti percentuali); il MaxDD campionato è -36.51% contro -36.51%. Nel periodo comune il differenziale di CAGR è +2.41 punti. La soglia economica richiede almeno +3 punti di CAGR e MaxDD non peggiore in entrambe le finestre; il 30% resta un obiettivo separato.

## Conti nella convenzione principale

| Conto | CAGR completo | MaxDD completo | CAGR comune | MaxDD comune | Giorni cash | Reset cash con acquisti | Costi EUR |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE | 22.57% | -36.51% | 20.01% | -36.51% | 0 | 0 | 4029.40 |
| STATIC_75 | 18.38% | -30.08% | 16.53% | -28.64% | 0 | 0 | 2633.73 |
| MEAN_RESET | 22.57% | -36.51% | 20.01% | -36.51% | 0 | 0 | 4029.40 |
| PRICE_RESET | 24.16% | -36.51% | 22.42% | -36.51% | 29 | 5 | 4713.87 |
| VIX_RESET | 16.92% | -36.52% | 11.59% | -36.52% | 81 | 10 | 4526.43 |
| TERM_RESET | 22.26% | -37.53% | 19.54% | -37.53% | 110 | 11 | 4741.28 |

Periodo completo: 2020-03-02–2026-10-30; capitale iniziale EUR10.000. Periodo comune: 2022-07-04–2026-10-30, ancorato per ciascun conto alla sua chiusura effettiva del 2022-07-01.

## Confronti e criterio materiale

| Conto principale | Delta CAGR vs BASE, completo | Delta CAGR vs BASE, comune | Delta MaxDD completo | Delta MaxDD comune | Criterio in entrambe | CAGR completo >=30% |
|---|---:|---:|---:|---:|---|---|
| MEAN_RESET | +0.000 pp | +0.000 pp | +0.0000 pp | +0.0000 pp | No | No |
| PRICE_RESET | +1.591 pp | +2.409 pp | +0.0017 pp | +0.0017 pp | No | No |
| VIX_RESET | -5.651 pp | -8.417 pp | -0.0075 pp | -0.0075 pp | No | No |
| TERM_RESET | -0.312 pp | -0.471 pp | -1.0135 pp | -1.0135 pp | No | No |

Un delta MaxDD positivo indica una perdita massima meno profonda. Il nome primario resta PRICE_RESET; VIX_RESET e TERM_RESET sono secondari.

## Riparazione del rientro

| Conto | Reset cash emessi | Reset con acquisti | Tentativi differiti per quote | Spell cash massimo | Spell chiusi dal reset |
|---|---:|---:|---:|---:|---:|
| MEAN_RESET | 0 | 0 | 0 | 0 | 0 |
| PRICE_RESET | 5 | 5 | 0 | 11 | 5 |
| VIX_RESET | 10 | 10 | 0 | 15 | 10 |
| TERM_RESET | 11 | 11 | 0 | 21 | 11 |

Il controllo verifica i flag del trace, il target originale, force=False, il segnale mensile, la successiva eleggibilità di esecuzione, gli acquisti effettivi e la fine dello spell cash. Uno spell non è respinto perché supera 21 sedute: contano il calendario mensile effettivo e le eventuali istruzioni in attesa/quote mancanti. Il cambio ripristina la continuazione mensile anche dal cash; non rende tutta la policy ripetuta uguale alla banca di interventi singoli.

## Effetto rispetto a OLC112

| Conto | Delta CAGR completo | Delta CAGR comune | Delta MaxDD completo | Cash completo, nuovo / precedente |
|---|---:|---:|---:|---:|
| MEAN_RESET | +0.00 pp | +0.00 pp | +0.000 pp | 0 / 0 |
| PRICE_RESET | +8.26 pp | +12.32 pp | +0.011 pp | 29 / 215 |
| VIX_RESET | +4.07 pp | +5.93 pp | +0.007 pp | 81 / 344 |
| TERM_RESET | +0.81 pp | +1.22 pp | -1.424 pp | 110 / 243 |

## Sensibilità ai costi ed esecuzione

| Conto | Scenario | CAGR | MaxDD | CAGR comune | MaxDD comune | Criterio entrambe |
|---|---|---:|---:|---:|---:|---|
| MEAN_RESET | NEXT_CLOSE | 22.57% | -36.51% | 20.01% | -36.51% | No |
| MEAN_RESET | DOUBLE_COST | 19.71% | -38.31% | 17.26% | -37.10% | No |
| MEAN_RESET | NEXT_OPEN | 25.75% | -37.92% | 23.23% | -36.00% | No |
| PRICE_RESET | NEXT_CLOSE | 24.16% | -36.51% | 22.42% | -36.51% | No |
| PRICE_RESET | DOUBLE_COST | 20.84% | -38.31% | 18.96% | -37.10% | No |
| PRICE_RESET | NEXT_OPEN | 25.55% | -37.92% | 22.94% | -36.00% | No |
| VIX_RESET | NEXT_CLOSE | 16.92% | -36.52% | 11.59% | -36.52% | No |
| VIX_RESET | DOUBLE_COST | 13.26% | -38.31% | 7.67% | -37.13% | No |
| VIX_RESET | NEXT_OPEN | 20.04% | -37.92% | 14.72% | -36.00% | No |
| TERM_RESET | NEXT_CLOSE | 22.26% | -37.53% | 19.54% | -37.53% | No |
| TERM_RESET | DOUBLE_COST | 18.98% | -38.31% | 16.15% | -38.28% | No |
| TERM_RESET | NEXT_OPEN | 26.38% | -37.92% | 24.19% | -37.23% | No |

Il ritorno alla convenzione Open è una sensibilità con il limite noto di disponibilità derivata dal volume giornaliero completato. Non dimostra eseguibilità reale all’apertura. Le tabelle JSON includono esplicitamente eventuali inversioni del guadagno con costi doppi.

## Anni e interventi

| Anno | PRICE_RESET | BASE | Differenza semplice | Incremento log |
|---|---:|---:|---:|---:|
| 2020 | 70.29% | 70.29% | +0.00 pp | +0.000000 |
| 2021 | -14.88% | -14.88% | +0.00 pp | +0.000000 |
| 2022 | 30.48% | 31.51% | -1.02 pp | -0.007806 |
| 2023 | 37.70% | 26.07% | +11.63 pp | +0.088277 |
| 2024 | 29.06% | 27.65% | +1.41 pp | +0.010967 |
| 2025 | 40.22% | 44.38% | -4.17 pp | -0.029296 |
| 2026 | -10.25% | -12.36% | +2.11 pp | +0.023824 |

I differenziali annuali semplici non sono sommabili. Gli incrementi log descrivono i conti osservati; non identificano un profitto causale isolato del singolo reset.

| Conto | CASH: eseguiti / separati completi | FRESH: eseguiti / separati completi | ENTRY: eseguiti / separati completi |
|---|---:|---:|---:|
| MEAN_RESET | 0 / 0 | 0 / 0 | 0 / 0 |
| PRICE_RESET | 5 / 4 | 8 / 7 | 0 / 0 |
| VIX_RESET | 10 / 6 | 18 / 10 | 0 / 0 |
| TERM_RESET | 11 / 7 | 3 / 2 | 0 / 0 |

I reset mensili sono conteggiati separatamente da ENTRY. Il numero di episodi con 21 sedute complete e separazione temporale è un controllo di supporto, non una garanzia di indipendenza.

## Verifiche e limiti

- complete12_new_paths_and6_existing_controls: PASS.
- all12_rotation_predecessors_compared: PASS.
- unchanged_protocol_code_data_and81_saved_fit_files: PASS.
- all12_path_receipts_valid: PASS.
- identical_complete_daily_and_trace_calendars: PASS.
- whole_post_metric_parity: PASS.
- exact_warmup_all12_paths: PASS.
- mean_exact_base_daily_and_orders_all_scenarios: PASS.
- account_reconstruction_all18_paths: PASS.
- held_quote_support_all18_paths: PASS.
- trace_account_state_reconciliation_all18_paths: PASS.
- fees_execution_prices_and_prefee_nav_all18_paths: PASS.
- monthly_cash_reset_contract_all12_paths: PASS.
- saved_forecast_hashes_all12_paths: PASS.

L’audit ricostruisce quantità, cash, costi, prezzi eseguiti e NAV prima dei costi e a chiusura; applica il limite di cinque giorni di calendario alle fonti dei prezzi detenuti. MEAN_RESET è confrontato esattamente con tutti i campi giornalieri e l’intero registro ordini BASE, in ciascuno scenario. Sono verificati protocollo, codice finanziario, dati, 81 file di modelli e ricevute complete dei 12 percorsi.

**L’audit non ha addestrato modelli, scelto nuove policy o rieseguito strategie finanziarie.** Tutti i risultati provengono dai registri congelati. Gli hash di ogni fonte e del codice di audit sono in `INDEPENDENT_SOURCE_MANIFEST.json`.

- Adaptive mechanism ablation on repeatedly inspected history; no untouched holdout.
- Scheduled reentry repair does not change the failed OLC111 incremental-information forecast evidence.
- Concurrent BASE and predecessor comparisons describe recorded accounts, not prospective or isolated causal alpha.
- Repeated policy continuation still differs from a one-intervention21-session bank.
- Calendar months and quote deferrals prohibit a universal21-session cash-spell cap.
- Separated completed intervention counts establish temporal support only.
- Current catalog, survivorship, adjustment vintage and next-Open availability limitations remain.

Fonti: `INDEPENDENT_DIAGNOSTICS.json`, `INDEPENDENT_SCORES.csv`, `INDEPENDENT_CRITERIA.csv`, `INDEPENDENT_MONTHLY_CASH_RESETS.csv`, `INDEPENDENT_CASH_SPELLS.csv`, `INDEPENDENT_ANNUAL_COMPARISONS.csv` e i registri originali identificati nel manifesto.
