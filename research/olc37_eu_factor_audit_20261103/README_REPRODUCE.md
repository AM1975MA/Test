# OLC37 — riproduzione controllata e significato dei risultati

La prova OLC37 **non è una strategia** e non è un nuovo modello ETF: è un audit dei dati OLC19/OLC32 e una diagnostica delle esposizioni europee. Nessun trade, nessuna modifica USA o `main`.

## Input richiesti (archivi già nella Library utente)

- `OLC19_Rischio_Rientro_Checkpoint_20261102.zip` SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540` (165,680,538 bytes).
- `OLC32_RESULTS.zip` SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d` (10,035,446 bytes).

Si possono mettere nella sottocartella `input` con questi nomi oppure passarli tramite CLI. Non vengono copiati nel branch GitHub, che conserva solo risultati, codice, fonti e SHA.

## Ambiente

Python 3.11+, numpy, pandas, scipy, matplotlib. Lo script usa solo i file locali, niente rete. Non richiede dati pubblicati dopo il 2026 per costruire le etichette; le fonti web servono esclusivamente per identificare il tipo degli ETF-proxy.

## Esecuzione

```bash
python src/run_olc37.py --olc19 input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip --olc32 input/OLC32_RESULTS.zip --out results
python src/analyze_holdings.py --olc19 input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip --results results
python src/factor_periods.py --olc19 input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip --results results
python src/plot_olc37.py
python src/verify_olc37.py --olc19 input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip --olc32 input/OLC32_RESULTS.zip --results results
```

**Controlli:** identificazione dei due zip via SHA256; parità esatta scorecard OLC19; reset della data del NAV a `dates[k+1]`; tutte le date proxy con `observed=True`; scaler/fit anno Y soltanto da 252 return intervals con maturazione prima del cutoff; output del clone indipendentemente ricostruito con quote e cassa; diagnostica fattori calcolata su 48 segnali. I test verificano la consistenza aritmetica, non l'eseguibilità di mercato né l'alpha.

## Regole interpretative

1. `OLC19 23,20%` è il CAGR del conto nello scorecard storico ufficiale; `23,29%` è una statistica matched su date Open osservate dal 4 gennaio 2021 al 30 dicembre 2024. Non usare come due versioni di strategia.
2. `Clone 14,45%` ha volatilità e esposizioni diverse da OLC19 e omette l'ETF semiconductor `VVSM.DE` per mancanza di storia sufficiente al primo fitting 2021. **Non è un clone a pari fattori/rischio e la differenza non è alpha certificata.**
3. Le proxy `EXSA` e `EXX1` distribuiscono dividendi, quindi i rendimenti dei loro prezzi Open non sono total-return; gli ETF USD quotati in EUR riflettono anche la valuta.
4. 2021–2024 e tutti gli altri anni fino a metà 2026 erano già stati esaminati più volte: nessun test qui è indipendentemente prospettico.
5. USA149 resta immutato, sia nel protocollo che nel codice. L'archivio OLC19 contiene dati storici USA, ma gli script analizzano soltanto il pannello e il conto EU.

## Status

`Gate A = INCOMPLETE` per mancanza di veri input storici PIT/TR/eseguibili. Il lavoro successivo corretto è costruire un universo storico per ISIN, valuta e indice, verificare ETF/mercati/fattori, poi confrontare un benchmark esposizioni/rischio-matched su una finestra autenticamente nuova. Nessun tuning dopo la ricerca negativa di OLC25–36.
