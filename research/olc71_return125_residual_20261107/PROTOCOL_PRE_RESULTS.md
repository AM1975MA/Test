# OLC71 — RETURN125: contenuto informativo residuo condizionato a Return/Hybrid/FUSION
**7 novembre 2026, protocollo congelato prima della lettura degli outcome OLC71.** Audit di ricerca; branch `main`, OLC19 e OLC67 invariati. Lo storico 2019–2026 è già esplorato: non è un holdout indipendente.

## Provenienza verificata
- OLC08F_01_FeaturePack_20261101.zip SHA256 `420faa56547721fd58db9f75ceef1370483047073d91c1b675587bd2d2e9db6c`, file `inputs/EU_RSI_COMPACT.pkl` e `USA_RSI_COMPACT.pkl`; 125 feature distinte come colonne del ramo RETURN.
- OLC14_Fitting_Risultati_20261101.zip SHA256 `4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1`, label di futuri rendimenti 21/42/63.
- OLC19_Rischio_Rientro_Checkpoint_20261102.zip SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`, score ORIGINAL_FUSION, RETURN, ORIGINAL_CURRENT, ORIGINAL_SMOOTH.
- Confrontare ogni fwd_ret_21/42 disponibile in OLC08 e OLC14 entro `1e-10`. Proibito leggere il target futuro fra le feature. `source_date <= signal_date` richiesto.

## Domanda primaria
Le **125 variabili Return** contengono segnale predittivo futuro che NON è già catturato dagli score disponibili di Return+ET/XGB+memoria, rispetto al loro modello predittivo di controllo, per il ranking cross-sectional dei prossimi 21 giorni? La distinzione Hybrid42/Return125 NON è una selezione 125→42.

## Contratti di training/evaluation
Una riga per (market, signal_date, ticker) eleggibile. Per confronto i modelli operano sullo *stesso supporto* con input score B0 presenti e label osservate; per predizione non applicare alcun filtro sul target ignoto. Solo gruppi mensili interamente maturi (`max(exit_date_63)<1 gennaio anno fit`) per il training, evitare leakage relativo a peer futuri. Train expanding 2019 fino all'anno precedente; fit una volta ogni gennaio 2021,2022,2023,2024,2025. Mercati separati. MAIN 2021–24, 2025 diagnostic-only already mined. 2026 parziale escluso dalla prova principale.
Label: `y=10^4[log(1+fwd_ret21) - mediana_{peer a data}(log(1+fwd_ret21))]`; non è il CAGR e non è un percentil rank. Impostare `y` soltanto con i rendimenti futuri effettivamente maturi per il training. Per la persistenza 42 giorni solo valutazione post-esito.

## Bracci prespecificati
- **ORIG_FUSION:** classifica l'ORIGINAL_FUSION vero per data (non è la selezione contestuale completa OLC19).
- **CTRL_RIDGE:** `SimpleImputer(median,keep_empty_features=True)`+ `StandardScaler`+ `Ridge(alpha=100)` con soli score già disponibili `RETURN, ORIGINAL_CURRENT, ORIGINAL_SMOOTH`. Score post-fit sono previsione economica del margine futuro; i learner originari restano congelati.
- **125_RIDGE:** identica pipeline e stessi fit/input dates, ma aggiunge le 125 feature originali; unico test di valore residuo lineare. Non ottimizzare alpha dopo gli esiti.
- **NULL_125_RIDGE:** tre controlli negativi (seed 71001,71002,71003) con l'intero blocco 125 rimescolato congiuntamente fra ticker entro la stessa data, sia su training sia su test (chiave market/date e shuffle riproducibile); le tre score di controllo restano intatte. Nessun null scelto come candidato.
- **CTRL_TREE / 125_TREE:** prova secondaria non lineare `HistGradientBoostingRegressor(max_iter=75, max_leaf_nodes=7, min_samples_leaf=100, l2_regularization=100, learning_rate=.04, max_bins=127, random_state=71071)`, sugli stessi due insiemi di input; dati mancanti trattati nativamente; no tuning o ricerca della migliore variante.

## Metriche e blocchi informativi
Valutazione MONTHLY OOF 2021–24 e 2025: cross-sectional RMSE e MAE del target in logbp, Spearman per mese, payoff medio statico Top2 a 21 e 42 sedute, quota Top2 nel 20% alto, eventuale Top2 loss. Differenze appaiate rispetto al proprio CTRL e FUSION. 6-month circular block bootstrap B=4000, seed 71071 solo descrittivo e senza correzione per ricerche OLC01–70. Confronto 2021–24 e 2025 separati, non scegliere miglior modello per performance futura. Diagnostica per 46 raw, 46 pct e 33 dev: conteggio missing/collinearità, non interpretare singola feature importante per semplice correlazione.

## Criteri di decisione
Un M1 che migliora soltanto la MSE ma peggiora Top2 non prova valore decisionale. Un M1 che pare migliore di CTRL ma non supera controlli shuffled non prova informazione stabile. Condizione per ipotesi da portare a ulteriori test indipendenti: migliora Top2 payoff e riduce MSE su 2021–24 in entrambi i mercati, senza danno importante nel 2025; **non si promuove nessuna variante in live**, non si calcola CAGR di policy complete senza rieseguire OLC19 con contestualizzazione/V6/FAST_LOCK3/costi. Qualunque risultato oggi resta diagnostico su storia già mined.

## QA
Verifica SHA256, schema 125, chiavi uniche, date asof, parità OLC14 labels, parità delle selezioni FUSION al checkpoint OLC19, uso del supporto comune, group maturity; seed riproducibili. Reportare problemi di missingness e drift in 2024/2025, dati USA observed mask mancante. Tutti gli input e gli output test non alterano i file originali.
