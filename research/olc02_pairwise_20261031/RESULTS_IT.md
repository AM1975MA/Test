# OLC-02: il confronto diretto aiuta il vecchio filtro, ma non supera CL01 nei due universi

31 ottobre 2026. Lotto concluso; nessuna modifica a main o alla produzione. Protocolli:84f5b0d0f4280147d6fa186583cea1dc7c791f27 e, per la successiva diagnostica età,b1798e14d4a9d729a4bb6809e5943aee81ad49a6. Il rapporto completo e tutte le tabelle sono negli archivi consegnati.

## Risultato

Il nuovo blocco prevede direttamente il valore incrementale di una proposta CL01 rispetto al mantenimento dei ticker realmente detenuti. Non può scegliere ticker esterni alle proposte, andare discrezionalmente in cash o ridurre il budget. Mantiene il motore e le protezioni originali. Sono conservati sia risultati favorevoli sia sfavorevoli.

Periodo2021–2024, prima azione appresa febbraio2021. Costi0,001 secondo convenzione legacy di metà turnover: NON automaticamente10bp per lato. Sono CAGR di conti persistenti, non somme di label sovrapposte. Non confrontarli col vecchio39,33%di una versione/finestra diversa.

| Politica | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| CL01 capitale50/50 |15,7504%|-26,4711%|33,6800%|-20,1546%|
| Vecchio Ridge assoluto, stesso filtro senza cash |7,1471%|-33,0581%|-16,0930%|-64,1800%|
| Nuovo Ridge differenziale profilo21/42/63 |20,8133%|-26,2687%|9,9937%|-34,4293%|
| Nuovo Ridge21, sostituzione di un solo slot ammessa |22,2057%|-27,9975%|-8,9100%|-51,6347%|
| Nuovo HGB differenziale profilo21/42/63 |12,0702%|-26,3876%|14,6542%|-29,2704%|
| Conserva i nomi, salvo protezioni/rientri |21,9437%|-33,7427%|-3,8058%|-53,8914%|

La formulazione diretta supera il vecchio filtro Ridge assoluto nei due mercati, ma non CL01. Il controllo assoluto usa le vecchie previsioni con la stessa restrizione HOLD/proposta e senza cash, separando questo aspetto. Cambiano però anche popolazione di training e contesto: non si attribuisce tutto al solo target.

Il controllo tecnico FOLLOW_CL01, che accetta sempre la proposta senza modello e senza riordinare inutilmente gli stessi nomi, rende15,8196%EU e33,6800%USA. Il piccolo scarto europeo rispetto alla baseline è una convenzione dei due slot, non alpha. Quattro percorsi aggiuntivi misurano questa differenza d'interfaccia.

## Metodo realmente eseguito

Quattro traiettorie causali dal2019 generano gli incumbent:CL01mensile,bufferTop4 e due fasi bimestrali. A ogni evento sono incluse la propostaCL01 e alternative di uno slot dai Top5, anche non eseguite. Deduplicazione degli stati/azioni identici e peso totale1per mese.2052righeEU,2090USA,88mesi per mercato: non migliaia di osservazioni indipendenti.

Target:log ricchezza futura normalizzata della nuova coppia50/50 meno log ricchezza del mantenimento delle quantità realmente detenute. Etichette su Open reali a21/42/63sedute; nessun futuro prezzo riempito. Le differenze statiche non includono tutte le protezioni/cambi successivi: solo il replay continuo valuta la strategia.

38feature: differenze degli score/trend, livelli dell'incumbent, età delle posizioni, overlap, volatilità e correlazione. Sono proxy di esposizione dai prezzi, NON nuove informazioni complete su settori/fondamentali.72modelli2021–2026:2mercati×2famiglie×3orizzonti×6anni. Ridgealpha20;HGB120iterazioni,15foglie,LR0,05,min_leaf60,L2=10,noearlystoppingcasuale. Ogni testa usa solo etichette mature prima del1gennaio. Nessuna ricerca di parametri post-risultati.

