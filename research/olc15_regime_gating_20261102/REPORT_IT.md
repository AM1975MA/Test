# OLC15 — contesto di mercato e scelta della formula

2 novembre2026. Lotto concluso; sintesi remota. Relazione estesa, curve e registri negli archivi verificati indicati da FINAL_CHECKPOINT.json. CUM_FIT rimane candidata; nessuna promozione, ordine o modifica a main.

## Risultato

32 fitting annuali attivi,120 fit interni,224 percorsi completi (48 controlli). Zero nuovi fit dei modelli ETF di base. Il contesto modifica i pesi di miscela ma non aggiunge scelte finali rispetto a un peso costante nell'anno o alla sola qualità recente:0/42 coppie differenti in Europa e0/42 negliUSA.64 confronti completi di percorso sono identici, non soltanto nei CAGR arrotondati.

Il risultato è limitato a questo gate, questi esperti e questo contesto. Non prova che i regimi siano irrilevanti o che i coefficienti annuali non possano dipenderne. La difficoltà osservata è che le due formule hanno pochissime differenze decisionali utilizzabili per il training.

## Contratto

Parent OLC14:6fcc215eeaa9834f5bcf8581e1fa6549a403f5b2. Protocollo iniziale e6ae78bb016525645e72c3aaea61e7cc4b49f84d. Dopo il primo risultato nullo è stata registrata l'estensione post-fusione a d0a03455a13ba2c9d653a146da06715337b8a00d: è un'estensione post-osservazione, non una conferma indipendente. Tutti i risultati iniziali sono preservati.

Esperti congelati CUM_FIXED e CUM_FIT; ORIGINAL controllo esterno. Cinque input noti alla chiusura locale: trend126 normalizzato per volatilità; efficienza del percorso63; log-volatilità21/126; drawdown dal massimo126; stabilità delle graduatorie del modello CUM_FIXED. ProxySPY USA ed EXSA.DE Europa dai prezzi già congelati; non è un modello completo bond/credit/commodity né una nuova certificazione del total-return. Nessun closeUSA futuro per l'Europa. L'input opzionale recent è il contributo delle ultime12 date con esiti già maturi, non gli esiti ancora aperti.

Il gate Ridge condiviso fraUSA/Europa prevede Delta=U(Top2_FIT)-U(Top2_FIXED), prima sulle scelte native e poi sulle scelte dopo fusione. U è l'utilità logaritmica incrementale0–21,21–42,42–63, pesi1,q,q² normalizzati, q=sqrt(.5); non CAGR. Il gruppo diventa disponibile solo dopo tutti gli esiti. Standardizzazione/imputazione solo training, mercati bilanciati, penalità1/10/100 con validazione cronologica interna e default10 in assenza di fold valido.

La trasformazione g=logistic(2*delta_prevista/RMS_training) produce un peso di segnale, non capitale o probabilità. La miscela CURRENT entra prima della memoria40/30/30, potenza1.1 e fusioneReturn.475/Hybrid.525. Nessuna media delle vecchieNAV. Stop, budget di esposizione e flussiV6 restano congelati.

## Periodo realmente adattivo

Nel2019–2020 FIT=FIXED;2021–2022 fallbackg1. Alcutoff2022 ci sono9 date mature per mercato, sotto il minimo12. Alcutoff2023:21EU e20USA. Primo segnale adattivo31gennaio2023, primo ordine1febbraio2023. Le finestre dal primo ordine sono separate da quelle che includono l'inizializzazione di gennaio.

42 segnali adattivi fino a giugno2026;35 gruppiEU e38USA con esiti63 completi entro1luglio2026. Campione principale2023–2024 con esiti pre2025:20EU/21USA. Anche tutti24 segnali2023–2024 con esiti successivi sono verificati, senza riaddestrare.

## Differenze effettive fra gli esperti

|Confronto FIT contro FIXED,42 segnali|EU|USA|
|---|---:|---:|
|Coppie native differenti|3|4|
|Coppie differenti dopo fusione|4|2|
|Differenziali nativi nonzero con esiti maturi|2/35|2/38|
|Differenziali post-fusione nonzero con esiti maturi|3/35|1/38|

Nel2023–2025 nativeTop2 identiche35/36EU e36/36USA. Coefficienti differenti non garantiscono decisioni differenti. Correlazioni medie C42/C63 circa.840EU/.872USA sono una diagnostica, non spiegazione causale.

## Che cosa cambia aggiungendo il contesto

Gate contesto+recent, target nativo: pesoFIT39,53–46,31%EU e39,57–45,23%USA. Con target post-fusione:46,11–51,04%EU e44,63–51,44%USA. Il peso costante annuale occupa già una zona vicina.

Nonostante queste variazioni, coppie finali differenti rispetto al controllo costante o recent:0/42 nei due universi, in entrambe le fasi. Nella prima fase cambia un solo Top2 intermedio europeo, ma non quello finale.64 confronti di array su costi,timing e input sistemici ritardati confermano risultati identici. Non attribuiamo quindi un eventuale vantaggio della miscela al regime.

Nella seconda fase il contesto riduce lievemente ilMSE del differenzialeEU ma peggioraUSA; nessun miglioramento comune o nuova decisione. I confronti con payoff identici hanno intervalli campionari nulli per identità, non come prova universale di assenza di informazione. Bootstrap appaiato6mesi,4000 estrazioni; nessun veto automatico per intervalli che includono zero.

## Decisione

Conservare CUM_FIT come candidata insieme a FIXED e ORIGINAL. Non promuovere questo gate. Prima di moltiplicare regimi e parametri, ottenere più storia genuinamente fuori campione e alternative con differenze decisionali motivate: opportunità immediata, prosecuzione, deterioramento. Questo lotto non ha fit di beta/alpha direttamente condizionati, néHMM. Non dimostra protezione2020, quando il gate non era addestrabile.

## Verifiche e preservazione

570 file parent verificati;42 test ereditati (23+19) e25 nuovi passati.48replay parent con quantità,cash,target e decisioni bitwise identici; NAV/ledger massimo scarto3.55e-15. Tolleranza numerica dichiarata prima dei fitting, non falsa parità bitwise.

32modelli gate rifittati esattamente;14verifiche di perturbazione futura;353483 valori di score ricostruiti dai pesi.91476 metriche native indipendenti,15232 metriche di portafoglio,421008 intervalli contabili. Revisione dell'autore con implementazioni distinte, non revisione esterna.

Ripristino pulito:436file conSHA256,25test,16portafogli rappresentativi con array identici. Il checkpoint è autonomo per questo lotto dai forecast preparati, non per rifare i predittoriETF dai dati raw. Tutti18moduli e i test sono versionati individualmente. Gli archivi completi sono nellaLibrary persistente, non assetGitHub. Nessun processo resta necessario dopo la consegna.

Limiti: universi correlati e sopravviventi, storia già esplorata, total-return/FX/distribuzioni non certificati, spread/costi e fill same-open ereditati; flussiV6 congelati. Il conteggio dei test non certifica trading reale.
