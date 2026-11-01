# OLC09: la rappresentazione conta; PATH non conferma un vantaggio comune

1 novembre 2026. Lotto concluso. Nessuna promozione, nessuna modifica a main. Sintesi del rapporto completo consegnato e conservato in Library.

## Contratto
544nuovi modelli Hybrid,272batch annuali2019–2026, più4refit originali di controllo separati. Return125RSI corretto, righe/label mature, calendario, protezioni/V6, prezzi e HALF invariati. Sono testati ordine inverso delle42colonne,39core/45core+PATH, tre blocchi nulli rimescolati per data e regimi di campionamento FIXED/ALL. Seed101 e sensibilità211/307 dichiarati prima dei risultati; nessuna scelta del seed migliore.312curve,48controlli identici e264nuove simulazioni; IMMEDIATE/DELAY3/PHASE5 e costo legacy0,001/0,003. I costi non sono automaticamente10/30bp per lato. Il vecchio39,33% è un altro contratto/finestra.

## 1. Ordine senza informazione nuova
Rifittare con colonne inverse e stesso seed cambia la coppia in32mesiEU e43USA su90; il primo ticker cambia13/21volte.2021–2024 IMMEDIATE: riferimento17,3053%EU/35,5184%USA; ordine inverso22,6398%/36,1714%. Non si promuove la permutazione favorevole. Un seed fisso assicura ripetibilità sotto lo stesso contratto, non la stessa attribuzione delle scelte casuali dopo una permutazione degli input.

Schema canonico e alias verificati ricostruiscono esattamente il contratto42 da39colonne distinte, rifiutando alias non identici e colonne mancanti/inattese.32matrici core e32view legacy verificate. Questo elimina cambi accidentali di rappresentazione, non crea alpha e non certifica equivalenze economiche fra ETF. Il refit39 rimane un modello diverso.

## 2. Numero di colonne campionate
Frazioni originali: ET nominalmente16/15/18candidati su42/39/45; XGB37/35/40colonne per albero. FIXED usa ET16 eXGB37 a ogni larghezza; ALL usa tutte. Non sono la stessa regolarizzazione. ET può esaminare più candidati per trovare split validi. Altri parametri e campioni restano invariati.

CAGR2021–2024, IMMEDIATE,HALF,costo0,001:

|Regime|Core39 EU|Core+PATH EU|Core39 USA|Core+PATH USA|
|---|---:|---:|---:|---:|
|Frazioni originali|15,93%|20,15%|15,60%|37,47%|
|Numero fisso|18,56%|23,62%|27,69%|25,48%|
|Tutte le colonne|23,40%|28,32%|30,94%|14,79%|

Il vantaggio incrementale PATH USA cambia segno. Non si attribuisce tutto il precedente guadagno al contenuto delle sei misure. ALL non risolve il problema: può togliere una regolarizzazione utile.

Controlli a identico numero di colonne, PATH rimescolato come blocco fra ticker della stessa data:
FIXED autentico23,62%EU/25,48%USA; null7101=20,11/34,09;7102=21,70/32,72;7103=18,98/30,31.
ALL autentico28,32/14,79; null7101=20,86/34,72;7102=16,70/31,11;7103=19,87/29,20.
InEU autentico supera tutti i tre null in entrambi i regimi; inUSA perde contro tutti. Tre null non sono un p-value calibrato e non dimostrano inutilità universale. Nessuna replica favorevole viene selezionata.

## 3. Seed e media prestabilita
CAGR2021–2024 IMMEDIATE, FIXEDcore->FIXEDPATH:
seed101 EU18,56->23,62%, USA27,69->25,48%;
seed211 EU25,10->18,64%, USA22,45->28,86%;
seed307 EU20,72->25,02%, USA34,14->21,53%.
Il segno del contributo non è stabile nei due universi. Media dei tre seed sulle previsioni grezze prima del ranking: FIXEDcore23,18%EU/32,15%USA; FIXEDPATH18,54%/23,56%. Nessuna nuova informazione esterna acquisita.

## 4. Ensemble originale42: challenger, non promozione

|2021–2024,IMMEDIATE|CAGR EU|CAGR USA|MaxDD EU|MaxDD USA|
|---|---:|---:|---:|---:|
|Originale42,seed101|17,31%|35,52%|-25,77%|-20,15%|
|Media42,seed101/211/307|22,05%|39,92%|-24,56%|-27,00%|

