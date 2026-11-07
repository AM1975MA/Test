# OLC70 — Controfattuali da stato identico e routing adattivo (7 novembre 2026)

**Esito: NEGATIVO, ricerca soltanto.** Il nuovo learner non supera la baseline OLC19 in USA e non sostituisce OLC67. OLC19 operativo e GitHub `main` non sono stati modificati.

## Contenuti

- `REPORT_OLC70_IT.md`: rapporto e CAGR/MaxDD/anni 2024–2026 verificati.
- `run_olc70.py`: 4 branches mensili dallo stato pre-evento **del controllo OLC19**, e routing che li usa in training. Implementa engine instrumented come derivazione non distruttiva del codice nativo.
- `run_olc70b.py`: 4 branches mensili dallo stato del **conto adattivo effettivo**, uno solo dei quali viene consolidato. Rifà il conto completo e controlla la parità bitwise su 7 matrici.
- `verify_and_summarize.py`: ricalcola CAGR/MaxDD, controlla etichette, date as-of, maturità train, azioni e pubblica tabelle comparative.
- `build_report.py`: ricompone il rapporto dai risultati congelati, senza training.
- `restore_inputs.py`: ripristina l'engine nativo, controllando SHA256 di ogni input.
- `engine_olc70_instrumented.py.txt`: sorgente Python dell'engine OLC19 come instrumentato dall'esperimento; solo a fini di audit.
- `results/`: tutte le etichette e le curve giornaliere OLC70A/B, 2 commissioni, confronto OLC19/67, diagnostica delle skill e audit.
- `inputs/`: gli input originali identificati per hash, inclusi `OLC67_Strategia_ETF_Verificata.zip` + pacchetto integrativo del suo engine nativo conservato nel bundle OLC69, e le feature pre-segnale OLC68.

## Riproduzione autonoma (Python >=3.10)

Estrarre questo archivio preservando le directory; entrare in `OLC70/`:

```bash
python -m pip install numpy pandas scikit-learn
python restore_inputs.py
python run_olc70.py --source ./inputs
python run_olc70b.py --source ./inputs
python verify_and_summarize.py
python build_report.py
```

I comandi rigenerano tutti i CSV e QA. **Non** modificano i file di origine OLC19/OLC67 né scrivono sul repository.

## Controlli metodologici

- Protocollo A GitHub commit `9e8c1331c26639ea060385934e1e88438eda2c9e`, fissato prima degli esiti OLC70A.
- Protocollo B GitHub commit `59b3dc39a72cf3e674aef25e48ab2fe46e195d71`, aggiunto dopo OLC70A e **prima** degli esiti on-policy OLC70B.
- Lo stesso setup di OLC69 (4 feature, StandardScaler/Ridge alpha25, 24 label mature, t-2, soglia +5 logbp) è mantenuto senza ottimizzazione.
- Due mercati EU165 e USA149; 89 mensilità valutabili e 4 azioni per mercato (712 rami) per ciascuno degli esperimenti OLC70A e OLC70B. Nessuna selezione ex-post degli esiti migliori per trading.
- 20 comparazioni di periodo per variante, confrontate contro rendimento giornaliero e drawdown ricalcolati indipendentemente.
- Nessuna nuova valida prova fuori campione: la serie 2019–luglio2026 è già ampiamente esplorata. Quotazioni, stop ed esecuzioni reali non certificati.

## Conclusione

Il confronto common-state risolve un problema legittimo delle etichette del test OLC69. Ma senza un segnale ex ante predittivo della convenienza di pesi e ritardo, lo switching peggiora l'USA. Nessuna promozione a trading o main.