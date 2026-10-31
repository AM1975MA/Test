# Audit debolezze V5 — 31 ottobre 2026

Research only, no production changes. Controlli indipendenti su `prepare_v5.py`, `fit_v5.py`, `replay_v5.py`, `source_v4/run_v4_clean.py` e tabelle congelate. Non è un nuovo backtest di rendimento.

## Priorità A — dimostrare alpha e non semplice esposizione beta

2021–24, cinque selezioni mensili LightGBM V5: rendimento **previsto** a 21 sedute +2,03% componente fattoriale, +0,12% componente ETF residuale; **94,4% della previsione** proviene dai fattori. Correlazione mu totale/fattori **0,992** sull'intero pannello 2021–24. Aggiungere V2/V3 allo stesso LightGBM produce **22,03% CAGR contro 22,06% senza ranker**, differenza log-return annualizzata -0,032pp, CI [-0,764,+0,698]pp. Rendimento non attribuibile a V2/V3 nel modello corrente.

V5 slot extra-Europa per anno 2021/22/23/24 = **7,3/58,2/96,7/65,0%**; V3 Pair25 corrispondente **12,7/5,5/15,0/35,0%**. La classificazione è metadata 2026, non storica PIT certificata. Principali sottostanti V5 includono USA technology, World semiconductors e Nasdaq 100.

**Rimedio:** benchmark-clone ex ante dello stesso fattore, industry, geographic beta, volatility e MA200; aggiungere settori tecnologia, semiconduttori, FX e duration a proxy fattoriali PIT; confrontare excess return factor neutral NET dei costi, non il solo CAGR.

## Priorità A — rischio realmente diversificato

Ricalcolate correlazioni dei cinque ETF selezionati sulle **63 precedenti** sedute. 2021–24 correlazione media V3 **0,610**, V5 **0,796**. Nel 2023 V5 **0,870**, effective-number-of-bets (mean individual variance / portfolio equal-weight variance) **1,18**, contro V3 1,58. Le cinque posizioni V5 non sono cinque esposizioni indipendenti.

**Rimedio:** shrinked cross-ETF/factor covariance, risk-contribution budgeting, CVaR e scenario shock, non un ETF per macrocluster arbitrario; permettere concentrazione solo per rendimento **residuo** credibile net cost. Benchmark a stessa covarianza.

## Priorità A — previsioni troppo deboli

IC 2021–24 V5 LightGBM con V2/V3 a 21/42/63 sedute = **+.0158/-.0255/-.0152**, alpha residual IC **-.0133/-.0064/-.0012**. 2023–24 AUC P(batte EXSA after 20bps) ~.516, Brier .2489 vs prior-baseline .2486 a 21 giorni. Bande nominali 80% coprono circa **90%**: eccessivamente larghe. Il motore usa quasi soltanto 21d; 42/63d non guidano la decisione e sono poco predittivi.

**Rimedio:** definire distribuzioni `R_candidate - R_incumbent - costs` e `R_candidate - R_passive - costs` su 21/42/63d; calibrarle su soli errori OOS precedenti con label maturate; richiedere miglioramento Brier/pinball/CRPS e uplift netto prima di allocatore di portafoglio.

## Priorità B — insufficienza storica del fit dei fattori

2021: regressioni dei 4 fattori addestrate su soltanto **21 mensilità** a 21d (20 a 42/63d) e cinque feature; le circa 1900 osservazioni ETF del secondo stadio sono fortemente correlate per data. Beta 126 giorni con mancanze fattoriali sostituite da 0 (`f.fillna(0)`) e returns ETF assenti sostituiti da 0 (`y0`): rischi di distorsione.

**Rimedio:** estendere solo con dati realmente disponibili e timestamp PIT; masked/weighted beta estimation, regularizzazione e shrinkage gerarchico; confronto diretto contro random walk, zero forecast, momentum lungo ed EWMA e poi eventualmente Kalman one-sided. Valutare anno per anno, non solo NAV.

## Priorità B — allocator non economico

Il portafoglio Top5 è obbligatorio, equiponderato e ribilanciato ogni mese; non ha un vero HOLD/SWITCH con stima di costi/incer­tezza e non possiede la possibilità di scegliere EXSA, SXR8 o liquidità come **outside option**. Il filtro rischio è soltanto EXSA 200d MA, non adatto da solo quando l'esposizione V5 è quasi interamente USA/tech.

**Rimedio:** decisione condizionale alla posizione endogena e al benchmark passivo; vincoli di cost/turnover/CVaR e probabilità di battuta del benchmark calibrate; nessun trade attivo se la previsione alpha non supera il controllo robusto.

## Priorità B — dati e codice

EU165 è l'insieme di ETF sopravvissuti e identificati nel 2026; prezzi price-only, dividendi e corporate actions non certificati, bid/ask e delisting storici mancanti. Nel replay:
- il valore -1e6 assegnato a score V5 mancante è **finito** e passa `np.isfinite` del successivo `run_v4_clean.py` (falla potenziale se shortlist ridotta);
- fallback V5→V3 silenzioso quando mancano i punteggi di un mese (voluto nel warmup 2019–20, ma da loggare e vietare come comportamento nascosto dopo 2020);
- `run_v4_clean.py` richiede anche il Close del giorno di trading nel filtro `base` (dato non noto al momento di decidere al successivo Open). Il valore è peraltro ffilled, ma occorre rimuovere qualsiasi dipendenza di selezione dalle informazioni post-apertura e misurare il replay differenziale;
- stale Close sulle posizioni V5 selezionate 2021–24: 24 di 5030 slot-giorni (0,48%), marginale in frequenza ma non da nascondere.

**Rimedio:** input total return in EUR con universo realmente PIT, controlli di negoziazione solo su osservabili al momento dell'ordine, fail-closed su score mancanti, versioning di fallbacks e fonte di prezzo, suite di unit test per calendar/market closures.

## Dati esplorati e next gate

La V5 vera inizia nel **2021**; nel 2019–20 il portafoglio etichettato V5 era un warmup V3. Risultati V5 LightGBM a 21d: CAGR **+1,44%** 2021–22, **+43,96%** 2023–24, **+20,02%** 2025. Delta annualizzato V5 vs V3 sul 2021–24 +5,45pp, 6m bootstrap CI [-2,49,+13,50]pp: non robusto, tanto più dopo lo sfruttamento ripetuto dello storico.

**Priorità operativa di ricerca:** (1) ripulire TR/PIT e accounting, (2) costruire clone passivo con fattori/tech/semis/FX/rischio uguali al V5, (3) falsificare alpha residuale con baseline semplici e 21/42/63, (4) solo se positivo costruire un ottimizzatore distribuzionale HOLD/SWITCH con opzione passiva; (5) validare su una futura vintage non utilizzata. Niente tuning retrospettivo per inseguire CAGR storico.

Il rapporto dettagliato analitico è `ETF_TRADER_V5_AUDIT_PUNTI_DEBOLI_20261031.md` (artifact ChatGPT), non duplicato nei dati grezzi. Nessuna variazione al codice o al NAV congelato.