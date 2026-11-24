# Perseo U21 — ricerca esterna e benchmark più esigenti

23 novembre 2026. Valutazione di metodi e opportunità di miglioramento; nessuna nuova strategia Perseo promossa. Le performance sotto sono calcolate ora sui prezzi congelati del progetto, non copiate da backtest pubblicati su periodi diversi.

**Conclusione:** c’è spazio di ricerca concreto, ma i benchmark settoriali ridimensionano il vantaggio attribuito alla selezione. Perseo EU è quasi equivalente al Nasdaq in euro; TR ha CAGR simile alla tecnologia USA con drawdown leggermente minore. Il vecchio USA conserva invece un risultato interessante di contenimento del drawdown rispetto a SMH, a rendimento simile. Questo non prova che il rendimento di Perseo sia spiegato interamente da quei settori: serve un’attribuzione dinamica del rischio e della selezione.

## Confronto ricalcolato

| Paniere | Riferimento | CAGR | Drawdown |
|---|---|---:|---:|
|EU|Perseo U20 candidato|20,78%|-31,25%|
|EU|S&P 500 (SXR8.DE)|14,78%|-33,69%|
|EU|Nasdaq 100 (SXRV.DE)|20,99%|-31,21%|
|EU|Tecnologia USA (QDVE.DE)|24,97%|-33,57%|
|EU|MSCI World (EUNL.DE)|12,95%|-33,20%|
|TR|Perseo U20 candidato|25,07%|-29,53%|
|TR|S&P 500 (IE00B5 BMR087)|14,78%|-33,69%|
|TR|Nasdaq 100 (IE00B53 SZB19)|20,99%|-31,21%|
|TR|Tecnologia USA (IE00B3 WJKG14)|24,97%|-33,57%|
|TR|MSCI World (IE00B4L5Y983)|12,95%|-33,20%|
|TR|World Momentum (IE00 BP3 QZ825)|16,07%|-30,50%|
|TR|USA Momentum (IE00 BD1F4N50)|16,75%|-32,62%|
|USA|Perseo U20 candidato|40,23%|-26,81%|
|USA|S&P 500 (SPY)|15,31%|-32,05%|
|USA|Nasdaq 100 (QQQ)|21,42%|-36,69%|
|USA|Semiconduttori SMH (SMH)|40,60%|-46,91%|
|USA|USA Momentum (MTUM)|17,35%|-31,59%|
|USA|Oro GLD (GLD)|15,69%|-28,40%|

Periodo: apertura 2 gennaio 2020 → apertura 1 luglio 2026. Costi identici a U20: 1 unità monetaria +15 bp per lato, capitale 10.000, frazioni, niente leva sul conto e niente fiscalità. Buy-and-hold paga un solo acquisto e resta aperto al termine, come Perseo. Valute separate: EUR per EU/TR, USD per USA. Drawdown alle aperture. I rendimenti usano le stesse serie rettificate del progetto; non costituiscono una verifica indipendente dei dividendi o delle rettifiche del fornitore. Eventuali valori mancanti restano segnati; per le regole operative le esecuzioni attendono un’apertura osservata.

Il periodo termina a luglio per conservare il confronto con U20: non rappresenta una valutazione aggiornata ai prezzi di novembre. Nel dataset USA manca la maschera originaria delle osservazioni: il motore considera disponibili le aperture archiviate, senza certificare l’assenza di riempimenti. I panieri storici di Perseo non hanno una ricostruzione completa delle disponibilità effettive a ciascuna data; i limiti di liquidità e di simulazione degli stop segnalati in U20 restano aperti. Questi controlli verificano il calcolo, non risolvono quei limiti del dato.

I controlli tecnologici sono esposizioni concentrate, non sostituti equivalenti di un indice ampio. Sono scelti perché Perseo ha già detenuto high-tech e semiconduttori, non perché si possa sapere a priori quale settore vincerà. Gli ETF settoriali sono confronti di attribuzione; S&P 500 e World restano benchmark generali. Per la replica europea dei semiconduttori non si inventa una storia prima del lancio: in questa tabella il riferimento completo SMH è solo USA.

![Confronto rendimento e drawdown](BENCHMARK_PERSEO_U21.png)

Il vantaggio rispetto al solo S&P 500 non dimostra alpha di selezione. EU: Perseo 20,78% / DD −31,25%, Nasdaq 20,99% /−31,21%. TR: Perseo 25,07% /−29,53%, tecnologia 24,97% /−33,57%. USA: Perseo 40,23% /−26,81%, SMH40,60% /−46,91%. Il 40,23% è il nativo originale conservato; la variante 44,31% con stop isolato rimane una variante diversa.

