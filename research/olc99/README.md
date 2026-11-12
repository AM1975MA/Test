# OLC99 — Ranker economico Top10 e allocazione matched-state

**12 novembre 2026 · ricerca, senza modifiche a main / OLC19 / OLC67.**

## Domanda
Un secondo ranker che prevede il payoff economico fra le dieci proposte migliori della FUSION originale e un allocatore ML addestrato su risultati nativi dallo stesso stato contabile migliorano il risultato investibile?

## Esito
**No nei test eseguiti.** Tre varianti economiche (Top10-only, training all-universe, label nativa con stato comune) non battono CONTEXT/50-50/DELAY3. L'allocatore ML migliora appena USA rispetto al 50/50 sulla stessa nuova selezione E1, ma il risultato combinato rimane inferiore alla baseline. Il periodo 2019–luglio 2026 è già stato esplorato estesamente e non è OOS indipendente.

## Ordine di esecuzione
Da questa directory, con Python 3.10+, NumPy, Pandas, SciPy, scikit-learn e matplotlib:

```bash
OPENBLAS_NUM_THREADS=1 python run_olc99.py
python verify_olc99_independent.py
OPENBLAS_NUM_THREADS=1 python run_olc99b.py
python verify_olc99b_independent.py
OPENBLAS_NUM_THREADS=1 python run_olc99c.py
python verify_olc99c_independent.py
python evaluate_model_skill.py
python forensic_olc99.py
python make_report.py
```

Per una riesecuzione pulita i file delle sorgenti originali OLC98+OLC70 sono disponibili nella cartella `source/`. I file `src/combined_engine.py`, `src/methods.py`, `portfolio_metrics_parent.py` e gli input NPZ originari non sono stati modificati. Il codice OLC99 usa il medesimo motore e ne verifica la parità contabile con sette array per ogni mercato.

## Output principali
- `REPORT_OLC99_IT.md`: decisione e risultati, con grafici `results/*.png`.
- `results/OLC99_NATIVE_SCORECARD.csv`: 32 replay native OLC99A, due mercati/fee/timing e allocatori on-policy.
- `results/OLC99B_NATIVE_SCORECARD.csv`: 8 replay all-universe training.
- `results/OLC99C_SCORECARD.csv`: 4 replay con label basata su 1.780 controfattuali singolo ETF.
- `results/OLC99_TOP10_ECONOMIC_PANEL.csv.gz`: score, feature a data segnale, prezzo futuro per 1.800 eventi ETF.
- `results/OLC99_MATCHED_STATE_COUNTERFACTUALS.csv`: 356 episodi mensili × cinque politiche peso, stesso stato di partenza per ciascuno.
- `results/OLC99_ALLOCATOR_WEIGHTS.csv`: pesi effettivamente applicati 0–100%.
- `results/OLC99_INDEPENDENT_QA.json`, `OLC99B_INDEPENDENT_QA.json`, `OLC99C_INDEPENDENT_QA.json`: metriche ricalcolate autonomamente.
- `PROTOCOL_PRE_RESULTS.md`: specifica primaria congelata prima degli outcome.
- `OLC99B_PROTOCOL_ADDENDUM.md`, `OLC99C_PROTOCOL_ADDENDUM.md`: esperimenti esplorativi aggiunti dopo i risultati precedenti, ma protocollati prima dei rispettivi outcome.
- `MANIFEST_SHA256.json`: controllo integrità di tutto il bundle.
- `results/OLC99_CLEANROOM_QA.json`: audit 70/70 file originali identici byte per byte dopo riesecuzione pulita, 3 verificatori PASS.

## Limiti
- Target e dati prezzo non dimostrano eseguibilità di ordini di broker; restano problemi di universe PIT, osservabilità USA, distribuzioni/FX, volatilità intraday, spread e stop.
- I benchmark di rendimento sono stati ricavati dal motore nativo, con i suoi coefficienti costo simulati, non da trading reale.
- Gli interventi sullo stesso stato identificano solo effetti causali **interni al simulatore** a prezzi esogeni. L'oracolo del Top10 conosce il futuro e non è una previsione negoziabile.
- La validazione futura richiede periodi successivi alla prima apertura di luglio 2026 e previsioni congelate *prima* di conoscerne gli outcome.