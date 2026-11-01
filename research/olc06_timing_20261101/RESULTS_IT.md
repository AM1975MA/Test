# OLC-06: il semplice ritardo spiega più della gradualità nel periodo principale

1 novembre 2026. Lotto concluso; ricerca retrospettiva, nessuna promozione e nessuna modifica a main.

## Che cosa è stato eseguito

48 percorsi persistenti su USA149 ed EU165: 32 riferimenti IMMEDIATE/PHASE5 riprodotti esattamente sulle sei matrici salvate e 16 nuovi DELAY3. Test con pesi finali 50/50 e originali, costi 0,001/0,003; sul 50/50 anche assenza delle protezioni e sensibilità al ritardo dei segnali di gap/breadth. Zero nuovi training. Protocollo registrato prima dei risultati al commit 146ec48636a219151a391d026826a69a1945abdc; parent OLC05 445944685c14bfe6cbeb4269319df1933176afe3.

DELAY3 mantiene il precedente target nelle prime due sedute del calendario aggregato locale e trasferisce interamente alla terza. Non riequilibra discrezionalmente le quantità durante l'attesa; le protezioni continuano a operare. Primo ingresso e rientro da una componente principale vuota sono immediati, come PHASE5. Una nuova coppia economica riavvia il countdown; la semplice permutazione 50/50 no. Nessun ordine viene eseguito su Open grezzo mancante.

## Risultati principali: 2021–2024, target finale 50/50

Stessi segnali CL01, rischio, contabilità per ticker e date effettive del successivo Open. Non è il confronto con il vecchio 39,33%, che appartiene ad altra versione e finestra.

| Variante | CAGR Europa | MaxDD Europa | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| Cambio immediato | 16,01% | -26,43% | 35,52% | -20,15% |
| **Cambio completo alla terza seduta** | **18,91%** | **-28,60%** | **38,72%** | **-20,15%** |
| Transizione in cinque sedute | 17,61% | -27,23% | 37,97% | -20,19% |

Al costo stressato, rispettivamente IMMEDIATE/DELAY3/PHASE5: Europa 13,57%/16,41%/15,15%, USA 32,25%/35,33%/34,63%. Il drawdown DELAY3 è -30,08% EU e -21,61% USA, contro -27,90%/-20,84% di IMMEDIATE. I costi sono coefficienti della convenzione legacy di mezzo turnover, non automaticamente 10/30 bp per lato. Il rendimento aggiuntivo non equivale a un miglioramento uniforme del rischio.

## Finestra completa febbraio 2019–1 luglio 2026

| Variante | CAGR Europa | MaxDD Europa | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| IMMEDIATE | 11,55% | -34,28% | 40,85% | -26,85% |
| DELAY3 | 14,60% | -36,25% | 45,53% | -28,28% |
| PHASE5 | 13,34% | -35,68% | 46,39% | -27,81% |

PHASE5 rimane superiore in crescita negli USA su questa finestra. DELAY3 non è un vincitore universale. Nel 2026 parziale i rendimenti effettivi USA sono +44,85% IMMEDIATE, +37,42% DELAY3 e +53,72% PHASE5; non sono CAGR annuali attesi.

Anche con i pesi originali DELAY3 migliora il CAGR 2021–2024 di entrambi: EU 10,95→15,84%, USA 44,48→45,31%; MaxDD EU -29,97→-29,55%, USA -21,86→-20,35%. Sull'intera storia i drawdown invece peggiorano. Il target originale può variare anche con i controlli giornalieri e riavviare la transizione; non confonderlo con il target mensile 50/50.

## Attribuzione giorno per giorno

Il beneficio DELAY3−IMMEDIATE nel 2021–2024, in punti logaritmici annualizzati a 252 sedute, si concentra nei primi due intervalli dopo il nuovo target: +3,229 EU e +3,497 USA. La terza seduta restituisce -0,778 e -1,117; gli intervalli restanti completano il totale a +2,464 e +2,332.

Il ponte per ticker chiude esattamente ogni giorno: vecchi nomi non più nella coppia, nuovi nomi, nomi condivisi, componente difensiva, effetto degli stop, commissioni e slippage. I vecchi nomi mantenuti contribuiscono +2,525 punti log/anno EU e +1,128 USA; i nuovi +1,013 e +1,160. È una decomposizione contabile condizionata a due traiettorie, non una causa unica o un alpha universale. PHASE5−DELAY3 è -1,097 EU e -0,538 USA nello stesso spazio logaritmico giornaliero annualizzato.

## Controprova da identico portafoglio iniziale

156 episodi distinti e 1.404 righe episodio×politica×costo. Alla partenza sono usate le quantità principali realmente detenute dal riferimento immediato; vengono confrontate le tre modalità per cinque intervalli, senza rischio/V6/stop o nuovi segnali. La normalizzazione a capitale 1 all'Open serve solo alla contabilità. Quattro finestre EU con quote non osservate e i due ultimi episodi di luglio 2026 senza esito completo sono esclusi esplicitamente. Questi controlli non si concatenano in un CAGR.

Nel 2021–2024, esiti completati entro fine anno: 43 episodi EU e 45 USA.