Nel 2020–2022 Perseo TR perde circa 6,05% annuo mentre tecnologia in EUR guadagna circa 12,82%; Perseo EU rende 2,27%, Nasdaq 10,14%. Dopo il 2023 TR cresce circa 59,98% annuo contro 36,46% tecnologia. Il problema prioritario è il rendimento perso nel primo regime, non soltanto il drawdown massimo del periodo completo. Le finestre sono le stesse di U20, con confine al 3 gennaio 2023.

## Controllo semplice già eseguito: trend mensile

Ho applicato il filtro sopra/sotto la media delle ultime 10 chiusure mensili a S&P 500 e Nasdaq, senza ottimizzare la lunghezza, eseguendo alla prima apertura osservata del mese dopo il segnale. Cash a rendimento zero, coerente con U20.

| Controllo | Buy-and-hold: CAGR / DD | Filtro 10 mesi: CAGR / DD |
|---|---:|---:|
|S&P 500 in EUR|14,78% /−33,69%|9,57% /−20,78%|
|Nasdaq in EUR|20,99% /−31,21%|13,59% /−29,47%|
|S&P 500 in USD|15,31% /−32,05%|8,79% /−27,24%|
|Nasdaq in USD|21,42% /−36,69%|17,78% /−27,56%|

La protezione compra riduzione del rischio rinunciando a rendimento; su questo periodo non realizza il miglioramento di CAGR desiderato. Non è la replica dell’intero modello multi-asset di Faber, né una confutazione universale del trend. È un controllo pertinente e riproducibile alle nostre condizioni.

## Dove investire la ricerca

| Priorità | Intervento | Perché conta per Perseo | Prova che deve superare |
|---|---|---|---|
|1|Decisione di cambio basata sul vantaggio economico netto|I costi doppi in U20 riducono il CAGR di circa 4,29 pp EU,7,28 pp USA e 5,64 pp TR. Anche l’esecuzione a una seduta diversa cambia sensibilmente gli esiti.|Stesso ranking congelato: cambiare solo se il vantaggio stimato del nuovo titolo rispetto a quello detenuto compensa costi e incertezza; confrontare turnover, CAGR e DD.|
|2|Obiettivo relativo al benchmark e possibilità di mantenere una posizione ampia|Le scelte attive TR perdono per tre anni mentre il mercato cresce. Due titoli al vertice di una classifica possono essere entrambi peggiori dell’alternativa passiva.|Previsioni calibrate sul vantaggio rispetto al benchmark e al titolo detenuto; azione HOLD/benchmark/cash esplicita, senza imporre sempre due scommesse attive.|
|3|Durata della posizione coerente con la durata del segnale|La scelta annuale fra architetture segue il passato con ritardo. Un segnale a 5 giorni e uno a 63 giorni non richiedono la stessa rotazione.|Previsioni congelate a più orizzonti, uscita quando decade il vantaggio; pochi orizzonti fissati prima e protezione locale separata da quella di mercato.|
|4|Diversificazione delle esposizioni, non del numero di ticker|Nel TR due ETF possono essere quasi la stessa scommessa. La traslazione USA ha mostrato sia valore sia buchi di copertura.|Attribuzione a mercato, settori e valuta; penalità di sovrapposizione e incertezza di replica, senza eliminare automaticamente tutto il momentum settoriale.|
|5|Confidenza economica calibrata e controllo dei tentativi|Ranghi alti e tracking fedele non sono probabilità di rendimento. Il filtro a 24 mesi non ha autorizzato il cambiamento.|Misurare calibrazione, vantaggio netto a parità di esposizione e perdita nei casi incerti; registro di tutti i tentativi e successiva verifica su dati non usati nello sviluppo.|

Questa priorità è una valutazione per il progetto, non una classifica universale dei metodi. Nessuna fonte dimostra 30–50% CAGR comune ai tre panieri con i nostri vincoli.

La prima prova proposta stima **quanto conviene cambiare la posizione**, includendo la persistenza prevista del vantaggio. Una banda di non intervento evita operazioni economicamente irrilevanti. Non basta ridurre artificialmente le commissioni: l’algoritmo deve decidere diversamente e conservare i profitti netti sullo stesso storico.

La seconda prova usa come riferimento generale un indice ampio definito prima dei test, non il settore che sappiamo ex post essere vincente. L’alternativa ampia deve essere una scelta economica, non un acquisto automatico quando il suo rischio è incompatibile. Il risultato non può essere valutato soltanto sui mesi in cui il filtro autorizza a investire: va misurato tutto il conto.

