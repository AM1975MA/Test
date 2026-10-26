# ETF Trader V3 — prova Ridge libero USA/EU e audit ISIN (2026-10-26)

**Eseguito e documentato. Solo ricerca, production unchanged.** Fonti: 18 fits annuali strict-matured-63d [Actions 40394516018](https://github.com/AM1975MA/Test/actions/runs/40394516018), backtest identico originale EUR [Actions 40395611231](https://github.com/AM1975MA/Test/actions/runs/40395611231), V3 baseline [40227417589](https://github.com/AM1975MA/Test/actions/runs/40227417589).

## Tutti gli ETF, zero restrizioni di categoria

| Top5, 101 segnali, febbraio 2018—luglio 2026, EUR, 10bps per lato | US149 CAGR | EU148 CAGR | US MaxDD | EU MaxDD |
|---|---:|---:|---:|---:|
| Ridge prevede signed return a 21 sedute | +19,654% | +4,345% | -44,44% | -30,02% |
| Ridge traiettoria signed 21/42/63 | +19,438% | +3,177% | -46,85% | -30,95% |
| V3 ranking originale 127 foglie | +13,862% | +3,908% | -41,31% | -46,97% |
| Passivi SPY EUR / EXSA EUR | +15,16% | +8,84% | n.a. | n.a. |

101 mesi segnale identici, 125 feature natie V3, training annuale 2012+, exit63 completamente maturata prima dell'anno target, nessuna selezione basata sul test, prezzo Open reale come memorizzato dal provider in EUR.

**Predittività Ridge P21 signed-forward IC:** US149 +0,079464, EU148 +0,023999. Delta +0,055465 bootstrap paired 6 mesi (10.000 repliche) intervallo 95% **[+0,009857;+0,099055]**. Il gap di ranking entro questo storico è dunque più evidente rispetto al vecchio V3, anche se l'insieme storico non è un holdout mai esaminato. MAE degli andamenti previsti a 21 sedute US Ridge 4,4865% versus zero forecast 4,4233%; EU Ridge 3,8626% versus zero 3,6326%. Nessuna evidenza di forecast numerico ben calibrato.

## Audit 148 ISIN EU dallo storico effettivamente utilizzato

- **148/148** ISIN superano verifica checksum.
- OHLC non numerici o non positivi: zero; violazioni dell'inviluppo OHLC giornaliero: **2**; quattro rendimenti close/close assoluti >18% dal 2012 a luglio 2026, dei quali due cali del 24 giugno 2016 plausibilmente legati a Brexit, che **NON** vanno esclusi solo perché forti.
- Volume zero medio nei file EU 2018—2026: **4,94%** delle barre, con estremi fino al 45% in uno strumento; assenza di trade print NON prova assenza di book maker.
- Sono disponibili **50** ISIN con diagnostica retrospettiva di prezzi coerenti, mediana fatturato giornaliero >=€250k, <=2% volume zero e <=10% barre OHLC perfettamente piatte. **103** superano controllo più permissivo €50k/10% volume zero/20% barre piatte. Questi insiemi NON possono essere riutilizzati per rivendicare un backtest OOS, perché calcolati su tutta la storia fino al 2026.
- ISIN verificati su emittente o listing esterno (non significa aver verificato indipendentemente ogni barra storica): DE0005933931 EXS1, DE0002635307 EXSA, DE0005933956 EXW1, LU0274211480 DBXD, LU0380865021 XESC, DE000A0F5UK5 EXV6.
- Non è stato scaricato un secondo archivio OHLC ufficiale o comprato feed Xetra: *stato cross-provider storico completo ancora aperto*. Storici Xetra d'origine: https://www.mds.deutsche-boerse.com/mds-en/historical-data

## Filtri SOLO as-of sulle 63 sedute precedenti: modelli congelati, nessun refit

| Cohort point-in-time EU, mean over 101 months | Eligible per month | Ridge IC | Top5 future21 excess per mese | V3 IC |
|---|---:|---:|---:|---:|
| Tutti | 131,9 | +0,0240 | +0,0705% | +0,0036 |
| Quality prezzi, senza soglia volume | 121,3 | +0,0230 | -0,0335% | -0,0056 |
| Quality + ADV>=€50k | 96,1 | +0,0271 | +0,0162% | -0,0105 |
| Quality + ADV>=€250k | 55,6 | +0,0139 | -0,0598% | -0,0228 |

Bootstrap paired 6 mesi dell'IC Ridge €250k vs tutti: **-0,01007**, 95% intervallo **[-0,03323;+0,01186]**. Non emerge che togliere serie apparentemente difettose risolva la debolezza predittiva EU. NB: l'addestramento originale usa comunque la storia complessiva, quindi è una diagnosi di selezione OOS, **non** un retraining da zero dopo cleaning.

Ridge Top5 EU su 505 ETF-mese: 256 EU sector, 67 EU country, 63 EUR sovereign, 53 property, 46 factor, 20 broad. **67** linee ordine con volume giornaliero riportato zero, contro **0** USA; il fill all'Open per quei casi non può essere considerato verificato.

## Ipotesi concorrenti, test più discriminante

I due panieri non rappresentano la stessa opportunità: US include USA, mercati internazionali ed emergenti, materie prime e obbligazioni; EU148 include solo azionario Europa, sovereign EUR e property. CAGR dei rispettivi benchmark EUR +15,16% SPY vs +8,84% EXSA (+6,32pp già diversi). Per attribuire il residuo a modello/dati, servono fattori geografici/settoriali corrispondenti e soprattutto **lo stesso sottostante quotato su venue differenti**.

Verificati presso issuer ETF sottostante USA quotati su Xetra: **IE00B5BMR087/SXR8.DE** S&P 500, **IE00B53SZB19/SXRV.DE** Nasdaq 100, **IE00B3XXRP09/VUSA.DE** S&P 500. *Non appartengono all'EU148 di sottostanti europei*. Occorre recuperare Xetra EOD originario e USD-US equivalente corretti per distribuzioni/divise, poi ripetere stesso modello e stessi calendari. Non attribuire risultati di performance Ridge a questo esperimento non ancora eseguito.

**Conclusione:** problema misto: qualità volume più debole EU, target/trajectories non ben calibrate, set europeo più omogeneo/matura meno esempi, e universi economici USA/EU non matched. Pochi errori OHLC espliciti non supportano l'ipotesi «quasi tutti gli ISIN europei sono corrotti». Sono disponibili nell'archivio consegnato CSV integrali e script per replica / quality flags.
