# OLC74 — Allocazione Top2: informazione ex ante, interventi a stato comune e QA

**8 novembre 2026 — research-only, nessuna modifica a main/OLC19/OLC67.**

Sono inclusi tre esperimenti (i protocolli B/C sono stati registrati DOPO aver visto il precedente esperimento, ma PRIMA degli outcome propri). Tutti i test 2019–luglio2026 sono retrospettivi e già ripetutamente esplorati nei precedenti OLC. Non sono prove di futura profittabilità né trading reale.

## Riprodurre da archivi originali
Servono in `/mnt/data` i checkpoint **immutati**:

- `/mnt/data/OLC73_Allocation_20261108/` estratto dal precedente `OLC73_Allocazioni_Top2_20261108_VERIFICATO.zip`, inclusi `OLC67/native/olc19_combined_risk_20261102` e `results/OLC73_DAILY_LOGRET.csv.gz`.
- `/mnt/data/etf_source/OLC16_Input_Code_Checkpoint_20261102.zip`.
- `/mnt/data/etf_source/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`.
- `/mnt/data/OLC73_Allocazioni_Top2_20261108_VERIFICATO.zip` (hash verificato prima dell'esperimento).

Dipendenze Python: numpy, pandas, scipy, scikit-learn, loader originale OLC19 dal checkpoint, Python 3.10+ e ambiente numerico compatibile con il motore OLC19. Nessun download di quotazioni necessario.

```bash
python run_olc74.py
python run_olc74b.py
python run_olc74c.py
python analyze_olc74.py
python verify_olc74_independent.py
python verify_olc74c_independent.py
python build_report.py
```

Per OLC74C, `original_olc70_reference/run_olc70.py` è la stessa funzione `state_matched_engine` usata e verificata in OLC70. Instrumenta in memoria la sorgente originale OLC19 senza modificarne i file.

## Metodo

- A: 7 policy × 2 timings × 2 mercati × 2 fee = 56 contabilità native; label Open-next-month e 6 feature as-of + missingness indicator; Ridge/Logit train expanding mensile con lag di 2 mesi.
- B: 45 coppie per Top10 mensile, simmetria di permutazione della coppia e pesi uguali per mese; due nuovi modelli ×2 timing×2mercati×2fee =16 replay, senza selezionare i vincitori ex post.
- C: fork mensili da **stesso stato** per w1=.25,.50,.75, 89 eventi ciascun mercato, tre rami potenziali e quarto ramo per la policy scelta. Le label controfattuali maturano da evento t a t+2; la policy corretta segue un unico portafoglio continuativo. 2 mercati×2 fee=4 full replay. Tutti i sette array nativi coincidono bitwise fra simulazione a segmenti e full replay di verifica.
- Totale 76 replay completi; 684 ricalcoli indipendenti di CAGR+MaxDD e 608 rendimenti annuali. Ricostruzione A del controllo HALF/OLC19 esatta sulle sette matrici; confronto log-return giornalieri OLC73 per HALF e MINVAR63 entro 1e-13.

## File principali

`REPORT_OLC74_IT.md`, `PROTOCOL_A_REFERENCE.md` (link al protocollo A immutato GitHub), `PROTOCOL_B_PRE_RESULTS.md`, `PROTOCOL_C_PRE_RESULTS.md`, `results/OLC74_PAIR_PANEL.csv` (feature e target), `results/OLC74B_TOP10_PAIR_POOL.csv.gz`, `results/OLC74C_ON_POLICY_COUNTERFACTUAL_LABELS.csv`, `results/OLC74_SCORECARD.csv`, `results/OLC74B_SCORECARD.csv`, `results/OLC74C_SCORECARD.csv`, tre `DAILY_LOGRET.csv.gz` con 76 percorsi, pesi per segnale, skill e QA. Il manifest contiene i checksum SHA256 dei file presenti.

## Limitazioni

Gli intervalli bootstrap non correggono i moltissimi esperimenti OLC precedenti; il FULL non è OOS. In Europa sono disponibili i flag di prezzi effettivamente osservati; nella copia nativa USA manca la maschera originale. I prezzi di esecuzione degli stop sono simulati secondo il motore, e non confermati da quotazioni broker. Le condizioni di efficacia causale hanno senso soltanto sotto l'ipotesi del simulatore a prezzi fissi (nessun market impact). Non confondere pesi di capitale e causalità della performance dei sottostanti.

## Versionamento

GitHub branch `research/olc74-top2-exante-allocation-20261108`, protocolli A/B/C registrati prima dei rispettivi risultati, `main` invariato. I checksum delle sorgenti congelate sono nel protocollo e in `results/OLC74_QA.json`.