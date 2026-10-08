# L2-Q — Superpowers: checkpoint immutabile e prova tecnica leaf-refresh XGBoost 3.1.3

**2026-10-08 — test ingegneristici locali completati; nessuna integrazione nella V2 reale, nessun backtest o training sull'Original149.** Repository **solo `AM1975MA/Test`**, branch `research/target-redesign-level2-v1`; `Etf_trader` e `Trader_selector` invariati. Questo documento aggiorna il dossier [ROOT_CAUSE_XGB_HGB_EXPERT_HANDOFF](ROOT_CAUSE_XGB_HGB_EXPERT_HANDOFF.md).

## Motivazione non ripetitiva

Forensics passati provano instabilità soprattutto nel **training annuale Compact21 XGBoost**, con revisioni di input e label che separatamente producono forti differenze di scelta; i modelli sostitutivi smussati hanno sacrificato opportunità e rendimento. Non ripetere L2-D/E/F/G/H/I/J, Q4/L50, L2-N/P o full replay 2017–2026.

La verifica sorgente in `vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py` mostra che il worker fitta `xgb.train` e salva `pred_*.npy`, **non** esporta il Booster `.ubj`. `source_only/models.py::fit_predict()` accetta `scores_{year}.csv` se esiste `fit_audit_{year}.json`, senza validare in quel ramo l'identità dei dati correnti. Ciò è una lacuna ingegneristica, NON prova che i vecchi replay fossero corrotti.

## Cosa è stato effettivamente implementato

Directory [`checkpoint_contract_v1`](checkpoint_contract_v1/README.md), codice nel repo:
- [`checkpoint.py`](checkpoint_contract_v1/checkpoint.py): `create_checkpoint` conserva copie esatte di modello UBJ e input con hash SHA256, schema feature, cutoff, seed, parametri e runtime; `verify_checkpoint` fail-closed su manifest/file/expected-data/params alterati; rifiuta sovrascrittura checkpoint esistente.
- [`test_checkpoint.py`](checkpoint_contract_v1/test_checkpoint.py): otto unit test TDD, RED (modulo assente) → GREEN.
- [`xgb_refresh_probe.py`](checkpoint_contract_v1/xgb_refresh_probe.py): esperimento **sintetico** di fattibilità su 8 query da 10 record, 4 features artificiali, 12 round e un seed `rank:pairwise`.
- [`test_xgb_compat.py`](checkpoint_contract_v1/test_xgb_compat.py): due test; uno verifica struttura durante update, uno salva un vero Booster UBJ (allenato solo su dati artificiali) nel nuovo contratto e controlla predizioni bit-identiche dopo reload.
- [`PROBE_RESULTS.json`](checkpoint_contract_v1/PROBE_RESULTS.json).

Comando effettivamente eseguito nel laboratorio isolato: `python -m unittest discover -s . -p 'test_*.py' -q`. **10 test PASS, exit 0**; Python `compileall` PASS. File Python caricati nel repo hanno lunghezze compatibili con i locali: `checkpoint.py` 7089 byte, `test_checkpoint.py` 4179, `xgb_refresh_probe.py` 3226; ci sono differenze di sola serializzazione nei file test secondari/README/JSON. Non esiste CI run GitHub dei test in questo commit, quindi **non** dichiarare CI PASS. Archivio con test output e tutti i sorgenti `ETF_Trader_XGB_checkpoint_superpowers.zip`, SHA256 `6b19fa668d62cd9bb304cdcf31276019606ba27a696639297f6c015ad1cd2720`, integrity PASS.

## Scoperta tecnica concreta: QuantileDMatrix incompatibile con refresh

**Versioni testate**: Python 3.13.5, XGBoost 3.1.3, sklearn 1.8.0. Il worker originale usa una `xgb.QuantileDMatrix` con `set_group`, per training `rank:pairwise`.

- Prima prova di fattibilità, stessa `QuantileDMatrix` per `process_type=update, updater=refresh, refresh_leaf=1`: **FAIL** con errore C++ `Not implemented for QuantileDMatrix`. È una limitazione API concreta in questa versione, non un test di qualità finanziaria fallito.
- Cambiato solo il **formato dati dell'update**, da `QuantileDMatrix` a `DMatrix`, preservando query grouping, objective, dati artificiali e 12 alberi originali.
- Test nuovo **PASS**: **12 alberi originali / 12 dopo refresh**, identica struttura dei nodi (feature, threshold, yes/no/missing), **87 foglie** modificate, `max |prediction_updated - prediction_loaded| = 0`, e `max |prediction_updated - prediction_original| = 0.54975146`.
- Warning XGBoost non fatale: specificando manualmente `updater=refresh` il parametro `tree_method` viene ignorato durante update. Questo è atteso per l'updater ma richiede pinning/QA del nuovo contratto.
- Sorgente ufficiale: [XGBoost tree methods / Refresh](https://xgboost.readthedocs.io/en/release_3.1.0/treemethod.html), [Model IO in 3.1](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/saving_model.html).

**Cosa NON è stato provato:** ranker canonico 360 alberi × 3 seeds × cutoff annuali, conservazione del CAGR 43% golden, qualità Top5, equivalenza P&L, robustezza ai futuri dati o idoneità di `refresh_leaf` come sostituto economico. NON modificare parametri/hyperparameters su Original149.

## Review Superpowers e limiti della delega

Skill effettivamente letti: `using-superpowers`, `brainstorming`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `dispatching-parallel-agents`. Lo strumento **dispatch subagents** rimane **non esposto** nell'elenco delle funzioni invocabili: non sono stati chiamati falsi agenti né generate opinioni attribuite ad agenti inesistenti. Competenze ML/numerico/statistica/rischio restano documentate nel dossier, per una delega reale quando il runtime la supporta. In questa sessione lo sviluppo del laboratorio è stato eseguito direttamente.

## Gate raccomandato prima della possibile integrazione

1. Recuperare il modello corretto nel preciso cutoff (non ricostruire il 2017 con conoscenze del 2026), salvare UBJ per 2 orizzonti × 3 seed × anno, tutti i manifest dati/target/preprocessori, ExtraTrees e stato MA3/KMeans; ogni input e training cohort deve essere causale ed effettivamente verificato, non solo attestato nel manifest.
2. Espandere la verifica checkpoint con lock tra processi, firma/autenticità manifest, atomic no-replace multiprocesso, sicurezza symlink, memoria/spazio per archivi grandi e versioning corporate actions. Lo schema v1 è dimostrativo non pronto per produzione.
3. Collegare il checkpoint **in `Test`** senza alterare output modello/portfolio; dimostrare per un fit controllato che UBJ reload produce gli stessi scores e che la cache si invalida alla variazione dei byte del training. Usare solo test minimi nuovi, non rilanciare intere batterie già svolte.
4. Soltanto dopo considerare un **singolo** esperimento economico preregistrato aggiornando le foglie: controllo rigoroso `rank:pairwise + DMatrix`, 360 alberi per seed, input asset raggruppati, preservazione di split, chronology. Gate di non inferiorità CAGR per *ciascuna vintage* V2 FULL, MaxDD giornaliero e stabilità; vietato ottimizzare sullo storico già studiato.

**Decisione:** la conservazione del modello/data-lineage è un intervento di ingegneria giustificato senza ridisegnare ETF Trader. `refresh_leaf` è tecnicamente possibile con `DMatrix`, non ancora un miglioramento finanziario dimostrato.
