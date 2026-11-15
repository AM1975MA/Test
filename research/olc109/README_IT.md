# OLC109 — Ricerca ETF, 15 novembre 2026

## Risultato e obiettivo corrente

Sono presenti **40 configurazioni e 200 percorsi finanziari**: ciascuna configurazione è simulata in cinque scenari di costo/esecuzione. Il candidato `DEDUP_DUAL_TREND_OPP` raggiunge **25,7526% di CAGR BASE**, contro **22,3751%** del precedente `DUAL21`, dal 2 marzo 2020 al 30 ottobre 2026. EUR 10.000 diventano EUR 46.045,58. Il drawdown campionato Open/Close è -37,92%.

L'obiettivo del 30% annuo rimane aperto: nessun percorso lo raggiunge, neppure senza costi. L'utente ha accettato drawdown maggiori e rinviato la protezione; **DD e Calmar non sono criteri di esclusione correnti**. Le configurazioni protette già completate restano disponibili come evidenza storica.

Il miglior candidato è stato individuato dopo i test. Tutti i risultati sono esplorativi: il periodo è già stato osservato e i blocchi 2 e 3 sono adattivi. L'audit verifica calcoli e regole, non certifica rendimenti futuri, liquidità di esecuzione o un universo storico privo di survivorship bias.

## Da leggere

| File | Contenuto |
| --- | --- |
| `RAPPORTO_OLC109_IT.md` | Risultati, regole, confronti, limiti e tabella completa delle 40 configurazioni |
| `figures/OLC109_RISULTATI_PRINCIPALI.png` | Capitale, costi/ritardi, tutti gli anni e rendimento/drawdown |
| `analysis/ALL_SCORECARD.csv` | Tutte le 200 righe, metriche non arrotondate |
| `analysis/ALL_ANNUAL_RETURNS.csv` | Tutti i rendimenti annuali, incluso il 2024 |
| `analysis/PAIRED_COMPARISONS.csv` | 16 confronti e intervalli bootstrap descrittivi |
| `analysis/MATCHED_STATE_INTERVALS.csv` | 160 intervalli comparati partendo dallo stesso conto |
| `validation/INDEPENDENT_REVIEW_IT.md` | Revisione indipendente di conti, segnali e analisi |
| `validation/COMBINED_QA.json` | Riconciliazione di 200 percorsi e 49.055 ordini |
| `validation/source_execution/AUDIT_NOTES.md` | Prezzi, aggiustamenti e partecipazione ai volumi |
| `docs/OBJECTIVE_UPDATE.md` | Aggiornamento dell'obiettivo richiesto dall'utente |

I campi `numeric_target_pass` e `operational_pass` nei risultati finanziari congelati conservano le definizioni originarie. Nella tabella aggregata i campi **`current_cagr_target_pass`** e **`current_drawdown_limit_active`** applicano l'obiettivo aggiornato a tutte le 200 righe. Il confronto principale con il 30% usa le righe `scenario == BASE`.

## Contabilità e universo

- 2.096 ETF con serie EUR su Xetra nel pannello ammesso V3. L'idoneità è calcolata per data. Questo non rappresenta tutti gli ETF mondiali né un catalogo storico completo dei fondi cessati.
- Il prezzo di quotazione in EUR non implica copertura del rischio di cambio sottostante.
- Capitale iniziale EUR 10.000; unità economiche frazionarie, cassa senza rendimento, imposte escluse.
- `BASE`: EUR 1 per ordine più 15 bp del controvalore di ogni lato. `ZERO_COST`: nessun costo. `DOUBLE_COST`: EUR 2 più 30 bp. `LAG1` e `LAG2`: costi BASE e una/due sedute aggiuntive rispetto all'esecuzione ordinaria.
- Segnali dopo Close, esecuzione al successivo Open disponibile secondo le regole congelate, banda di ribilanciamento 3%. Nessuna leva di conto e nessuno short.
- La maschera degli Open accettati usa retrospettivamente il volume positivo della giornata completata. Il vintage storico dei fattori di aggiustamento non è certificato. Questi limiti non sono eliminati dall'audit.
- Il drawdown osserva Open e Close, non tutti i minimi intraday. Le verifiche dei volumi della singola sede non certificano il prezzo ottenibile all'asta.

## Struttura dell'archivio

Estrarre in una cartella nuova mantenendo le due directory sorelle `olc109/` e `olc108/`.

`olc109/` contiene codice finanziario, protocolli congelati, dati accettati, risultati completi, analisi, test e revisori. `results/`, `results_stage2/` e `results_stage3/` contengono rispettivamente 110, 50 e 40 percorsi. Per ogni percorso sono presenti NAV giornalieri, ordini, istruzioni, decisioni e metriche.

La directory sorella **`olc108/` è un sottoinsieme di supporto**, non l'intero progetto precedente. Include i 2.096 CSV di prezzo ammessi, la mappa ISIN/simbolo, i cataloghi di eventi sorgente e aggiustamenti necessari all'audit e gli 11 percorsi di confronto precedenti disponibili. Il file sotto `superseded_v2/` conserva un catalogo di eventi, non risultati finanziari V2 utilizzati come evidenza corrente. I quattro stress passivi precedenti non esistevano e restano dichiarati non disponibili.

