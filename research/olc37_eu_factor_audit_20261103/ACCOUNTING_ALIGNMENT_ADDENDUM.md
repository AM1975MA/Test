# OLC37 — addendum di allineamento contabile, prima delle metriche fattoriali

**2026-11-03.** Registrato DOPO il protocollo iniziale `65cee88`, a seguito di un test di parità non superato e PRIMA del calcolo dei risultati dello screening. Non viene effettuata alcuna ricerca di pesi/modelli o di soglie dopo avere visto gli esiti. Il test fallito e la riparazione restano documentati.

## Fatto ricavato dal codice padre OLC19

Nel file sorgente originale `olc16_contextual_rank_20261102/src/portfolio_metrics_parent.py`, la funzione `metrics` definisce:

```python
ds = pd.DatetimeIndex(q['dates'])
actual = ds[1:]
log = np.diff(np.log(np.r_[1.,r['nav']]))[:-1]
```

Quindi `r['nav'][k]` è la ricchezza che termina alla seduta `ds[k+1]`, NON a `ds[k]`. Lo scorecard `ACTIVE2021_2024` non usa il semplice rapporto `nav[last_date]/nav[first_date]` per date nominalmente uguali: così facendo si misallineerebbe la sequenza di una seduta.

## Regola corretta e congelata

Allineare ai prezzi `Open[dates[i]]` il valore `NAV_actual[i] = 1` per i=0 e `NAV_actual[i] = nav_saved[i-1]` per i>=1. Gli incrementi di `NAV_actual` e dei proxy sono valutati fra gli **stessi due Open osservati**. Se il mercato è chiuso, l'analisi può saltare la data di Open mancante e accumulare il ritorno del NAV fino al successivo giorno validamente osservato, ma non finge una negoziazione alla data mancante. Per il confronto con lo scorecard ufficiale si applica prima la sua convenzione `actual = ds[1:]` e `log` come sopra; si verifica l'identità del rendimento di periodo e del CAGR entro 1e-10.

La finestra del clone rimane esattamente quella del protocollo, Open comune 2021-01-04 fino all'ultimo Open comune osservato 2024-12-30 (il 2024-12-31 conserva Open numerici ma maschera observed False). Questo sottoinsieme *non* deve essere presentato come perfettamente identico alla finestra ufficiale `ACTIVE2021_2024` del conto OLC19. Restano fisse le cinque proxy, i 252 intervalli di fit pre-anno, i pesi long-only<=1, i costi illustrativi e tutti i gate; USA congelato.

**Origine dell'errore di audit:** lo script preliminare ha confrontato direttamente `nav[date=2024-12-31]/nav[date=2021-01-04]-1` con lo scorecard ed è fallito. Il nuovo test deve registrare l'errore di questo confronto e l'identità della formula originale. Nessun nuovo risultato finanziario era stato calcolato/pubblicato prima di questa correzione.