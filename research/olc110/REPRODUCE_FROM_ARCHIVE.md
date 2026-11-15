# Ripristinare e riprodurre OLC110

## 1. File presenti in Git e input esterni

Il repository conserva codice, test, protocollo, tutti i 78 conti finanziari, analisi, diagnostica, audit, figura e rapporto. Conserva anche `source/data/TR29.npz`, richiesto da un test di regressione. Sono esterni a Git soltanto due pannelli binari originali, entrambi identici agli input OLC109:

| File | Byte | SHA-256 |
| --- | ---: | --- |
| `source/data/XETRA_EUR_ETF.npz` | 28.682.014 | `14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96` |
| `data/LIQUIDITY.npz` | 17.319.970 | `b95fa3d67837fa06c5705aa4aea09807d396464ab44ec1671031d797b57f4485` |

Scaricare l'[archivio OLC109 completo](https://chatgpt.com/library?file_id=libfile_78a392f2bcac81919669f3fd5cbee900&account_id=personal) usando l'account che può accedere al file della conversazione. È un file da 238.685.250 byte con SHA-256 `fc89eadb3ee94f6ade1dceafbd43707f5bac518bb889e4dc350f55de32e2281e`. Include lo studio OLC109 e il supporto OLC108, compresi i 2.096 CSV di prezzo richiesti dagli audit; non include l'intera acquisizione HTTP originaria OLC108.

Dalla radice del checkout di Test, sostituire i percorsi seguenti con percorsi locali reali:

```bash
python3 research/olc110/tools/restore_research.py \
  --olc109-archive /percorso/OLC109_RICERCA_ETF_20261115.zip \
  --destination /percorso/OLC110_RESTORED
```

Il ripristino richiede Python 3.11 o successivo e solo la libreria standard. La destinazione deve essere inesistente. L'helper verifica tutti i 3.577 membri dell'archivio precedente, copia OLC110 e verifica ogni file originale contro `provenance/OLC110_SOURCE_MANIFEST.json`. Solo dopo questi controlli rende disponibile la destinazione, con tre directory sorelle `olc108/`, `olc109/`, `olc110/`. Non modifica il checkout né esegue una simulazione.

Le tre directory sono necessarie: il runner e la revisione confrontano cinque scenari con OLC109; gli audit sorgente e la diagnosi precedente leggono anche i dati OLC108. I percorsi assoluti storici presenti in alcuni verbali documentano la prima esecuzione e non sono percorsi da ricreare manualmente.

## 2. Ambiente e test

L'esecuzione originale usa Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0 e threadpoolctl 3.6.0. La figura usa matplotlib 3.10.8. Le versioni sono fissate in `requirements.txt`, ripreso dall'ambiente OLC109 condiviso.

```bash
cd /percorso/OLC110_RESTORED
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r olc110/requirements.txt
python -m unittest discover -s olc110/tests -v
python -m unittest discover -s olc110/validation -p 'test_independent_reference.py' -v
python -m unittest discover -s olc110/research/policy_review -p 'test_cross_slot_admission.py' -v
python -m unittest discover -s olc110/analysis/action_diagnostics -p 'test_action_markouts.py' -v
```

La suite finanziaria principale contiene 91 test. Le altre tre chiamate esercitano il riferimento indipendente, le regressioni della revisione della policy e la diagnostica. I test non sono equivalenti alla ricostruzione dei 78 conti già documentata nei verbali originali.

## 3. Nuova simulazione senza sovrascrivere i conti congelati

Dalla directory che contiene le tre cartelle ripristinate, creare una quarta cartella nuova con codice, protocollo e input:

```bash
python - <<'PY'
from pathlib import Path
import shutil

source = Path('olc110').resolve()
target = Path('OLC110_RERUN').resolve()
target.mkdir(exist_ok=False)
for name in ('src', 'source', 'data', 'docs'):
    shutil.copytree(source / name, target / name,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(target)
PY
python OLC110_RERUN/src/run_protection.py OLC110_RERUN
```

Il runner genera 78 conti e usa l'OLC109 sorella per le repliche iniziali. Non usare `--resume` per presentare l'operazione come una nuova simulazione integrale: tale opzione salta i conti già completati. I timestamp dei nuovi manifest saranno diversi; per confrontare i risultati usare target, quantità, ordini, NAV e metriche con tolleranze dichiarate.

Per leggere i libri finanziari utilizzare `pd.read_csv(..., float_precision='round_trip')`. La nota [validation/AUDITOR_PRECISION_NOTE.md](validation/AUDITOR_PRECISION_NOTE.md) documenta la conservazione degli zeri numerici e la convenzione adottata dal revisore. Non modificare quella convenzione solo per ottenere un hash o un arrotondamento differente.

## 4. Ripetere la revisione indipendente

Su una seconda estrazione, se si desidera conservare anche tutti i verbali originari byte per byte:

```bash
python olc110/validation/run_independent_audit.py
python olc110/validation/check_aggregate_tables.py
python olc110/validation/check_prefix_causality.py
python olc110/validation/check_tamper_rejections.py
python olc110/validation/source_execution/audit_source_execution.py
python olc110/validation/source_execution/finalize_audit_notes.py
```

Questi comandi rigenerano artefatti di revisione nella copia OLC110, senza riscrivere il codice finanziario. Gli audit sorgente richiedono i dati e le evidenze precedenti ripristinati; la sola cartella Git senza l'archivio non basta a rieseguirli. Il rapporto descrive separatamente correttezza del conto, evidenza descrittiva e limiti di eseguibilità: un audit positivo non trasforma l'esito negativo delle protezioni in una promozione.

## 5. Manifest e controlli di integrità

`provenance/OLC110_SOURCE_MANIFEST.json` elenca ogni file originale OLC110, compresi i due input esterni. `REPOSITORY_MANIFEST.json` descrive i file effettivamente salvati in Git, escluso se stesso. `DATA_ARTIFACT_MANIFEST.json` collega input, archivio precedente e helper di ripristino. I file aggiunti per archiviare e ripristinare sono distinti dai risultati congelati e non introducono una nuova variante finanziaria.
