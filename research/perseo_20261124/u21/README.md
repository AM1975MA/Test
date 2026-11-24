# Perseo U21 — ricerca e benchmark, 23 novembre 2026

Contiene 21 simulazioni benchmark sul periodo 2 gennaio 2020–1 luglio 2026: 15 buy-and-hold e 6 filtri mensili a 10 mesi. EU/TR in EUR, USA in USD. Perseo U20 è un riferimento storico conservato nel CSV, non viene ricalcolato da questo archivio.

## Riproduzione

Python 3 con numpy e pandas. Matplotlib e Markdown servono per il rapporto.

```sh
python3 benchmarks21.py
python3 verify21.py
python3 report21.py
```

`BENCHMARK_INPUTS.npz` contiene prezzi rettificati e osservazioni, con storico 2019 per il riscaldamento. Non servono gli archivi U19/U20. Il programma riscrive soltanto i risultati nella propria cartella. `PERSEO_U20_REFERENCE.csv` conserva le metriche della strategia di confronto.

`BENCHMARKS_2020_2026.csv` e `BENCHMARKS_REGIMES.csv`: CAGR/drawdown in frazione (0.20 = 20%). `cost_currency` è la somma nominale dei costi; `final_capital` usa base 10.000. I NAV sono normalizzati a 1.

`ADDITIONAL_QA.json`: 18 verifiche che modificare i prezzi futuri non cambi le decisioni precedenti e 6 ricostruzioni indipendenti dei conti dagli ordini. I buy-and-hold sono confrontati anche con formula chiusa.

## Limiti

Dati del progetto congelati, non download indipendente aggiornato a novembre. Costi 1 unità monetaria + 15 bp per lato, quote frazionarie, cash senza interessi, imposte escluse; nessuna liquidazione artificiale al termine. Drawdown sulle aperture, non intraday. Le date senza apertura osservata rinviano l'esecuzione; per USA la maschera originaria non è disponibile e i valori archiviati sono assunti disponibili. Rettifiche, dividendi e disponibilità storica dei panieri Perseo non sono certificati da questo lavoro. Confronti settoriali concentrati, utili per attribuzione e non benchmark ampi equivalenti. Lo storico è già stato usato nello sviluppo: non è un nuovo test indipendente.

Il rapporto distingue prove eseguite e proposte di sviluppo. Nessuna nuova strategia promossa e nessuna modifica alle automazioni.
