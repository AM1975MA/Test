# ETF Trader V2 — Spec di integrazione checkpoint XGBoost e provenienza dati
**Spec di progettazione Superpowers | 2026-10-08 | SOLO `AM1975MA/Test` | branch `research/target-redesign-level2-v1`**

**Stato:** design proposto per revisione dell'utente; **non implementato e non approvato per la V2 reale**. Non modifica `Etf_trader` o `Trader_selector`. L'utente ha già approvato la direzione generale: preservare la V2 e rendere riproducibile il training, evitando nuovi test finanziari già eseguiti. Prima di un'integrazione ampia Superpowers richiede revisione di questa specifica e successivo piano esecutivo.

## 1. Scopo, criteri e non-obiettivi

### Scopo
Eliminare **refit accidentali e cache di previsioni obsolete** dovuti a revisioni silenziose delle serie storiche, rendendo identificabile ogni run annuale e ogni predizione tramite la sua precisa origine. Preservare la qualità non lineare del Compact21 XGBoost canonico (125 features, `rank:pairwise`, 3 seed 101/202/303, orizzonti 21/63, parametri/360 iterazioni invariati), MA3, allocazione e risk execution.

### Successo della Fase 1
- Con input e modello *identici*, score della modalità checkpoint = score dell'esecuzione canonica (equivalenza numerica appropriata fino alla precisione attesa; preferire byte-identità per output nello stesso processo/runtime).
- Re-ingestione di input identici -> riutilizzo checkpoint senza alcun fit XGBoost; modifica di *uno* dei byte di feature/label/group/params/code/runtime -> FAIL CLOSED, mai caricare il vecchio modello come se fosse compatibile.
- Sola modifica delle caratteristiche di inferenza non impone retraining del modello, ma invalida le *previsioni* in cache.
- Maturità delle label `exit_date_h < cutoff` verificata su dati reali, non semplicemente dichiarata nel manifest.
- Vecchi score annuali senza modello o manifest completi sono **legacy read-only**, non checkpoint con prova di parità; non ricostruire artificialmente i booster Golden.
- Nessuna modifica ai rendimenti del sistema canonico su base invariata; nessun nuovo backtest sui 149 ETF è richiesto per la semplice definizione del contratto.

### Non-obiettivi
- Nessun intervento su obiettivi, feature, pesi, stop, MA3 producer, HighCAGR24, V6 o prezzi.
- Nessun tentativo di recuperare 43.145952% Golden con nuovo training sui dati Yahoo 2026.
- Nessun `refresh_leaf`, nuovi ensemble, smoothing, Ridge/HGB, modifiche a soglie o seed nella Fase 1.
- Non confondere **riproducibilità del checkpoint** con **robustezza intrinseca dei futuri fitted trees** o validazione economica prospettica.

## 2. Evidenze e limiti già verificati — NON RIPETERE

- `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json`: inferenza-input-only Top1 0% diverso, training-X-only 62.5%, training-Y-only 58.33% su 4 annualità diagnostiche; non additive.
- `target_redesign_level2_v1/L2D_RESULTS.md`: stesso inference input, XGB Top1 agreement ~45–57%, Ridge 100% ma perdita capacità selezione delle opportunità estreme.
- `compact21_stability_v1/results/FULL_REPLAY.json`: full V2 Repeat1 29.75%, Repeat2 30.84%, Repeat3 34.68%; nessuna equivalenza con Golden 43.146% su vintage differente.
- `target_redesign_level2_v1/L2Q_SUPERPOWERS_CHECKPOINT_RESULTS.md`: prototipo di archiviazione hash con 10 test sintetici PASS; leaf refresh compatibile con `DMatrix` ma non `QuantileDMatrix` in XGBoost3.1.3. **Il prototipo NON è integrato**.
- `vendor/etf_trader_v2/src/etf_trader/source_only/_xgb_worker.py`: fit `xgb.train`, salva `pred_*.npy`, non `.ubj`.
- `vendor/etf_trader_v2/src/etf_trader/source_only/models.py`: cache `scores_{year}.csv` accettata se `fit_audit_{year}.json` esiste; manca check dei contenuti dei dati correnti sul cache-hit.
- `vendor/etf_trader_v2/src/etf_trader/ma3/hybrid_producer.py`: ExtraTrees+XGB annuali e preprocessing indipendenti; repository include stato di KMeans dinamico in `source_only/a4_cluster_destination.py`. Va coperto a posteriori nello stesso contratto globale, senza modificarne i calcoli.

## 3. Alternative considerate

