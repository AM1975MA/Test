# OLC100 — Protocollo di congelamento e validazione prospettica ETF

**Registrazione: 12 novembre 2026. Stato: architecture freeze / NO NUOVI RISULTATI.**
Questo documento viene scritto dopo gli esiti OLC01–99. Non trasforma il 2019–luglio 2026 in un campione indipendente e non autorizza trading live.

## 1. Scopo e regola di integrità
Validare, su decisioni non impiegate nella selezione dei modelli, la differenza fra la baseline OLC19 e il candidato OLC67. Ogni segnale è prodotto a partire da uno snapshot disponibile PRIMA del cutoff e firmato (SHA256) prima di conoscere l'outcome. Nessuna selezione di nuove soglie, strategie per mercato, pesi, lag, learner, feature, score o protezioni in base al risultato forward. GitHub `main`, OLC19, OLC67, OLC98, OLC99 e i loro archivi restano invariati.

## 2. Provenienza eseguibile congelata (sha256 calcolati sugli ZIP della Library)
- `main` HEAD al freeze: `a87e84bc4e53e94a4a4e4c5ecc157e338f2716a3`.
- OLC19 GitHub commit `0c405bb63432cd338a7db84058a1116b161c952c`; Library `/ETF_Research/OLC19_Rischio_Rientro_20261102/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`; SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`.
- OLC56 Library `/ETF_Research/OLC56_Robust_Timing_20261106/OLC56_TESTS_20261106_VERIFICATI.zip`; SHA256 `f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573`.
- OLC67 GitHub commit `2e173ecd7b9f0e396241cb54c62a3a8a9e80bf94`; Library `/ETF_Research/OLC67_Combined_Strategy_20261107/OLC67_Strategia_ETF_Verificata.zip`; SHA256 `dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4`.
- OLC98 GitHub commit `b32f7b843d07e0939f5b6c860e651137442604b9`; Library `/ETF_Research/OLC98_Model_Review_20261112/OLC98_Model_Review_Completa_20261112_VERIFICATO.zip`; SHA256 `85a38f82946186cdc393982542cb012818f85f33a42489db7f17e5cbb002fa83`.
- OLC99 GitHub commit `b722d706afc503008d8e59d857d8a8b15b89f862`; Library `/ETF_Research/OLC99_Economic_Top10_20261112/OLC99_Economic_Top10_Allocazione_20261112_VERIFICATO.zip`; SHA256 `0659c1d91c233851b2380f54f442a376704308e07a5d026cf1f3b38d8c768672`.
- OLC70 causal/matched-state GitHub commit `f49f5c560d8bf74ba52c314b63b949787cb4492a`. Archivi OLC98/OLC99 includono una selezione degli input, **non** un generatore completo e certificato di nuovi segnali OLC19. Prima di qualsiasi replay forward occorre riprodurre e verificare il produttore originale di score, il calendario e i dati point-in-time; non riempire i vuoti con rendimenti futuri.

## 3. Contratti dei layer — nessun tuning
- **S (selezione):** S0 = Top2 dalla FUSION originale; S1 = Return125 + ET/XGB Hybrid42 (60/40), memoria Hybrid 40/30/30 e potenza 1,1, FUSION 47,5/52,5, `TOP2_CONTEXT_REVALUE`. I due ticker vengono fissati prima del timing. R2 OLC98 (shortlist Top10 originale e contesto) è equivalente a S1 sui 180 eventi storici, NON è un nuovo miglioramento.
- **A (allocazione Top2):** A0 = 50/50; A1 = MINVAR63 usando 63 sedute di Close già complete alla data del segnale, limiti [25%,75%] sulla quota relativa fra Top1/Top2, fallback 50/50 in assenza di dati.
- **T (timing):** T0 = IMMEDIATE nativo OLC19; T1 = DELAY3 nativo OLC17/OLC56, terza apertura utile `k+2`; non scegliere ex post il ritardo.
- **P (protezione):** P0 = V6 invariato + FAST_LOCK3 nativo OLC19 (barriera `0,945 * Close_prev`, vendita simulata con frizione, divieto di riacquisto alle aperture k+1, k+2, k+3; primo riacquisto possibile k+4 se eleggibile). P1 = V6 invariato + BASE, solo controllo diagnostico con rischio potenzialmente superiore. Stati e liquidità difensiva devono seguire la contabilità nativa.
- **Mercati:** EU165 e USA149; decisioni mensili, stessi universi e regole di ammissibilità storico/PIT. Futures e CFTC short restano indicatori di ricerca non tradabili; non vengono inseriti nella politica congelata. Nessuna politica distinta per EU e USA.

## 4. Bracci forward preregistrati: sei combinazioni, non una ricerca
`B_BASE = S1/A0/T0/P0`: baseline ufficiale OLC19.
`C_CANDIDATE = S1/A1/T1/P0`: challenger OLC67, test principale.
`D_SELECTION = S0/A0/T0/P0`: valuta S1 vs S0 a pari resto.
`D_ALLOCATION = S1/A1/T0/P0`: valuta A1 vs A0 con T0; confronto addizionale A1 vs A0 con T1 usando C_CANDIDATE e D_TIMING.
`D_TIMING = S1/A0/T1/P0`: valuta T1 vs T0 con A0.
`D_PROTECTION = S1/A0/T0/P1`: valuta P0 vs P1 con A0/T0 (descrittivo, non candidato se peggiora i limiti di rischio).
I confronti causali *locali* al segnale devono partire dallo stesso stato contabile pre-trade; i replay di portafoglio *integrali* devono invece portare avanti lo stato realmente generato da ciascuna politica. Non sottrarre CAGR di esperimenti disallineati né imporre lo stesso stato ai replay integrali.

OLC98 R1/R3–R6 e OLC99 A/B/C non sono candidati promuovibili; possono soltanto essere archiviati come controlli negativi, senza accesso ai risultati forward per ulteriore tuning.

## 5. Nuova evidenza: due finestre rigorosamente separate
- `BRIDGE_2026H2`: segnali luglio–ottobre 2026 e outcome maturati, **solo estensione retrospettiva out-of-time**, perché alla data di questo freeze il mercato ha già rivelato quei rendimenti. Non presentare come prospective holdout blind; non usare per cambiare il modello.
- `PROSPECTIVE`: **primo segnale mensile successivo a questo freeze**, previsto alla chiusura di novembre 2026 secondo il calendario nativo verificato, poi cadenza mensile. Predizioni e azioni per mercato devono essere persistite prima delle aperture negoziabili e prima di qualsiasi outcome, con timestamp UTC, commit e hash immutabili.
- `CUTOFF`: input osservati solo fino all'ultimo Close completato disponibile al segnale; timestamp di pubblicazione per macro/futures/short; evitare prezzi retro-aggiustati ex post non conservati alla fonte. Fit annuale/prequential solo secondo una regola originale già congelata; no refit opportunistico.

## 6. Formato minimo per audit e dati
Per ogni segnale e mercato salvare: `strategy_id,market,signal_date,signal_generated_at_utc,source_data_asof_utc,first_eligible_open_utc,model_commit,code_sha256,input_snapshot_sha256,universe_snapshot_sha256,ticker1,ticker2,weight1,weight2,timing,protection,exposure_budget,portfolio_state_hash,prediction_file_sha256`.
Per ogni seduta e strategia conservare: OHLC source/observation mask, time zone/FX/dividend policy, costi, liquidità, units, orders/fills o fill simulati, stop/lock, NAV gross/net e log-return. Un file modificato dopo la prima esecuzione invalida la serie prospettica; correzioni sempre come versioni separate con motivazione e hash.

### Preflight bloccante
1. Parità su OLC19/OLC67 già verificati: decisioni, ledger, NAV, risk states e contatori a precisione originale; la stessa pipeline forward non deve modificare gli archivi.
2. Coverage PIT effettiva dei due mercati, tickers/ISIN ed eleggibilità storica, corporate actions, dividendi/FX, total return/adjusted coerenti, timezone, origin/missingness quote USA, prezzi eseguibili e stop gap.
3. Nessun input con `available_at` dopo il cutoff, nessun label maturato dopo cutoff nel fitting, nessun `data_asof` ricostruito retroattivamente senza distinguerlo.
4. Controlli invarianti: 50/50 somma 1, MINVAR63 limiti, V6, costo fee `0,001` base e `0,003` stress, stop friction `0,001` base e `0,005` stress. I costi non sono una prova di fill broker reale.
Un fallimento marca `DATA/EXECUTION INCONCLUSIVE`, non un CAGR favorevole.

## 7. Metriche fisse e inferenza
Valutare sempre entrambi i mercati sullo stesso calendario per ogni contrasto: differenza di **log-rendimento netto per decisione** e annualizzata, CAGR NAV daily native (252 sedute), MaxDD, Calmar, volatilità downside, turnover, costo, cash/risky exposure medio, reentry, stop, gap/slippage e anni/mesi di leadership. Per S misurare anche hit Top2, rank IC, utilità controfattuale su Top2 allo stesso stato e costo degli errori; per A utilità del differenziale dei due pesi a coppia e timing fissi; per T costo delle prime tre aperture vs evitato ribasso; per P coda sinistra, stop fill, DD e rinuncia ai rimbalzi.

L'inferenza primaria è il contrasto accoppiato `C_CANDIDATE - B_BASE` sui soli rendimenti prospettici maturi, con intervallo bootstrap a blocchi di mesi, seed predefinito `100112`, e nessuna scelta retrospettiva del blocco. Riportare anche tutti i cinque contrasti diagnostici con incertezza; non scambiarli per test indipendenti né ignorare il numero elevato di esperimenti passati. Le due aree geografiche possono essere correlate.

## 8. Regola prima del risultato
Stato iniziale: **NON PROMOSSO**. Primi 12 segnali completi = sola diagnosi; verifiche prefissate a 12/24/36 mesi maturi, senza ricalibrare la policy. Mancanza di campione o intervalli larghi = `INCONCLUSIVE`, mai promozione automatica.

Per considerare una promozione è richiesto contemporaneamente: tutte le QA PASS, miglioramento netto del candidato in EU **e** USA, MaxDD non peggiore di 3 punti percentuali in nessuno dei due, assenza di crollo sotto stress costi, stabilità dei contrasti appaiati e intervalli di confidenza prospettici sufficientemente stretti da sostenere un vantaggio positivo in entrambi i mercati. Il numero di mesi non sostituisce la potenza statistica; qualunque modifica apre un nuovo identificativo e un nuovo test prospettico.

**Stato al freeze: nessun outcome nuovo verificato, nessun replay OOS eseguito, nessuna strategia live modificata.**
