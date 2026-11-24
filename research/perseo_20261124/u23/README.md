# Perseo U23 — altre linee, 24 novembre 2026

Nove varianti, BASE e due procedure di scelta annuale. Risultati completi nel rapporto HTML/Markdown. Nessuna nuova strategia promossa.

## Riproduzione

Python 3 con numpy e pandas; matplotlib e Markdown per il rapporto.

```sh
python3 run23.py
python3 walkforward23.py
python3 analyze23.py
python3 verify23.py
python3 report23.py
```

L'archivio include tutti gli input necessari e le NAV U20 per la parità. Non richiede il progetto padre né accesso a Internet. Gli script riscrivono solo i risultati della propria cartella. Il ranking originale non viene riaddestrato. Le dipendenze Python sono in requirements.txt.

## Contenuti

- PROTOCOL_U23.md: famiglia chiusa e criterio di scelta, registrati prima dei risultati.
- core23.py: segnali causali e guardie di composizione.
- engine23.py: motore U22/U20 con modifica limitata al cooldown globale; le altre protezioni restano operative. BASE replica U20.
- run23.py: 90 conti fissi/stress.
- walkforward23.py: 12 conti WF continui; training basato su chiusure precedenti il cutoff annuale.
- results/SUMMARY.csv: tutte le metriche.
- results/MONTHLY_DIAGNOSIS.csv: tutti i confronti mensili.
- results/REGIMES.csv, ANNUAL.csv, EXPOSURE.csv: sottoperiodi, anni ed esposizione cash.
- results/STATISTICS.csv: intervalli nominali sul differenziale di log-rendimento, non sul CAGR.
- results/WF_PLAN.csv, WF_SELECTION_AUDIT.csv, WF_INPUT_CUTOFFS.csv: scelte annuali e verifiche cronologiche.
- results/QA.json: 102 ricostruzioni contabili indipendenti e controlli causali.
- NPZ e CSV per ciascun conto: posizioni, NAV, ordini e stop.

Percentuali espresse come frazioni nei CSV (0.20 = 20%). NAV base 1, capitale iniziale 10.000. Colonne ereditate cost_eur e notional_eur significano valuta del conto: USD per USA, EUR per EU/TR. Quote frazionarie; nessuna fiscalità, nessuna leva sul conto; cash senza interesse. I risultati terminano all'apertura del 1 luglio 2026.

Fonte degli input: archivio U22, Library ID libfile_fde3_f-a2e09ccaa5d881919774ab3c507ca796_549d1bce98388191a0aeb13709c4eff9, SHA-256 4585500661935a383a6fb93ba5d7e9aa297a64213dded0ef232f4b82b8e684e7. Tutti i 133 file ripristinati sono stati verificati rispetto al manifesto originale prima dei nuovi test. Il nuovo archivio contiene copie autonome dei soli input necessari.

I limiti del dataset originario restano aperti: cataloghi storici non completi, prezzi rettificati non verificati con un secondo fornitore, maschera osservazioni USA assente, stop a barra e liquidità. Lo storico è già stato esplorato. Nessun invio di ordini reali o cambiamento alle automazioni.
