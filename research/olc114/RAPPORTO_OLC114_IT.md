# OLC114 — Protezione sulle singole posizioni e rientro completo

**Ricerca del 16 novembre 2026. Modello principale scelto prima dei risultati: TREE_CYCLE.**

## Esito

Il nuovo modello migliora la protezione nel periodo in cui può intervenire. Dal **4 luglio 2022 al 30 ottobre 2026**, il CAGR passa dal **20,01% della base al 21,40%**, mentre il massimo drawdown scende in valore assoluto dal **-36,51% al -27,24%**. La riduzione della perdita massima è di **9,28 punti percentuali**.

Sull'intero periodo, **2 marzo 2020–30 ottobre 2026**, il CAGR è **23,49%**, contro **22,57%** della base e **24,16%** della precedente variante PRICE_RESET. L'obiettivo del **30% non è raggiunto**. Anche il criterio fissato prima del test — almeno tre punti di CAGR in più della base, senza peggiorare il drawdown, in entrambe le finestre — **non è soddisfatto**: il vantaggio è di +0,92 punti nell'intero storico e +1,39 punti nel periodo comune.

La conclusione operativa della ricerca è conservare TREE_CYCLE come **candidato di protezione da validare ulteriormente**, mantenendo PRICE_RESET come confronto di rendimento. I nuovi risultati non autorizzano a dichiarare risolto il problema del rientro sulle opportunità, né a promuovere automaticamente il modello in produzione.

## Perché le due finestre raccontano aspetti diversi

Il periodo comune era stabilito nel protocollo. I due modelli di valore diventano stimabili il 1° giugno 2022; l'intervento resta comunque vietato prima del limite già condiviso con gli studi precedenti, **1° luglio 2022**. I rendimenti del confronto iniziano quindi il **4 luglio 2022**, partendo dal valore effettivo di ciascun conto alla chiusura del 1° luglio.

Per i conti appresi nello scenario principale questo valore è **17.631,84 €**, identico a quello della base. Il modello non viene retroattivamente applicato al periodo necessario per addestrarlo. Il suo peggior drawdown nell'intero storico resta il **−36,10% del 2020**, prima dell'attivazione. Nel periodo comune, invece, il drawdown misura effettivamente la strategia con il nuovo meccanismo abilitato. La prima scelta positiva dell'albero arriva soltanto il **17 gennaio 2024**.

| Strategia, esecuzione principale | CAGR intero | MaxDD intero | CAGR comune | MaxDD comune |
|---|---:|---:|---:|---:|
| Base | 22,57% | -36,51% | 20,01% | -36,51% |
| Base con obiettivo 75% | 18,38% | -30,08% | 16,53% | -28,64% |
| Piani — media | 22,57% | -36,51% | 20,01% | -36,51% |
| Piani — modello lineare | 20,56% | -36,10% | 16,99% | -27,55% |
| Piani — albero, principale | 23,49% | -36,10% | 21,40% | -27,24% |
| OLC113 PRICE_RESET | 24,16% | -36,51% | 22,42% | -36,51% |

Tutte le cifre sono al netto dei costi di negoziazione simulati e prima delle imposte. Il drawdown campiona il valore prima dei costi di esecuzione e il valore di chiusura. Per il periodo comune il rapporto CAGR/perdita massima, o Calmar, passa da **0,55** a **0,79**. È una descrizione del campione osservato, non una previsione.

## Cosa cambia nella strategia

Il selettore mensile DEDUP_DUAL_TREND_OPP resta quello congelato. Il modello può intervenire su **una posizione effettivamente posseduta**, conservando le quantità delle altre. Valuta tre possibilità: lasciare il portafoglio invariato, vendere quella posizione e conservare il ricavato in cash fino al successivo aggiornamento mensile, oppure venderla e tentare un reinvestimento settimanale.

Nel terzo caso la scelta del sostituto avviene alla prima chiusura settimanale consentita **successiva alla vendita realmente completata**. Il nuovo ordine deve poi attendere un'ulteriore barra eseguibile. Il candidato viene scelto in quel momento, con il selettore originale e il controllo di correlazione già fissato. Il ricavato disponibile determina la dimensione dell'acquisto. Se manca un candidato, il piano resta in cash fino al passaggio mensile; non effettua tentativi aggiuntivi. Anche l'ETF appena venduto può tornare candidato se il selettore lo propone.

È consentito un solo piano attivo. Ogni aggiornamento mensile ha priorità e restituisce il controllo al selettore di base, anche se un ordine è ancora pendente. Il passaggio mensile è un nuovo segnale: gli ordini rispettano comunque la loro maturazione e l'eseguibilità effettiva. Non equivale a un riempimento o annullamento istantaneo.

