# OLC46 — Bonifica storici OHLC, identità PIT degli ETC e gate per OLC44 nativo

**4 novembre 2026. Stato: audit dati riproducibile, bonifica senza valori inventati, gate modelli parzialmente superato. NON eseguito un nuovo OLC19 nativo.** Lavoro isolato in `research/olc46-price-reconciliation-20261104` su `AM1975MA/Test`. `Etf_trader`, EU165 e USA149 ufficiali non sono stati modificati.

## Sintesi semplice

1. Abbiamo separato i dati verificabili da quelli incoerenti. Non è lecito sostituire i massimi/minimi con la massima/minima di Open e Close, perché può creare stop fittizi. Perciò nelle nuove serie **Open/Close originali restano**, High e Low sono marcati `NaN` quando la quadrupla OHLC non è coerente, e la riga originaria resta in `bad_bar_audit.csv`. Le nuove serie sono destinate a **feature Open/Close** e QA; **non** sono state promosse come prezzo eseguibile intraday.
2. Nel periodo 2017-01→2026-07, 743 barre problematiche per `PHAG.MI`, `NGAS.MI`, `CMOD.MI`. **Tutte 743 sono esclusivamente `Close` fuori dai limiti High–Low; nessun `Open` fuori e nessun `Low>High`.** È possibile una differenza di definizione fra chiusura ufficiale/asta e range negoziato, non è dimostrato che il singolo High/Low sia sbagliato.
3. La funzione Yahoo `repair=True` è stata eseguita *con scipy installato* e non ha corretto nessuna delle 743 barre. Seconda sede e Stooq non hanno fornito una valida fonte indipendente **stessa venue** su cui sostituire gli High/Low. `PHAG.AS` non è sicura come serie sostitutiva: gap assoluto fra Close cross-venue a p95 44,4%, e correlazione dei log-rendimenti giornalieri 0,429; non si fanno backfill basati su tale serie.
4. **Nuova verifica critica: contratto Natural Gas 1783:1.** RNS 27 ottobre 2023, WisdomTree `GB00B15KY104` ultima giornata di negoziazione **1 dicembre 2023**, sostituito da `JE00BN7KB334` dal **4 dicembre 2023**, **1783 vecchie unità per una nuova**. L'ISIN corrente **NON può essere retroattribuito al 2021–2022**. La serie Yahoo storica può essere back-adjusted sul nuovo nominale; mai simulare acquisti e unità precedenti ignorando l'evento. Tutte le 5 altre classi annunciate nell'RNS sono registrate in `ETC_2023_CONSOLIDATIONS_PIT.csv`.
5. **OLC44 gate previsionale:** 7 nuovi ETF (4 UE, 3 USA) dispongono di Open/Close e di una finestra integra High/Low di 252 sedute per **48/48** mesi 2021–24. I tre strumenti `PHAG.MI,NGAS.MI,CMOD.MI` hanno Open/Close 252 sedute in 48/48 mesi ma **nessuna** finestra 252 full-OHLC coerente (0/48). È quindi possibile riprendere lo studio native `UCITS-only` separatamente dagli ETC.
6. Il gate di ricostruzione *realmente nativa* OLC14 ha trovato i tre moduli sorgente e i parametri originali nell'albero di GitHub, ma **non** 6 file binari di input / parità: pannelli annuali 42-feature 2021 EU+USA, etichette training annuali, score originali OLC14. Sono in archivi della Library, non nel checkout GitHub. Riuscire a scaricare prezzi non equivale a ricostruire quella pipeline.

## Data-quality report automatico

| Linea | Barre 2017–2026 | Incoerenti | % | Mediana gravità del Close fuori range | 95° percentile |
|---|---:|---:|---:|---:|---:|
| PHAG.MI, argento | 2410 | **109** | **4.52%** | 6.20 bp | 25.45 bp |
| NGAS.MI, gas | 2410 | **95** | **3.94%** | 36.10 bp | 132.11 bp |
| CMOD.MI, commodity aggregate | 2400 | **539** | **22.46%** | 11.94 bp | 67.05 bp |

Scomposizione per tipo di errore:

| Linea | Close > High | Close < Low | Open fuori range |
|---|---:|---:|---:|
| PHAG.MI | 61 | 48 | **0** |
| NGAS.MI | 74 | 21 | **0** |
| CMOD.MI | 253 | 286 | **0** |
| TOTALE | **388** | **355** | **0** |

I prezzi originali non sono sovrascritti. `repair_and_crosscheck.py` conferma automaticamente uguaglianza esatta di Open/Close originali e mascheramento di High/Low su ogni barra classificata non coerente. Nessuno dei tre strumenti è approvato per un replay intraday completo mentre mancano prezzi indipendenti. Un backtest non può saltare soltanto le giornate *future* che risultano difettose: sarebbe leakage.

