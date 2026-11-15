# OLC110 — protezione, liquidità e rientro

**Esito negativo: nessuna nuova protezione promossa.** La ricerca conserva il selettore OLC109 `DEDUP_DUAL_TREND_OPP` e confronta 13 configurazioni in sei scenari, per **78 conti completi**. Il candidato primario dichiarato prima dei rendimenti, **`EXIT21_STAGED_FRESHW`**, ottiene CAGR BASE **6,61%** e drawdown Open/Close **−46,78%**, contro **25,75%** e **−37,92%** del riferimento OLC109. Nessun conto raggiunge il 30% annuo, nemmeno a costi zero.

| Modello, scenario BASE | CAGR | DD Open/Close | Capitale finale da EUR 10.000 |
| --- | ---: | ---: | ---: |
| OLC109 originale (`BASE`) | 25,75% | −37,92% | EUR 46.045,58 |
| Controllo nominale 75% investito (`STATIC_75`) | 20,50% | −31,96% | EUR 34.653,97 |
| Migliore protezione dinamica per CAGR (`EXIT63_STAGED`) | 17,50% | −36,62% | EUR 29.297,47 |
| Candidato primario (`EXIT21_STAGED_FRESHW`) | 6,61% | −46,78% | EUR 15.319,17 |

Il controllo `STATIC_75` domina **tutte le nove protezioni dinamiche nello scenario BASE** su CAGR e drawdown campionato. È una riduzione dell'esposizione con ribilanciamento mensile, non una dimostrazione di timing. OLC109 resta il riferimento di ricerca. I risultati completi, compresi quelli sfavorevoli, sono in [results/SCORECARD.csv](results/SCORECARD.csv); il confronto è documentato in [analysis/CONTROL_DOMINANCE.csv](analysis/CONTROL_DOMINANCE.csv).

## Che cosa è stato provato

Il candidato primario combina uscita per deterioramento del trend breve, rientro graduale sullo stesso ETF dopo una conferma e ricerca settimanale di nuove opportunità quando un posto è effettivamente libero. Il conto verifica quantità detenute, liquidità disponibile, acquisti realmente eseguiti e istruzioni pendenti. Le alternative separano frequenza, criteri di uscita, velocità del rientro e frequenza delle nuove opportunità.

Il periodo è 2 marzo 2020–30 ottobre 2026, con 2.096 ETF EUR su Xetra, EUR 10.000 iniziali, unità economiche frazionarie, cash a rendimento zero e imposte escluse. `BASE` applica EUR 1 più 15 bp per ordine; gli altri casi sono `ZERO_COST`, `DOUBLE_COST`, `LAG1`, `LAG2` e `NEXT_CLOSE`. Il drawdown di `NEXT_CLOSE` usa Close prima/dopo i costi: va confrontato soltanto con conti dello stesso scenario, non equiparato al campionamento Open/Close degli altri cinque.

Codice, soglie, 13 configurazioni e candidato primario sono congelati prima dei nuovi rendimenti in [docs/EXPERIMENT_FREEZE.json](docs/EXPERIMENT_FREEZE.json). La storia precedente era già nota: lo studio resta adattivo, senza periodo di verifica mai osservato. Non è stata aggiunta una variante per recuperare il risultato negativo.

## Da leggere

