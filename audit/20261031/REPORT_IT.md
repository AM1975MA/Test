# ETF Trader — audit trasversale delle evidenze

**31 ottobre 2026. Stato: censimento completo dei branch esistenti; revisione critica e verifica numerica MIRATE, non certificazione integrale del repository. Nessuna strategia promossa o modificata.**

Repository: `AM1975MA/Test`. Snapshot main esaminato: `77f7a4706f934e7061541cd62c1c0ce64ab7135d`. Il lavoro nuovo risiede esclusivamente sul branch `audit-repository-evidence-20261031`. `main`, V2/V3 operativi e il repository `AM1975MA/Etf_trader` non sono stati modificati.

## 1. Risposta operativa

Non emerge una giustificazione per assemblare immediatamente una strategia sommando i vincitori dei singoli test. Il risultato ricorrente è più specifico: **migliorare il ranking, il riconoscimento dei vincitori estremi o la stabilità del modello non assicura un miglioramento della decisione economica nel sistema completo**. Esistono componenti utili, ma devono conservare il proprio contratto sperimentale: universo, prezzi congelati, date, feature, target, esecuzione, costi e rischio.

Questo audit non dimostra l'assenza di alpha. Dimostra che varie attribuzioni intuitive non sono sostenute dai confronti controllati già presenti e che alcune ipotesi sono state già respinte. Gli intervalli che comprendono zero non provano equivalenza fra modelli.

## 2. Cosa è stato effettivamente censito

| Oggetto | Conteggio verificato | Significato |
|---|---:|---|
| Branch preesistenti | 293 | Tutti i tip remoti presenti nello snapshot; escluso il nuovo branch di audit |
| File in main | 958 | File, non cartelle |
| Directory in main | 195 | I precedenti 1.153 elementi erano 958 file + 195 directory |
| Blob Git distinti tra tutti i tip | 4.689 | Versioni di contenuto deduplicate per SHA Git |
| Blob testuali esportati e verificati | 4.251 | Dimensione, SHA-256 e SHA-1 del blob Git controllati indipendentemente |
| Blob non esportati | 438 | Tipologia, dimensione o codifica; comprendono archivi e dati binari |
| Versioni Markdown distinte | 667 | Indicizzazione, NON 667 revisioni critiche complete |

L'inventario include rami non confluiti in main, fra cui EU165, V4 e V5. Non esaurisce tutte le revisioni cancellate o superate nella storia Git, i soli tag, né tutti gli artifact storici di Actions. Il conteggio dei branch non è il numero di esperimenti indipendenti.

Evidenze persistenti: `input_manifest.json.gz`, `checks/branch_inventory.csv`, `checks/blob_integrity.csv`, `checks/SUMMARY.json`. Export: run **41157260582**. Verifica separata e salvataggio dei risultati: run **41158064263**, concluso con successo. Il manifest compresso è versionato nel branch; la conservazione dell'inventario non dipende soltanto dalla scadenza dell'artifact.

## 3. I confronti che cambiano la decisione

### 3.1 Compact127: migliore in una metrica isolata, peggiore nello Stage19 completo

Il confronto controllato `STAGE19_BASE_VS_127_CONTROLLED_RESULTS_20261021.md`, blob `83c19d02bbed150848bf0e628a86e46592539c4d`, cambia soltanto il ranker all'interno dello Stage19, mantenendo prezzi, costi, protezioni e gli altri layer. I risultati documentati sulle tre acquisizioni congelate sono:

| Acquisizione | Stage19 originale, CAGR | Stage19 con Compact127, CAGR |
|---|---:|---:|
| r1 | 29,7534% | 26,9566% |
| r2 | 30,8437% | 23,2308% |
| r3 | 34,6771% | 24,9469% |
| Media descrittiva | 31,7581% | 25,0448% |