## Check indipendenti e limiti

- `PHAG.AS`: stessa esposizione/ISIN secondo fonte storica, ma Yahoo cross-venue non passa un confronto di prezzi storici sufficientemente coerente. Non copiare massimi e minimi.
- `NGAS.PA`, `OD7L.DE`: quotazioni previste dalle schede emittente ma nessuno storico quotidiano in Yahoo nel run; escludere la venue non significa escludere l'ETC.
- `CMOD.L`: diversa valuta e comunque 516 barre OHLC incoerenti nel confronto; non è prova indipendente dei dati di Milano.
- `VZLC.DE`: errore storico di identificazione. Scheda emittente 2022 riporta ISIN `DE000A0N62F2` invece di `JE00B1VS3333` attribuito nello screening precedente; rimane **no-fungibility-by-assumption** senza ulteriori documenti storici.
- Euronext `NextHistory` offre OHLC e trades storici ufficiali, ma non è stato fornito nel test alcun archivio storico acquisito da tale servizio. Prima di creare prezzi ricostruiti serve **sede e definizione di ogni campo**: High/Low degli eseguiti, prezzo d'asta, chiusura ufficiale/di riferimento, valuta, fattore di conversione/raggruppamento.

### Riferimenti verificabili

- [OLC46 GitHub Actions QA](https://github.com/AM1975MA/Test/actions/runs/41738263341) e [feature readiness](https://github.com/AM1975MA/Test/actions/runs/41738728879)
- [Euronext NextHistory](https://www.euronext.com/en/products-services/nexthistory)
- [WisdomTree Natural Gas — emittente](https://www.wisdomtree.com/it/products/commodities/wisdomtree-natural-gas)
- [RNS 27 ottobre 2023 consolidamento 1783:1](https://www.lse.co.uk/rns/consolidations-of-cld-commodity-securities-uxn9emovp1a7646.html)
- [OLC14 fonte model refit](https://github.com/AM1975MA/Test/tree/research/olc14-fitted-ranking-20261101/research/olc14_fitted_ranking_20261101)

## Oggetti pubblicati su GitHub

- `repair_and_crosscheck.py`: fonte raw, Yahoo repair, cross-venue, Stooq probe, regole di mascheramento, hash.
- `results/{PHAG_MI,NGAS_MI,CMOD_MI}_quality_masked.csv.gz`: quotazioni ricondizionate per integrità, senza valori fittizi.
- `results/bad_bar_audit.csv`, `results/close_vs_highlow_failure_modes.csv`, `results/quality_summary.csv`, `results/cross_venue_provider_diagnostic.csv`: log per riga e diagnostica.
- `asof_feature_gate.py`, `results/feature_eligibility_asof_2021_2024.csv`, `results/asof_feature_eligibility_summary.csv`: controllo warm-up causale per data.
- `olc44_native_preflight.py`, `results/olc44_native_preflight.json`: check di input e identità per refit autentico.
- `ngas_pit_consolidation.py`, `ETC_2023_CONSOLIDATIONS_PIT.csv`: storico ISIN ed evento di raggruppamento.
- `.github/workflows/olc46-price-integrity.yml`: QA ricostruibile con commit automatico di output sulla branch di ricerca.

## Decisione operativa ed evoluzione

**Accettare la correzione e il mascheramento nel solo dataset QA; NON sostituire i dati storici originali nelle strategie e NON promuovere ancora gli ETC a un portafoglio con stop intraday.**

**Avanzamento immediato per OLC44:** procedere con `EU152 PIT + quattro nuovi ETF UCITS` e `USA149 + tre nuovi ETF`, mentre si ripristinano in runtime privato OLC14 Heads+Results e OLC11 annual 42-feature per ricreare **lo stesso** modello, i seed, le label mature e il gate di parità sui ticker originali. Solo allora ricalcolare score di tutti gli strumenti, OLC19 risk/execution e nuovo CAGR.

**Nessun nuovo CAGR convalidato da questa fase.** Riferimento OLC19 invariato 2021–24: EU165 **23.1999%**, USA149 **50.7722%**. I precedenti nuovi CAGR E2 shadow-momentum (EU13.76/14.66, USA39.57/36.72) restano prove negative di regole alternative, NON un native refit.

## Criterio di passaggio finale

Prima di dire che il paniere ampliato migliora: (a) dati e share class point-in-time, (b) warm-up per data, (c) **parità perfetta sugli score dei vecchi ETF** nella pipeline originale, (d) esecuzione OLC19 uguale prima di aggiungere ticker, (e) nuovi pesi e nuova NAV unica con costi/stop, (f) confronto con stessa finestra e costo, (g) conferma prospettica perché 2019–2026 è uno storico ampiamente esplorato. Lo scopo è un miglioramento dimostrabile, non massimizzare a posteriori il 50%.
