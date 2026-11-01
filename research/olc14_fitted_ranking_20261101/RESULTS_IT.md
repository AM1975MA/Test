# OLC14 — risultati del fitting cronologico

1 novembre2026. Lotto concluso. Nessuna nuova baseline, nessuna modifica a main o Etf_trader. Il rapporto integrale e tutte le tabelle sono nell'archivio finale identificato nel CHECKPOINT_03.json; questa è la sintesi verificata sul repository.

## Contratto e lavoro eseguito

Protocollo precedente agli esiti: facad01242bca20502dcf5563b84c9f60d0bd015. ParentOLC13 c7e831cab0934ac7e51ce94ee39b47a2cb875526.480 nuovi regressori ET/XGB,4 refit di parità,198 fit interni e12 fit annuali finali della combinazione,6 selezioni fra target e96 portafogli.

TARGET_SELECT è selezione discreta fra quattro targetOLC13; NON è una ricerca continua di ogni possibile formula della label. CUM_FIT e INC_FIT apprendono pesi nonnegativi di somma1 su tre previsioni separate; alpha1/1,5/2 e regolarizzazione0,01/0,1/1 scelti temporalmente. Nessuna regressione simbolica o nuovo ampio sweep delle label. I42 e I63 sono percentili dei rendimenti incrementali21–42/42–63; C21/C42/C63 quelli cumulativi. La potenza delle label di base rimane1,5. Alpha della combinazione agisce invece sugli SCORE PREVISTI.

Tutti i modelli usano gli stessi Hybrid42, campioni OLC11 interamente maturi e seed101/211/307. ReturnRSI immutato. Confronto causale annuale2021–2026: solo OOS precedenti con intero gruppo di esiti noto prima del cutoff, due finestre interne disponibili.2019–2020 warm-up fisso. Stessi parametri perEU/USA, peso50% per mercato. La ricerca usa una loss pairwise orientata alla coda alta, pesata per divari economici e regolarizzata, mai il CAGR.

Task economico comune: U=(L0_21+q*L21_42+q²*L42_63)/(1+q+q²),q=sqrt(.5). Ogni blocco logaritmico contato una volta. È utilità scontata a blocchi, NON CAGR, NON un conto e NON sconto giornaliero esatto. Il fitting si giudica prima sui due ETF selezionati rispetto all'universo della stessa data. Il mapping allo stesso intervallo empirico del controllo, prima della vecchia fusione, preserva le graduatorie; una gestione delle ripetizioni nell'ancora introduce al massimo1e-12 di perturbazione monotona, prima dei risultati economici.

## Layer nativo: risultato principale2021–2024

Solo esiti63 maturi prima del2025:44dateEU/45USA. Valori =100*eccessoU, punti logaritmici di utilità, non rendimenti annualizzati.

|Ranking|EU|USA|
|---|---:|---:|
|Originale|0,560|0,734|
|Selezione temporale quattro target|0,742|0,409|
|Cumulativi separati, pesi fissi|0,307|0,202|
|Cumulativi separati, fitting|0,383|-0,124|
|Incrementali separati, pesi fissi|0,304|0,214|
|Incrementali separati, fitting|0,521|-0,102|

Fitting cumulativo meno proprio controllo:+0,076EU/−0,326USA; incrementale:+0,218EU/−0,315USA. Nessun miglioramento comune del ranking. Anche le teste separate a pesi fissi sono inferiori al vecchio modello con target aggregato; non attribuire tutto al fitting.

TARGET_SELECT sceglie ORIGINAL_P10 nel2021/2022, ORIGINAL_P15 dal2023. Non seleziona esponenziale e non batte l'originale in entrambi i mercati.

Controllo di copertura post-risultato, senza rifit: includendo tutti48segnali2021–2024 e i relativi esiti maturati anche nel2025, il vantaggio cumulativoEU diventa−0,050punti e USA resta−0,306. Il fitting incrementale resta+0,237EU/−0,136USA. Non enfatizzare il piccolo beneficioEU della sola finestra44mesi.

Bootstrap descrittivo appaiato6mesi/4000estrazioni: CUM deltaU EU+0,076,[−0,073;+0,223], USA−0,326,[−0,668;−0,032]. INC EU+0,218,[−0,197;+0,688], USA−0,315,[−1,566;+0,958]. Intervalli che attraversano zero non sono veto; non sono posteriori né correzioni dell'intera ricerca storica.