Il pacchetto permette di ricostruire contabilità, selezioni e liquidità a partire dai dati congelati. Non duplica tutte le risposte HTTP grezze e l'intera acquisizione/normalizzazione del catalogo OLC108. Per la provenienza completa di quella fase rimane disponibile l'archivio precedente: [OLC108 V3](https://chatgpt.com/library?file_id=libfile_52187d5941cc8191945bc3296f19a5ea&account_id=personal).

`BUNDLE_MANIFEST.json`, nella radice dell'archivio, elenca dimensione e SHA-256 di ogni file incluso, escluso se stesso. I manifest di ciascun esperimento rimangono la fonte delle impronte del codice, dei protocolli e degli input finanziari. Gli orari originali e i percorsi assoluti presenti nei verbali sono provenienza dell'esecuzione iniziale.

## Ambiente

Esecuzione originale: Python **3.12.14**, NumPy **2.3.5**, pandas **2.2.3**, SciPy **1.17.0**, threadpoolctl **3.6.0**. Il grafico usa matplotlib **3.10.8**. I test usano `unittest`, incluso in Python. Le dipendenze sono fissate in `requirements.txt`.

Da un ambiente Python dedicato:

```bash
python3 -m pip install -r olc109/requirements.txt
python3 -m unittest discover -s olc109/tests -v
```

La suite attesa contiene 51 test. È stata eseguita con esito positivo; i controlli indipendenti dei risultati sono più estesi della sola suite locale.

## Ripetere i 200 percorsi senza modificare gli originali

Eseguire dalla directory che contiene `olc109/` e `olc108/`. Il seguente blocco crea una directory nuova e fallisce se esiste già:

```bash
python3 - <<'PY'
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
python3 OLC109_RERUN/src/run_research.py OLC109_RERUN
python3 OLC109_RERUN/src/run_stage2.py OLC109_RERUN
python3 OLC109_RERUN/src/run_stage3.py OLC109_RERUN
```

I tre runner scrivono esclusivamente sotto la radice passata. Confrontare le metriche, i target, i NAV e gli ordini con le copie originali, ammettendo soltanto tolleranze numeriche esplicite; i timestamp dei nuovi manifest saranno diversi. **`--resume` salta i percorsi già completati: non equivale a una nuova simulazione integrale.**

Il pannello `LIQUIDITY.npz` è già incluso. Per ricostruirlo nella nuova cartella dai CSV di supporto:

```bash
python3 OLC109_RERUN/src/prepare_liquidity.py OLC109_RERUN olc108
```

Questa operazione aggiorna il manifest di liquidità della sola copia; non è necessaria per eseguire i conti con il pannello congelato.

## Ripetere i controlli e le analisi

I seguenti comandi, dalla radice estratta, rigenerano verbali di audit e tabelle di analisi. Non cambiano codice finanziario, segnali o risultati originali. Se si desidera conservare byte per byte anche i verbali, eseguirli su una seconda copia dell'archivio.

```bash
python3 olc109/validation/run_independent_audit.py
python3 olc109/validation/run_independent_audit.py --results-directory results_stage2 --output-directory validation/stage2
python3 olc109/validation/run_independent_audit.py --results-directory results_stage3 --output-directory validation/stage3
python3 olc109/validation/check_tamper_rejections.py
python3 olc109/validation/check_csv_precision_regression.py
python3 olc109/validation/check_prefix_causality.py
python3 olc109/validation/check_held_price_age.py
python3 olc109/analysis/analyze_results.py olc109
python3 olc109/analysis/matched_state_trend_gate.py olc109
python3 olc109/validation/check_analysis_bootstrap.py
python3 olc109/validation/check_matched_state_review.py
python3 olc109/validation/build_audit_report.py
python3 olc109/validation/source_execution/audit_source_execution.py --results results results_stage2 results_stage3
python3 olc109/validation/source_execution/finalize_audit_notes.py
python3 olc109/analysis/build_report.py olc109
python3 olc109/analysis/build_figure.py olc109
```

Per i CSV finanziari usare `pd.read_csv(..., float_precision='round_trip')`. Il parser predefinito può azzerare un residuo di unità economiche di ordine 1e-12 e cambiare un contatore descrittivo di rinvio; la nota specifica è in `validation/AUDITOR_PRECISION_NOTE.md`.

## Lettura corretta delle evidenze

Gli intervalli bootstrap sono intervalli descrittivi della media annualizzata dei log-rendimenti relativi mensili; non sono intervalli della differenza dei CAGR. Tutti i 16 intervalli includono zero e non correggono la scelta dopo molte prove. I confronti sullo stesso stato contabile sono intervalli separati: le loro medie in punti base non sono composte né annualizzate.

I test di concentrazione Top1 e di allocazione fra tre orizzonti sono inclusi anche quando peggiorano. L'obiettivo del 30% non viene dichiarato raggiunto per arrotondamento, eliminazione dei costi o esclusione degli anni sfavorevoli. L'iterazione termina con un candidato migliore da approfondire e una misura esplicita dei suoi limiti.
