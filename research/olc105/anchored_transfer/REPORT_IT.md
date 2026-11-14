# OLC105 — Risultati del trasferimento congelato su 29 fondi Trade Republic

**14 novembre 2026. Replay economici completati; ricerca retrospettiva condizionale. NON promuovere al trading reale.**

## Esito
I quattro bracci ML congelati sono stati eseguiti. Sul nuovo universo non raggiungono i controlli World e momentum. MINVAR63 + DELAY3 e negativo nello scenario base. Il risultato riguarda la precisa formulazione ANCHORED_TRANSFER: non e un nuovo CAGR della strategia originale EU165 e non dimostra che ogni possibile riaddestramento sul nuovo universo fallirebbe.

## Contratto e periodo
- 165 strumenti storici servono soltanto per contesto, cluster e normalizzazioni. Acquisti e alternative V6 limitati ai 29 nuovi ISIN e due segnaposto cash EUR a interesse zero. Nessun anchor detenuto.
- Il test primario clusterizzato indipendentemente sui soli 29 fondi resta BLOCKED_CONTRACT_SIZE. ANCHORED_TRANSFER e il diverso esperimento gia registrato nell'addendum.
- Modelli annuali originali Return125, ET/XGB e contesto riaperti e congelati; nessun training sui risultati dei candidati. Feature e cluster ricostruiti sul contesto congiunto.
- Elegibilita comune: almeno 253 osservazioni, prezzo non piu vecchio di cinque giorni, almeno 12 candidati e sei macro-gruppi; stessa prima apertura per World.
- Periodo principale: apertura 2 marzo 2020 fino all'apertura 2 novembre 2026, 80 cicli completi. 81 decisioni prodotte; il segnale 30 ottobre inizia il ciclo novembre, riportato separatamente come parziale.
- HALF/MINVAR63 x IMMEDIATE/DELAY3, V6/FAST_LOCK3 congelati. DELAY3 mantiene posizioni precedenti e protezioni durante l'attesa; non e una liquidazione obbligatoria in cash.
- World fisso: IE00BFY0GT14 / SPPW.DE. Controllo momentum: due maggiori rendimenti a 252 osservazioni, 50/50 mensile. World e momentum non applicano V6 o stop: riferimenti semplici del portafoglio, non ablation causali risk-matched.

## Risultato economico principale
Capitale ipotetico EUR 10.000, EUR 1 per ordine effettivo sul singolo strumento, shortfall sfavorevole ipotetico 15 bp (0,15%) per lato, anche sugli stop. Costi detratti dalla liquidita senza indebitamento. Non sono spread Trade Republic osservati. Unita economiche frazionarie su prezzi adjusted, NON quote intere.

| Configurazione | CAGR calendario | Cumulato netto | MaxDD aperture | Capitale finale EUR | Ordini | Costi simulati EUR |
|---|---:|---:|---:|---:|---:|---:|
| Trasferimento OLC19, 50/50 immediato | 5,20% | 40,22% | -29,94% | 14.021,80 | 364 | 1.868,54 |
| ML 50/50 DELAY3 | 2,45% | 17,50% | -30,65% | 11.750,04 | 369 | 1.736,51 |
| ML MINVAR63 immediato | 1,47% | 10,25% | -31,79% | 11.024,90 | 388 | 1.952,46 |
| Trasferimento OLC67, MINVAR63 DELAY3 | -1,62% | -10,32% | -40,76% | 8.967,52 | 394 | 1.772,60 |
| World passivo SPPW.DE | 14,50% | 146,77% | -25,76% | 24.677,41 | 1 | 15,98 |
| Momentum252 Top2 50/50 | 16,12% | 170,96% | -25,12% | 27.096,31 | 123 | 1.162,99 |

CAGR su giorni di calendario (365,2425), non la convenzione 252 rendimenti dei precedenti report. MaxDD sulle aperture del periodo. Terminale valorizzato senza liquidazione forzata; imposte personali e interessi cash esclusi. Distribuzioni incorporate nei proxy adjusted, non in accrediti cash reali. Non confrontare direttamente con i vecchi CAGR 2019-luglio2026.

## Non e soltanto il costo
| Configurazione | CAGR senza costi | CAGR base |
|---|---:|---:|
| OLC19 trasferito, 50/50 immediato | 8,42% | 5,20% |
| 50/50 DELAY3 | 5,59% | 2,45% |
| MINVAR63 immediato | 5,07% | 1,47% |
| OLC67 trasferito | 1,88% | -1,62% |
| World | 14,53% | 14,50% |
| Momentum252 | 17,36% | 16,12% |

La debolezza resta senza commissioni e shortfall. Nessuna selezione di nuovi parametri per salvare il risultato.

## Sensibilita predichiarate
EUR 10.000, ticket EUR 1; CAGR con 5/15/30 bp per lato:

| Configurazione | 5 bp | 15 bp | 30 bp |
|---|---:|---:|---:|
| 50/50 immediato | 6,94% | 5,20% | 2,64% |
| 50/50 DELAY3 | 4,11% | 2,45% | circa 0,00% |
| MINVAR63 immediato | 3,41% | 1,47% | -1,37% |
| MINVAR63 DELAY3 | 0,22% | -1,62% | -4,33% |
| World | 14,52% | 14,50% | 14,48% |
| Momentum252 | 16,86% | 16,12% | 15,02% |