## Pesi appresi

CUM2021:beta38,38/6,04/55,58%,alpha1;2023:43,90/34,05/22,05%,alpha2;2025:44,03/34,04/21,93%,alpha1;2026:38,80/18,45/42,76%,alpha1. Il primo fit dispone soltanto di21date mature per mercato. Molte righe/pairwise non sono molte repliche temporali indipendenti. Nessuna formula unica stabilmente identificata; non applicare i pesi2026 retroattivamente. Le variazioni non provano da sole una causalità di regime.

## Il portafoglio può dare un segno diverso

2021–2024,IMMEDIATE,fee0,001 nella convenzione legacy mezzoL1 turnover. Target50/50; Return, memoria, rischio/V6 congelati. Il classificatore precedente non è riottimizzato. Non è la ricostruzione end-to-end di ogni sottosistema.

|Configurazione|CAGR EU|MaxDD EU|CAGR USA|MaxDD USA|
|---|---:|---:|---:|---:|
|Originale|20,03%|-23,25%|39,92%|-27,00%|
|Selezione temporale target|11,93%|-38,44%|27,99%|-32,51%|
|CUM fisso|22,11%|-25,79%|30,83%|-20,15%|
|CUM fitting|22,75%|-30,82%|39,01%|-19,18%|
|INC fisso|12,32%|-34,45%|17,88%|-30,97%|
|INC fitting|16,04%|-29,30%|5,93%|-42,02%|

Il fittingCUM migliora la crescita rispetto al suo controllo fisso in entrambi, ma peggiora il drawdownEU. Sulla finestra completa febbraio2019–1luglio2026, CUM_FIT raggiunge18,10%EU/42,08%USA, contro14,94%/38,13%originale; DD−32,09%/−25,53%,contro−33,68%/−30,69%. È una candidata di PORTAFOGLIO da conservare, non dimostrazione di ranking migliore.

I ritardi modificano il confronto: nel periodo principale, DELAY3 CUM_FITmenoORIGINAL vale−4,49ppEU/+6,58USA; PHASE5−2,61EU/+4,66USA. Con IMMEDIATE e input sistemici ritardati peggiora entrambi. Non scegliere una politica diversa per mercato. Il vecchio39,33%resta un diverso contratto/finestra.

Già sulle stesse44/45date, dopo fusione conReturn il deltaU del fittingCUM cambia segno rispetto al layer nativo: EU1,069→0,916;USA1,130→1,237. Questo localizza interazioni, non autorizza ad attribuire al ranker un miglioramento misurato altrove.

## Decisione e verifiche

Conservare originale, procedura causale e candidataCUM_FIT. Nessuna promozione di TARGET_SELECT o INC_FIT come miglioramento comune. Non conclude che fitting o target incrementali siano inutili in generale. Restano storia ripetutamente esaminata, universi correlati, survivorship,total-return/FX non certificati, spread/costi/same-open legacy, revisione dell'autore non esterna.

480 modelli riaperti, previsioni identiche.16percorsi originali identici.180432intervalli ricostruiti,4992metriche,418176calcoli payoff e11616NDCG verificati separatamente.19test nuovi più15/23parent.4perturbazioni di esiti futuri conservano fit precedenti. Piccoli scarti BLAS del refit, massimo2,78e-16, separati dalla prova causale nello stesso ambiente e dall'identità delle Top2.

Ripristino in directory pulita:848voci manifestHeads e220manifestRisultati verificate;19test passati;12replay reali con TUTTI gli array identici. Le sovrapposizioni tra manifest non sono contate come file distinti nuovi. Nessun processo di training lasciato attivo.

Modelli/input e archiviofinale sono nella Library persistente `/ETF_Research/OLC14_Fitting_Ranking_20261101/`, non negli assetGitHub. Estrarre entrambi nella stessa directory. CHECKPOINT_03 riporta hash,dimensioni,ID e ambito. Il repository contiene tutti17moduli runtime,4filetest e sintesi; i grandi dati,modelli,curve e gli script accessori di packaging/report sono negli archivi. Non confondere questi due perimetri.
