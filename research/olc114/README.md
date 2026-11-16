# OLC114 — Piani completi di protezione e rientro

Ricerca esplorativa su 2.096 ISIN quotati in EUR nel pannello Xetra già congelato. Ogni decisione sulla singola posizione comprende la vendita, l'eventuale attesa, un tentativo settimanale di reinvestimento e il ritorno obbligatorio al selettore mensile. Le altre quantità restano invariate durante l'intervento mirato.

Il modello principale è TREE_CYCLE, un singolo piccolo albero; MEAN_CYCLE e RIDGE_CYCLE sono confronti fissati prima dei risultati. BASE e STATIC_75 completano cinque conti, ciascuno simulato con costi normali, costi doppi e un giorno aggiuntivo di ritardo: 15 percorsi. Nessuna selezione successiva del modello principale.

## Documentazione

- `docs/DESIGN_AND_PROTOCOL.md`: ipotesi, azioni, calendario, criteri e limiti fissati prima dei risultati.
- `docs/IMPLEMENTATION_PLAN.md`: responsabilità e contratti dei moduli.
- `docs/BANK_FREEZE.json`: identità di codice e ingressi prima delle etichette.
- `docs/EXPERIMENT_FREEZE.json`: identità di banco, codice e ingressi prima delle stime e dei conti.
- `docs/PROGRESS.md`: avanzamento e decisioni operative.
- `research/design/`: revisioni indipendenti.
- `results/`: tutti i conti, le stime, le previsioni, i piani, le verifiche e i confronti.

## Riproduzione

Mantenere `olc110`, `olc111`, `olc113`, `olc114` come cartelle sorelle. I sorgenti storici sono archiviati nei rami di ricerca precedenti. Gli ingressi originali sono descritti in `olc111/docs/RESTORE_INPUTS.md`; usare le identità SHA256 e non scaricare una nuova versione dei prezzi per una riproduzione identica. Non modificare le cartelle precedenti.

Ambiente verificato: Python 3.12, NumPy 2.3.5, pandas 2.2.3, scikit-learn 1.8.0, SciPy 1.17.0, threadpoolctl. Le previsioni salvate usano gli alberi numerici esportati, senza pickle.

Test sintetici:

```bash
python -m unittest discover -s olc114/tests -v
```

Esecuzione già congelata, con ripresa verificata:

```bash
python olc114/src/run_cycles.py --root olc114 --resume
```

Il runner carica il banco congelato e non rigenera le etichette. Le stime hanno cut-off mensili e usano soltanto risultati terminati prima del cut-off. Le ricevute impediscono una ripresa silenziosa con codice, dati o risultati modificati.

## Interpretazione

Il catalogo corrente non rappresenta ogni ETF storicamente esistito. Rimangono selezione dei sopravvissuti, versione dei prezzi rettificati, limitazioni dei dati giornalieri e capacità non dimostrata. Conti in EUR con capitale iniziale 10.000 EUR, quote frazionarie, cash a rendimento zero, imposte escluse; nessuna leva di conto o vendita allo scoperto. Lo storico è stato studiato ripetutamente e non è una verifica indipendente mai vista. Gli intervalli a 42 sedute si sovrappongono; le loro etichette non si sommano per ottenere un CAGR. Il percentile inferiore dei bootstrap è una soglia euristica, non un intervallo di confidenza calibrato.
