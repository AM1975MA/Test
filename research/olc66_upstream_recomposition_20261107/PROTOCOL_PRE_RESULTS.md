# OLC66 — Test upstream + ricomposizione causale degli strati (PRE-RESULTS)
Data: 2026-11-07. Stato RESEARCH ONLY. Questo protocollo viene registrato prima di valutare gli outcome OLC66. Il periodo 2019–2026 è stato ampiamente esplorato da OLC01–65: qualsiasi risultato è **esplorativo**, non OOS vergine. Nessuna strategia operativa, `main` o OLC19 modificata.

## Obiettivo
Verificare due ipotesi distinte e falsificabili: (A) separare scoperta Top10 e ranking economico Top2 recupera opportunità migliori della FUSION nativa? (B) invertire *l'ordine* fra smoothing temporale e fusione modifica il valore dei Top2? Individuare la migliore configurazione *supportata*, che può essere l'originale.

## Input congelati
OLC14 Fitting Results, OLC16 Input/Code, OLC19 risk, OLC11 Selection Results, OLC60/61 baseline selections, OLC63 reconstruction. Versione di ogni file identificata tramite SHA-256 in output. Stesse righe eleggibili e calendari dei risultati OLC14/16; ticker/mercati EU165/USA149. Confronto B0: `ORIGINAL_FUSION` esatto, parità 180/180 coppie con OLC19 richiesta.

## Pre-definizioni metodologiche
Ranking percentile per data/mercato, score ex ante senza il target. Top2 a pesi .5/.5 con gestione media dei pareggi alle soglie. Orizzonte primario fwd_ret_21, secondario fwd_ret_42, quota persistent top quintile a 21 e 42, quota fwd_ret_21 negativa. MAIN=2021–2024 (48 market-month per mercato). LATE=2025 diagnostico, non OOS; etichette non osservate mai riempite. Per confronto definito su date complete e supporto comune ai candidati. Niente nuovi dati esterni.

## Esperimenti upstream fissati
- **B0**: ranking ORIG FUSION (100% nativo).
- **C1 CLASS-FUSION**: usare direttamente il ranking FUSION del checkpoint OLC11 XGB classifier, già addestrato cronologicamente sulle 42 feature originali (nessun refit).
- **C2 EARLY-BLEND**: percentile per data del FUSION nativo e del FUSION CLASS OLC11, poi media 50/50 **prima** della selezione Top2. Non ottimizzare peso.
- **R1 NATIVE-POOL**: candidati originali Top10; ricalcolare un ranking economico *dentro la shortlist* con un singolo LogisticRegression `C=0.1, solver=lbfgs,max_iter=2000` su StandardScaler train-only. 
- **R2 UNION-POOL**: stesso classificatore, addestrato sullo stesso identico storico e applicato alla unione Top10 della FUSION nativa e CLASS-FUSION, senza passare di nuovo dalla FUSION come gate. Il confronto R2-R1 isola l'effetto della scoperta.
  Features: i ranghi percentili per data di ORIGINAL_FUSION, RETURN, ET, XGB, ORIGINAL_SMOOTH, CLASS_FUSION e discordanza assoluta fra i due ranking FUSION; nessuna identità ticker. Target: 1 se il rendimento futuro 21 sedute cade nel quintile superiore del **mercato intero** a quella data. Per ciascun mercato e anno 2021–25 un refit expanding su **mesi interi** con exit_date_63 strettamente precedente al 1° gennaio dell'anno di previsione, supporto del train limitato all'unione Top10 ex ante delle stesse due FUSION. La predizione avviene per tutti i ticker candidati senza impiegare rendimenti futuri. Un fit per anno, uguale per R1/R2, 10 fit totali.
- **O1 FUSE-THEN-SMOOTH**: 0.475*RETURN+0.525*CURRENT, poi smoothing temporale originale 0.4/0.3/0.3 e trasformazione ^1.1 sull'intera fusione.
- **O2 SMOOTH-BOTH-THEN-FUSE**: la stessa memoria temporale e potenza ^1.1 applicate separatamente a RETURN e CURRENT, poi fusione 0.475/0.525. Pesi, lookback e capitale invariati. In B0 la memoria è applicata solo a CURRENT prima della fusione.
I valori dei layer originali seguono esattamente il contratto OLC63; le due variazioni non sono approssimazioni ottenute da un post-filtro del Top2. Nessuna griglia di pesi, orizzonti, soglie, seed o numero candidati.

## Gate predefiniti e controllo
1. Data QA e parità B0 originale su 90 mesi EU + 90 USA, supporto e rendimenti fwd uguali a OLC63/OLC65.
2. Calcolo matched performance 21/42 per tutti i sette bracci, per mese, anno e 2025; recall futuro oracle Top2 dentro Top10, persistenza, selected negatives, turnover approssimato come cambia coppia (non ledger di trading).
3. Bootstrap descrittivo paired circular block6 `B=2000,seed=66007`, LOYO 2021–24; risultati 2025 non used to optimize.
4. Promuovere al **solo stress test contabile nativo**, non alla produzione, un candidato che migliori la media dei Top2 21d in EU e USA sul MAIN senza deteriorare la persistenza 21+42 in nessuno e senza peggiorare materialmente il 42d. Se fallisce, fermarsi senza simulare nuovi NAV e confermare come miglior candidato *supportato* OLC19 originale.
5. Per l'eventuale replay nativo, stesse selezioni per il rischio, V6 ricalcolato senza overlap, FAST_LOCK3, costi .001 e .003 e confronto NAV/MaxDD, ma mai dichiarare fill reali (dati solo OHLC).

## Misure di cautela
Le metriche 21d/42d sono mean arithmetic per finestra NON CAGR. Le serie appaiate sono correlate per i mercati e per gli orizzonti. Il bootstrap è descrittivo non inferenziale corretto per ricerca multipla. OLC11 CLASS originale può differire dal training OLC14 per target/refit, differenza dichiarata; nuove strategie non economicamente confrontabili finché V6 e risk non vengono effettivamente rieseguiti.
