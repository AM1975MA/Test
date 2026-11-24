# Perseo U24 — esiti e riproduzione

Il rapporto RAPPORTO_PERSEO_U24.md / PERSEO_U24_ANALISI.html riporta tutti i risultati. Nessuna strategia promossa; U20 resta il riferimento.

## Esecuzione

Da questa cartella, Python 3 con le dipendenze di requirements.txt:

```sh
python3 run24.py
python3 walkforward24.py
python3 analyze24.py
python3 verify24.py
python3 attribution24.py
python3 confidence24.py
python3 report24.py
```

`inputs` è un collegamento relativo a ../u23/inputs. Su sistemi che non ripristinano i symlink, sostituirlo con una copia di quella cartella. `verify24.py` legge inoltre i nove conti di controllo in ../u23/results. Tutti sono inclusi nel checkpoint Git. Nessun accesso a Internet è necessario per i test. Gli script riscrivono risultati di U24 e non cambiano versioni precedenti. Il motore engine23.py e i suoi moduli sono copiati senza modifiche da U23; core23.py contiene le regole originali di controllo. I nuovi segnali sono in core24.py.

120 conti e 9.360 righe mensili. Le analisi statistiche distinguono intervalli nominali e simultanei della famiglia U24; nessuna delle due corregge l'intera ricerca storica. L'attribuzione ticker è una riconciliazione contabile, non una previsione.

Il protocollo è congelato nel commit c2f17b8 precedente all'esecuzione. Attribuzione e correzione statistica della famiglia sono diagnostiche successive; non hanno introdotto nuove varianti o modificato i conti.

Dati congelati al 1 luglio 2026. Ranking 125/42 precedente, non riaddestrato. Il replay non valida a ritroso cataloghi point-in-time, prezzi rettificati, osservabilità o realizzabilità degli stop.