Gate con testa21 oppure media fissa delle tre teste cumulative, meno costo stimato noto prima dell'apertura. Valore netto positivo accetta; altrimentiHOLD. È un surrogato, non probabilità calibrata o controllo dinamico ottimale. FULLaccetta la coppia, SLOTpuò sostituire un solo nome con un membro degli attualiTop2CL01. Nessun ticker estraneo, nessun nuovo cash. Con meno di due posizioni dopo gli stop si segue la reentryCL01. HOLDnon abolisce la protezione originale.

## Opportunità salvate e perse

Controprove statiche sulle proposte complete negli stati effettivi del filtroRidgeprofilo, con esiti maturati prima2025:

| A21sedute, punti logaritmici netti sul capitale principale | Proposte accettate | Proposte rifiutate |
|---|---:|---:|
| Europa |+1,13(27casi)|-1,44(13casi)|
| USA |+2,04(24casi)|+3,47(20casi)|

A63sedute le20proposte americane rifiutate hanno vantaggio medio+5,96punti logaritmici. Non è CAGR o profitto automaticamente recuperabile: gli orizzonti si sovrappongono e i conti reali cambiano nel frattempo. Gli esempi non sono vincitori futuri inventati: erano proposteCL01disponibili alla decisione.

### Falso HOLD americano di febbraio2022
Al31gennaio2022 il filtro mantieneTUR/KWEB invece di accettareURA/USO, perché il vantaggio netto stimato è circa-1,7puntibase. Dal1febbraio alla successiva apertura mensile1marzo, CL01guadagna16,44%, il filtroperde12,89%.

Altri casi: marzo2023EWN/EIRLmantenuti invece diSMH/SOXX, -1,50%contro+8,22%; febbraio2024SOXX/UNGinvece diHACK/SOXX,-1,99%contro+7,99%. In Europa novembre2021EXV5.DE/EXV9.DEinvece diEXH1.DE/CB3G.DE,-11,27%contro-2,39%. Sono rendimenti dei rispettivi intervalli tra aperture mensili, non annualizzati. Tutte le decisioni, anche favorevoli, sono conservate.

## Informazione predittiva limitata, non assenza universale di segnale

RidgeUSA63riduce MSEdi circa10%rispetto a differenzialezero e4,7%rispetto alla media di training sul campione delle proposte complete della baseline. Non tutte le teste sono inutili. In Europa nessuna delle sei combinazioni famiglia/orizzonte batte quei controlli nel campione. Sulle41proposte abbinate ai tre orizzonti per mercato, RMSEdel profiloRidge5,81punti logaritmiciEU e10,08USA; negliUSA effetto medio reale2,55punti contro previsione0,60. Sono diagnostiche statiche, non errori dellaNAV né direttamente comparabili ai vecchi target assoluti.

La capacità media non certifica le scelte vicine alla soglia, dove una stima di pochi punti base può bloccare una proposta importante. Non sono state prodotte probabilità posteriori o predittive calibrate di successo.

## La sensibilità ai costi annulla il vantaggio europeo

| Costo legacy | CAGR CL01 EU | CAGR Ridge diretto EU | CAGR CL01 USA | CAGR Ridge diretto USA |
|---|---:|---:|---:|---:|
|0,001|15,75%|20,81%|33,68%|9,99%|
|0,003|12,96%|7,60%|30,11%|7,48%|

I costi non si limitano a sottrarre commissioni: cambiano le decisioni e il percorso. Al31gennaio2022 entrambi i contiEU detengonoEXV1.DE/S7XE.DE; a0,001il modello accettaEXV6.DE/VVSM.DE(+4,34bpnetti previsti), a0,003mantiene(-15,70bp). Le posizioni successive possono divergere. Nessuna soglia è stata ritoccata per recuperare il risultato.

## Durate fuori dal campione di training

Ridge21EU mantiene44volte su48, raggiunge685sedute di età e supera34volte il supporto del training. La varianteSLOTarriva722sedute. Dopo le prime72curve è registrata una sola diagnostica: se l'età supera il massimo già presente nelle etichette mature delle teste richieste, il nuovo gate si astiene e segueCL01. Nessuna soglia numerica scelta dal rendimento, nessun refit.32percorsi aggiuntivi nei due universi/costi.