Sul terzo punto, la combinazione di velocità ha senso solo se aggiunge decisioni diverse dopo i costi. La selezione Return/Hybrid usa già più orizzonti; DELAY3, minvar, ensemble di ranker e rientri semplici sono già stati provati. La ricerca utile riguarda la durata economica delle posizioni e l’esecuzione, non il rinominare queste prove. Le coorti di calendario sono un controllo di sensibilità, non un modo di scegliere la fase vincente.

Il momentum residuo della letteratura azionaria è utile per capire se stiamo comprando solo beta tecnologico o una scelta specifica. Applicarlo indiscriminatamente agli ETF può eliminare proprio le esposizioni che vogliamo cogliere: lo tratterei inizialmente come diagnostica, non come sostituzione del selettore.

## Metodi che non considero scorciatoie

Il volatility targeting è interessante per stabilizzare il rischio ma, limitato tra 0% e 100% di esposizione, può soprattutto ridurre il CAGR. Non importiamo i vantaggi di strategie con leva in un conto senza leva. La ricerca successiva a Moreira–Muir documenta anche fallimenti fuori campione: la cautela è empirica, non teorica.

Dual Momentum/GEM è un controllo serio di rotazione geografica e risk-off, ma i risultati pubblicati dall’autore sono simulazioni senza commissioni e con indici/proxy storici. I rientri possono ritardare. In questo turno ho esaminato la metodologia; non ho eseguito una replica GEM completa e non assegno a Perseo i rendimenti pubblicati online.

Reti neurali più grandi, reinforcement learning e ulteriori centinaia di feature non hanno qui una priorità sostenuta da questi confronti. Il limite osservato è prima economico e di generalizzazione. I 1.846 ETF non equivalgono a 1.846 storie di mercato indipendenti: molti sono repliche della stessa esposizione.

## Protocollo per il prossimo confronto

Congelare nativo USA, U20 EU/TR e benchmark generali; mantenere anche Nasdaq, tecnologia, momentum e semiconduttori come controlli di attribuzione. Separare selezione, allocazione, esecuzione e protezione: una modifica per volta, poi verificare l’interazione.

Usare training cronologico con etichette interamente maturate, validazione interna e finestre successive di test per l’intero processo; segnali all’ultima chiusura disponibile ed esecuzione successiva osservata. L’esistenza di un walk-forward non cancella la ricerca già svolta su tutti questi anni. Servono una parte futura congelata e un registro unico dei tentativi; il DSR richiede quel registro e non va inventato a partire dai 107 conti fortemente correlati di U20.

Valutare CAGR, drawdown, durata del recupero, downside capture, valore rispetto ai benchmark, costi 15/30 bp, ritardo di esecuzione e liquidità. Analizzare 2020–2022 e 2023–2026 separatamente, senza scegliere retrospettivamente il modello migliore in ciascun regime. Un modello che batte il mercato solo dopo il 2023 non soddisfa la richiesta di strategia unificata robusta.

## Fonti e trasferibilità

