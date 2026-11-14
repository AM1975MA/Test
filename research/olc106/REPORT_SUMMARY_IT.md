# OLC106 — Primo test nuovo su Europa, USA e fondi globali

**14 novembre 2026. Ricerca retrospettiva; nessun ordine, nessuna promozione.**

## Esito
Eseguiti 120 replay: cinque regole x quattro universi x sei scenari. Nessuno supera contemporaneamente CAGR >=20%, MaxDD non inferiore a -25% e CAGR/|MaxDD| >=1. I risultati riguardano la precisa prima costruzione rules-based OLC106: non dimostrano l'impossibilita dell'obiettivo o il fallimento di qualsiasi strategia nuova.

Protocollo prima dei risultati: commit f5327a86ff5b4d37c85272740c404e1af9fc2089. Addendum delle scale di fonte USA prima del replay: 2d46ae9da40e18383dcc175487423bad000d7920. Non sono stati riaddestrati modelli, riutilizzati gli score OLC19 o ritoccati i parametri dopo gli esiti.

## Copertura
- EU165: 165 ETF quotati in Europa, in EUR; i sottostanti non sono solo europei.
- USA149: 149 ETF quotati negli USA, rendimento in USD; non si presume acquistabilita su Trade Republic retail italiano.
- TR29: 29 ISIN del catalogo pubblico precedentemente congelato, quotazioni EUR, esposizioni World/Europa/USA/emergenti/bond/real assets. Non sono 29 soli World.
- EU194: EU165 + TR29 in EUR, ammissibilita Trade Republic dei vecchi 165 non certificata.
Non si sommano i quattro insiemi come prove indipendenti. Nessun portafoglio mescola prezzi EUR/USD senza serie di cambio.

## Regole testate
PASSIVE: EUNL.DE nel primo universo, ACWI negli USA, IE00BFY0GT14/SPPW.DE negli altri due.
MOM252_TOP2: due migliori momentum a 252 sedute, 50/50 mensile e banda di non intervento 3% per strumento.
DIVERSE_TREND: momentum annualizzati 63/126/252 divisi per volatilita 63d, filtro prezzo sopra media 200 e momentum annuale positivo; fino a sei posizioni con correlazione a 126 sedute <=0,90, pesi inversi alla volatilita, cap 25% per posizione, residuo in cash.
DIVERSE_RISK15: stessa selezione, volatilita ex-ante target 15%, riduzione se stima >18,75%, nessuna leva.
DIVERSE_GUARD: aggiunge riduzione al 50% a drawdown del ciclo -12%, richiesta di uscita a -18%, almeno 20 sedute e conferma del trend prima del rientro mensile. Il massimo usato dal controller puo ripartire al rientro; il drawdown riportato del conto NON viene mai azzerato. Non si garantisce un drawdown massimo.
Decisioni solo su chiusure note; ordini dalla successiva apertura osservata; ritardi aggiuntivi 1/2 sedute per tutte le istruzioni incluse quelle di rischio. Nessun Low usato per inventare fill intraday.

## Confronto base
Periodo comune: prima apertura 2 marzo 2020 -> chiusura 30 ottobre 2026. 2020 e 2026 parziali; la discesa prima di marzo 2020 non e inclusa. CAGR su giorni di calendario; MaxDD su Open e Close campionati, non intraday.
Capitale 10.000 unita della valuta del pannello, ticket 1 unita per ordine e 15 bp per lato. Sono costi ipotetici, non spread Trade Republic misurati. Cash a zero rendimento, imposte escluse, nessuna liquidazione forzata terminale.

| Universo | Strategia | CAGR | MaxDD |
|---|---|---:|---:|
| EU165 | Globale passivo | 14,37% | -25,32% |
| EU165 | Momentum Top2 con banda 3% | 16,41% | -40,65% |
| EU165 | Trend diversificato | -0,83% | -32,76% |
| EU165 | Trend + rischio 15% | -1,34% | -32,73% |
| EU165 | Trend + rischio + allarme | -1,86% | -29,27% |
| USA149 | Globale passivo | 14,01% | -29,08% |
| USA149 | Momentum Top2 con banda 3% | 25,03% | -40,19% |
| USA149 | Trend diversificato | 1,27% | -18,24% |
| USA149 | Trend + rischio 15% | 1,63% | -15,94% |
| USA149 | Trend + rischio + allarme | 0,97% | -15,14% |
| TR29 | Globale passivo | 14,54% | -25,76% |
| TR29 | Momentum Top2 con banda 3% | 18,75% | -23,26% |
| TR29 | Trend diversificato | 8,07% | -16,94% |
| TR29 | Trend + rischio 15% | 7,71% | -16,92% |
| TR29 | Trend + rischio + allarme | 4,72% | -16,60% |
| EU194 | Globale passivo | 14,54% | -25,76% |
| EU194 | Momentum Top2 con banda 3% | 15,37% | -32,50% |
| EU194 | Trend diversificato | 2,50% | -20,69% |
| EU194 | Trend + rischio 15% | 2,02% | -20,23% |
| EU194 | Trend + rischio + allarme | 0,76% | -19,16% |