Le etichette di apprendimento e la simulazione usano la stessa implementazione del piano. Per ogni stato iniziale si confronta il patrimonio dopo **42 sedute** con quello della continuazione di base, includendo vendite, acquisti, costi e passaggi mensili. Non si impone una liquidazione fittizia alla fine dell'orizzonte. Dopo il passaggio mensile, l'etichetta prosegue con la politica di riferimento: resta quindi una differenza fra gli stati di addestramento e quelli che la strategia può produrre.

## Modelli e controlli

I confronti erano fissati prima dei risultati: una media storica, una regressione lineare Ridge e un singolo albero con profondità massima due. L'albero era il modello principale; gli altri servono a distinguere l'effetto del piano completo da quello della scelta delle condizioni.

Ogni mese entrano nelle stime soltanto gli esiti terminati **prima** del cut-off. Ogni data ha peso totale uno, anche quando offre due posizioni. Servono almeno 504 date mature, 24 mesi di segnali e 12 intervalli di 42 sedute senza sovrapposizione. I 32 ricampionamenti a blocchi di 63 sedute generano una soglia inferiore euristica. Una scelta richiede valore medio e soglia inferiore entrambi positivi. Questa soglia **non è un intervallo di confidenza calibrato**.

Il banco contiene **1698 date iniziali**, di cui **1579 confronti validi**, 78 date mensili escluse e 41 date troppo vicine alla fine del campione. Ogni famiglia contiene **3.158 righe**, perché si esaminano le due posizioni di ogni data valida. Queste righe non costituiscono altrettante osservazioni indipendenti. La differenza massima fra ogni continuazione BASE ricostruita e il conto congelato è **2.18e-11 euro**.

## Resistenza a costi e ritardi

Lo scenario principale costa 1 euro più 15 punti base per ordine effettivo. Lo stress dei costi usa 2 euro più 30 punti base. Lo stress di ritardo aggiunge una seduta, spostando la prima possibile esecuzione da k+1 a k+2. Le stime restano quelle ottenute sul banco principale; non vengono riaddestrate per lo stress.

| Scenario, periodo comune | CAGR base | CAGR albero | Differenza CAGR, pp | MaxDD base | MaxDD albero | Miglioramento DD, pp |
|---|---:|---:|---:|---:|---:|---:|
| Chiusura successiva | 20,01% | 21,40% | +1,39 | -36,51% | -27,24% | +9,28 |
| Costi doppi | 17,26% | 18,61% | +1,35 | -37,10% | -28,22% | +8,89 |
| Una seduta di ritardo in più | 11,86% | 12,92% | +1,06 | -37,30% | -29,85% | +7,45 |

Il vantaggio relativo dell'albero conserva il segno in entrambi gli stress, sia nell'intero storico sia nel periodo comune. Tuttavia il livello assoluto dei rendimenti è sensibile all'esecuzione: con una seduta aggiuntiva il CAGR dell'intero conto scende al **15,43%**, e quello della base al **14,72%**. Questo limita la forza della conclusione economica. Non esiste un conto PRICE_RESET con questo stesso ritardo; il confronto non viene inventato.

## Tutti i 15 conti

| Scenario | Conto | CAGR intero | MaxDD intero | CAGR comune | MaxDD comune | Piani | Ordini | Costi totali |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NEXT_CLOSE | BASE | 22,57% | -36,51% | 20,01% | -36,51% | 0 | 225 | 4.029,40 € |
| NEXT_CLOSE | STATIC_75 | 18,38% | -30,08% | 16,53% | -28,64% | 0 | 228 | 2.633,73 € |
| NEXT_CLOSE | MEAN_CYCLE | 22,57% | -36,51% | 20,01% | -36,51% | 0 | 225 | 4.029,40 € |
| NEXT_CLOSE | RIDGE_CYCLE | 20,56% | -36,10% | 16,99% | -27,55% | 50 | 249 | 4.531,74 € |
| NEXT_CLOSE | TREE_CYCLE | 23,49% | -36,10% | 21,40% | -27,24% | 10 | 236 | 4.302,41 € |
| DOUBLE_COST | BASE | 19,71% | -38,31% | 17,26% | -37,10% | 0 | 226 | 7.345,29 € |
| DOUBLE_COST | STATIC_75 | 16,01% | -31,78% | 14,10% | -29,22% | 0 | 227 | 4.903,39 € |
| DOUBLE_COST | MEAN_CYCLE | 19,71% | -38,31% | 17,26% | -37,10% | 0 | 226 | 7.345,29 € |
| DOUBLE_COST | RIDGE_CYCLE | 14,99% | -38,31% | 10,22% | -27,92% | 40 | 253 | 7.645,12 € |
| DOUBLE_COST | TREE_CYCLE | 20,61% | -38,31% | 18,61% | -28,22% | 9 | 234 | 7.788,57 € |
| DELAY1_CLOSE | BASE | 14,72% | -42,84% | 11,86% | -37,30% | 0 | 222 | 3.129,80 € |
| DELAY1_CLOSE | STATIC_75 | 12,35% | -35,42% | 10,11% | -29,31% | 0 | 222 | 2.183,79 € |
| DELAY1_CLOSE | MEAN_CYCLE | 14,72% | -42,84% | 11,86% | -37,30% | 0 | 222 | 3.129,80 € |
| DELAY1_CLOSE | RIDGE_CYCLE | 16,12% | -42,84% | 13,96% | -27,72% | 36 | 245 | 3.614,67 € |
| DELAY1_CLOSE | TREE_CYCLE | 15,43% | -42,84% | 12,92% | -29,85% | 9 | 230 | 3.382,73 € |

