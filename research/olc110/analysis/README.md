# Analisi OLC110

Questa cartella legge i 78 conti congelati; non sceglie nuove soglie e non crea altri modelli finanziari.

## Riproduzione

Dalla directory OLC110, dopo il ripristino degli input descritto nel README del repository:

```bash
python analysis/analyze_results.py
python analysis/action_diagnostics/action_markouts.py . analysis/action_diagnostics
python analysis/plot_results.py
python analysis/build_report.py
```

`analyze_results.py` produce i rendimenti mensili, le 13 coppie di confronti nei sei scenari, i controlli di dominanza e i prospetti dei costi. I rendimenti mensili iniziano da EUR 10.000 e si chiudono agli ultimi Close di ciascuno degli 80 mesi. Le percentuali e i punti percentuali sono distinti nei nomi delle colonne.

Il bootstrap accoppia le stesse date per i due conti. Usa blocchi circolari di sei mesi, 10.000 repliche, seed 110, e misura 12 volte la media dei log-rendimenti relativi. L'intervallo non è un intervallo della differenza tra i CAGR di calendario, non corregge i confronti multipli e non trasforma il campione adattivo in un holdout.

`CONTROL_DOMINANCE.csv` compara separatamente ciascuna delle nove protezioni a tre controlli nei sei scenari. Un controllo domina se ha CAGR almeno pari e drawdown campionato meno negativo, con almeno una disuguaglianza stretta. I drawdown si confrontano soltanto entro lo stesso scenario; NEXT_CLOSE usa Close prima/dopo i costi.

`action_diagnostics/` conserva istruzioni inframensili, confronti sul medesimo stato del conto, intervalli incompleti, suddivisioni annuali e riconciliazioni delle esecuzioni. Le finestre sovrapposte non sono additive né indipendenti; le azioni miste non vengono attribuite artificialmente a una singola causa. Le medie dei soli ingressi puri non riassumono tutti gli acquisti di opportunità.

`plot_results.py` esporta PNG e SVG; riconcilia i drawdown delle quattro curve con i conti. `build_report.py` genera il rapporto italiano e tutte le sue tabelle dai CSV congelati. La revisione dei valori e del grafico è conservata in `validation/ANALYSIS_REVIEW.*`; quella del rapporto in `validation/REPORT_REVIEW.*`.

## Esito

Ipotesi primaria non promossa: CAGR 6,61% e drawdown −46,78% contro 25,75% e −37,92% del riferimento. Tutte le nove protezioni BASE sono dominate dal controllo nominalmente investito al 75%. Nessuno dei 78 percorsi raggiunge il CAGR del 30%. I limiti di fonti, esecuzione e capienza restano parte dell'evidenza, anche dopo il controllo contabile.