Il controllo momentum di questo lotto NON e lo stesso esecutore OLC105: banda 3%, griglia comune e osservabilita, estremo finale e misura del drawdown sono espliciti. Non interpretare le differenze fra report come un incremento convalidato.

## Costi e ritardo: candidato principale DIVERSE_RISK15
| Universo | Senza costi | Base | Ritardo +1 seduta | Ritardo +2 sedute |
|---|---:|---:|---:|---:|
| EU165 | 2,01% | -1,34% | -1,46% | -2,27% |
| USA149 | 3,56% | 1,63% | 0,82% | -0,06% |
| TR29 | 9,80% | 7,71% | 6,82% | 6,34% |
| EU194 | 5,43% | 2,02% | 1,34% | 0,29% |

Anche senza costi l'obiettivo non e raggiunto. Non e semplicemente eccesso di cash: esposizione media del candidato circa 92,8% EU165, 98,1% USA149, 96,1% TR29 e 97,3% EU194.
Le nuove strategie richiedono circa 11,6-15,5 giorni operativi l'anno nello scenario base, spesso con vari ordini nella stessa giornata. Non sono notifiche reali inviate all'utente.

## Verifica
- 653 membri degli archivi OLC104/105 controllati e tre ZIP autenticati per SHA256.
- P500 mantiene la rettifica 100:1 gia documentata; nessun outcome corretto ad hoc.
- Parita dei 29 contro OLC105: errore relativo massimo 7,49e-16.
- Scales USA su overlap O/C: errore massimo residuo 2,1341e-7, raw immutati.
- 14 test automatici: causalita, prezzi mancanti, costi, limiti, ritardi, ratio passivo e drawdown.
- 120 conti ricostruiti indipendentemente da singoli ordini e prezzi; 44.261 timestamp verificati.
- Errore massimo cash/NAV 6,55e-11; costo ordine 1,42e-14; CAGR/MaxDD 2,00e-15.
- Action 43646000325: SUCCESS sui test di contratto. I 120 replay finanziari e la ricostruzione indipendente sono stati eseguiti nell'ambiente locale di calcolo; questa Action non viene descritta come una nuova esecuzione dei 120 conti.

## Limiti materiali e stato del progetto
Si tratta ancora di unita economiche frazionarie su prezzi rettificati, NON di quote intere broker. Restano da certificare catalogo storico/conti Trade Republic, quote USA originariamente osservate, anomalie dei dati, corporate actions, bid-ask/aste, imposte e liquidita remunerata. Vecchi e nuovi ETF possono avere le stesse esposizioni: il campione non e un holdout vergine.
Completato il primo screen nuovo sui quattro universi, non il tool definitivo, la tassonomia economica completa o un motore basato su nuova informazione fondamentale. Nessun segnale live. Non arrotondiamo quote adjusted chiamandole quote fisiche.

## Decisione e consegna
Nessuna configurazione ammessa alla fase live. Questa prima architettura di trend risk-adjusted/diversificato e respinta rispetto al mandato, senza retuning sul suo risultato.
Il repository conserva sorgenti, test, protocolli e sintesi verificabili. Il pacchetto scaricabile OLC106_MULTIUNIVERSE_20261114_VERIFICATO.zip contiene anche quattro pannelli prezzo, tutte le 120 curve, ordini, alert, annualita e manifest per riesecuzione autonoma.
I grandi archivi originali servono solo a rigenerare i pannelli con prepare.py; i pannelli congelati del pacchetto bastano per run.py e verify.py.
Nessuna modifica a main, OLC19, OLC67 o automazioni.