Eseguiti tutti gli scenari EUR 5.000/10.000/50.000 x ticket EUR 1/2 x 5/15/30 bp, oltre ai controlli gross/legacy. Con EUR 50.000, ticket EUR 1 e 15 bp, 50/50 immediato rende circa 5,71%, MINVAR63 DELAY3 circa -1,00%: la dimensione del conto non risolve il problema.

Novembre parziale, fino all'apertura 13 novembre: CAGR 4,74% HALF immediato, 2,17% HALF delay, 0,76% MINVAR immediato, -2,01% MINVAR delay, 14,61% World, 15,28% momentum. Questi numeri non sostituiscono il periodo completo comune.

## Correzione decisiva: split omesso da Yahoo
Il primo replay diagnostico conteneva un falso crollo del 99% di P500.DE il 15 dicembre 2025. Close=Adj Close e Stock Splits=0 nello snapshot. Il comunicato ufficiale Invesco del 30 ottobre 2025 conferma lo split 100 nuove quote per una vecchia, ISIN IE00B3YCGJ38 invariato, ex-date 15 dicembre 2025. Pagine 2-3 verificate visivamente.

Fonte: https://www.invesco.com/content/dam/invesco/emea/en/product-documents/etf/fund/shareholder-notice/invesco-sp-500-ucits-etf-acc_shareholder-notice_en_281025.pdf

Nella copia derivata: OHLC x100 e volume /100 soltanto dalla data effettiva, in unita economiche forward. Prefisso storico identico, controvalore preservato; raw e manifest originari invariati. Tutti i passaggi, forecast e controlli sono stati rieseguiti dopo la correzione. Il replay non corretto e INVALIDO e conservato separatamente. Questo intervento e post-diagnosi di qualita dati, non una preregistrazione prima di ogni outcome o un nuovo tuning.

## Limiti di prezzo ed esecuzione
I quattro bracci ML hanno 51-55 giornate-strumento detenute con geometria OHLC segnalata. Nessuno dei 22-23 stop finali coincide con tali barre, ma i prezzi non sono certificati. Ci sono 5-6 stop su strumenti acquistati nella stessa seduta. Quando manca l'Open necessario, il relativo ordine viene rinviato; il prezzo precedente serve soltanto per valorizzare, non per inventare un fill.

Non sono simulati lotti interi, esecuzioni frazionarie reali, offerte/domande, asta, fiscalita, remunerazione cash o disponibilita storica sul conto. Le sedi Yahoo sono proxy e non quote certificate Trade Republic. Restano incomplete PIT universe/survivorship, mapping storico e fonti aggiustate successivamente. Nuovi ISIN su mercati gia studiati NON sono un vero holdout economico/prospettico.

## Verifica numerica
- 148 checksum sorgenti congelate, 29 ISIN.
- 192 riaperture teste Hybrid; raw error circa 1e-7. Return125: 90/90 classifiche EU uguali.
- 90/90 coppie contestuali storiche uguali; score NON bitwise (max errore assoluto 0,0001338722 per percentili/pareggi).
- OLC19 originale: 14 matrici bitwise (7 EU + 7 USA) a costi legacy.
- 118 conti e 236 righe scorecard ricalcolate indipendentemente; errore metriche massimo 7,28e-16 e costi per ordine 5,69e-14 EUR.
- Dieci percorsi completi riconciliati per quantita e liquidita; zero holdings di anchor.
- Riesecuzione isolata di tutti i 118 conti dai soli stati congelati; 70 matrici reference bitwise; differenza da roundtrip CSV <=4,45e-16.
- 11 test automatici verdi, compresa correzione split e vincoli as-of/candidate-only.

I conti e la riesecuzione isolata sono stati eseguiti nell'ambiente di calcolo. L'Action GitHub 43640051824 verifica il digest dei 19 sorgenti archiviati e riesegue gli 11 test: NON viene presentata come un nuovo refit o come 118 backtest eseguiti sulla CI.

## Decisione
**Non adottare questo trasferimento sul conto reale.** Nel campione non emerge una ragione economica per preferirlo al World passivo. Neppure il controllo momentum viene automaticamente promosso al trading: non e validato prospetticamente e mantiene rischi di fonte/esecuzione.

Nessun ordine reale; main, OLC19, OLC67 e automazioni invariati.

## Riproduzione
Sorgenti esatti in src/ e tests/, BASE_RESULT.json e VALIDATION_SUMMARY.json in results/. Il pacchetto consegnato nella conversazione contiene sei stati congelati, tutti i diari, ordini/stop, scorecard, snapshot originali, protocolli e manifest. `python src/replay_saved_states.py --out /nuova/cartella` ripete i 118 conti senza i modelli annuali. Per rigenerare anche feature/forecast servono gli archivi originali esterni identificati in ORIGINAL_DEPENDENCIES.json e il layout OLC104. La parita numerica non certifica fill o generalizzazione.