| Percorso | Contenuto |
| --- | --- |
| [RAPPORTO_OLC110_IT.md](RAPPORTO_OLC110_IT.md) | Rapporto italiano completo, risultati, anni, esecuzione, diagnostica e limiti |
| [figures/OLC110_RISULTATI.png](figures/OLC110_RISULTATI.png) | Figura riepilogativa |
| [src/](src/), [source/src/core.py](source/src/core.py), [tests/](tests/) | Codice finanziario congelato e suite di 91 test |
| [docs/](docs/) | Protocollo, freeze e verifiche finali |
| [results/](results/) | Tutti i 78 conti: NAV, ordini, istruzioni, decisioni CSV/NPZ, metriche e trace quando previsto |
| [analysis/](analysis/) | Tutti gli scenari, anni, segmenti, confronti descrittivi e codice di analisi |
| [analysis/action_diagnostics/](analysis/action_diagnostics/) | 3.869 eventi e 11.607 intervalli sullo stesso conto iniziale; esiti censurati conservati |
| [validation/INDEPENDENT_REVIEW_IT.md](validation/INDEPENDENT_REVIEW_IT.md) | Revisione di 78 conti, 32.533 ordini e 20.810 istruzioni |
| [validation/source_execution/AUDIT_NOTES.md](validation/source_execution/AUDIT_NOTES.md) | Prezzi, eventi sorgente, anzianità e capienza |
| [DATA_ARTIFACT_MANIFEST.json](DATA_ARTIFACT_MANIFEST.json) | Due input grandi esterni, hash, archivio e confini del salvataggio |
| [REPRODUCE_FROM_ARCHIVE.md](REPRODUCE_FROM_ARCHIVE.md) | Ripristino e comandi verificati |

## Limiti di capienza ed esecuzione

L'audit delle fonti non certifica che gli ordini fossero eseguibili ai prezzi registrati. **65 osservazioni ordine/scenario su 32.533 hanno controvalore almeno pari all'intero turnover giornaliero riportato sulla sede**, con massimo **6,407 volte**. Nel candidato primario BASE un ordine arriva a **3,300 volte**; nel riferimento BASE il massimo è comunque **48,64%**. Il denominatore è volume dell'intera giornata per Close grezzo: non è profondità dell'asta, spread o capacità complessiva dell'ETF su tutte le sedi. Il filtro di liquidità passata e costi fissi di 15/30 bp non garantiscono il prezzo ottenibile. I valori per tutti i 78 conti sono in [ALL_78_PATH_CAPACITY_SUMMARY.csv](validation/source_execution/ALL_78_PATH_CAPACITY_SUMMARY.csv).

Restano il survivorship del catalogo corrente, il vintage non certificato degli aggiustamenti e la disponibilità degli Open originari collegata anche al volume positivo della giornata completata. Il drawdown Open/Close non copre ogni minimo intraday. La diagnostica favorevole di alcuni nuovi ingressi è condizionata ai conti del modello fallito, include finestre sovrapposte e non può essere sommata o capitalizzata come un rendimento alternativo; le istruzioni miste e censurate, comprese quelle legate a LBRA, restano esplicite nel rapporto.

## Dati e riproduzione

Questo salvataggio contiene **tutti i conti OLC110 e tutti gli altri file dello studio**, salvo due input binari: `source/data/XETRA_EUR_ETF.npz` e `data/LIQUIDITY.npz`. Sono identici a quelli dell'[archivio OLC109 già consegnato](https://chatgpt.com/library?file_id=libfile_78a392f2bcac81919669f3fd5cbee900&account_id=personal), SHA-256 `fc89eadb3ee94f6ade1dceafbd43707f5bac518bb889e4dc350f55de32e2281e`. Il link richiede accesso al file della conversazione; non è un endpoint anonimo di download.

Il comando di ripristino verifica l'archivio, ricrea le tre directory sorelle `olc108/`, `olc109/`, `olc110/`, recupera i due input e verifica ogni file originale OLC110 contro il manifest. La piccola fixture `TR29.npz` è inclusa in Git: i test locali non richiedono il download dei pannelli grandi.

```bash
# Dalla radice del checkout di Test:
python3 -m pip install -r research/olc110/requirements.txt
python3 -m unittest discover -s research/olc110/tests -v

# Sostituire i percorsi di esempio; la destinazione deve essere nuova:
python3 research/olc110/tools/restore_research.py \
  --olc109-archive /percorso/OLC109_RICERCA_ETF_20261115.zip \
  --destination /percorso/OLC110_RESTORED
```

I file finanziari, i protocolli, il rapporto e i risultati sono copie identiche agli originali. Le aggiunte di archiviazione sono indicate nei manifest. Il branch `research/olc110-protection-reentry-20261115` deriva dal commit OLC109 `12908133d98dba91d09cdb1a5266a64421d9d075`; il nuovo contenuto è limitato a `research/olc110/`. Nessuna strategia operativa viene sostituita da questo salvataggio.
