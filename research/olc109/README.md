# OLC109 — strategia ETF congelata il 15 novembre 2026

Questo salvataggio conserva il candidato **`DEDUP_DUAL_TREND_OPP`**, il codice che lo genera e le evidenze dell'intera ricerca: **40 configurazioni, cinque scenari ciascuna, 200 percorsi**. Il risultato BASE è **25,7526% CAGR**, con drawdown campionato Open/Close **−37,9205%**, dal 2 marzo 2020 al 30 ottobre 2026. Il precedente `DUAL21` aveva CAGR BASE 22,3751%. Il traguardo del 30% annuo rimane aperto.

La strategia è una ricerca esplorativa su storia già osservata. I blocchi 2 e 3 sono adattivi e il candidato è stato individuato dopo i confronti. Il salvataggio non modifica selettori, dati, protocolli o risultati. La protezione è rinviata a uno studio successivo; in OLC109 drawdown e Calmar sono descrittivi e non escludono più un candidato.

## Risultati del candidato

| Scenario | CAGR | Drawdown Open/Close | Capitale finale da EUR 10.000 |
| --- | ---: | ---: | ---: |
| BASE | 25,7526% | −37,9205% | EUR 46.045,58 |
| ZERO_COST | 28,8205% | −37,4300% | EUR 54.068,74 |
| DOUBLE_COST | 22,6914% | −38,4065% | EUR 39.071,83 |
| LAG1 | 18,6490% | −40,7282% | EUR 31.253,61 |
| LAG2 | 13,1942% | −45,6796% | EUR 22.839,51 |

Le cifre complete si trovano nei cinque `METRICS.json` sotto `results_stage2/DEDUP_DUAL_TREND_OPP__*/` e in [analysis/ALL_SCORECARD.csv](analysis/ALL_SCORECARD.csv). BASE applica EUR 1 per ordine più 15 bp per lato. LAG1 e LAG2 aggiungono una o due sedute al normale Open successivo al segnale. Gli stress mostrano sensibilità materiale a costi e ritardi.

## Contenuti salvati nel repository

| Percorso | Contenuto |
| --- | --- |
| [RAPPORTO_OLC109_IT.md](RAPPORTO_OLC109_IT.md) | Rapporto italiano completo e tabella delle 40 configurazioni |
| [src/](src/) e [source/src/core.py](source/src/core.py) | Tutto il codice finanziario congelato |
| [tests/](tests/) e [research/engine/](research/engine/) | 51 test e fixture del motore OLC108 |
| [docs/](docs/) | Protocolli, freeze, aggiornamento dell'obiettivo e verbali |
| [analysis/](analysis/) | Tutte le 200 righe aggregate, anni, segmenti, mesi, confronti e codice di analisi |
| `results*/` | Aggregati dei tre blocchi e tutti i 200 file `METRICS.json`, compresi i risultati peggiori |
| `results_stage2/DEDUP_DUAL_TREND_OPP__*/` | Cinque conti completi del candidato: NAV, ordini, istruzioni, decisioni e metriche; compressione originale preservata |
| [validation/](validation/) | Revisori indipendenti, riepiloghi e verifiche dei 200 percorsi e 49.055 ordini |
| [data/](data/) | Provenienza della liquidità, classificazioni, quarantene e copertura dell'universo |
| [provenance/BUNDLE_MANIFEST.json](provenance/BUNDLE_MANIFEST.json) | Dimensione e SHA-256 di tutti i 3.577 file dell'archivio riproducibile |
| [REPOSITORY_MANIFEST.json](REPOSITORY_MANIFEST.json) | Impronte SHA-256 e Git blob di ogni file di questo salvataggio, escluso il manifest stesso |

I file originari copiati sono identici byte per byte. `README_IT.md` descrive l'archivio completo: le sue istruzioni si applicano dopo averlo estratto. Il presente `README.md` descrive invece la selezione salvata in Git.

## Dati completi e riproduzione

Il repository contiene codice ed evidenze, ma **non contiene tutti i pannelli binari, i 2.096 CSV sorgente OLC108 e tutti i conti completi delle altre 195 simulazioni**. Questi file sono nell'[archivio OLC109 completo](https://chatgpt.com/library?file_id=libfile_78a392f2bcac81919669f3fd5cbee900&account_id=personal), 238.685.250 byte, con SHA-256:

```text
fc89eadb3ee94f6ade1dceafbd43707f5bac518bb889e4dc350f55de32e2281e
```

Il link richiede l'accesso al file condiviso nella conversazione. Non è un endpoint di download anonimo. Il [manifest degli artefatti](DATA_ARTIFACT_MANIFEST.json) documenta la separazione e i file omessi. [REPRODUCE_FROM_ARCHIVE.md](REPRODUCE_FROM_ARCHIVE.md) contiene i comandi verificati per estrarre, verificare e ricostruire i 200 percorsi senza sovrascrivere gli originali.

I test locali utilizzano dati sintetici, il piccolo pannello congelato `source/data/TR29.npz` e il riferimento del motore, tutti inclusi; si possono eseguire senza scaricare i grandi pannelli, dalla radice del repository:

```bash
python3 -m pip install -r research/olc109/requirements.txt
python3 -m unittest discover -s research/olc109/tests -v
```

## Limiti congelati dello studio

L'audit verifica contabilità, regole e riconciliazioni. Rimangono la selezione del catalogo corrente e il rischio di survivorship, la maschera degli Open che usa il volume positivo dell'intera giornata, il vintage non certificato dei fattori di aggiustamento e l'eseguibilità non certificata dei prezzi di apertura. Il conto usa unità economiche frazionarie, cassa senza rendimento e nessuna imposta. Il drawdown osserva Open e Close, non tutti i minimi intraday. Gli intervalli descrittivi non correggono la ricerca adattiva su molte varianti.

Il salvataggio aggiunge soltanto `research/olc109/` nel branch `research/olc109-freeze-20261115`, basato sul commit `a87e84bc4e53e94a4a4e4c5ecc157e338f2716a3`. Non integra la strategia operativa. Il [rapporto completo](RAPPORTO_OLC109_IT.md) e la [revisione indipendente](validation/INDEPENDENT_REVIEW_IT.md) rimangono il riferimento per interpretare risultati e limiti.