A. **Solo freeze del CSV `scores_YEAR.csv`**: semplice, nessun rischio P&L sul vecchio dataset, ma incapace di riprodurre il modello, verificare la compatibilità di un nuovo input o fare update as-of: insufficiente.
B. **Checkpoint immutabile content-addressed per fit + separata cache inferenza**, con adattatore esclusivamente in Test e modalità `shadow` iniziale: **scelta raccomandata**. Preserva il ranker e dà prova verificabile di quali bytes l'hanno generato.
C. **Integrazione subito di leaf-refresh/nuovo training**: affronta ipoteticamente la fragilità del fitting, ma modifica il segnale economico e rischia perdita di CAGR; vietata prima del checkpoint e senza un confronto causale nuovo.

## 4. Confini implementativi della Fase 1

Sviluppare isolatamente in `target_redesign_level2_v1/checkpoint_contract_v2/`; NON modificare `vendor/etf_trader_v2`, `Etf_trader`, trading engine o parametri.

Componenti distinti:
1. `identity.py`: produce due digest canonici, uno per `FitIdentity` (anno, horizon, seed, cutoff, `Xtr` NaN normalized serialization, `y`, `groups`, `rowkeys`, feature schema ordered, XGB `params` including rounds, code/blob/runtime versions and feature-source hashes) e uno per `PredictionIdentity` (model digest, `Xte`, ordered inference keys, model/predict configuration). **Inferenza non appartiene alla fit identity**.
2. `archive.py`: salva Booster `model.ubj`, copie esatte npz train/labels/groups/meta, `manifest.json` content-addressed; no silent overwrite, immutabilità e atomic publish. `training_exit_before_cutoff` deve derivare dal confronto effettivo di ogni `exit_date_h`, non da un boolean dell'utente. Input critici devono essere confrontati su bytes canonicalizzati, non su soli nomi file.
3. `worker_adapter.py`: collega in modalità separata il worker canonico: `fit_and_save`, `load_and_predict` e `validate`, con stesso `QuantileDMatrix` e `set_group` in FIT, stesso numero di round e stream RNG; nessun `refresh` o cambio di objective. Quando il checkpoint esiste, validarLo; se fingerprint mismatch, arrestare con errore esplicito (NON usarlo, NON sovrascriverlo, NON fare fallback automatico a retraining).
4. `prediction_cache.py`: keys (FitIdentity + PredictionIdentity), storing float64/float32 exactly as produced and sha; never reuse predictions when Xte, date/ticker availability, feature schema or effective model hash differs.
5. `tests/test_*.py`: red-green TDD con dataset sintetico raggruppato, senza istanze finanziarie reali, e confronto all'output del worker source-only **solo su input sintetici**. File di spec è design, non autorizza da solo implementazione.

**I nomi sono proposti per il successivo piano TDD**; eventuali singole file division devono seguire responsabilità e dimensioni della libreria esistente.

## 5. Integrazione a due livelli, sequenziale

### Livello A — Compact21 sul sorgente canonico
`_fit_compact_rankers_isolated()` crea due dataset `data_{21/63}.npz` con `Xtr,Xte,y,groups` da feature ordinatamente selezionate, e tre fit isolati per orizzonte; il codice attuale elimina scratch. La nuova modalità di laboratorio intercetta `data_h.npz` prima dell'eliminazione, conserva *solo le matrici mature train* nel checkpoint (più origine e schema), salva `Booster.save_model(model.ubj)` dal worker, verifica lo score prodotto dal Booster appena salvato e dal Booster ricaricato, poi usa le stesse predizioni per produrre `compact21`/`compact63`. I fit canonici precedenti privi di booster vengono etichettati `LEGACY_PREDICTION_ONLY` e non falsamente convertiti in checkpoint causali.