La differenza media è circa **−6,71 punti percentuali**, con peggioramento anche del MaxDD medio. Le tre acquisizioni sono revisioni degli stessi mercati, non tre holdout indipendenti. Il bootstrap temporale del differenziale logaritmico comprende zero: il risultato storico sfavorevole non autorizza una legge universale sul modello, ma certamente non sostiene la sostituzione.

Il precedente aumento della cattura Top3 nei panieri non contraddice questo risultato: misura un altro compito. Anche i test 255/511 foglie vanno letti correttamente: nel relativo esperimento le foglie effettive erano limitate dai dati e gli output coincidono; non sono evidenza di miglioramento indefinito aumentando il limite.

### 3.2 Vincitori estremi: conservarli come obiettivo, non confonderli con profitto

La campagna Tensor/Listwise su 476 date settimanali è una controprova forte. ListNet e ListMLE aumentano la sovrapposizione con i cinque vincitori realizzati, ma i CAGR documentati sono rispettivamente circa **−3,93% e −5,20%**. Il controllo che seleziona soltanto alta volatilità raggiunge **19,50% di Top5 overlap**, superiore alle varianti Listwise, ma ha CAGR **−6,46%**. Il semplice momentum21, nello stesso contratto, riporta **+13,41%**.

Conclusione: non eliminare automaticamente i grandi movimenti, e non scegliere il modello dalla sola hit-rate. Occorre distinguere cattura delle opportunità, rendimento delle scelte errate, concentrazione, costi e rischio. Analogamente, smussare il ranker per renderlo stabile può perdere opportunità: stabilità e rendimento non sono sinonimi.

Fonte: `tensor149_tcn5d/RESULTS_FULL_20261020.md`, blob `ec778684`; studi daily/R1/R2, blob `b72747b4`; reset L2, blob `1338750a`.

### 3.3 Ridge: il confronto a pari K è già stato fatto, non va dimenticato

Il rapporto main `etf149_rank_to_pnl_20261030/README_IT.md` non si ferma al confronto iniziale V2 Top10 contro Ridge Top15. Contiene anche sei controlli **a pari K=5/10/15**, con o senza massimo tre strumenti per categoria, sugli stessi 42 mesi, con turnover drifted e costo simulato di 10 bp per nozionale.

Ho ricalcolato da `equal_k_same_months.csv` tutte le **12 righe gross/net** della tabella riepilogativa: le differenze medie coincidono entro 1e-12. Tutti gli intervalli riportati dei sei confronti netti comprendono zero. La migliore correlazione Spearman generale di Ridge non si converte, in questi controlli, in una superiorità economica stabilita. I test sono diagnostici post-selezione; non scegliere retrospettivamente K=15 come nuova prova indipendente.

