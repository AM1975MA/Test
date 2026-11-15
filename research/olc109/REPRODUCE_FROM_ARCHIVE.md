# Riprodurre OLC109 dal salvataggio congelato

## 1. Recuperare l'archivio e verificare tutti i file

Scaricare [OLC109_RICERCA_ETF_20261115.zip](https://chatgpt.com/library?file_id=libfile_78a392f2bcac81919669f3fd5cbee900&account_id=personal). Occorre poter accedere al file nella conversazione; il collegamento non è un URL di download anonimo.

L'archivio contiene lo studio completo `olc109/` e il sottoinsieme di supporto `olc108/` necessario ai revisori: 2.096 CSV prezzo, cataloghi sorgente e 11 percorsi precedenti disponibili. Contiene anche i pannelli `.npz`, gli snapshot, tutte le decisioni e tutti i conti delle 200 simulazioni. Non include l'intera acquisizione HTTP originale OLC108, come dichiarato nel README congelato.

Dalla radice del checkout di Test, indicare il file scaricato e una directory nuova. Sostituire i due percorsi di esempio con percorsi locali reali:

```bash
python3 research/olc109/tools/restore_bundle.py \
  --archive /percorso/OLC109_RICERCA_ETF_20261115.zip \
  --destination /percorso/OLC109_RESTORED
```

Il comando richiede Python 3.11 o successivo e solo la libreria standard. Verifica il SHA-256 dell'intero ZIP, il manifest incorporato, l'elenco esatto dei membri, tutte le dimensioni e tutti i 3.577 SHA-256 prima di rendere disponibile la directory finale. La destinazione deve essere inesistente. Per verificare senza estrarre, sostituire `--destination ...` con `--verify-only`.

Conservare `olc109/` e `olc108/` come directory sorelle. Le posizioni assolute storiche presenti nei verbali sono provenienza dell'esecuzione originale: i runner e i revisori risolvono i dati dalla directory del progetto o dagli argomenti indicati.

## 2. Ambiente e test

Entrare nella directory estratta, creare un ambiente dedicato e installare le versioni fissate:

```bash
cd /percorso/OLC109_RESTORED
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r olc109/requirements.txt
python -m unittest discover -s olc109/tests -v
```

L'esecuzione originale usa Python 3.12.14. Le dipendenze e i loro numeri di versione sono in `requirements.txt` e nei manifest. La suite attesa è di 51 test; il riferimento `research/engine/olc108_engine_reference.py` e la fixture `source/data/TR29.npz` sono inclusi sia in Git sia nell'archivio.

## 3. Ricostruire i 200 percorsi in una copia nuova

Sempre dalla directory `OLC109_RESTORED`, il blocco seguente copia codice e input in una directory nuova. I file finanziari originali estratti rimangono intatti:

```bash
python - <<'PY'
from pathlib import Path
import shutil

source = Path('olc109').resolve()
target = Path('OLC109_RERUN').resolve()
target.mkdir(exist_ok=False)
for name in ('src', 'source', 'data', 'docs'):
    shutil.copytree(source / name, target / name,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
print(target)
PY
python OLC109_RERUN/src/run_research.py OLC109_RERUN
python OLC109_RERUN/src/run_stage2.py OLC109_RERUN
python OLC109_RERUN/src/run_stage3.py OLC109_RERUN
```

I tre blocchi producono rispettivamente 110, 50 e 40 percorsi. Non usare `--resume` per una simulazione integrale: salta le directory già completate. I manifest rigenerati hanno nuovi timestamp; per confrontare la finanza usare target, NAV, ordini e metriche con tolleranze numeriche esplicite. Leggere i CSV finanziari con `pd.read_csv(..., float_precision='round_trip')` come spiegato in `validation/AUDITOR_PRECISION_NOTE.md`.

Il pannello `data/LIQUIDITY.npz` è già congelato nell'archivio. Se serve ricostruirlo dai CSV sorgente sulla sola copia:

```bash
python OLC109_RERUN/src/prepare_liquidity.py OLC109_RERUN olc108
```

## 4. Ripetere revisione e analisi

I revisori richiedono i file completi estratti, compresi quelli omessi da Git. Per conservare anche i verbali originari, estrarre una seconda copia con `restore_bundle.py` in una destinazione nuova e lavorare in quella copia. I seguenti comandi rigenerano la revisione dei tre blocchi:

```bash
python olc109/validation/run_independent_audit.py
python olc109/validation/run_independent_audit.py --results-directory results_stage2 --output-directory validation/stage2
python olc109/validation/run_independent_audit.py --results-directory results_stage3 --output-directory validation/stage3
```

La sequenza completa di causalità, manomissione, precisione CSV, prezzi, bootstrap, confronti sullo stesso conto e audit sorgente è in [README_IT.md](README_IT.md), sezione «Ripetere i controlli e le analisi». Va eseguita dalla radice estratta che contiene le due directory sorelle. Per il solo confronto del candidato, i cinque conti già presenti in Git mantengono nomi e byte originali, senza decompressioni o conversioni.

## Provenienza e confini

`provenance/BUNDLE_MANIFEST.json` è la copia esatta del manifest dello ZIP. `REPOSITORY_MANIFEST.json` identifica le copie in Git e gli strumenti aggiunti per l'archiviazione. Le differenze fra l'archivio completo e il salvataggio in Git sono intenzionali e dichiarate in `DATA_ARTIFACT_MANIFEST.json`; non sono risultati mancanti o simulazioni eliminate dalla selezione.
