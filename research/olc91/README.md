# OLC91 — Download futures dei cluster ETF (GitHub Actions)

**Scopo:** acquisire giornalmente una fotografia *versionata e tracciabile* di 14
serie continue di futures Yahoo Finance associate ai 16 cluster economici del
progetto ETF. **Non modifica** Return125, FUSION, OLC19, OLC67 o i Top2.

## Esecuzione
Il workflow GitHub Actions è in
[.github/workflows/olc91-yfinance-futures.yml](../../.github/workflows/olc91-yfinance-futures.yml).
La prima esecuzione viene innescata dal push sul ramo
\`research/olc91-yfinance\`. Dopo un eventuale merge su main, è disponibile
anche l'avvio manuale \`workflow_dispatch\` da **Actions**.
L'esecuzione manuale è attivabile dall'interfaccia solo dopo che il workflow
è presente nel ramo predefinito.

Per esecuzione locale:

\`\`\`sh
pip install "yfinance>=0.2.65" "pandas>=2.2,<4"
python research/olc91/fetch_yfinance_futures.py --check-only
python research/olc91/fetch_yfinance_futures.py --start 2018-01-01 --out research/olc91/output
\`\`\`

## Output
Il job allega l'Artifact **olc91-yfinance-futures-\<run_number\>** (retention 7 giorni):

- \`daily/*.csv\`: OHLC e volumi per ticker, date di mercato
- \`manifest.json\`: versioni, timestamp di acquisizione, errori e copertura annuale
- \`coverage.csv\`: esito e prima/ultima data per ogni ticker
- \`SHA256SUMS.txt\`: hash di integrità
- \`cluster_catalog.csv\`: mappa utilizzata

I file giornalieri **non vengono committati nel repository**.

## Interpretazione per OLC92
- I simboli \`NG=F\`, \`CL=F\`, ecc. sono **serie continue** e non dati dei
  singoli contratti con specifica scadenza; non consentono da soli il calcolo
  del roll yield di UNG/USO/USL/DBO.
- I dati Yahoo possono essere ricalcolati in seguito, non rappresentano un
  archivio immutabile point-in-time. Verificare sempre \`manifest.json\` e
  gli hash; per un backtest causale usare solo prezzi disponibili al segnale.
- L'assenza di un ticker o di un periodo deve rimanere \`missing\`; non
  usare valori futuri o backfill inventati.
- Verificare copertura effettiva e qualità prima di qualsiasi training ML.
- Rispettare i termini d'uso e di redistribuzione dei dati Yahoo.

Il branch sperimentale non è destinato all'operatività senza audit.
