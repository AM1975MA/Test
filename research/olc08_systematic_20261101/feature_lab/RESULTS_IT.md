# OLC08-F — nuove feature e ridondanza: risultati verificati

1 novembre 2026. Lotto concluso, ricerca retrospettiva, nessuna promozione e nessuna modifica a main. Il rapporto esteso, tutte le tabelle e le curve sono nel checkpoint e nel pacchetto risultati consegnati; questa sintesi conserva i risultati decisivi e i limiti.

## Contratto

Riferimento Return125 con RSI corretto e Hybrid42. Si modificano soltanto i rispettivi input dei primi learner, mantenendo identici campioni, etichette mature, parametri, seed e supporto di previsione. Il modello complementare resta congelato. Tutti i candidati su USA149/EU165, HALF50/50, IMMEDIATE/DELAY3/PHASE5, costo legacy0,001/0,003. Quest'ultimo non è automaticamente10/30bp per lato. Rischio e V6 congelati. Periodo principale2021–2024; fullfebbraio2019–1luglio2026 e singoli anni distinti. Nessun numero è una nuova versione del vecchio39,33%.

## Le18misure nuove

PATH6: età del massimo63, tempo sotto i massimi, concentrazione del rialzo nelle3sedute migliori, energia ribassista, accelerazione21vs42, persistenza del segno.
SESSION6: rendimentoovernight/intraday normalizzato, quota overnight di energia, recupero dei gap, efficienza intraday, frequenza di gap estremi usando volatilità già nota.
LEADERSHIP6: variazioni e persistenza della posizione cross-sectional, instabilità della graduatoria e differenza fra leadership21/63.

Sono trasformazioni nuove dei prezzi/rank esistenti, NON nuovi dati fondamentali, flussi o notizie. Nessuna futura disponibilità dei rendimenti modifica le feature live. Dati mancanti non diventano zeri o quotazioni eseguibili. Il catalogo comprende370righe per167vecchi input+18nuove misure, due mercati. In4snapshot del solo training nessuna nuova misura supera0,985 di correlazione assoluta con una vecchia; accelerazione resta vicina a0,94. Non equivale a informazione predittiva indipendente.

## Compressione del Return, DELAY3,2021–2024

| Variante | CAGR EU | CAGR USA | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|
|Riferimento125RSI|20,61%|38,72%|-26,51%|-20,15%|
|Senza6volume/liquidità,119|21,91%|35,83%|-19,40%|-23,87%|
|Soli46percentili|22,47%|31,76%|-25,88%|-20,86%|
|Pruning solo training,99–100EU/96USA|20,20%|19,42%|-23,22%|-25,31%|
|Pruning+18nuove|21,42%|22,70%|-24,99%|-25,48%|
|125+18nuove|11,28%|24,82%|-34,82%|-22,40%|

Pruning: costanti o Spearman assoluto>=0,985, minimo300coppie e stessa mascheraNaN, sul solo training di ognianno; nessuna label futura sceglie le colonne. Ridurre colonne correlate non garantisce miglioramento. Cambia anche il budget assoluto di feature campionate dagli alberi, pur mantenendo le frazioni e tutti gli altri iperparametri.

La variante119 senza volumi resta una pista: fullDELAY3 CAGR19,69%EU/49,87%USA contro17,15%/45,53%; stress16,98%/45,95% contro14,38%/41,78%. FullMaxDD-33,32%/-26,03% contro-33,01%/-28,28%. Non nascondiamo il risultato favorevole, ma il confronto USA2021–2024 peggiora e una quota importante nasce nel2025/2026parziale, già studiati. Nessuna selezione della finestra più favorevole come prova indipendente.

## Hybrid: nuova informazione contro cambiamento della rappresentazione

2021–2024, IMMEDIATE, HALF, costo0,001:

| Hybrid | CAGR EU | CAGR USA | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|
|42originali|17,31%|35,52%|-25,77%|-20,15%|
|39senza duplicati|15,93%|15,60%|-26,63%|-46,70%|
|39+6PATH|20,15%|37,47%|-25,40%|-19,76%|
|42+6PATH, cella post-risultati|22,27%|26,03%|-26,16%|-23,67%|

H_PATH migliora entrambi rispetto al riferimento immediato, anche stress(17,74%/33,94% contro14,73%/32,25%). Ma conDELAY3 USA2021–2024 scende36,22% contro38,72%, mentreEU21,92%contro20,61%. FullIMMEDIATE16,32%EU/51,35%USA contro13,40%/40,85%, con MaxDD europeo peggiore:-39,09%contro-31,99%. Non è un pacchetto dominante né una combinazione di benefici sommabili.

