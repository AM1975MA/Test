# Meteor Titanium V2 — live parity fixed

Questa versione corregge la contaminazione tra il Titanium V2 ufficiale recuperato e il successore retrained S3B/Opportunity.

La copia GitHub conserva sorgenti, manifest e output testuali. Per eseguire il runner usare l'archivio completo, con i quattro input binari canonici verificati, indicato nel file `../ARTIFACTS.md`.

## Regole bloccate

- I 500 panieri sono quelli ufficiali in `authentic/SUPER_GOLD_BASKET_MEMBERSHIP.csv`.
- Ogni paniere contiene 24 ETF: esattamente 4 per ciascuna delle 6 categorie macro statiche.
- Sul periodo autenticato, il ranking è `TIT_R` del pannello ufficiale; non viene ricalcolato.
- La matrice ufficiale `BASE_SELECTED` è il controllo indipendente delle 56.500 decisioni paniere/mese.
- Titanium V2 applica soglia 12%: 100% sul primo classificato se il margine è almeno 0,12, altrimenti 75%/25% sui primi due.
- I cluster dinamici S3B e il router Opportunity restano in una lane successiva separata. Non modificano né i panieri né il ranking della base V2.

## Esecuzione

```bash
python source/titanium_v2_live_parity_fixed.py
```

Per una data finale storica diversa, ma interna al path congelato:

```bash
python source/titanium_v2_live_parity_fixed.py --final-date YYYY-MM-DD
```

L'esecuzione termina con errore se cambia un hash canonico, se un paniere non rispetta la struttura 4×6 o se anche una sola delle 56.500 selezioni non coincide.
Alla data ufficiale controlla inoltre CAGR medio, MaxDD medio e Sharpe medio del V2 con tolleranza `1e-12`; rifiuta date posteriori al path autenticato.

## Limite temporale importante

La parità esatta è dimostrata fino alla data finale ufficiale `2026-07-01`, usando l'ultimo segnale autenticato del `2026-05-29` (entrata `2026-06-01`, uscita `2026-07-01`). Per date successive non esiste nel recupero un nuovo stato autentico di `TIT_R`: una stima retrained può essere prodotta, ma deve essere etichettata come successore e non come replica identica del Titanium V2 ufficiale.

## Output principali

- `outputs/PARITY_REPORT.json`: gate complessivo e hash.
- `outputs/OFFICIAL_FROZEN_SCORECARD.csv`: risultati dai path ufficiali alla stessa data finale.
- `outputs/LATEST_OFFICIAL_BASKET_SIGNALS.csv`: segnale più recente per ciascuno dei 500 panieri.
- `outputs/LIVE_SIGNAL_ASOF.json`: segnale unrestricted autenticato più recente compatibile con la data finale.
- `outputs/BASKET_STRUCTURE_AUDIT.json`: verifica 24 = 6×4.

## Perché la precedente live divergeva

La precedente ricostruzione live calcolava nuovamente l'universo eleggibile, estraeva altri 500 panieri con un nuovo seed e ricalcolava mensilmente S3B tramite PCA e balanced K-means. Queste operazioni sono deterministiche solo a parità di input, universo, preprocessing e seed; non erano la continuazione dello stato ufficiale congelato. Per questo panieri apparentemente simili e formule nominalmente uguali producevano scelte diverse.
