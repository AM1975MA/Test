# ETF Trader V3 Corrected — checkpoint meta-ranker del 24 ottobre 2026

## Stato: ricerca riproducibile, non promossa in produzione

La direzione di ricerca promettente è **ranker CORRECTED125 → decision tree condizionale → riordino esclusivo del Top-3**. L'esperimento più rigoroso già condotto usa **NESTED_24_TOP1_GUARD**: scelta cronologica tra 36 alberi candidati sulla base di 24 mesi OOS precedenti, con 60 giorni di maturazione, e accetta un albero soltanto se il Top-1 non peggiora sullo storico eleggibile. In assenza di evidenza, non corregge nulla.

- Universo originale: 149 ETF, 500 panieri canonici da 24, 101 mesi con target forward maturato (2018-01..2026-05).
- Modelli first-stage: tre seed, riaddestramento espandente annuale; output OOS immobilizzati, nessun ulteriore fitting del ranker durante i test meta.
- Validazione classificazione e scelta cronologica: GitHub Actions [40032282233](https://github.com/AM1975MA/Test/actions/runs/40032282233) — PASS.
- Simulazione di economia reale: GitHub Actions [40032693599](https://github.com/AM1975MA/Test/actions/runs/40032693599) — PASS; prezzo alla successiva apertura, costo 10 bps per transazione, 500 panieri, verifica esatta delle 50.500 decisioni prima del replay.
- **CAGR economici per portafoglio medio 2022-02–2026-06**: Top1 21,21% → 24,62%; Top2 19,82% → 21,45%; Top3 17,96% → 18,54%. Sono CAGR sull'equity media di panieri sovrapposti, non dell'unico portafoglio composito implementabile.
- **Avvertenza essenziale**: il bootstrap temporale dell'alpha economico include zero per Top1/Top2/Top3; periodo storico largamente riusato in precedenti esperimenti. Quindi **nessun vantaggio futuro è ancora dimostrato**.
- Il kernel V3 originale, la V2, Tail, il controllo rischi, la configurazione di produzione e gli altri layer **non sono stati modificati**.

## Dove risiede tutto

Il progetto V3 originale è `etf-trader-v3 corrected/`.

- [Sorgenti, protocolli, rapporto principale e studi intermedi](experiments/l00_rank_reg_fusion/) — `evaluate.py`, `aggregate.py`, `weighted_ranker.py`, `parallel_meta.py`, `nested_tree_selector.py`, `nested_economic.py`, `archive_verified_results.py`, report .md e workflow sotto `.github/workflows/`.
- [Indice archivi e tabelle](experiments/l00_rank_reg_fusion/results/README.md).
- [Manifest riproducibile con SHA-256 per ogni archivio e file](experiments/l00_rank_reg_fusion/results/ARCHIVE_MANIFEST.json).
- [Archivi integrali degli esperimenti](experiments/l00_rank_reg_fusion/results/archives/) — dodici ZIP versionati nel repository (inclusi i segnali OOS annuali, le decisioni reali e le NAV giornaliere).
- [Tabelle CSV direttamente consultabili](experiments/l00_rank_reg_fusion/results/tables/).

La sorgente OHLCV congelata è in Actions **39482809691**; il benchmark OOS originario in **39515716383**. Non creare nuovi pannelli o panieri per confronti futuri senza versionare esplicitamente il protocollo.

## Prossime verifiche prima della produzione

1. Conferma di robustezza su intervalli cronologici realmente nuovi, fuori dalla ricerca già usata per selezionare modelli e meta-selettori.
2. Analisi dell'impatto di turnover, liquidità e distribuzione delle correzioni nei diversi regimi.
3. Prove della gerarchia completa senza ritarare i layer superiori per massimizzare il CAGR.
4. Decisione esplicita di promozione soltanto dopo audit e controprove.

**Checkpoint di ricerca immutabile:** i risultati non vanno sovrascritti da esperimenti successivi; usare nuove cartelle, commit e run ID.


## Aggiornamento: stress test del 24 ottobre 2026

È stato completato e archiviato un secondo lotto di 9 esperimenti senza ritarare il ranker CORRECTED125, il meta-albero né le soglie di rischio. [Rapporto di robustezza](experiments/l00_rank_reg_fusion/ROBUSTNESS_COST_RISK_20261024.md); [risultati integrali e audit SHA256](experiments/l00_rank_reg_fusion/results/robustness_20261024/).

- Costi next-open da 0 a 100 bps: il vantaggio storico tree vs ranker persiste anche a fee elevate, ma la redditività assoluta collassa.
- Tree come solo trigger e secondo candidato originale: prestazione del 21D forward simile, ma backtest 2022–26 Top1 a 10 bps 24,27% contro 24,62% dell'albero completo; conservarli entrambi come alternative di ricerca.
- Risk overlay originale, soglie non cambiate: Top2 2022–26 ranker 16,23% vs ranker+tree 17,62% CAGR con risk ON (contro 19,82% vs 21,45% risk OFF). Nel periodo 2018–26 risk ON migliora molto il MaxDD aggregato, ma il vantaggio tree con risk ON non è statisticamente confermato.
- 2.209 modifiche fra 50.500 scelte dei 500 panieri si riducono a 786 diversi eventi coppia ETF/data; l'analisi non deve contarle come osservazioni indipendenti.
- Vantaggio di extra rendimento 21D +0,1432 punti percentuali intero periodo, +0,0404 pp con differenze ETF limitate a ±5%, +0,0212 pp escludendo insieme gli anni 2022, 2025, 2026. Rischio di concentrazione di regime e di eventi estremi tuttora presente.

**Stato invariato: ricerca promettente, NON modello autorizzato per produzione.** I moduli `src`, il full-stack preesistente e i layer operativi non hanno subito modifiche. Il prossimo test prioritario richiede informazioni veramente successive o indipendenti dal calendario già sfruttato.


## Nuova evidenza — benchmark di 23 famiglie di decision tree (24 ottobre 2026)

La seconda ricerca amplia il controllo sul livello meta, **senza cambiare la strategia selezionata**. Sono stati testati 113 sfidanti da 23 famiglie, fra cui XGBoost, LightGBM, CatBoost, Random Forest, Extra Trees, histogram gradient boosting, regressione del vantaggio economico, classificazione loss-sensitive, feature event-level invarianti per coppia ETF e training contestuale con deduplicazione ponderata. Tutti i job di training e il confronto `as of` 60 giorni sono terminati con successo.

- [Report tecnico completo](experiments/l00_rank_reg_fusion/TREE_ALGORITHM_COMPARISON_20261024.md)
- [26 ZIP integrali, 127 tabelle e manifest SHA-256](experiments/l00_rank_reg_fusion/results/tree_algorithms_20261024/)
- [Verifica definitiva su 23 famiglie](https://github.com/AM1975MA/Test/actions/runs/40038509415)

**Risultato:** la selezione cronologica combinata `ALL__GUARD24` perde **0,1280 punti percentuali di excess forward 21D e 0,7921 punti di hit rate Top1** rispetto all'attuale `NESTED_24_TOP1_GUARD`. Il selettore solo sfidanti perde 0,1508 punti di forward selected excess. Il benchmark vecchio `PRIOR_ONLY__GUARD24` è stato ricostruito con **parità numerica esatta su tutti i 101 mesi**. Top3 invariato per tutti i modelli. Gli intervalli bootstrap mostrano peggioramenti compatibili con un calo reale, ma lo storico resta ampiamente riusato e non costituisce un holdout indipendente.

**Decisione:** mantenere **CORRECTED125 + decision tree cronologico NESTED_24_TOP1_GUARD** come unico candidato di riferimento (research-only). Non promuovere alcuna variante nuova; sospendere il tuning di algoritmi sul medesimo calendario in favore di holdout temporali realmente non utilizzati. La V2, i kernel e i layer operativi V3 rimangono invariati.


## Aggiornamento — Hurdle decisionale expected-regret del 24 ottobre 2026

Sulla stessa storia OOS congelata 2018–2026, sono state eseguite **4 famiglie di meta modelli di utilità economica (8 regole fisse)**. Ogni modello separa la probabilità di battere il Top1, il vantaggio atteso condizionato al successo e la perdita attesa condizionata all'errore. Sono state aggiunte feature causali di momentum, volatilità e regime SPY/breadth 21/63 sedute, con controlli di massimo timestamp e refit solo trimestrale su label maturati >=60 giorni prima.

- [Rapporto di ricerca completo](experiments/l00_rank_reg_fusion/EXPECTED_REGRET_RESULTS_20261024.md).
- [Tutti i nove archivi, 50 tabelle leggibili e checksum SHA256](experiments/l00_rank_reg_fusion/results/utility_regret_20261024/).
- [Protocollo bloccato di test futuri non contaminati](experiments/l00_rank_reg_fusion/PROSPECTIVE_VALIDATION_LOCK_20261024.md).
- GitHub Actions [modelli](https://github.com/AM1975MA/Test/actions/runs/40079852872), [confronto strutturale](https://github.com/AM1975MA/Test/actions/runs/40080236687), [replay economico](https://github.com/AM1975MA/Test/actions/runs/40080407962), [stress calendariale](https://github.com/AM1975MA/Test/actions/runs/40080774850).

**Fatti:** `UTILITY_DT14_L1.5` migliora Top1 dal 14,54 al 14,87%, ma non il rendimento selezionato in misura dimostrabile e peggiora la frequenza di grandi perdite. `UTILITY_RF_REGIME_L1` presenta selected excess forward +1,002%, ma Top1 solo 13,72% e correzioni ~29%. Il Top2 economico della RF 2022–2026 è 22,71% contro 21,45% del checkpoint, ma **escludendo il 2026 perde** 19,10% contro 20,23%; tutti gli IC dell'alpha RF vs checkpoint comprendono zero. Il calendario resta storico riusato; non esiste in questa campagna un holdout esterno successivo a maggio 2026 del first-stage.

**Decisione:** mantenere `CORRECTED125 + NESTED_24_TOP1_GUARD` checkpoint di ricerca, nessun challenger promosso. Non cambiare V2, kernel o layer operativi. Per adottare altri modelli, bloccare le impostazioni e ottenere first-stage OOS realmente nuovi prima delle label.
