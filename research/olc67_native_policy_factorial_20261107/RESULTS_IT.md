# OLC67 — Backtest nativo completo della ricomposizione dei layer ETF
**7 novembre 2026 · Research only · nessuna modifica a OLC19/main · periodo 2019–luglio 2026 già ampiamente esplorato.**

## Risposta
La strategia che supera i criteri di ammissibilità definiti prima dei risultati usa **FUSION originale → TOP2_CONTEXT_REVALUE → minima varianza 63 sedute con cap 25/75 → DELAY3 → V6/FAST_LOCK3**. La combinazione è stata ESEGUITA nel motore contabile nativo, non ricostruita sommando CAGR di esperimenti separati.

| Mercato/finestra | OLC19 B0 CAGR | OLC67 candidato CAGR | Δ CAGR | MaxDD B0 | MaxDD candidato |
|---|---:|---:|---:|---:|---:|
| Europa 2021–2024 | 23,20% | **34,43%** | +11,23 pp | -28,61% | -22,42% |
| USA 2021–2024 | 50,77% | **51,27%** | +0,49 pp | -20,23% | -16,62% |
| Europa FULL | 19,76% | **22,61%** | +2,84 pp | -28,61% | -26,59% |
| USA FULL | 39,48% | **42,10%** | +2,61 pp | -26,12% | -27,60% |

CAGR native = exp(media log rendimento per seduta × 252)−1; MAIN gennaio 2021–dicembre 2024; FULL febbraio 2019–1 luglio 2026 (luglio parziale). Fee legacy coefficient 0,001 e stop friction 0,001; tali coefficienti non sono quotazioni broker reali.

### Anni, costi e cambi di regime
| Anno | EU OLC19 | EU candidato | USA OLC19 | USA candidato |
|---|---:|---:|---:|---:|
| 2019 | 20,11% | 15,28% | 11,29% | 28,60% |
| 2020 | 0,71% | -5,01% | 10,74% | 11,71% |
| 2021 | 21,83% | 28,67% | 24,07% | 39,57% |
| 2022 | -6,30% | 7,31% | 79,11% | 58,11% |
| 2023 | 67,30% | 78,69% | 29,56% | 39,79% |
| 2024 | 22,44% | 35,17% | 78,61% | 68,88% |
| 2025 | 17,95% | 10,15% | 13,57% | 17,83% |
| 2026 * | 16,51% | 15,28% | 62,44% | 52,06% |

*2026 parziale, rendimenti cumulati da gennaio all’inizio di luglio, NON annualizzati. 2025 e 2026 sono stati oggetto di molte analisi precedenti: non sono holdout vergini.*

### Stress dei costi (fee coefficient 0,003)
| Mercato/finestra | Baseline OLC19 | Candidato OLC67 |
|---|---:|---:|
| EU 2021–2024 | 19,88% | 30,72% |
| USA 2021–2024 | 42,73% | 43,60% |
| EU FULL | 16,18% | 18,81% |
| USA FULL | 31,34% | 33,89% |

### Differenziale storico, incertezza e interazione
Il bootstrap circolare a blocchi di 6 mesi descrive il **differenziale di log-rendimento annualizzato**, non la differenza fra CAGR. Sono 6.000 estrazioni (nessuna correzione per molteplici esperimenti OLC precedenti).
| Mercato/finestra | Δ log annuo | IC95% descrittivo |
|---|---:|---:|
| EU MAIN | +8,88 pp | [+5,25, +12,39] pp |
| USA MAIN | +0,33 pp | [-11,89, +12,83] pp |
| EU FULL | +2,35 pp | [-2,26, +6,81] pp |
| USA FULL | +1,83 pp | [-6,55, +10,16] pp |

**Entrambi gli intervalli FULL comprendono zero**. Il nuovo CAGR positivo su entrambi i mercati non prova un beneficio riproducibile fuori campione. La combinazione ha interazione leggermente negativa fra minvar e ritardo: non si possono sommare i loro vantaggi singoli.

## Cosa succede quando massimizziamo soltanto il CAGR storico?
| Politica applicata identicamente in EU e USA | EU MAIN CAGR | USA MAIN CAGR | EU FULL CAGR | USA FULL CAGR | EU FULL DD | USA FULL DD |
|---|---:|---:|---:|---:|---:|---:|
| OLC19 baseline 50/50 IMMEDIATE FAST_LOCK3 | 23,20% | 50,77% | 19,76% | 39,48% | -28,61% | -26,12% |
| Minvar63 + DELAY3 + FAST_LOCK3 (candidato) | 34,43% | 51,27% | 22,61% | 42,10% | -26,59% | -27,60% |
| Minvar63 + DELAY3 + BASE (aggressiva) | 38,06% | 54,36% | 24,52% | 48,97% | -31,94% | -36,67% |
| 50/50 + DELAY3 + BASE (alternativa aggressiva) | 28,86% | 55,83% | 23,55% | 49,97% | -27,71% | -35,90% |

