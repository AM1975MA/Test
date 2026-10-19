# ETF Trader V2, USA149 libero — ADAPT4 congelato da EU48, 20 ottobre 2026

## Obiettivo e vincoli
Replicare sul **singolo universo di tutti i 149 ETF americani** il medesimo modello ADAPT4 già testato sugli ETF europei: NON 500 portafogli bilanciati da 24 strumenti, NON 4 ETF obbligatori per categoria. Tutti 149 possono essere selezionati top1/top2 ogni mese. No trading dell'ETF prima che esistano i suoi prezzi reali. Repository production AM1975MA/Etf_trader intatto.

## Stato dati e source
- Il workflow di preflight #39337455843 ha confermato 149 ticker dell'originale archived yfinance data (Github Actions artifact run 36551650325, 25.9MB), esattamente categorie 25/25/25/24/25/25.
- 2924 sessioni **effettivamente comuni** e presenti in tutte le quotazioni originali, 2014-11-12–2026-07-01, 538 ante-2017 per warmup e 1379 dal 2021. Non usare dati sintetici o fill; per costanza/fedeltà ai 149 candidati usa il calendario di intersezione. OHLC incoerenti: ZERO, nessuna correzione.
- Modelli Titanium source-only e MA3 Hybrid24 genuine yearly annual re-fit sui 149 ETF, 2021–2026 con date maturity per il fit e previsioni all-ETF di ogni mese. Per formazione/training segnali 2017–2020 con etichette già mature. 65 segnali eseguibili gennaio2021–maggio2026, 1360 daily open marks USA 2021-02–2026-07. Macro SPY/HYG/IEF, cash BIL/SHV, feature USD originali, senza sostituzioni EU.
- Originale Titanic anno e original ensemble MA3 source repo frozen identici, ricreati da source 149 raw originale, non riutilizzati i punteggi di 500 basket. Elaborazione dei cluster MA3 con S3B originale 149 + sue categorie/seed source, non l'adapter 5+1 europeo.

## Identità ADAPT4 esattamente congelata
In Europa ADAPT4 combinava quattro expert cross-sectional percentile ranks: MA3 originale, Mom21, Mom126, Ridge trained trailing36 mature months. In USA si riaddestra ciascuno sul medesimo universo 149 (soprattutto Ridge a standard scaler e alpha40), non si riciclano i pesi stimati in Europa. I pesi online vengono applicati con **ultimi 12 mesi i cui exit date sono strettamente precedenti al segnale**, reward 0.5 signed Spearman + 0.5 Top5 realized forward log excess over EW149 / within-month dispersion, softmax temperature4 e floor10% per ciascuno, equal25% se meno di 6 mesi maturi; stessa versione e codice/version SHA in RESULT.json. Calcolo da Signal Close fino alla prossima Open realmente tradabile, mai forward close.

No diversa ricetta fitting al raggiungimento del risultato, benchmark ALWAYS real 149 unrestricted MA3.

## Risultati initial real model fits (dal Github Action #39337711855: output scientifico completo già generato, primo processo fallì unicamente il post-run guard per .first method name collision, risolto in workflow successivo #39338133099)

| Metodo all-149 (one portfolio) | CAGR netto dopo fonte V2 risk DD-first/V6 10bp stop5.5% | MaxDD | Sharpe | Turnover ann |
|---|---:|---:|---:|---:|
| ORIGINAL MA3 Hybrid24, tutti149 | **+10.5061%** | -47.5140% | +0.4610 | 13.2017 |
| ORIGINAL MA3 + V2 concentrator, tutti149 | **+10.4792%** | -47.5140% | +0.4603 | 12.9644 |
| **ADAPT4 + FULL source V2**, tutti149 | **+29.1748%** | **-38.8694%** | **+0.9749** | **14.8110** |
| ADAPT4 + Hybrid24 WITHOUT incremental V2 concentrator | +29.1748% | -38.8694% | +0.9749 | 14.8110 |
| Original MA3 Top2 without risk/stops, 10bp | +11.5499% | -42.5500% | +0.4782 | 10.2749 |
| ADAPT4 Top2 without risk/stops, 10bp | +25.2582% | -42.3820% | +0.8406 | 10.8762 |
| Original MA3 Top5 equal 20% each without stop, costed10bp | +23.2557% | -29.9360% | log Sharpe ~0.7494 | |
| ADAPT4 Top5 equal 20% each without stop, costed10bp | **+27.8971%** | **-24.1918%** | log Sharpe ~0.8997 | |

**+18.6956 punti di CAGR** e **+8.6447 punti di drawdown in meno** per full V2 in un unico universo USA149 rispetto alla medesima strategia originale. Nessun effetto incrementale del concentratore V2 con nuovo ranking (come in EU48): il beneficio viene dalla nuova selezione dei titoli, non dalle regole extra V2.

NOTA statistica: il delta di Spearman medio signed mensile ADAPT4-MA3 su 65 = **+0.0210**, circular block-bootstrap 3 mesi CI95 **[-0.0310,+0.0752]**; delta Top5 mean forward log excess / mese +0.0034556 (0.346 punti per mese) CI95 **[-0.00802,+0.01445]**. Entrambi comprendono ZERO. Inoltre lo stesso campione 2021–26 e la famiglia ADAPT4 4-expert già sono stati selezionati dopo osservare 2021–26 EU48: validazione cronologica ma NON prospettica/cieca e rischio di overfitting research-wide. I 149 fondi sono 2026 survivors, no contemporaneous PIT membership. NON dire +18.7pp alpha causalmente dimostrato.