Due distinte firme: un retraining è consentito soltanto con un nuovo `FitIdentity` as-of (es. nuove label finalmente maturate all'anno successivo); i prezzi vecchi revisionati non devono alterare retroattivamente un vecchio FitIdentity senza l'esplicita creazione di una **nuova** versione di training. Il controllo del vendor historical diff non è una regola che scarta automaticamente dati corretti: versiona entrambi gli stati.

### Livello B — MA3 e altri stati
Dopo passaggio test del livello A, congelare gli oggetti ExtraTrees, XGB regressor e `SimpleImputer` fitted di MA3 e i relativi `FEATURES_42`, cutoff e label maturate. I componenti che usano PCA/KMeans e cluster remapping richiedono un **snapshot di stato e provenienza di tutte le date precedenti**, poiché un nuovo fit dei cluster può cambiare features future. Non serializzare oggetti `pickle/joblib` non attendibili; se usati in un archivio localmente trusted, indicarne esplicitamente il rischio di deserializzazione. Separare lo stato dei cluster dal run giornaliero; non apportare modifiche ai calcoli esistenti.
**La Fase 1 non cambia MA3**, e la V2 full-data release non può dichiararsi `fully reproducible` prima che sia coperto il Livello B.

## 6. Invarianti tecnici e sicurezza

- Cutoff: per ogni riga di training `signal_date < cutoff` e `exit_date_h < cutoff`. `sum(groups) == len(Xtr) == len(y) == len(rowkeys)`; gruppi e query ordinati; nessuna chiave duplicata; feature ordered schema esatto. Nessun fit sui dati di futuro.
- Fail-closed su ogni mismatch; logging dei due digest, seed, horizon, rows e data source revision; distinguere `CACHE_HIT_VALIDATED`, `FIT_NEW_IMMUTABLE_VERSION`, `CACHE_STALE_REJECTED`, `LEGACY_READ_ONLY`.
- Filesystem: directory temporanea nello stesso FS, `fsync` esplicito, atomic publish che non possa **rimpiazzare** destinazione già esistente anche in race multi-processo; lock o contenuto object-store per `FitIdentity`; verifica symlink/path traversal; no write nel repo in run.
- Authenticity: checksum SHA256 protegge dagli errori e revisioni accidentali, non è una firma digitale. Documentare firma/ACL se rischio di manomissione; nessuna chiave privata nel repository.
- Environment parity: pin Python, numpy, XGBoost, filesystem sort, locale/encoding; `QuantileDMatrix` da train originale non deve essere trasformata in `DMatrix` nel fit canonico. Il `DMatrix` è ammesso solo nell'eventuale Fase 2 separata di `refresh`.

## 7. Test da sviluppare, senza ripetere vecchi esperimenti finanziari

**TDD RED-GREEN:**
1. FitIdentity invariato se cambia SOLO Xte, ma PredictionIdentity cambia.
2. FitIdentity cambia per un solo byte logico in Xtr, label o groups; anche per feature order, seed, rounds e runtime/code version.
3. Il worker raggruppato `rank:pairwise` sintetico con 3 seeds su due horizon salva 6 `.ubj`, reload e predict replicano le previsioni del worker baseline nello stesso runtime (no change in source-only algorithm).
4. `exit_date` uguale/posteriore cutoff -> FAIL; duplicati, group length e order mismatch -> FAIL.
5. `cache-hit` a modello salvato con Xte diverso forza una nuova inferenza, NON un fit.
6. Corruzione di `.ubj`, `model manifest`, `npz` o `groups` -> FAIL; attacco path traversal/symlink -> FAIL.
7. Publishing parallelo identico: un solo oggetto valido, nessuna sovrascrittura, nessuna cache half-published.
8. Cache legacy con solo `scores_YEAR.csv` e audit -> rifiuto in modalità strict, lettura solo esplicita `legacy` per ricostruzione storica, audit indica stato inaffidabile come modello.
9. Nessun input finanziario Original149; no full backtest o calcolo CAGR in questa fase.

**QA finale:** `pytest` completo sulla nuova directory, specifica test di regressione invarianti delle predizioni nel simulatore sintetico, check SHA exact, report test & failure coverage. Distinguere green locale da CI GitHub green; nessun risultato asserito prima dell'output effettivo.

## 8. Fase 2 separata: structural XGB refresh (NON IN QUESTA SPEC)

Superpowers L2-Q ha provato **solo tecnicamente su sintetici** `process_type=update,updater=refresh,refresh_leaf=1` con ordinary `DMatrix`, non `QuantileDMatrix`, nel runtime XGBoost3.1.3. Stessa split topology su 12 alberi non equivale a capacità di catturare rendimenti estremi su 360 alberi canonici. Qualunque eventuale candidato leaf-update deve avere **pre-registrazione di un singolo intervento**, confronto same-data/same-engine per **ogni** vintage su CAGR, DD giornaliero, fees, turnover e Top1 quality, e dati prospettici realmente nuovi. Non cambiare i parametri o fare una sweep sullo storico 2017–2026 già studiato.

## 9. Prossimo passo secondo Superpowers

**Necessita revisione e approvazione dell'utente di questa specifica scritta**; solo dopo invocare `writing-plans` e presentare il piano TDD dettagliato, prima di implementare la nuova integrazione. Rispetto della separazione fra *design approval*, *plan approval* ed *execution*. I precedenti 10/10 test L2-Q si riferiscono **al solo prototipo**, non a questa integrazione v2.
