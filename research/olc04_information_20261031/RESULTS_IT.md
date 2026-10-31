# OLC-04: informazione relativa, conferma fra ETF e controllo delle opportunità

31 ottobre 2026. Lotto concluso, ricerca retrospettiva. Nessuna modifica a main e nessuna strategia promossa. Il protocollo b2236ac765e64730613c16da8615df052ff72916 è stato registrato prima dei nuovi fit.

## Risultato principale

L'informazione aggiunta migliora molte previsioni e decisioni americane, ma non produce una strategia comune superiore. Con HGB a21sedute il filtro passa dal15,77% al33,18% CAGR USA nel2021–2024; CL01half senza filtro rimane33,68%. L'Europa passa invece dal7,62% al4,38%, contro15,75% CL01. Questi non sono i CAGR della vecchia strategia al39,33%, che rimane un riferimento diverso per versione e finestra.

Non sono nuove fonti economiche: sono nuove rappresentazioni dei medesimi prezzi congelati. Non abbiamo acquisito flussi ETF, fondamentali o comunicati macro storici. Le conclusioni riguardano queste trasformazioni e modelli, non l'impossibilità di prevedere opportunità europee.

## Confronto controllato

OLD:38feature originali OLC02 e72modelli archiviati. REL:aggiunge12misure del rapporto fra il portafoglio proposto e quello detenuto (movimento5/21/63,accelerazione,persistenza,drawdown,distanze da medie/massimi e contributi su mercato positivo/negativo). PEER:aggiunge18misure relative a fino5ETF correlati nel passato e al mercato locale (residui,ampiezza,accelerazione e contesto). I peer escludono il ticker stesso, usano126sedute, almeno84osservazioni e3vicini. Sono proxy statistici, non una tassonomia economica certificata.

Le serie dei panieri delle feature usano le quantità implicite nei pesi conosciuti al segnale; non sono presentate come storia effettiva di possesso. Solo chiusure già disponibili, massimo3sedute di carry per le feature, nessun Open sintetico. Le informazioni aggiuntive sono finite su tutte le coppie, senza eliminare righe difficili.

Stesse chiavi di training, etichette mature prima del cutoff annuale, target21/42/63, iperparametri, numero di osservazioni e pesi mensili.144nuovi modelli REL/PEER,72OLDriusati; Ridgealpha20 e HGB120iterazioni/15foglie/minleaf60/l2=10/lr=.05,seed101,noearlystopping. Le nuove decisioni iniziano a febbraio2021.

104percorsi:96configurazioni con3feature-set×2modelli×2orizzonti×2gate×2costi×2universi, più8controlli CL01half/original. RAW è il gate OLC02 invariato; UTILITY è il veto OLC03 invariato, con ricalibrazione cronologica,12mesi maturi,scala.05,peso2alle opportunità perse e astensione fuori supporto. Nessun nuovo selettore, cash discrezionale o soglia ritarata.

## Risultati2021–2024

Costi legacy0,001, non automaticamente10bp per lato. Le regole di rischio e le ipotesi di esecuzione originarie sono conservate.

| HGB21 / set | EU CAGR | EU MaxDD | USA CAGR | USA MaxDD |
|---|---:|---:|---:|---:|
| OLD |7,62%|-28,98%|15,77%|-37,36%|
| REL |2,42%|-28,88%|22,69%|-24,24%|
| PEER |4,38%|-28,12%|33,18%|-19,36%|
| CL01half |15,75%|-26,47%|33,68%|-20,15%|

PEER migliora REL nei due mercati in questa specifica variante, ma la base europea REL era già deteriorata. Non significa battere CL01. Le altre famiglie non sono nascoste: Ridgeprofilo REL18,25%EU/10,63%USA controOLD20,81%/9,99%; HGBprofilo REL16,33%/20,04% ePEER4,69%/33,08%.

A costi0,003, PEER_HGB21 ottiene2,64%EU/22,90%USA contro12,96%/30,11%CL01. I costi cambiano anche alcune decisioni e il percorso dei possessi, non solo le commissioni. Il nuovo contributo non è robusto al controllo stressato.

## Previsione e decisione non sono la stessa cosa

Rapporto MSE contro media del proprio training, sugli stessi stati BASE/full-proposal e soli esiti maturi prima del2025, aggregazione prima per mese:

| HGB orizzonte | OLD EU | PEER EU | OLD USA | PEER USA |
|---|---:|---:|---:|---:|
|21|1,259|1,255|1,035|0,978|
|42|1,103|1,236|0,969|0,892|
|63|1,073|1,223|1,018|0,995|

PEER migliora tutti6confronti americani controOLD e5su6battono la media; nessuna delle6celle europee batte la media. Sono41mesi europei;42USA sul21,41sui successivi. Non sono centinaia di osservazioni indipendenti.