La media USA500 historical +24.897% 2017–26 è CAGR medio di 500 portafogli da 24 ETF e NON è il benchmark stesso-periodo/universe, quindi non confrontarlo direttamente col 29.17%. USA149 unrestricted MA3 contemporaneo è +10.479%, benchmark appropriato per questo esperimento.

## Controlli e file
- Pre-flight completed successful run https://github.com/AM1975MA/Test/actions/runs/39337455843 .
- Original model+V2 fit produced all result JSON/CSV successfully in run https://github.com/AM1975MA/Test/actions/runs/39337711855 , ma final assertion aveva errore tecnico di attributo dataframe per il guard (nessun errore nel risultato: JSON completo già verificabile nei logs).
- Retry con hard guard corretto: https://github.com/AM1975MA/Test/actions/runs/39338133099 .
- research_reset/us149_adapt4_free/PREREGISTERED_20261020.md frozen design.
- research_reset/us149_adapt4_free/prepare.py archived raw source mapping, timestamps, SHA, category list, no ffill.
- research_reset/us149_adapt4_free/run.py genuine yearly fitting Titanium+MA3 S3B, Ridge36, ensemble online weights and true v6.simulate_with_alt no 500 basket.
- Quando workflow green: results/RESULT.json , SOURCE_ORIGINAL_US149 quote quality, TITANIUM_RETRAIN_AUDIT.json, weekly monthly leader/ADAPT scores, 65-month maturing-label Ridge fit audit, 1360 daily equity curves and checksum SHA256_MANIFEST.

## Raccomandazione
**Ricerca promettente, production gate chiuso.** Non applicare azioni live. Confermare su nuovo arco dati PIT, gruppi settoriali e market regimes, e auditare US equity 2025 regime/turnover. Non risintonizzare pesi dopo i risultati.


## FINAL SUCCESS and independent after-run recomputation from archived 1,360 daily NAV rows

The final workflow run https://github.com/AM1975MA/Test/actions/runs/39338133099 is **completed SUCCESS**, all gates passed and reports/CSV/SHA256 committed under results/. One single 149 ETF basket confirmed and no category quota applied, genuine data source 2924 historic Open dates, 538 warmup pre2017. Full source refit rather than historical weights reuse. Original MA3 10.47935% CAGR (minor 0.00014 percentage point run-to-run rounding/training variability from preliminary 10.47922%, not a scientific change), ADAPT4 29.17477%.

### Actual annual year-end net wealth returns, from saved NAV 1360 date rows (not signal-year regrouping!)

| Civil period | Original MA3 USA149 FULL V2 | ADAPT4 USA149 FULL V2 |
|---|---:|---:|
| **2021 Feb–Dec (partial)** | -26.44% | +42.92% |
| 2022 | +11.49% | +21.06% |
| 2023 | +2.46% | **-19.28%** |
| 2024 | **+45.61%** | **-0.01%** |
| 2025 | +14.33% | **+79.12%** |
| **2026 Jan–Jul 1 (partial)** | +22.41% | **+59.15%** |

The variability across years is extreme. Adaptive outperformance is neither monotonic nor guaranteed: **in 2023 and 2024 the old MA3 was substantially better**. ADAPT4 has strong retro returns in 2021/2025/2026, may be driven by a few high-beta winners. Original MA3 top1 historically KWEB 9, GDXJ 6, SOXX 5, GDX 5; adaptive top1 UNG 7, URA 6, EPOL 4, ARGT 4, TAN 3, GDX 3. This source market contains highly volatile natural gas, uranium and thematic sector ETFs. Not equivalent to strictly Europe ETF opportunity/risk profile.

### Predictive diagnostics independent of CAGR

Signed rank Spearman original MA3 across 65 monthly cross-sections: **+0.02864**; ADAPT4 **+0.04967**. Difference +0.02103 with three-month circular bootstrap confidence interval [-0.03098,+0.07520]. Original Top5 next-month log excess vs equal149 mean **+0.9554% each month**, ADAPT4 **+1.3009% each month**, difference **+0.3456 monthly points**, bootstrap [-0.8015,+1.4452 monthly points], thus not statistically significant. Both methods have 37/65 months with positive Top5 excess. Historical source 10bps Top5 cumulative risk method ADAPT4 27.8971% CAGR versus old 23.2557%; MaxDD improved from -29.936% to -24.192%; this is a genuine all149 top5, no V2 stops. Full original V2 risk+stops 29.1748% vs old 10.4794%, MaxDD -38.869% vs -47.514%.

Important: 2021–2026 final full horizon is reused from prior research; the block bootstrap does **not** correct multiple-experiment selection bias, 149 survivor universe bias, or implementation execution spreads. The risk regime may benefit ADAPT4 but volatility remains high. No claim independent future alpha until prospectively unseen dates and PIT roster.

Archived evidence:
- https://github.com/AM1975MA/Test/tree/research/us149-adapt4-unrestricted-20261020/research_reset/us149_adapt4_free/results
- GitHub SUCCESS https://github.com/AM1975MA/Test/actions/runs/39338133099
- 149_UNRESTRICTED_PREDICTIVE_MONTHLY_RANK_SKILL.csv
- ORIGINAL_SOURCE_V2_US149_ONE_FREE_UNIVERSE_DAILY_NAV.csv
- ORIGINAL_SOURCE_US149_65_MONTH_ONE_FREE_UNIVERSE_LEADERS.csv
- ADAPT4_MONTHLY_LEARNED_WEIGHTS_PREVIOUS12_ONLY.csv
- TITANIUM_RETRAIN_AUDIT.json
- ORIGINAL_SOURCE_AUDIT.json
- SHA256_MANIFEST.txt
