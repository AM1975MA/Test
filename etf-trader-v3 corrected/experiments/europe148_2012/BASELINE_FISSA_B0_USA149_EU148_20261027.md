# BASELINE BLOCCATA B0 — ETF Trader: USA149 vs EU148, 27 ottobre 2026

**Stato: TEST CONFRONTABILI RICONCILIATI, NO RETRAINING AGGIUNTIVO in B0.** Il confronto B0 e' esclusivamente dei modelli liberi Top1/Top3/Top5, usando gli originali universi USA149 ed EU148 e **senza i 10 UCITS globali ex-post EU158**.

## Contratto esatto B0

101 date segnale identiche **gennaio 2018–maggio 2026**; 2076 giornate di NAV per scenario, ingresso **1 febbraio 2018** e finale **1 luglio 2026**; tutti i ritorni in EUR, costi unilaterali 10bp come da backtest source, Top1/Top3/Top5 con pesi uguali, filtro as-of originario, nessun fullstack risk layer, FX EUR/USD da dati originali as-of. Calcolati/verificati NAV->CAGR e MaxDD di **9 strategie x 2 universi x 3 cardinalita' = 54 scenari**. Numeric read-only replay delle serie archiviate, NON nuovo fitting dei 9 modelli.

## Top5 CAGR EUR verificato da NAV giornalieri

| Strategia | USA149 | EU148 | gap USA−EU pp |
|---|---:|---:|---:|
| Momentum 21 | 17,72% | 6,70% | +11,03 |
| Momentum 63 | 4,28% | 3,05% | +1,23 |
| Momentum 126 | 11,84% | 4,29% | +7,55 |
| **Momentum 252** | **21,24%** | **6,37%** | +14,87 |
| V3 ranker albero 127 foglie | 13,86% | 3,91% | +9,95 |
| Ridge125 futuro 21 sedute | 19,65% | 4,34% | +15,31 |
| Ridge125 traiettoria 21/42/63 | 19,44% | 3,18% | +16,26 |
| LightGBM futuro 21 sedute | 18,07% | **6,77%** | +11,30 |
| LightGBM traiettoria 21/42/63 | 15,12% | 5,04% | +10,08 |

## Top3 CAGR EUR stesso contratto

| Strategia | USA149 | EU148 |
|---|---:|---:|
| Momentum 252 | 21,07% | 3,87% |
| V3 ranker 127 | 9,72% | 1,78% |
| Ridge125 21 | 16,82% | 3,35% |
| LightGBM 21 | 18,80% | 6,19% |

Top1, tutti Top3, Top5, MaxDD, zero-volume e indicatori sono nel pacchetto dati `ETF_V3_CONFRONTO_FISSO_USA149_EU148_20261027.zip` consegnato nella conversazione. Contiene 3 archivi ORIGINALI dalla sperimentazione, sorgente Python per riconciliazione, 54 esecuzioni verificate sui NAV quotidiani, 5454 rendimenti mensili, bootstrap temporali paired 6 mesi (4000 repliche x 48 confronti) vs momentum252, confronto dei due sottoperiodi e audit predittivo.

## Capacita' predittiva Spearman IC, full

| Scoring | USA149 | EU148 |
|---|---:|---:|
| V3 127 | +0,0343 | +0,0036 |
| Ridge125 P21 | +0,0795 | +0,0240 |
| LightGBM P21 | +0,0656 | +0,0002 |

**Nessun modello complesso Top5 dimostra un vantaggio statisticamente stabile rispetto al momentum252**, con intervalli nominali dei differenziali di crescita logaritmica annualizzata su blocchi temporali di 6 mesi che includono zero. La performance EU esposta presenta problemi execution-data: ben **67** ordini euro Top5 Ridge P21 con volume 0 riportato alla Open, **15** per LGBM P21, **4** per V3 e **15** per momentum252.

## SECONDO INSIEME DA NON CONFONDERE CON B0: USA149 fullstack 500 panieri

Backtest COMPLETO V2, non B0: **500 panieri x 24 ETF USA**, Top2 non equiponderato, sei macro-categorie, Titanium, Hybrid24 Tail, DD-first, V6, HighCAGR24, USD. **2018+ per basket CAGR medio +22,0077%; NAV agreggato equal-capital CAGR +24,7739%.** Inserendo veto math 25% prima del Top2: **+15,9449% medio, +17,7244% aggregato** (PEGGIORAMENTO). [GitHub run fullstack certificato 40473372871](https://github.com/AM1975MA/Test/actions/runs/40473372871), che riproduce l'originale con precisione NAV 1e-13. **EU148 fullstack analogo NON eseguito; nessun valore va inventato.** Panieri USA originali non sono i panieri EU.

## Cosa resta MANCANTE per potere dire «tutte le versioni su entrambi i gruppi»

Ridge16 e modelli dinamici V4 e math-veto erano stati calcolati solo EU (oppure USA in un'altra architettura). Il V2 completo e i 500 panieri hanno origine SOLO USA149. Per la parita' FULLSTACK EU servono: nuovo schema **europeo** 500x24 ex ante a sei categorie, dataset point-in-time certificato dei sottostanti, fasi vintage di Titanium/ExtraTrees/XGB, Tail, V6 e motore esecuzione coerente; modello/basket nuovo e **non** gli stessi identici membri dei panieri USA. Non usare il controllo EUR Top5 per giudicare performance USD 500-basket fullstack.

Il roster EU158 (10 ETF world/US Xetra selezionati oggi) resta **escluso dalla baseline** per ragioni di selezione retrospettiva/survivorship. Storico 2018–26 analizzato ripetutamente, **non holdout vergine**. USA ed EU rimangono universi di esposizioni differenti, quindi calendari/costi uguali non significano causalita' del gap modello vs mercato.

## Fonti riproducibili preesistenti

- [Risultato paired V3 rank127 nel repository](US_EU_TRAJECTORY_LM_VS_RANKING_RESULTS_20261026.md) e base `paired_v3_us149_eu148_economics.zip`.
- [GitHub Actions annual Ridge/LGBM](https://github.com/AM1975MA/Test/actions/runs/40394516018), [economics 101m](https://github.com/AM1975MA/Test/actions/runs/40395611231), archivi `V3_US_EU_SIGNED_TRAJECTORIES_LM_LGBM_20261026.zip`.
- Momentum in `paired_us149_eu148_controls.zip`.
- [Test fullstack original USA V2 e veto](V5_FULLSTACK500_MATH_GATE_NEGATIVE_RESULT_20261027.md).

**Da qui in poi B0 non viene retroattivamente corretto per migliorare CAGR.** Tutte le future versioni devono riportare quali dati/funzioni vengono modificati rispetto a B0, US ed EU separati, Top3/Top5 identici, capability predittiva separata da allocazione e benchmark momentum252.