- [Gârleanu e Pedersen, Dynamic Trading with Predictable Returns and Transactions Costs (2013)](https://www.aqr.com/Insights/Research/Journal-Article/Dynamic-Trading-With-Predictable-Returns-and-Transactions-Costs) — I segnali con durate differenti richiedono decisioni di negoziazione che considerino il portafoglio corrente, la persistenza attesa, rischio e costi. È un modello e una verifica su mercati differenti dai nostri panieri ETF; non certifica il CAGR di Perseo.

- [MSCI, aggiornamento Momentum del luglio 2025](https://app2.msci.com/webapp/index_ann/DocGet?pub_key=kiUSObVqj%2Fs%3D) — L’annuncio introduce revisione trimestrale e attuazione parziale del turnover dall’agosto 2025. È un riferimento concreto per attuazione graduale, non una prova che il rinvio fisso di tre giorni sia ottimale. MTUM segue una specifica variante dell’indice: non confondiamo la metodologia generale con ogni prodotto.

- [Man AHL, The Need for Speed in Trend-Following Strategies (2023)](https://www.man.com/insights/need-for-speed-trend-following) — Confronta più velocità di trend su 50 futures/forward nel 1995–2022. Velocità rapide aiutano alcune proprietà difensive, ma pagano più turnover; le velocità non sono equivalenti per rischio e rendimento. Portafogli long/short, scaling del rischio e leva non sono direttamente confrontabili con ETF long-only.

- [Man Group, Strategic Rebalancing (2020)](https://www.man.com/insights/strategic-rebalancing) — Nel caso 60/40, ribilanciare meccanicamente può vendere il vincitore e comprare il perdente mentre la divergenza continua. Studia il rinvio o dimensionamento delle operazioni sulla base del trend. L’adattamento a due ETF concentrati richiede una nuova verifica.

- [Blitz, Huij e Martens, Residual Momentum; guida Robeco](https://www.robeco.com/files/docm/docu-robeco-guide-to-factor-investing-global.pdf) — La ricerca sul momentum residuo separa la componente specifica dal rendimento spiegato dai fattori. Risultati su azioni non si trasferiscono automaticamente agli ETF, il cui scopo è spesso proprio fornire esposizioni fattoriali. Per Perseo è anzitutto uno strumento di attribuzione e controllo delle duplicazioni.

- [Cederburg, O’Doherty, Wang e Yan, On the Performance of Volatility-Managed Portfolios (2020)](https://www.lehigh.edu/~xuy219/research/COWY.pdf) — Su 103 strategie azionarie non riscontra superiorità sistematica dei portafogli gestiti in base alla volatilità; combinazioni realistiche fuori campione spesso peggiorano, anche per instabilità strutturale. Impedisce di considerare il volatility targeting una soluzione automatica.

- [Moreira e Muir, Volatility-Managed Portfolios (2017)](https://www.nber.org/papers/w22208) — La ricerca iniziale trova benefici della riduzione del rischio in alta volatilità su diversi fattori. La conclusione deve essere letta insieme alle verifiche successive e ai vincoli di leva/esecuzione; non trasferiamo i rendimenti della pubblicazione ai nostri ETF.

- [Meb Faber, A Quantitative Approach to Tactical Asset Allocation](https://mebfaber.com/2017/12/13/episode-86-quantitative-approach-tactical-asset-allocation/) — Il filtro mensile sulla media a 10 mesi è un riferimento semplice di trend. Qui abbiamo applicato il principio a singoli ETF con ingresso all’apertura successiva e cash a rendimento zero: non è la replica integrale del portafoglio multi-asset del paper.

- [Gary Antonacci, Global Equities Momentum (GEM)](https://www.optimalmomentum.com/global-equities-momentum/) — Combina forza relativa e assoluta tra azionario USA, azionario globale ex-USA e obbligazioni, con valutazione mensile. Il sito dell’autore distingue le simulazioni dagli investimenti reali ed esclude i costi pubblicati: non confrontiamo direttamente tali numeri con Perseo netto.

- [Bailey e López de Prado, The Deflated Sharpe Ratio (2014)](https://davidhbailey.com/dhbpapers/deflated-sharpe.pdf) — Corregge la significatività dello Sharpe per selezione fra tentativi e rendimenti non normali. Richiede informazioni sui tentativi non selezionati e sulla loro dipendenza; un semplice bootstrap della sola strategia vincente non basta. Non abbiamo calcolato un DSR completo del progetto senza quel registro.

- [AQR, Which Trend Is Your Friend? (2016)](https://www.aqr.com/Insights/Research/Journal-Article/Which-Trend-Is-Your-Friend) — Mostra relazioni tra diverse formulazioni dei segnali di trend e richiama l’importanza di costruzione del portafoglio, rischio e attuazione. Cambiare nome o formula di un filtro simile non crea necessariamente una nuova fonte di rendimento.

- [iShares, MTUM: scheda ufficiale](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf-mtum) — ETF azionario USA momentum, avviato nel 2013. Usiamo il suo percorso reale presente nel dataset, non ricostruiamo retroattivamente le regole attuali dell’indice. I rendimenti in tabella sono nostri calcoli sui prezzi congelati, non performance estratte dalla pagina al novembre 2026.

## Cosa è stato fatto in questo turno

Ricerca su fonti accademiche e operatori originali; lettura del rapportoU20; ricalcolo di 21 conti benchmark, di cui 6 con filtro mensile; controllo degli acquisti buy-and-hold contro formula chiusa;18 verifiche di invarianza ai dati futuri e 6 replay indipendenti degli ordini. Nessun nuovo addestramento dei 125/42 input, nessuna modifica a Perseo o alle automazioni.

I file includono codice, prezzi dei soli benchmark, NAV, ordini, segnali, metriche per regime e fonti. Il codice può ricalcolare i benchmark dai prezzi salvati senza dipendere dagli archiviU19/U20. Perseo resta un confronto storico non certificato per esecuzione reale; i limiti dei cataloghi e dei prezzi congelati restano espliciti.
