# OLC100 — Controlli eseguiti e validazione prospettica

Stato al 12 novembre 2026: **48 replay storici verificati; nuovi prezzi USA certificati entro lo scopo; nessuna prova prospettica valida**.

## Contenuto

- `REPORT_OLC100_IT.md`: report completo e limiti.
- `run_olc100_controls.py`: ripete i sei bracci OLC100 sui dati OLC19 congelati; 2 mercati × 2 fee × 2 frizioni = 48 replay. Ricostruisce MINVAR63 in modo indipendente e controlla parità OLC19/OLC67.
- `audit_olc100_bridge_prices.py`: verifica la sorgente USA149 GitHub del 24 ottobre 2026 e compatibilità con i prezzi OLC19 al 1 luglio. Non emette nuove coppie Top2 o NAV forward.
- `validate_olc100_forward_packet.py`: rifiuta segnali con lookahead, regole alterate o senza gli snapshot obbligatori. Una verifica offline non è una ricevuta GitHub temporale indipendente.
- `test_olc100_packet.py`: sette test automatici.
- `results/`: scorecard, log giornalieri, contrasti per layer, diagnostica OHLCV e QA JSON.

## Riproduzione

Python 3.10+ con `numpy`, `pandas`, `scipy`, `scikit-learn`, `tabulate` (per rigenerare il report). Restaurare senza alterazioni tre archivi originali:

- `OLC98_Model_Review_Completa_20261112_VERIFICATO.zip` in una cartella locale con `OLC98_Model_Review_20261112/`.
- `OLC56_TESTS_20261106_VERIFICATI.zip` con cartella sorella `OLC56_ROBUST_20261106/`.
- `OLC67_Strategia_ETF_Verificata.zip` con cartella sorella `OLC67/`.

Disporre nella cartella `--archives` **tutti e cinque** gli ZIP originali elencati in `research/olc100/ARCHITECTURE_LOCK.json`, incluse le copie OLC19 e OLC99. Gli hash sono verificati prima di partire.

```bash
python -m unittest -v test_olc100_packet.py
python run_olc100_controls.py --archives /path/archivi --root /path/OLC98_Model_Review_20261112 --out ./results
python audit_olc100_bridge_prices.py --zip /path/V3_149_FORWARD_20261024.zip --root /path/OLC98_Model_Review_20261112 --out ./results
python validate_olc100_forward_packet.py --packet /path/segnale_preoutcome.json
```

Per l'ultimo comando serve un **segnale nuovo effettivo**: in sua assenza restituisce un errore intenzionale, perché non è possibile affermare che esistano nuovi risultati prospettici.

I prezzi USA provengono dal [workflow GitHub](https://github.com/AM1975MA/Test/actions/runs/40082539622), artefatto `v3-forward-frozen-149-raw-20261024` (`12555507287`), reperibile finché non scade. Il dataset di circa 26 MB **non è duplicato nello ZIP OLC100**. Lo SHA256 del pacchetto recuperato è registrato nel QA del bridge. Non usare il ranker del V3 come sostituto del diverso ranker OLC19.

**Nessun dato viene trasmesso a broker e nessuna strategia reale viene modificata.**
