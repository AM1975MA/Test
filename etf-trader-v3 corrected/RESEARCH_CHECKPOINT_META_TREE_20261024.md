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
