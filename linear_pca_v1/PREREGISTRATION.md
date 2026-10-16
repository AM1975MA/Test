# LINEAR PCA95 annuale: riduzione ortogonale preregistrata

Utente: riprovare LINEAR con ablation delle125feature cercando baseortogonale. Solo AM1975MA/Test, branch research/linear-pca95-20261016. Produzione intatta, input Yahoo originali conservati. Nessun nuovo download prezzi. Protocollo preparato il14ottobre, esecuzione autorizzata ripresa il16ottobre2026; nessun fit PCA precedente.

## Domanda e confronto

Una rotazione ortonormale completa conserva score e penalitaL2 di LINEAR; non e un candidato di miglioramento. Verificare matematicamente e sui30checkpoint annuali archiviati l'equivalenza completa, senza nuovi fit125rotati. La candidata unica e LINEAR_PCA95: riduzione delle direzioni delle125feature standardizzate, tramite base PCA che conserva almeno95%varianza sulsubtraining. Non e selezione di un sottoinsieme di nomi originali: ogni componente e una combinazione di feature.

Prima dei fit controllati ledger, PR41–44/K12–K16 e ablation per famiglie. Le precedenti selezioni ortogonali usavano XGBoost e non questo LINEAR ListNet PCA95. Non ripetere gli esperimenti completati. La ricerca esplora una sola soglia95%, fissata prima dei risultati; niente griglia95/99/90 o selezione CAGR sui periodi osservati.

## Ricetta congelata

Controllo LINEAR_NUMERICAL_REPAIR annuale completo, run38580178650, hashRESULT19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f. Stesso storico originale crescente, 2017–2026,149Original149,treparquet TI congelati e tre raw gia archiviati. Stesse label/eligibility>=30feature originali, split10%finale delle date pervalidazione e purge, senza refit su training completo. Il noto ritardo dei dati effettivamente allenati resta invariato per isolare la riduzione dimensionale.

Imputazionemediana e scaling originali fit soltanto sulsubtraining di ogni anno/download. PCA ottenuta dalla decomposizione simmetrica di X'X/(n-1), X gia centrato/scalato. Minimo k con varianza cumulativa>=95%; se la soglia taglia un blocco di autovalori quasi coincidenti, includere il blocco intero, tolleranza1e-10*lambda_max. Nessun whitening, nessuna nuova standardizzazione deiPC, nessun uso target per scegliere PCA/k.

Stesso ListNetdecili,L2=.001,solverL-BFGS riparato, inizializzazionezero,budget2000,memoria10,Armijo1e-4,max50backtrack,residuo1e-7. La convergenza si verifica nelle coordinate PC vincolate: il gradiente125 non deve essere nullo.30nuovi fit(10anni x3download). Salvare basis,beta,autovalori,k e w125=basis@beta per inferenza compatibile. Featureoriginali,interfaccia e altri modelli invariati. Nessun Opportunity, nessun intervento aggiuntivo DD. Stesso replay portafoglio,costi,esecuzione e protezioni annuali verificati; ricalcolo dei discendenti di Compact21.

## Verifiche

Test sinteticimatematici: score e normaL2 invarianti con rotazione completa, covariance diagonalizzata, soglia95%, blocchi degeneri completi. PCA nonriceve dati futuri: nessunfit delpreprocessing sulla validazione o sull'intero periodo. Audit indipendente su30modelli: ricostruzione state e PCA dal solo subtraining, ortonormalita, spettro/soglia/proiettore, beta->w125, inferenza native e comune, gradientePC indipendente<=1e-7 e hash checkpoint/input. Fullrotation su coefficienti archiviati: errore score e norma<=1e-10, senza refit. Controlli maturazione/fingerprint esistenti e parita replayBASE richiesti.

Riportare k,varianza,eigengap peranno/download. Confrontare sottospazi via distanza normalizzata tra proiettori e angoli principali: segni/numerazionePC non hanno significato. Confronto nello spazio delle feature standardizzate constate di ciascun download; non equivale ad indipendenza statistica. Componenti decorrelate neltraining possono essere correlate fuori campione. Una direzione a bassa varianza potrebbe contenere segnale predittivo.

## Valutazione fissata

Tre replay completi 2017-02-01–2026-07-01,2366osservazioni,113periodi completi/114segnali disponibili. Risultati CAGR,MaxDD,Sharpe,turnover,span eSDCAGR,pairwise eanyTop1/Top2, rendimentiannui incl2021/2023. Stessa aggregazione perdata perqualitaStandalone. Controllo principale LINEARannuale archiviato; benchmarkBASE riportato come contesto se utile.

Riutilizzare i gate originali, riferiti qui al LINEARannuale: CAGRmedio eognidownload>=95%controllo,Sharpe medio>=95%,MaxDD medio/ognidownload nonpeggioreoltre2pp,spanCAGRridottoalmeno25%,Top1anyridottoalmeno25%,Top2ordinatononpeggiore. Qualita Top1percentile eNDCG5perdata>=95%controllo. Tutti congiunti per avanzamento di ricerca. Riportare anche fallimenti,nessunapromozione perCAGRmedio solo. Tre revisioni correlate eperiodo giausato per ricerca: nessuna significativita su3mercati indipendenti ovalidazione futura. Non ottimizzare per recuperare solo2021/2023.