Il massimo CAGR europeo della griglia risulta 38,06% MAIN / 24,52% FULL con Minvar63+DELAY3+BASE. Il massimo USA risulta 55,83% MAIN / 49,97% FULL con 50/50+DELAY3+BASE. Sono due politiche **diverse, individuate a posteriori**; non costituiscono una singola strategia robusta. Disattivare FAST_LOCK3 porta il MaxDD FULL USA verso −36%/−37%, contro −26,12% baseline. Il protocollo aveva escluso in anticipo questa regressione del rischio.

## Test completi (8 politiche, 2 mercati) fee 0,001
| Pesi | Esecuzione | Rischio | EU MAIN | USA MAIN | EU FULL | USA FULL | EU DD FULL | USA DD FULL |
|---|---|---|---:|---:|---:|---:|---:|---:|
| HALF | IMMEDIATE | FAST_LOCK3 | 23,20% | 50,77% | 19,76% | 39,48% | -28,61% | -26,12% |
| HALF | IMMEDIATE | BASE | 22,23% | 50,55% | 19,71% | 43,59% | -28,37% | -32,00% |
| HALF | DELAY3 | FAST_LOCK3 | 28,11% | 55,31% | 22,05% | 43,26% | -28,65% | -30,40% |
| HALF | DELAY3 | BASE | 28,86% | 55,83% | 23,55% | 49,97% | -27,71% | -35,90% |
| MINVAR63 | IMMEDIATE | FAST_LOCK3 | 29,31% | 47,73% | 20,84% | 38,98% | -23,76% | -25,23% |
| MINVAR63 | IMMEDIATE | BASE | 30,88% | 47,22% | 21,22% | 41,86% | -31,58% | -33,90% |
| MINVAR63 | DELAY3 | FAST_LOCK3 | 34,43% | 51,27% | 22,61% | 42,10% | -26,59% | -27,60% |
| MINVAR63 | DELAY3 | BASE | 38,06% | 54,36% | 24,52% | 48,97% | -31,94% | -36,67% |

## Verifiche
- 32 replay nativi = 8 politiche × 2 mercati × 2 coefficienti costo, nessun tuning aggiuntivo dopo i risultati.
- Controllo esatto, sette matrici contabili OLC19 (EU e USA) nel braccio HALF/IMMEDIATE/FAST_LOCK3 fee0.001; parità con gli archivi OLC56 per i bracci isolati MINVAR63 e DELAY3 (MAIN/FULL, entrambe le commissioni), con confronto del diario giornaliero OLC56 per HALF/DELAY3.
- Ricalcolo **indipendente** dei 160 valori CAGR e MaxDD da file giornalieri, su 32 percorsi × 5 finestre, verificati entro 1e−10.
- Controllo original source ZIP SHA256 OLC19: `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`; OLC56: `f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573`.
- L’unica variante nuova che supera **tutti** i criteri fissati prima dei test è MINVAR63+DELAY3+FAST_LOCK3, oltre alla baseline per definizione. I criteri erano: FULL CAGR non inferiore in entrambi; FULL MaxDD non peggiorato più di 3pp in alcuno; MAIN CAGR non inferiore in entrambi.

## Decisione
**Promuovere a candidato per paper/shadow testing, NON al trading live.** Migliora il CAGR retrospettivo in entrambi i mercati, con rischio storicamente contenuto, ma beneficia di un decennio di ricerca sullo stesso periodo; FULL bootstrap include zero, gli USA 2021–2024 hanno vantaggio marginale e nel 2025 l’Europa sottoperforma. Mancano prezzi/stop realmente eseguibili, point-in-time dell’universo, original quote mask USA, omogeneità adjusted/total-return e validazione temporalmente nuova.

**Nessuna nuova modifica** a `main`, OLC19 e operatività. Per usare la combinazione in simulazione va ripristinato il contratto OLC19/OLC56 dal checkpoint, senza scegliere manualmente pesi sui risultati.

### Riproduzione
Archivi originali richiesti nella Library: OLC19_Rischio_Rientro_Checkpoint_20261102.zip e OLC56_TESTS_20261106_VERIFICATI.zip. Copiarli nei percorsi attesi o aggiornare `extract_inputs.py` e `run_olc67.py` per risolverli in altro posto; non alterare parametri o dataset.
```bash
python extract_inputs.py
python run_olc67.py
python validate_and_summarize.py
python make_report.py
```