Il controllo della media non trova piani con valore sufficientemente positivo e riproduce la base. Il modello lineare interviene molto più spesso: **50 piani** nello scenario principale, con esposizione media del **76,94%** e CAGR inferiore alla base. L'albero avvia **10 piani**, sette parcheggi in cash e tre tentativi di reinvestimento, tutti e tre seguiti da acquisto. L'esposizione media resta al **96,90%**, contro **99,73%** della base. Gli ordini passano da 225 a 236, i costi totali da 4.029,40 € a 4.302,41 €.

## Dove si forma il risultato

| Anno | Base | Base 75% | Media | Lineare | Albero principale |
|---|---:|---:|---:|---:|---:|
| 2020 (parziale) | 70,29% | 53,14% | 70,29% | 70,29% | 70,29% |
| 2021 | -14,88% | -11,26% | -14,88% | -14,88% | -14,88% |
| 2022 | 31,51% | 24,77% | 31,51% | 40,57% | 31,51% |
| 2023 | 26,07% | 20,10% | 26,07% | 32,65% | 26,07% |
| 2024 | 27,65% | 22,51% | 27,65% | 31,45% | 28,41% |
| 2025 | 44,38% | 34,84% | 44,38% | -1,66% | 34,25% |
| 2026 (parziale) | -12,36% | -8,49% | -12,36% | -0,49% | -1,51% |

Il risultato non è uniforme fra gli anni. Nel 2025 l'albero rende il **34,25%**, contro **44,38%** della base; nel 2026 fino al 30 ottobre perde **1,51%**, contro **12,36%** della base. Due parcheggi della stessa posizione, avviati il 14 maggio e il 1° giugno 2026, appartengono alla fase in cui il nuovo conto evita parte della successiva perdita della base. Il registro dei piani consente di esaminare le esecuzioni; queste associazioni temporali non identificano da sole il contributo causale isolato di ciascun intervento.

## Le previsioni non dimostrano ancora un vantaggio del rientro

La verifica delle previsioni usa soltanto i modelli disponibili alle rispettive date e assegna peso uguale alle date. Nel periodo comune ci sono 1.013 date con esito completo, equivalenti a **26 intervalli da 42 sedute senza sovrapposizione** secondo il conteggio fissato. Il confronto previsivo resta distinto dai rendimenti dei conti.

| Piano | Modello | Errore quadratico medio | Differenza contro media | Date con soglia positiva | Intervalli positivi non sovrapposti | Vantaggio realizzato medio nei casi positivi |
|---|---|---:|---:|---:|---:|---:|
| PARK | MEAN | 0.0014454 | +0.0000000 | 0 | 0 | — |
| PARK | RIDGE | 0.0014398 | -0.0000056 | 602 | 22 | 0,25% |
| PARK | TREE | 0.0015398 | +0.0000943 | 42 | 4 | 1,25% |
| REDEPLOY | MEAN | 0.0013391 | +0.0000000 | 0 | 0 | — |
| REDEPLOY | RIDGE | 0.0013571 | +0.0000180 | 291 | 19 | 0,42% |
| REDEPLOY | TREE | 0.0013765 | +0.0000373 | 11 | 3 | -0,24% |

L'albero ha errore quadratico medio superiore alla media semplice in entrambe le famiglie. Per i reinvestimenti, i casi con soglia positiva sono solo **11 date**, distribuite in **tre intervalli non sovrapposti**, e il vantaggio medio realizzato è negativo. Il valore riportato è una differenza logaritmica di patrimonio a 42 sedute, espressa in percentuale per leggibilità; non è un CAGR e non si somma fra date. I tre acquisti del conto principale non bastano a dimostrare che il modello riconosca sistematicamente rimbalzi o opportunità emergenti.