RidgeprofiloEU passa20,81→21,35%,USAresta9,99%; il problemaUSAavviene senza escursioni d'età. A costostress ancheEUprotetto resta sotto baseline10,16%contro12,96%. Altre varianti peggiorano. Il supporto dell'età identifica un problema reale ma non spiega tutto e non verifica l'intera distribuzione degli stati. La diagnostica è post-primi-risultati, non un nuovoholdout.

## Incertezza e periodi successivi

48mesi2021–2024; bootstrapappaiato3/6mesi,10000repliche,seed20261031, stessi blocchiUSA/EU. Ridgeprofilo-CLO1half,costo0,001,blocchi6mesi:EU+4,36punti logannui,IC95%[-2,25;+11,55];USA-19,44,IC[-37,58;-4,26]. Nessun veto automatico per lozero. Il problema è economico e trasferibilità/costi, non il p-value. Le frequenze bootstrappositive non sono posteriori e non correggono tutte le ricerche passate.

2025rendimenti effettiviRidge+33,70%EU/+49,75%USA,CL01+25,59%/+49,45%.2026parziale fino1luglio:+28,86%/+44,94%contro+3,60%/+38,91%. Non CAGRannui, non nuoveholdoutvergini; non selezionati per cancellare il risultato2021–2024.

## Verifiche e limiti

108percorsi:72iniziali+32supportoetà+4FOLLOWtecnici;8traiettorie training conteggiate separatamente.72modelli salvati e hash/maturazione verificati.23nuovi test passati; non dichiarata verde l'intera suite del repository.108NAV ricostruiti indipendentemente da quantità post-stop e Opensuccessivi:errmax3,55e-15;4212metriche:errmax6,58e-14.104warmupimmutati.8refit con futurelabel/featureperturbate e8replayprefix:err0.0. I104percorsi allora presenti sono byte-identici dopo la modifica dei soli import per portabilità. MotorelegacyimmutatoSHA256831ce8ea44a4d76b5775244d2a1a155a61b1c2494e9e6c2768c689547094ca28. Revisione autonoma dell'autore; nessun revisore indipendente.

Restano survivorship,totalreturn/dividendi,corporateaction,spread/liquidità e timing del gaplegacy allo stessoOpen non certificati. Fitcronologico non rende vergine una storia già studiata. Le correzioni contabili non attestano eseguibilità reale.

## Decisione e consegna

Nessun filtroOLC02promosso. Conservo il confronto diretto e l'infrastruttura, ma non do a una stima rumorosa il potere indiscriminato di bloccareCL01. Il prossimo problema è distinguere i falsi veto e i cambi davvero sfavorevoli, con informazioni adeguate, calibrazione temporale e supporto degli stati, non una nuova soglia scelta ex post. Questo ulteriore modello non è stato eseguito qui.

Il repository conserva protocolli, nucleo leggibile di training/controller e test selezionati, sintesi e hash. Il pacchetto risultati contiene TUTTI i nuovi sorgenti/supporti,72modelli,previsioni,108curve/ledger e verifiche. Il checkpoint contiene anche32inputpreparati autenticati, sufficienti a riprodurre questo lotto, NON un rebuildcompleto dei vecchi espertiCL01dai raw. La directoryGitHubnon viene descritta come uploadintegrale dei grandi binari.

Risultati ZIP:OLC02_Confronto_Diretto_Risultati_20261031.zip,25618482byte,SHA256e5387ad77d15d14ed232b4f9cd829a41fe7477aee83a2f886d8dcfb026e420d6.
Checkpoint ZIP:OLC02_Confronto_Diretto_Checkpoint_20261031.zip,106951802byte,SHA2568bccd2b80956f92de4094d204625d6d1a0f6e2687ef7a7770c9bf10687e83cdb.
Parent checkpointSHA2566151028ccff8419a057485817d003993969e352c00eb707fdb63c4a9d696203f,commit7fabf54213b7405f55b9c12a5490fa8934f3566e. Nessuna modifica operativa o promessa di calcoli locali in background.
