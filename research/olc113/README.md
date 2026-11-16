# OLC113 — Rientro mensile dopo la protezione

**Esito:** la correzione del rientro riduce l'attesa in cash e recupera rendimento rispetto a OLC112, ma non produce il miglioramento materiale richiesto. PRICE_RESET raggiunge un CAGR completo del **24,1622%**, contro **22,5708%** della base, con MaxDD campionato rispettivamente **−36,5126%** e **−36,5142%**. Nessuna variante raggiunge il 30% o supera il criterio prefissato in entrambe le finestre.

Questo archivio aggiunge soltanto `research/olc113` al commit `26f962502db9fa3eb527423720fdea65f7698ee2` di AM1975MA/Test. Branch di ricerca: `research/olc113-reentry-reset-20261116`. Nessuna promozione operativa deriva da questi risultati.

## Documenti principali

- [Rapporto completo in italiano](RAPPORTO_OLC113_IT.md): risultati, confronti, costi, rientri, verifiche e limiti.
- [Protocollo scritto prima dei risultati](docs/DESIGN_AND_PROTOCOL.md) e [piano di implementazione](docs/IMPLEMENTATION_PLAN.md).
- [Congelamento dell'esperimento](docs/EXPERIMENT_FREEZE.json), [revisione del codice](docs/INDEPENDENT_CODE_REVIEW.md) e [registro del lavoro](docs/PROGRESS.md).
- [Lettura indipendente dei risultati](research/design/RESULT_ANALYSIS_NOTES.md) e [revisione dell'auditor](research/design/INDEPENDENT_RESULT_AUDIT_REVIEW.md).
- [Diagnosi del precedente rientro](research/reentry_diagnosis/REENTRY_DIAGNOSIS.md).
- [Diagnostica verificabile](results/INDEPENDENT_DIAGNOSTICS.json), [tabella completa](results/INDEPENDENT_SCORES.csv) e [criteri di esito](results/INDEPENDENT_CRITERIA.csv).

## Contenuto e dipendenze

Dodici nuovi conti simulati: MEAN_RESET, PRICE_RESET, VIX_RESET e TERM_RESET, ciascuno con esecuzione al Close successivo, costi raddoppiati e sensibilità al successivo Open. Ogni cartella conserva conto giornaliero, ordini, istruzioni, decisioni, trace della policy, metriche e ricevuta degli artefatti. L'audit usa anche sei controlli OLC111 e dodici predecessori OLC112, preservati nel commit genitore. Gli 81 file di modelli originali rimangono sotto `../olc111/results/FITS/`; OLC113 non addestra alcun modello.

Le cartelle `olc109`, `olc110`, `olc111`, `olc112` e `olc113` devono restare sorelle, come nel percorso `research/` del repository. I due pannelli originali di prezzi/liquidità e gli snapshot Cboe restano negli archivi originali, con istruzioni e SHA256 in [RESTORE_INPUTS.md](../olc111/docs/RESTORE_INPUTS.md). Non sostituire questi input con download di una data successiva: i controlli di identità li respingono.

## Riproduzione

Ambiente usato: Python 3.12, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, matplotlib e threadpoolctl. Dalla directory che contiene le cartelle `olc111`–`olc113`, dopo aver ripristinato gli input originali:

```bash
python -m unittest discover -s olc113/tests -p 'test_*.py' -v
python olc113/src/run_monthly_reset.py --root olc113 --resume
python olc113/src/analyze_results.py --root olc113
```

La seconda istruzione verifica gli artefatti già completati e rifiuta una cache dei modelli mancante o alterata; non rifà il fitting. Per una riproduzione integrale dei percorsi, usare una copia separata dello studio con cartella `results/` nuova e omettere `--resume`, preservando prima l'archivio originale. Il runner ricontrolla il congelamento prima e dopo il calcolo. L'audit ricostruisce i conti dai registri salvati e non esegue nuove strategie.

Tutti i risultati sono esplorativi su una storia già esaminata più volte. La correzione non dimostra una capacità di market timing stabile e non elimina i limiti del catalogo attuale, della revisione dei prezzi storici o dell'esecuzione giornaliera.