Fonte immutabile: [rapporto e controlli a pari K](https://github.com/AM1975MA/Test/blob/77f7a4706f934e7061541cd62c1c0ce64ab7135d/etf-trader-v3%20corrected/experiments/etf149_rank_to_pnl_20261030/README_IT.md). Nuovo controllo: `checks/equal_k_reconciliation.csv`.

### 3.4 V5 EU165: il 22% non dimostra valore aggiunto dei ranker V2/V3

Ho ricalcolato i CAGR e i MaxDD dai NAV archiviati per tutte le **84 combinazioni strategia-periodo**, ossia **168 valori**. Gli scarti massimi sono rispettivamente circa 7,8e-16 e 4,2e-16. Questo verifica l'aritmetica delle tabelle, NON la correttezza dei prezzi sottostanti o l'esecuzione reale.

Periodo preciso della tabella principale: **1 febbraio 2021–31 dicembre 2024**; 1.006 osservazioni NAV. Convenzione conservata: CAGR annualizzato su 252 sedute, rapporto fra ultimo e primo NAV e 1.005 intervalli. Il primo NAV del periodo è la base; non si aggiunge arbitrariamente il rendimento del giorno precedente.

| Modello nello stesso replay EU165 | CAGR ricalcolato | MaxDD ricalcolato |
|---|---:|---:|
| V3 Pair25 con HALFMA | 15,6662% | −16,5102% |
| V5 fattori soltanto | 20,9886% | −23,0239% |
| V5 GBM con feature di base, senza V2/V3 | 22,0637% | −20,8178% |
| V5 stesso GBM con esperti V2/V3 | 22,0256% | −20,7252% |

L'ablazione corretta è l'ultima riga contro la penultima: stesso learner, non GBM contro Ridge. Il contributo medio degli esperti è **−0,0318 punti percentuali di rendimento logaritmico annualizzato**. Un nuovo bootstrap circolare, seed 10312026, blocchi di sei mesi e 10.000 estrazioni, restituisce **[−0,7722; +0,7160] pp**.

Contro V3 HALFMA il differenziale logaritmico annualizzato è +5,4499 pp, ma l'intervallo ricalcolato è **[−2,8292; +13,5435] pp**. Contro il solo modello fattoriale il differenziale è +0,8690 pp, intervallo **[−0,9291; +2,7459] pp**. Tutti sono esplorativi su storia già esaminata; non sono conferme prospettiche.

Sono state ricostruite anche le **90 medie** delle 15 righe del riepilogo predittivo dai dati mensili. La modesta o negativa qualità dell'alpha residuo non viene cancellata da un CAGR favorevole del portafoglio. Il rendimento documentato è concentrato soprattutto nel 2023–2024; i controfattuali fattoriali non consentono ancora di separare nettamente esposizione e alpha.

Fonte: [V5 EU165, commit congelato](https://github.com/AM1975MA/Test/tree/a36a71dc1d02ce6cd54347f61098e5169727b366/etf-trader-v3%20corrected/experiments/etf_v5_hierarchical_factor_forecast_eu165_20261031). Nuove prove: `checks/v5_nav_reconciliation.csv`, `checks/v5_predictive_means_reconciliation.csv`, `checks/v5_independent_block_bootstrap.csv`.

## 4. Lettura trasversale delle famiglie, incluse quelle respinte

Le righe seguenti riassumono fonti lette criticamente; salvo i controlli numerici esplicitati, riportano risultati DOCUMENTATI, non nuovi backtest eseguiti in questo audit.

| Famiglia | Evidenza rilevante | Decisione supportata |
|---|---|---|
| Provenienza/raw vintage e forensics | Stesso codice e periodo possono cambiare molto con diverse acquisizioni; il training Compact21 amplifica perturbazioni. Tre vintage non sono nuovi mercati. | Preservare dati e modello congelati; non attribuire il gap 43%→31% a una strategia diversa senza riconciliare i prezzi. |
| Stabilizzazione, quantizzazione, learner alternativi L2 | Q4 riduce la dispersione tra vintage ma perde rendimento; Ridge è più stabile, non per questo superiore nel sistema completo. | Conservare i test negativi; non ottimizzare l'identità delle scelte sacrificando l'obiettivo economico. |
| Correzione matematica delle 125 feature | Il test matched XGB-only documenta CAGR medio panieri 13,297% legacy contro 12,057% corrected; nessun vantaggio stabilito. | Correggere il significato matematico e rifittare con versioning; non chiamare la correzione un miglioramento di performance già dimostrato. |
| Capacità 15/31/63/127/255/511 | Richiamo dei vincitori e risultati full-stack divergono; 127 non è vincitore universale. | Nessuna promozione basata sulle sole foglie o sul Top3. |
| Tail e macro bonus | Tail contiene complementarità; i pesi cambiano gli esiti. Nel test specifico il bonus macro è quasi sempre inattivo. | Non fare un blend fisso sulla base del CAGR migliore; non generalizzare il fallimento di quel bonus a ogni informazione macro. |
| DD guard / FUSION1 | Il dossier storico documenta miglioramenti di drawdown con perdita minima di CAGR per alcuni controller; gli incrementi successivi spesso falliscono. | Preservare FUSION1 come riferimento storico, non respingere indiscriminatamente ogni risk overlay. La sua validazione originale non viene rieseguita qui. |
| Escape topology STEP09A–A4 | Il target best-of-24 produce una classe ROTATE artificiosamente dominante. Il target robusto migliora AUC, ma non passa il gate; funding e CFTC non lo superano. | Non ripetere semplicemente tuning di soglie o finestre per aggirare il gate già fallito. |
| OASIS149 | Diversificare riduce concentrazione e drawdown, ma opportunità/crisi non mostrano probabilità sufficientemente calibrate. | Beneficio di struttura del capitale distinto da alpha predittivo. |
| TCN, Listwise, SoftSpearman, daily/R1/R2 | I pilot favorevoli non sopravvivono sempre alla storia completa; alta cattura estremi può essere preferenza per volatilità. | Preservare il controllo momentum e i controlli risk-only; non promuovere dalla sola loss o dal pilot. |
| HMM/RMT e gate degli esperti | Complementarità ex post fra esperti, ma il gate causale testato non identifica bene il futuro vincitore e rimane vicino al mix uniforme. | Respinto quel gate; non dimostrata l'inutilità universale dei regimi. |
| V3 full-stack, FS01–FS04, fallback | Migliorie isolate non si sommano. Nel FS04 l'incremento è piccolo; nel 2023–2026 i rendimenti delle varianti coincidono. Il fallback su cinque panieri fallisce i gate. | Non espandere a 500 soltanto per recuperare un esito negativo; non chiamare il periodo con decisioni identiche una validazione dell'incremento. |
| Meta-tree e hurdle | Il tree condizionale è più parsimonioso; molti challenger peggiorano. Alpha economico incerto e concentrato. Giugno ha segnali archiviati prima dell'esito; luglio/agosto ricostruiti dopo non sono veri forward prospettici. | Conservare il checkpoint di ricerca senza promozione. Non moltiplicare gli algoritmi sulla stessa storia. |
| Trasferimento Holdout70 / EU48 / EU148 | Il vantaggio Original149 non si trasferisce intatto. I primi report EU48 avevano feature legacy pur chiamandosi V3 corrected; l'erratum e il vero retest vanno letti insieme. | Tenere separati mercati, prezzi, calendario, feature e motore di portafoglio. |
| EU148 paired e composizione | Limitare ex post il sottoinsieme europeo alle azioni recupera gran parte del divario di CAGR, ma cambia beta e opportunità. | Indizio di problemi cross-asset; non prova causale che basti eliminare bond/property in futuro. |
| V4 / V5 EU165 / factor leadership | V4 è una combinazione fissa, V5 design non equivale a engine completo testato; V5 eseguito non dimostra vantaggio incrementale degli esperti, né leadership fattoriale universalmente prevedibile. | Trattare ciascun ramo come esperimento distinto, non come release progressivamente convalidata. |

### Precisazione EU48

Il retest con kernel realmente corrected documenta leaf31 Top1 CAGR **8,3941%**, contro **3,8462%** di leaf127 e **4,7279%** del V2 depth4; il MaxDD di leaf31 è però peggiore del V2 e gli intervalli comparativi comprendono zero. Non selezionare 31 dopo il risultato e presentarlo come nuovo standard convalidato. Fonti: `EUROPE48_V3_TREE_RESULTS_20261024.md` (con erratum, blob `6b88c946`) e `EU48_TRUE_CORRECTED_CAPACITY_20261025.md` (blob `bd8e933e`).

## 5. Rischi tecnici verificati e limiti di riproducibilità

### 5.1 Fallback V5 non limitato al warm-up — verifica eseguita

In `replay_v5.py`, `score_by_source` passa al vecchio `PAIR25` quando non trova il modello/data. Il commento dice warm-up, ma non esiste un controllo che limiti questo comportamento al 2019–2020. Ho estratto soltanto la funzione e l'ho eseguita con un input sintetico datato giugno 2024: il fallback avviene anche allora.

**Correzione proposta, non applicata al modello:** separare warm-up autorizzato e assenza imprevista, far fallire esplicitamente il secondo caso o registrare una politica predefinita, e rendere visibile ogni fallback nel ledger.

### 5.2 Sentinel finito per previsione mancante — verifica eseguita

La funzione restituisce `-1e6` per valori non finiti: il valore è quindi finito e non garantisce da solo l'ineleggibilità. La prova sintetica conferma questa trasformazione. La presenza di una guardia nel motore padre è decisiva.

**Non affermo che siano stati comprati ETF senza previsione:** il motore padre non è disponibile come file autonomo nei tip ispezionati e il replay raw non è stato rifatto. **Correzione proposta:** maschera esplicita di eleggibilità, controllo del numero di candidati validi, cash/fail-closed dichiarato. Nessun impatto PnL quantificato in questo audit.

### 5.3 Source-only V5 non chiuso nel normale checkout

Gli script importano `source_v4/run_v4_clean.py` e dipendono da pannelli e archivi descritti nei README come parte di un pacchetto esterno. Il relativo file Python non compare come file autonomo nell'inventario dei tip. Non è quindi dimostrata la riproduzione integrale da un normale checkout del solo ramo V5. Non si afferma che quel contenuto non esista dentro uno dei 438 blob non ispezionati o in artifact esterni.

**Rimedio proposto:** versionare o referenziare in modo recuperabile e verificabile input e engine, con hash e comando source-only. I NAV pubblicati sono sufficienti per i controlli aritmetici svolti, non per certificare acquisti/vendite raw.

### 5.4 Causalità: risultato positivo circoscritto

Tutte le **90 righe** di `ANNUAL_LABEL_MATURITY_AUDIT.csv` hanno `last_label_exit` precedente al primo gennaio dell'anno di previsione. Anche il codice annuale letto impone maturazione prima del cutoff. Questo non certifica automaticamente la causalità di ogni feature, il prezzo di esecuzione, la selezione dell'universo o tutti i fallback.

Il dossier shadow documenta separatamente una verifica del filtro basato sul Close del giorno di esecuzione: la sua rimozione non cambia i NAV nel campione provato. È scorretto trasformare un difetto di contratto in una falsa affermazione di rendimento gonfiato quando il controfattuale documentato misura impatto zero. Questa controprova non è stata rieseguita qui.

## 6. Valutazione della revisione

I denominatori sotto riguardano solo l'unità indicata, non l'intero repository. L'assenza di errori aritmetici non equivale a validazione del modello.

### Utilità e completezza

| Categoria | Difetti osservati | Valutazione |
|---|---|---|
| Completezza della revisione critica di tutti gli esperimenti | Non determinabile integralmente | PARZIALE: inventario completo dei tip; fonti sostanziali di 15 famiglie lette in modo mirato, non tutti i 667 documenti e non tutti i binari |
| Chiarezza dei confronti | Non determinabile integralmente | Distinte baseline, cardinalità, vintage, politica, unità statistica e periodi; gli errata EU48 sono conservati |
| Interfaccia/grafici interattivi | N/A | Nessun dashboard interattivo oggetto di questo audit |

### Correttezza analitica

| Categoria | Difetti osservati | Valutazione |
|---|---|---|
| Integrità dei blob esportati | 0 / 4.251 | Tutti verificati su dimensione e due digest; non attesta la verità finanziaria del contenuto |
| CAGR e MaxDD V5 pubblicati | 0 / 168 valori | Ricalcolo indipendente sui NAV archiviati e finestre esplicite |
| Medie predittive V5 | 0 / 90 valori | Ricalcolo dai risultati mensili; non dai prezzi e dalle predizioni raw |
| Differenze gross/net a pari K | 0 / 12 righe | Ricalcolo dei confronti sui 42 mesi comuni |
| Maturazione nel registro annuale V5 | 0 / 90 righe | Controllo dei timestamp registrati, non certificazione di ogni record usato dal fit |
| Contratto adapter V5 | 2 / 2 comportamenti testati | Fallback non delimitato e sentinel finito confermati; impatto economico non dimostrato |
| Conclusioni, prezzi, investibilità, selezione e test multipli | Non determinabile integralmente | Principali limiti identificati; nessuna promozione economica autorizzata |

## 7. Cosa conservare e cosa non ripetere

**Conservare:** baseline originale del sistema completo; prezzi e score congelati; feature matematicamente corrette ma versionate; complementarità Tail; controller DD con evidenza storica favorevole distinta; meta-correzioni parsimoniose con possibilità di astensione; fattori e categorie come controlli di attribuzione, non come alpha già provato. Preservare l'obiettivo di cogliere movimenti ampi e misurare anche il costo dei falsi veto.

**Non ripetere senza nuova informazione:** aumentare foglie perché cresce il Top3; smussare i modelli soltanto per ridurre divergenza nominale; scegliere loss Listwise dai pilot; gate HMM/RMT o blend statici sulla sola complementarità ex post; selezionare il K o l'universo dal CAGR migliore; ripresentare gli stessi anni come nuovi holdout.

**Restano necessari per chiudere l'audit integrale:** esame dei 438 blob esclusi e degli artifact mancanti; ricostruzione delle revisioni storiche non presenti ai tip; verifica puntuale dei restanti report e dei relativi script; chiusura source-only dei rami incompleti; riconciliazione esterna di corporate actions, prezzi negoziabili, universo storico e delisting; replay raw matched dei confronti decisivi. In questa sessione: **zero nuovi training e zero backtest integrali da OHLCV**.

## 8. Fonti e navigazione

Il manifest contiene per ciascun branch il commit, il percorso, lo SHA del blob e la dimensione. I prefissi SHA citati in questo rapporto identificano contenuti, non versioni scelte per comodità. Principali riferimenti aggiuntivi:

- [Stage19: sostituzione isolata Compact127](https://github.com/AM1975MA/Test/blob/f40c16966ebe3be30d8e9bb64626b89725c9f681/STAGE19_BASE_VS_127_CONTROLLED_RESULTS_20261021.md).
- [Checkpoint meta-tree, compresi challenger e forward](https://github.com/AM1975MA/Test/blob/77f7a4706f934e7061541cd62c1c0ce64ab7135d/etf-trader-v3%20corrected/RESEARCH_CHECKPOINT_META_TREE_20261024.md).
- [Registro del sistema V3 e studi L10](https://github.com/AM1975MA/Test/blob/77f7a4706f934e7061541cd62c1c0ce64ab7135d/etf-trader-v3%20corrected/registry/V3_INTEGRATION_FREEZE.json).
- [Adapter V5 esaminato](https://github.com/AM1975MA/Test/blob/a36a71dc1d02ce6cd54347f61098e5169727b366/etf-trader-v3%20corrected/experiments/etf_v5_hierarchical_factor_forecast_eu165_20261031/replay_v5.py).
- Dossier raw-vintage: blob `147da8f8`; forensics `174dde55`; data-quality `3cd267e4`; confronto modelli `543a66d8`.
- DD e topologia: `6e922184`, `1f538e9d`, `8815af47`, `ccd65588`, `54e498b5`.
- OASIS `802c9b0f`; HMM/RMT `b63f9b0e`; Holdout70 `1350ccb0`; paired US149/EU148 `bd3ef20c`.
- V4 `d1d8cfe2`; V5 design `b88a758e`; V5 eseguita `c92a4923`, `2ab251de`, `ec7c470b`; shadow `0cf6e8bf`; factor leadership `26678fcf`.

Gli script di questo audit e i CSV in `checks/` consentono di ispezionare esattamente i controlli eseguiti. Il successo del workflow certifica quei controlli, non l'intera strategia.