Nel gatePEER_HGB21, il vantaggio netto logaritmico a21sedute delle proposte accettate/rifiutate è rispettivamente: EU−1,22punti(25mesi)/+3,26(16mesi); USA+5,61(19mesi)/+0,07(25mesi). Controfattuali statici sul capitale confrontato, non CAGR o profitto recuperabile automaticamente. I due conti hanno stati endogeni diversi.

Esempi europei: al28aprile2023HOLD EEPG.DE/EXI5.DE invece della propostaEEPG.DE/VVSM.DE; maggio−9,68%contro+4,21%CL01. Al31maggio2024HOLD IBCJ.DE/EXV5.DE invece diVVSM.DE/QDVE.DE; giugno−1,04%contro+8,82%. Le proposte erano note al segnale, non scelte ex post. Negli USA il29dicembre2023mantiene EDV/GDXJ invece diTUR/SMH; gennaio−5,77%contro+10,07%. I rendimenti mensili comprendono lo stato successivo e le protezioni, non una causalità isolata di un singolo ordine.

## Veto selettivo, periodi successivi e incertezza

UTILITY non blocca proposte europee con i nuovi set. Negli USA PEER_HGB21interviene una sola volta:33,75%contro33,68%; PEER_HGBprofilo anch'esso una volta ma scende a30,56%. Gli altri restano sulla baseline. Astensione o un unico episodio positivo non sono nuova capacità predittiva.

Il risultato europeo REL_Ridgeprofilo sul2021–1luglio2026è27,57%contro16,63%CL01, e26,25%contro13,81%al costo stressato. Va conservato, ma USA24,02%contro41,20%(23,01%contro37,41%stress). Una parte forte è il2025EU:+66,32%effettivo contro+25,59%CL01. Non si sceglie una configurazione diversa nei due universi. La variante RAW raggiunge anche età di posizione597sedute; non certifica permanenza fuori dal supporto di training. UTILITY ha una guardia esplicita sul supporto.

Bootstrap appaiato48mesi2021–2024,blocchi3/6,6000estrazioni seed20261031; stessi mesi ricampionati nei due universi. PEER_HGB21menoREL_HGB21, blocchi6:EU+1,92punti log/anno IC[−5,65;+9,78], USA+8,18 IC[−7,28;+23,81]. Non viene scartato per lozero. ControCL01:EU−10,53 IC[−21,89;−0,64],USA−0,37 IC[−13,72;+13,30]. Il giudizio dipende dal danno economico e dalla trasferibilità, non da una soglia statistica. Le frequenze positive sono stabilità al ricampionamento, non probabilità posteriori e non correggono tutti i tentativi precedenti.

## Verifica e limiti

40curve di controllo riprodotte con errore0;104ricostruzioni indipendenti da quantità e Open successivi, errore3,55e−15;4056metriche ricalcolate, errore4,44e−14.100avvii invariati prima di febbraio2021.833file di provenienza verificati.12test nuovi più23OLC02e26OLC03nelle loro suite; non è dichiarata verde l'intera suite storica del repository.14verifiche temporali reali:6prefix/training-live e8refit con righe future alterate. Revisione dell'autore, non indipendente.

Un primo test di refit è fallito per l'arrotondamento del parserCSVpredefinito. Anche il refit NON alterato divergeva; con round_trip ricostruisce esattamente il modello. Aggiunto test di regressione osservato fallire e poi passare. Nel casoHGBdiagnosticato l'errore massimo nelle previsioni era0,00333unitàlog. I replay economici usavano già gli input originali e non sono stati ritarati; resta una sensibilità numerica da non occultare.

Restano survivorship,dividendi/totalreturn,corporateaction,spread e stessa-Open legacy non certificati. Tutta la storia è già studiata;2025/2026non sono holdout vergini e2026si ferma al1luglio. Nuove feature non certificano prezzi o negoziabilità.

## Decisione e persistenza

Nessuna variante OLC04è promossa come strategia comune. Conservare le piste separatamente senza scegliere il vincitore locale. Prima di un altro veto sulle medesime rappresentazioni, il passo informativo distinto è identificare esposizioni economiche storiche verificabili (indice,settore,valuta,copertura) e la leadership fra esposizioni: correlazione statistica non è una verifica economica. Questa nuova fase non è stata eseguita in questo lotto.

Il repository contiene protocollo, nucleo di feature/training/integrazione/replay, test essenziali e sintesi. Tutti i sorgenti ausiliari di analisi/verifica,144modelli,104curve e registri dettagliati sono nei pacchetti consegnati, con hash. I grandi binari e i checkpoint parent NON sono implicitamente dichiarati caricati suGitHub. Main invariato.
