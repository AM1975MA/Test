# ETF Trader V2 — Revisione specialistica strutturata con metodo Superpowers (senza nuovi backtest)

**2026-10-08.** Solo `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. Questo documento approfondisce il dossier [ROOT_CAUSE_XGB_HGB_EXPERT_HANDOFF.md](ROOT_CAUSE_XGB_HGB_EXPERT_HANDOFF.md); non modifica modelli, dati, soglie o codice produttivo. **Stato della delega:** competenze e skill Superpowers disponibili, ma nel presente harness **non è esposto uno strumento di dispatch di subagenti**; le quattro verifiche di seguito sono **review dello stesso assistente per specializzazione**, NON quattro giudizi di agenti indipendenti. In assenza di un runtime di dispatch, Superpowers prescrive esecuzione inline. L'assegnazione a quattro agenti indipendenti resta preparata nel dossier precedente, non falsamente dichiarata eseguita.

## 1. Evidenza comune, da non ristudiare né ricalcolare

- Golden Annual V2 `43.145952%`, stesso source contract sulla fresh Oct2 `31.603995%`; dati vintage distinti. Baseline Repeat2 full `30.843705%`. `gap_analysis/results/BASELINE_LINEAGE_DECISION.md`.
- Repeat1/2/3 Yahoo: max relativa OHLC `2.511e-6`, stesse date e volumi, 137/149 ETF prezzi modificati. `gap_analysis/results/yfinance_repeatability_v1/RESULT.json`.
- **Compatta21 XGBoost** training, objective `rank:pairwise`, 125 feature, 360 rounds, seeds 101/202/303. Non scambiare con `HistGradientBoostingRegressor` sperimentale L2-G e vecchia linea storica HGB25 ricostruita.
- **Amplificazione durante annual fit**: stesso input predittivo = Top1 0% diverso sui 4 anni campionati, cambiando X-train Top1 62.5%, cambiando y-train 58.33%, cambiando entrambi 43.75%; non sommare percentuali. `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json`. Training label disagreement `~0.05–0.07%` non autorizza inferire un bug di floating-point; tree-building strutturalmente discontinuo è una possibile spiegazione ancora NON confermata nodo per nodo.
- Multiple vecchie prove NEGATIVE: HGB_DIRECT/TEACHER50, Ridge, Fourier smooth/consistency, L50 label coarsening, Q4 feature rounding, 75/25 blends e capital sleeves, vintage committees, 6mo moving-block XGB bootstrap. Non ripeterle.
- Same-byte 6 replay full V2 deterministici: niente instabilità nondeterministica con dati identici. I tre Yahoo re-download *non* sono 3 mercati indipendenti.

## 2. Revisione codice: lacuna importante nella persistenza delle identità di training

Sorgente canonico in `vendor/etf_trader_v2/src/etf_trader/source_only/models.py` e `_xgb_worker.py`:

- `models.py::_fit_compact_rankers_isolated()` chiama 3 worker/seed/horizon in processi separati, raccoglie `pred_*.npy`, rimuove directory temporanea al termine. `_xgb_worker.py` fitta `xgb.train()`, fa `predict()` e salva `npy` ma nel codice visibile **NON salva alcun booster con `save_model()`**.
- `models.py::fit_predict()` usa `scores_YEAR.csv` per accelerare, e richiede solo che esista `fit_audit_YEAR.json`. L'if di riuso cache **non valida hash dei raw input, delle label, delle feature, del codice del modello, della versione librerie o dell'anno di cutoff in ingresso**. Questo non prova un effettivo cache-poisoning storico, ma è una lacuna strutturale del contratto di cache.
- `hybrid_producer.py::fit_hybrid_producer()` rifitta annualmente `ExtraTreesRegressor` e `XGBRegressor` sugli input forniti; non si vede una policy di artifact immutabili condivisi su tutta la catena. `a4_cluster_destination.py` ricostruisce periodicamente PCA/KMeans e rimappa i cluster ai precedenti membri: può introdurre discontinuità ulteriori.
- Preservare **sia i dati storici aggiustati usati nel fit che il modello salvato**; `booster.save_model("....ubj")` è l'interfaccia XGBoost ufficiale, gli iperparametri non contenuti nel model file devono essere in un manifest separato. Fonte: https://xgboost.readthedocs.io/en/release_3.1.0/python/python_api.html e https://github.com/dmlc/xgboost/blob/master/doc/tutorials/saving_model.rst.

## 3. Quattro specialist review, evidenza → proposta → falsificatore

### A. Ingegneria numerica e market-data lineage

**Verificato:** perturbazione OHLC per milione, grande cambiamento tra **fit annuali**; stesso input = replay deterministico. Cache attuale è prediction-only e il suo audit non è sufficiente a validare contenuti.

**Prima azione**, senza alcun modello modificato: **immutabilità a cutoff** dei 149 CSV originali / Adj Close ratio / rettifiche OHLC con hash, `signal_date,ticker,feature schema`, label cutoff e ordini gruppi, matrice di train, seed/parametri/rank objective, booster salvato per seed/horizon/year, preprocessori, MA3 estimator e cluster state, decoder e manifest delle dipendenze. La cache si accetta solo per firma completa dei dati/params/feature/code, non `audit_file.exists()` soltanto. Non mutare i prezzi passati dell'archivio di training sul successivo download; mantenere distinte le correzioni della fonte e le nuove informazioni mature.

**Non confondere:** il checkpoint garantisce stesso modello sullo stesso input e impedisce refit accidentali, non annulla future revisioni delle caratteristiche di inferenza, non cancella possibili errori di dati, non garantisce migliore performance prospettica. Vecchi snapshot point-in-time mancanti NON si ricreano congelando quelli del 2026.

**Falsificatore/QA futuro differente dai vecchi replay:** su dati sintetici o mini-fixture, invalidazione cache al cambiare di hash, ri-load UBJ e parità di prediction, rifiuto di feature schema differenti, divieto di dati posteriori al cutoff; **NON** rifare i 6 determinism replay finanziari.

### B. Gradient boosted ranking / XGBoost internals

**Verificato:** le perturbazioni di *training features* e *relevance labels* sono ciascuna sufficienti a variare molti Top1; non sappiamo ancora il **primo albero/nodo** in cui cambiano split oppure la relazione con il delta di CAGR.

**Ipotesi inedita e chirurgica per i futuri aggiornamenti:** conservare albero/split topology di un **checkpoint as-of**, e aggiornare solo i leaf weights quando maturano nuovi label. XGBoost documenta `process_type=update`, `updater=refresh`, `refresh_leaf=1`; nessuna struttura nuova costruita. ATTENZIONE: `refresh_leaf=0` modifica statistiche interne, quasi non cambia la previsione ed è un **controllo negativo**, non una soluzione numerica. La documentazione evidenzia che le iterazioni di update riutilizzano alberi precedenti; se num_boost_round diverso, il nuovo modello può contenere meno alberi. Necessaria compatibilità esplicita con `rank:pairwise`, gruppi QID, QuantileDMatrix, 360×3 seed e funzione di costo vera della V2. Fonte: https://github.com/dmlc/xgboost/blob/master/doc/parameter.rst e https://github.com/dmlc/xgboost/blob/master/doc/treemethod.rst.
**Rischio principale:** split congelati non incorporano nuove opportunità/regimi; alla lunga la capacità di riconoscere grandi vincitori potrebbe diminuire. Non chiamarla soluzione provata, né equazione causale che elimina tutta l'instabilità.

**Prerequisito prima del nuovo fit:** sola ispezione di dump alberi già salvati, se esistono nelle vecchie artifact, con confronto seed/year e margini delle split gain. Se i booster non sono archiviati, la prima acquisizione di checkpoints da un fit futuro differente dai test storici non è una prova di profittabilità. Non rieseguire L2-D o L2-J.

### C. Statistica learning/robust optimization

**Verificato:** 113 date mensili dello stesso periodo ripetute in 3 versioni Yahoo; selezione Top1 è discontinua anche quando i *scores* differiscono poco. Inoltre fenomeno tree instability non dimostra che tutte le divergenze siano economicamente nocive: il vintage CAGR range varia, ma non tutte le scelte differenti hanno lo stesso impatto sul capitale.

**Distinzione obbligatoria:** riproducibilità del benchmark storico vs robustezza di nuovo fitting annuale vs robustezza economica sui futuri dati. Sono tre outcome separati. Evitare nuove ricerche di seed, quantization grid, penalty e soglie su Original149. Test cross-vintage storico è diagnostico di fragilità, non conferma indipendente.

**Valutazione decisionale raccomandata:** costo economico delle decisioni divergenti ponderato per esposizione reale e contributo P&L, più worst-case CAGR vintage, non puro Top1 agreement al 90%. Nuovi dati futuri con snapshot auditabile consentirebbero un test veramente prospettico. Se si vuole preservare Top1 opportunities, vincolo economico per **ciascuna vintage** (no solo media).

### D. Portfolio/risk/execution

**Verificato:** serie full V2 Repeat1/2/3 29.75/30.84/34.68% CAGR, giornaliero DD -34.86/-25.69/-36.10%, contro storico Golden 43.146% su raw diverso. Non confondere proxy Top1 del 22% o Titanium 13.8% con CAGR Annual V2. Gli interventi L2-N e L2-P hanno peggiorato rendimento/drawdown: cambi stop non sono parte della stabilità del ranker.

**Priorità:** preservare MA3, DDfirst, HighCAGR24, V6, cash BIL/SHV, fee, gap e top1/top2. Per qualsiasi futuro challenger, misura full V2 2366 date e 3 vintage matched con varianza (CAGR e daily DD), turnover, costi e **net wealth dispersion**. Il fatto che un update renda uguali gli alberi non rende necessariamente migliori le scelte. Non scegliere `refresh_leaf` settings con dati 2017–26 già esaminati.

## 4. Decisione con ordine di esecuzione e stop conditions

1. **Adesso — azione sicura ingegneristica:** proteggere checkpoint canonici e schema dati; implementare *in Test soltanto* un manifest/checkpoint contract, senza fare model fitting o modificare il selettore. Dopo review dell'interfaccia, se c'è audit logic difettosa, test sintetici red-green; non rifare il dataset 149×3.
2. **Dopo, soltanto su un cutoff genuinamente causale**, valutare una singola ipotesi strutturale `refresh leaf` come alternativa al refit annuale totale, non combinata con altre modifiche; necessaria validazione di compatibilità dell'API e di version pinning. Mantenere esattamente lo stesso cutoff del training mature label e ranking group; conservare vecchia e nuova struttura per confronto.
3. **Non perseguire** nuovi Ridge/HGB, Fourier, Q4, L50, bootstrap, score/capital blending, trailing momentum, risk-stop filters sullo storico 2017–26. La ricerca può ripartire da dati *realmente nuovi e versionati as-of*, con gate economico preregistrato.

**Riserva importante:** la root-cause forensics prova il fitting come primo amplificatore significativo di Compact21 ma non prova che HGB25, MA3/KMeans, vendor historical vintage delta e P&L siano causalmente tutti spiegati da XGBoost. È prematuro promettere una cura definitiva che preservi il 43% historical golden.