| Vantaggio medio locale su cinque intervalli, costo 0,001 | Europa | USA |
|---|---:|---:|
| DELAY3 meno IMMEDIATE, punti logaritmici | +0,528 | +0,167 |
| PHASE5 meno IMMEDIATE | +0,389 | +0,104 |
| PHASE5 meno DELAY3 | -0,139 | -0,063 |

DELAY3 è favorevole nel 55,8% dei casi EU e 55,6% USA: frequenze descrittive, non probabilità di successo futuro. Nei primi due intervalli le nuove coppie fanno mediamente -0,238% EU e -0,200% USA; le detenute +0,283% e -0,023%. Compatibile con un costo dell'ingresso immediato in questo campione, non prova di sovraestensione o di un effetto di fine mese.

Esempio favorevole: EU 1 novembre 2023, IM2A.DE/ZPRP.DE verso EXV4.DE/VVSM.DE; vecchi +7,76% nei primi due intervalli contro +2,73% nuovi; vantaggio locale DELAY3 di circa +4,76 punti logaritmici. Esempio sfavorevole: EU 3 giugno 2024, EXV5.DE/IBCJ.DE verso QDVE.DE/VVSM.DE; vecchi -2,53% contro -0,06% nuovi; ritardo costa circa 2,50 punti logaritmici. Le proposte erano disponibili prima degli esiti.

## Concentrazione, rischio e incertezza

Eliminando solo come diagnosi ex post i tre mesi di differenziale più favorevole, il vantaggio DELAY3−IMMEDIATE diventa -0,70 punti logaritmici annui EU e -1,45 USA. Per PHASE5 è -1,06 e -1,31. Non è una regola di trading né dimostra inutilità: mostra che pochi episodi sostengono gran parte del risultato. Non scegliamo i mesi da eliminare in produzione.

Bootstrap temporale appaiato USA/EU, blocchi 6 mesi, 10.000 estrazioni seed 20261101, 48 mesi 2021–2024. DELAY3−IMMEDIATE: +2,508 punti logaritmici annui EU, IC95%[-1,682;+6,579]; +2,325 USA, IC[-3,842;+8,696]. PHASE5−DELAY3: -1,117 EU, IC[-2,885;+0,561]; -0,537 USA, IC[-4,131;+3,263]. Questa annualizzazione usa 12 mesi, leggermente diversa dal ponte a 252 sedute; non sono errori di riconciliazione. Le frequenze bootstrap non sono posteriori. Lo zero non è un veto automatico, né i due universi sono repliche indipendenti.

Nessuna soluzione al 2020: febbraio–marzo DELAY3 rende -26,49% EU/-4,91% USA, contro -25,37%/-3,05% IMMEDIATE. Il vantaggio di crescita 2021–2024 permane nelle sensibilità senza protezioni e con input gap/breadth ritardati, ma ciò non certifica eseguibilità. La sensibilità LAG1 modifica anche input condivisi dagli stop.

## Decisione e fasi non eseguite

Conservare IMMEDIATE, DELAY3 e PHASE5 come tre riferimenti. Nel confronto principale il semplice ritardo è una spiegazione più parsimoniosa del beneficio della gradualità; non è dimostrato che il controllo predittivo debba necessariamente modulare una transizione in cinque sedute.

La domanda successiva è quanto costa aspettare, usando solo informazioni note prima dell'ordine e dando valore anche al vecchio portafoglio. Ma prima di attribuire il risultato al fine mese occorre ricomputare davvero i forecast su diverse date segnale. Ritardare l'esecuzione delle stesse previsioni NON è un nuovo calendario del segnale. In questo lotto non sono stati eseguiti quei refit né addestrati modelli di urgenza/tempo-evento. Non proseguono in background. Nessuna variante promossa o soglia ottimizzata dopo aver identificato gli episodi migliori.

## Verifiche e consegna

48 percorsi, 90.216 intervalli contabili indipendentemente riconciliati, 1.872 metriche ricalcolate. Errore massimo NAV 3,55e-15, metriche 1,79e-13, identità log giornaliera 4,91e-16; zero operazioni su Open grezzo mancante. Sei perturbazioni reali dei dati futuri non modificano decisioni/NAV precedenti. 49 test passati nel pacchetto completo:24 ereditati e25 nuovi. Revisione dell'autore, non indipendente.

Il codice della nuova regola è generato dal sorgente OLC05 verificato per digest. Un errore di parentesi nel runner è stato corretto prima dei risultati; un test su prezzi piatti era eccessivamente esatto e rilevava 2,22e-16 di arrotondamento: adottata tolleranza1e-14, nessuna modifica economica. I log RED/GREEN sono conservati.

Main rimane 77f7a4706f934e7061541cd62c1c0ce64ab7135d. Il repository conserva protocollo, generatore, runner, nucleo di attribuzione, test mirati e risultati compatti. Il pacchetto scaricabile è la consegna completa con tutti gli script, 49 test, input autenticati, NAV e ledger. Non si afferma che grandi binari o ogni script ausiliario siano caricati in GitHub.

Restano i limiti su universo retrospettivo, total-return/distribuzioni, FX, spread, quote, quantità frazionarie e rischio legacy sullo stesso Open. Nessun backtest è presentato come rendimento futuro; l'ordine a mercato non garantisce il prezzo osservato. Fonte primaria di contesto: SEC Investor.gov, Types of Orders, https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders.
