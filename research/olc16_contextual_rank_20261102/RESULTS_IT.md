# OLC16 — ranking contestuale e memoria rivalutata

2 novembre 2026. Esperimento concluso. Nuova candidata di ricerca: TOP2_CONTEXT_REVALUE. Nessun ordine, nessuna promozione su main. CUM_FIT resta candidata distinta e immutata.

## Esperimento e attribuzione

24 modelli annuali principali,24 controlli con contesti rimescolati nel solo training,66 fit interni,342 inizializzazioni prefissate. Nessun nuovo predittoreETF addestrato.208 portafogli incluse48 riproduzioni dei controlli. Protocollo principale681bc11ed9d0732b71c8bf33cc92849cd7b97f14; parent763387eceee4b7fbf131827f10dee7f608abeb68.

La curva combina le previsioni congelate C21/C42/C63 con pesi beta(x)=softmax(log(.45,.35,.20)+(a1,a2,0)+(B1*x,B2*x,0)). Stessi coefficienti nei due universi, contesti locali diversi. I tre input sono trend126, log(vol21/vol126), stabilità dei leader. I proxySPY/EXSA.DE descrivono soprattutto equity, non tutte le esposizioni. Scaler e imputazione solo sul training; interi gruppi di etichette maturi prima del cutoff. Fit annuali2021–2026, applicazione mensile. Prima del2021 pesi fissi.

Controlli abbinati statici e contestuali, con due obiettivi: pairwise economico e surrogato differenziabile della selezioneTop2. Nel secondo, pesi soft di training<=.5,somma1; sono soltanto un'approssimazione per apprendere, non l'allocazione reale. I portafogli usano ancora le due scelte nominalmente50/50. Nessun CAGR entra nel fitting. Target economicoU=(L0_21+sqrt(.5)*L21_42+.5*L42_63)/(1+sqrt(.5)+.5).

La memoria rivalutata è un'estensione post-osservazione registrata prima dei suoi esiti ad ab29481db16311e070bd102e5fdc2f837ac827a0. Applica i coefficienti noti OGGI alle previsioni originali degli ultimi tre segnali; dopo il mapping di scala usa la stessa memoria40/30/30,potenza1.1 e fusione47.5%Return/52.5%Hybrid. Non cambia previsioni storiche, non riscrive vecchi ordini e non usa esiti futuri. La stessa modifica è applicata al controllo statico. La diagnostica placebo sulla nuova memoria è registrata a8e8b8ee53fabe8211fe637c47f0d2852a477949c.

## 1. Cambiamenti decisionali e qualità del layer

Su66 segnali2021–giugno2026, TOP2_CONTEXT controSTATIC cambia15coppie nativeEU/11USA e14finaliEU/13USA. Con la nuova memoria cambia17coppie finaliEU/13USA. Non è il casoOLC15 di pesi variabili e zero nuove decisioni.

Beneficio nativoCURRENT, punti logaritmici diU in eccesso all'universo, segnali2021–2024 con tutte le uscite63 prima del2025:44EU/45USA. TOP2_STATIC=.2488EU/-.1216USA; TOP2_CONTEXT=.2888/-.0865. PAIR_STATIC=.3079/.0290; PAIR_CONTEXT=.3342/.3471. Il contesto migliora ciascun controllo statico nei due universi; non supera ORIGINAL(.5599/.7342). Non presentiamo un selettore isolato universalmente migliore.

Dopo memoria e fusione:

| Variante | U eccesso EU | U eccesso USA |
|---|---:|---:|
| TOP2_STATIC | .8258 | 1.0230 |
| TOP2_CONTEXT | 1.0996 | .9982 |
| TOP2_STATIC_REVALUE | .8258 | 1.2135 |
| TOP2_CONTEXT_REVALUE | .8773 | 1.5493 |

Sono punti logaritmici scontati per opportunità, NON CAGR. Il confronto con pari nuova memoria è favorevole nei due mercati. Sui48 segnali2021–2024 includendo gli esiti successivi, resta .7853->.8325EU e1.0188->1.3325USA. Contro CUM_FIT il datoEU nativo post-fusione resta inferiore(.8773contro.9161).

## 2. Portafoglio principale2021–2024

IMMEDIATE,costo.001 nella convenzione legacy mezzo turnoverL1, capitale nominale50/50. CAGR a252sedute, massimo drawdown nella finestra. Return,esposizione,stop e flussiV6 congelati per attribuzione; non è ridisegno completo del rischio.

| Variante | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| ORIGINAL |20.031%|-23.249%|39.922%|-27.003%|
| CUM_FIT |22.753%|-30.818%|39.008%|-19.178%|
| TOP2_STATIC |21.961%|-26.421%|33.311%|-20.155%|
| TOP2_CONTEXT |25.034%|-23.249%|33.416%|-20.155%|
| TOP2_STATIC_REVALUE |21.961%|-26.421%|38.833%|-20.155%|
| TOP2_CONTEXT_REVALUE |24.000%|-24.772%|44.153%|-20.155%|

