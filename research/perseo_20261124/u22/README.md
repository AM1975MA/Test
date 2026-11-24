# Perseo U22 — filtro economico del cambio

Esito: nessuna variante promossa. Leggere RAPPORTO_PERSEO_U22.md o PERSEO_U22_ANALISI.html.

## Riproduzione

Python 3 con numpy e pandas. Per generare il rapporto servono anche matplotlib e Markdown.

```sh
python3 run22.py
python3 verify22.py
python3 analyze22.py
python3 report22.py
```

L'archivio contiene gli input congelati e le NAV U20 per la parità. Non serve una connessione esterna né il progetto padre. Il ranking originario non viene riaddestrato. Gli script riscrivono risultati soltanto nella propria cartella.

La copia di engine22.py deriva dal motore U20. Le sole modifiche funzionali sono il parametro opzionale selection_hook e la sua chiamata prima dell'ammissione del target. La parità con hook disattivato è verificata sui tre conti BASE.

Se i file inputs non sono presenti, run22.py tenta il recupero dal progetto U20 nella cartella adiacente; tale recupero non è necessario nell'archivio completo.

## File

- PROTOCOL_U22.md: regole fissate prima dei risultati. La disponibilità effettiva dei modelli inizia nel 2023, come mostrato nel rapporto e in FIT_AUDIT.csv.
- core22.py: variabili, regressioni, bootstrap e filtro. Il quantile della media non è una probabilità di profitto.
- inputs: prezzi, segnali e riferimento U20; MANIFEST.json conserva gli hash.
- results/SUMMARY.csv: metriche complete dei 24 conti.
- results/MODELS.json e FIT_AUDIT.csv: coefficienti annuali e date limite.
- results/TRAINING_PAIRS.csv: 2.086 righe fra mercati, orizzonti e controfattuali; non 2.086 osservazioni indipendenti.
- results/MONTHLY_DIAGNOSIS.csv: tutti i mesi, positivi e negativi.
- results/FORECASTS_VS_OUTCOMES.csv: previsioni e risultati buy-and-hold controfattuali, senza gli stop dell'etichetta.
- results/STATISTICS.csv: bootstrap dei differenziali di log-rendimento dal 2023, non intervalli sul CAGR.
- results/QA.json: riconciliazione dei 24 conti, causalità delle nuove variabili e maturazione delle etichette.
- *_ORDERS.csv, *_STOPS.csv, *_DECISIONS.csv e *.npz: ricostruzione delle operazioni e dei conti.

Metriche percentuali espresse in frazione nei CSV (0.20 = 20%). I nomi ereditati notional_eur e cost_eur significano valuta del conto: USD negli USA, EUR negli altri panieri. NAV base 1, capitale iniziale 10.000. Prezzi e osservabilità, cataloghi storici, stop a barra e liquidità mantengono i limiti descritti nel rapporto. Lo storico non è un test indipendente dell'intera ricerca.