Con costo0,003: ensemble19,51/36,36% contro14,73/32,25%; maggiore drawdownUSA resta. Intera finestra febbraio2019–1luglio2026: ensemble15,47%EU/38,13%USA contro13,40%/40,85%, MaxDDensemble-32,20/-30,69% contro-31,99/-26,85%.2025 rendimento effettivoEU16,92%contro24,89%; USA12,16%contro43,38%. Con DELAY3/PHASE5 il vantaggio USA2021–2024 non permane. Non si adotta il solo periodo favorevole.

## 5. Informazione e incertezza
Sul target Hybrid maturo, il MSE riferimento migliora quello della media del training di1,32%EU e0,08%USA; ensemble1,33%/0,13%. Piccoli guadagni d'errore non implicano incremento di utilità del portafoglio.45mesi target63 e46mesi payoff21, stessi supporti in tutti i confronti. Ranking Hybrid corrente e portafoglio combinato Return/rischio non sono lo stesso oggetto.

Bootstrap appaiato6000estrazioni,blocchi3/6mesi,seed20261101,48mesi2021–24. Ensemble42menoREF,IMMEDIATE,blocchi6: EU+4,03pp log/anno,ICindividuale[+0,70;+8,48]; USA+3,19,IC[-7,39;+14,26]. I simultanei della famiglia comprendono zero ancheEU. Anche la permutazione inversa senza nuova informazione ha un ICindividualeEUpositivo: non è prova di alpha.

Zero non è veto automatico; decisione basata sull'insieme di mercati,periodi,drawdown,seed,null ecomplessità. Frequenze positive bootstrap non sono posteriori o probabilità di vincere. Dati storici già usati molte volte,universi con sottostanti condivisi; correzione simultanea non copre tutta la storia del repository.

## 6. Decisione
Conservare schema/alias e riferimento RSI+Hybrid42. Tenere ensemble42 come challenger con rischioUSA maggiore. Non scegliere ordine,seed o regime che salva una singola curva. PATH non è promosso come informazione incrementale universale; non è escluso per il solo zero. Nessun nuovo campionatore per gruppi o sorgente fondamentale implementato. Il seguito deve dimostrare utilità delle scelte Top2 sotto rappresentazioni controllate, non moltiplicare subito gli indicatori.

## Verifiche e conservazione
1360file di272batch autenticati;32modelli originali riaperti,4rifittati con parità0;48curve di controllo identiche.586404intervalli contabili e12168metriche ricostruite, scarti massimi3,55e-15 e7,11e-14.24verifiche raw/rank da modelli salvati,12test di alterazione delle sole righe future di inference,errore0: non sono nuovi audit integrali dei refit.
28test nuovi passati,20test del parent passati.112errori di raccolta storica non scoping conservati; pytest.ini dichiara solo il progetto nuovo, nessuna falsa dichiarazione di verde su tutto il repository. Lookup iniziale dei forecast RSI e import omonimo dell'analisi corretti con regressioni, prima di risultati validi. Revisione dell'autore,non indipendente.
Restano total-return,delisting,spread,fill legacy allo stessoOpen,quantità frazionarie e dati storici non certificati. Nessun trading.

Tutti i nove nuovi moduli sperimentali e sei file di test sono versionati qui. Tutti i312percorsi,modelli e input sono nei nuovi checkpointLibrary, non automaticamente in releaseGitHub. Tre volumi nuovi, richiesti anche i due volumi padreOLC08F indicati nelREADME. Ripristino in directory pulita: verificati2460file del primo pacchetto completo,28test e12replay reali identici; la versione finale aggiunge il verbale di ripristino e una precisazioneREADME, senza cambiare modelli,sorgenti o risultati. I file finali sono2461 piùmanifest. Dipendenza padre già autenticata e collegata esplicitamente, non inclusa di nuovo.

Fonti ufficiali degli algoritmi: scikit-learn1.8 ExtraTreesRegressor e XGBoost3.1.3 parameters. Non sono validazioni dei rendimenti. Protocollo, file di controllo e archiviHash costituiscono le evidenze dell'esperimento.