ControCUM_FIT:+1.247puntiCAGREU/+5.145USA; MaxDDEU migliora6.046punti, USA peggiora.977punti. ControSTATIC_REVALUE:+2.039EU/+5.320USA. Una parte del guadagnoUSA è già ottenuta dalla sola nuova memoria statica; non attribuiamo tutto al regime. InEU la memoria rivalutata riduceCAGR rispetto aTOP2_CONTEXT25.034%.

Costi triplicati: candidata21.492%EU/40.347%USA,DD-26.302%/-20.567%; CUM_FIT20.136%/35.331%,DD-32.587%/-20.145%. Non sono costi per lato garantiti nel mercato reale.

## 3. Storia completa e risultati avversi

Febbraio2019–1luglio2026,FULL,costo.001: candidata18.229%EU/44.773%USA controCUM_FIT18.097%/42.085%. Il guadagnoEU è piccolo. MaxDDcompleto identico-32.089%/-25.526%: entrambi i minimi comuni sono nel2020, prima dell'adattamento. Non è una nuova protezione per quel crollo.

LAG1,input sistemici ritardati di una seduta,IMMEDIATE2021–2024: candidata20.372%EU/52.301%USA controCUM_FIT20.773%/44.380%. L'Europa non migliora più. SulFULL_LAG1EU18.763%contro19.496%. Il controllo non certifica tutta l'eseguibilità live.

Rendimenti di periodo, nonCAGR: nel2025EU candidata16.744%contro26.402%CUM_FIT; USA38.346%contro32.376%. Nel2023USA36.162%contro45.618%.2026parziale finoal1luglio:16.505%EU/75.139%USA contro11.190%/84.225%. Non si seleziona una politica diversa percontinente.

## 4. Controprove e incertezza

Due controlli con contesti rimescolati nel training e poi la stessa nuova memoria: U post-fusioneEU.8186/.8043 controautentico.8773; USA1.0095/1.6057 controautentico1.5493. Una replicaUSA supera l'autentico; non dichiariamo dimostrata la nuova informazione di regime. Due repliche non producono una probabilità di successo calibrata.

Bootstrap descrittivo,blocchi6mesi,4000estrazioni. DeltaU controSTATIC_REVALUE:+.0515puntiEU,CI95%[-.2071;+.3981]; +.3358USA,[-.2971;+1.1428]. Lo zero non è un veto. Intervalli non corretti per tutta la ricerca. Eliminando ex post i tre mesi più favorevoli del differenziale, la media logaritmica annualizzata diventa negativa nei due mercati(circa-1.40EU/-1.19USA): diagnostica di concentrazione, non regola per escludere mesi dal trading.

Conclusione: conservare la candidata senza sostituire automaticamente CUM_FIT oORIGINAL. Progresso reale nelle scelte e confronto positivo con il controllo a pari memoria, ma debolezzeEU2025/LAG1, dipendenza dall'integrazione, placeboUSA e campione già esplorato rimangono espliciti.

## 5. Verifiche e conservazione

19test nuovi e25parentOLC15 passati nelle rispettive suite. Quattro importazioni fallite nella raccolta ricorsiva dei parent documentate; non è dichiarato verde l'intero repository.48modelli finali rifittati/ripredetti esattamente;48percorsi parent identici. Calcoli indipendenti:390936intervalli contabili,8112metriche portafoglio,274428valori nativi e7623NDCG; errori massimi3.55e-15/2.31e-13/3.33e-16.6perturbazioni future conservano il passato. Revisione dell'autore, non esterna.

Tutti18moduli e3file di test sono individualmente versionati al commit c4ba6149e5ea3ec7be6c35b215ec0d31aef9a625; l'albero sorgenti remoto0a58a1bb375db1615f390d04f9e4a65e5c7047e4 coincide con quello locale. Checkpoint finali autonomi per questo esperimento dai forecast preparati, non per i modelliETF dai raw.

Il checkpoint iniziale31MB è inLibrary(libfile_a9d37832fd948191aa887f2645fc3eff). Il caricamento dei dueZIP finali ha restituito 'Cannot use ConversionTreeTransaction when not in context', anche nel tentativo singolo. NON è dichiarato completato: iZIPfinali sono consegnati nella chat, non assetGitHub. I loro hash e il ripristino pulito sono nel checkpoint finale.

Restano storia riutilizzata, mercati correlati, survivor bias,total-return/FX/distribuzioni non certificati, spread/costi/fill same-open ereditati. Nessuna simulazione è una previsione o certificazione per trading reale. Nessun lavoro richiede un processo in background.