### Controprova nulla, registrata dopo gli esiti principali

Stesse45colonne, modello, seed, label e campioni; seiPATH rimescolate insieme fra ETF della stessa data, spezzando l'associazione al ticker senza cambiare la distribuzione del blocco. Tre seed predichiarati, nessun seed scelto dai risultati. CAGR2021–2024IMMEDIATE:

| Blocco | EU | USA |
|---|---:|---:|
|PATH autentico|20,15%|37,47%|
|Rimescolato7101|19,18%|34,08%|
|Rimescolato7102|22,39%|30,29%|
|Rimescolato7103|21,43%|33,87%|

Due controlli superano il vero blocco inEuropa, nessuno negliUSA. Non è dimostrata informazione incrementale comune ai due universi. Tre permutazioni non producono un p-value calibrato o una probabilità di alpha e non dimostrano inutilità universale. La successiva cella42+6completa il fattoriale deduplicazione×PATH: anch'essa esplicitamente post-osservazione, non un holdout.

SESSION inHybrid, DELAY3, produce29,32%EU/9,50%USA: non si sceglieSESSION solo perEuropa ePATHsolo perUSA. Il rankIC americano0,0293 è superiore allo0,0036 di riferimento, ma il payoff aggiuntivo Top2 medio21sedute scende da2,38%a0,82%. Ranking globale migliore non è sinonimo di migliori investimenti concentrati; questi payoff non sonoCAGR.

## Ridondanza eliminabile senza effetti nascosti

Implementata una rappresentazione39Hybrid canonica+3alias che ricostruisce esattamente gli input42originali, ordine,NaN e tipi, su entrambi i pannelli. Può ridurre duplicazione di memorizzazione senza cambiare modello/predizioni. Non risolve automaticamente la possibile doppia ponderazione nel learner e non è nuovo rendimento. Il refit su39è un intervento diverso, con gli esiti sfavorevoli sopra.

## Incertezza

48mesi appaiati2021–2024, blocchi3/6,6000estrazioni, stessi indici nei due mercati. H_PATHmenoREF,IMMEDIATE,blocchi6:EU+2,44pp logannui IC[-4,86;+11,79];USA+1,43 IC[-13,89;+16,60]. Intervalli che contengono zero non sono veto automatico. Conservati anche intervalli simultanei della famiglia; non correggono tutta la ricerca passata. Frazioni positive bootstrap non sono posteriori. La mancata promozione deriva dal quadro di controprove, rischio, mercato e periodo, non da un singolo test statistico.

## Verifiche e perimetro

480modelli/176batch e156curve principali incluse24baselineesatte;96modelli/12curve null;32modelli/12curve fattoriali aggiuntive. Totale608modelli,180curve,338310intervalli ricostruiti da quantità e Open e7020metriche ricalcolate. Errori massimiNAV3,55e-15/metriche4,71e-14.

Audit completo delle matrici,etichette,maturazione e880file dei176batch principali;8batch2022ricaricati dal modello con previsioni identiche, non nuovi refit. Verificati tutti64batchausiliari.12prefix/futurechecks reali,4ricalcoli del pruning solo training.20test nuovi e12recovery ereditati passati nelle rispettive suite. Raccolta indiscriminata:111errori import/path da test storici copiati/symlink, log conservato, nessuna affermazione di verde sull'intero repository. Corretto un import omonimo nel runner null con regressione rossa-verde prima che producesse risultati.

Autorevisione, non revisore indipendente. Non certificati dati total-return, fondi delistati, mapping economico storico, spread/quantità minime o fill legacy allo stessoOpen. Nessuna nuova fonte esterna. Il checkpoint completo conserva sorgenti/input/modelli/curve, con RESTORE_LAYOUT per l'alias interno e verifica manifest. I checkpoint sono persistiti nella Library autorizzata con hash registrati suGitHub: non sono implicitamente assetGitHub e il vecchio backlog binario non è dichiarato risolto.

## Decisione

Mantenere il riferimentoRSI e la rappresentazione lossless39+alias; conservare H_PATH eR_NO_LIQ come challenger distinti. Non adottare la compressione massiva o tutte18feature insieme. Non forzare un nuovo vincitore dalle sole righe favorevoli. Il pacchetto tecnico è ora documentato, verificabile e riutilizzabile; il massimo globale e un miglioramento universalmente trasferibile non sono dimostrati.