La verifica del supporto osserva anche stati nuovi. In cinque righe del conto albero principale, l'indicatore di disponibilità del candidato vale zero dopo una stima in cui era sempre uno. La deviazione standard numerica quasi nulla produce un valore standardizzato enorme nei log. L'albero usa le caratteristiche grezze e il valore standardizzato non è una condizione operativa. Questo caso va interpretato come una categoria non ancora osservata, separatamente dalle deviazioni su variabili continue; i log e le stime congelati restano invariati. Escludendo le dimensioni costanti in addestramento, il massimo valore standardizzato resta 11,02: lo scostamento fra gli stati osservati e quelli di addestramento rimane un limite concreto.

## Verifica e tracciabilità

**Verifica indipendente completata: 9/9 gruppi di controlli superati sui 15 conti.** Sono state controllate 48,953 valutazioni di posizioni, senza prezzi mancanti o troppo vecchi rispetto al limite di cinque giorni; l'errore massimo di ricostruzione del patrimonio è 1.31e-10 euro. Sono verificati 81 file di stima e 318 modelli numerici salvati. La suite completa finale supera 66 test sintetici. Il controllo non ha riaddestrato modelli né generato altre strategie. Esiti, fonti e dettagli sono in `results/INDEPENDENT_DIAGNOSTICS.json` e nei manifesti associati.

I quattro conti BASE/STATIC_75 con costi normali o doppi riproducono esattamente tutti i valori giornalieri e tutti gli ordini dei corrispondenti conti precedenti. Il banco è stato congelato prima delle etichette; il runner e il banco completo sono stati congelati prima delle stime e dei conti. Il secondo congelamento ha SHA256 **511e0cf134467b88f1cfae93865f84f58e53e2845c008eced140adb21138764d**. Le ricevute di ogni conto legano artefatti, metriche e identità dell'esperimento.

Sono disponibili i prezzi di riferimento e le loro identità nelle istruzioni di ripristino, tutte le stime mensili numeriche, le previsioni, gli stati effettivi dei conti, le istruzioni, le quantità, gli ordini e i passaggi dei piani. I test sintetici coprono maturità temporale, conservazione delle altre quantità, vendite ritardate, priorità mensile e rientri settimanali. Il rapporto indipendente documenta separatamente ciò che ha verificato.

## Limiti che incidono sull'interpretazione

L'universo è il catalogo corrente congelato di **2.096 ISIN con quotazioni EUR nel pannello Xetra**, non una ricostruzione completa di tutti gli ETF storicamente esistiti. Le condizioni di ammissibilità restano quelle del selettore originale. Quotazione in euro e copertura del rischio valutario sono caratteristiche diverse. Il campione mantiene i limiti di sopravvivenza, versione dei prezzi rettificati, qualità delle serie, dati giornalieri e capacità eseguibile non dimostrata.

Il capitale iniziale è 10.000 euro, con quantità frazionarie, nessun prestito di conto o vendita allo scoperto, cash remunerato a zero e imposte escluse. Le ipotesi sugli strumenti restano quelle dell'universo precedente.

Gli stati del banco derivano dalla politica di base. Dopo interventi, costi, scostamenti di peso e passaggi mensili, il conto appreso può trovarsi in stati differenti. Gli intervalli di risultato si sovrappongono e gli episodi di reinvestimento effettivi sono pochi. Lo storico è già stato usato in diversi esperimenti e **non è un campione indipendente mai esaminato**. Questi risultati sostengono un miglioramento storico della protezione nel periodo comune, con un guadagno limitato di CAGR; non sostengono una promessa del 30% o una capacità di rientro già dimostrata.

## File principali

- `results/SCORES.csv`: tutti i 15 conti.
- `results/COMMON_POST_WARMUP.csv`: finestre comuni e denominatori effettivi.
- `results/ANNUAL_RETURNS.csv`: rendimenti annuali.
- `results/FORECAST_SCORES.csv` e `FORECAST_RANKING.csv.gz`: verifica delle previsioni.
- `results/*/PLAN_SUMMARIES.json.gz`: selezione, attesa e passaggio mensile di ciascun piano.
- `results/*/ELIGIBLE_STATES.jsonl.gz` e `PLAN_VALUES.csv.gz`: stati effettivi e valori previsti.
- `results/*/PATH_RECEIPT.json`: identità di tutti gli artefatti di conto.
- `docs/DESIGN_AND_PROTOCOL.md`: regole fissate prima dei risultati.
- `research/design/`: revisioni indipendenti del codice e dell'analisi.
