# OLC75 — Affidabilità dei segnali e allocazione Top2: audit completo
**9 novembre 2026 · ricerca retrospettiva · esito negativo per l’allocazione ML.** Nessun cambiamento a OLC19, OLC67 o `main`. Gli anni fino a luglio 2026 sono stati esaminati ripetutamente in OLC01–74 e non sono un holdout vergine. Tutte le cifre qui riportate provengono dai replay OLC75 o dai checkpoint originali; non sono rendimenti di trading reale.

## Executive summary
OLC75 testa una nuova ipotesi: il disaccordo/consenso fra Return125, ET e XGB, la dispersione dei seed e la persistenza della preferenza fra due ETF possono quantificare l’affidabilità della leadership prima dell’investimento? **No nel test eseguito:** un classificatore prequential che usa queste caratteristiche ha Brier score peggiore sia della probabilità storica sia del solo differenziale FUSION, in entrambi i mercati sul 2021–2024. Le allocazioni risultanti non superano il gate economico congiunto. La baseline OLC19 resta invariata.
**Dato indisponibile:** gli score originali terminano al 30 giugno 2026, e l’ultimo evento del motore è il 1 luglio 2026. Non è stato trovato nei checkpoint di ricerca un pannello verificato agosto–ottobre 2026 con gli stessi titoli, convenzioni e calendario. NON è stata costruita una falsa validazione OOS.

## 1. Predizione cronologica, 2021–2024
La label è `1{ETF1 batte ETF2 alla prossima apertura mensile}`. Per la previsione del mese t si utilizzano soltanto label fino a t−2 e feature già note al segnale. Brier score e log-loss sono perdite probabilistiche: minore è meglio.

| Mercato | Metodo | N previsioni | Brier ↓ | Log-loss ↓ | Accuratezza direzione |
|---|---|---:|---:|---:|---:|
| EU | p_prior | 44 | 0.2562 | 0.7056 | 45.5% |
| EU | p_score | 44 | 0.2615 | 0.7164 | 40.9% |
| EU | p_reliability | 44 | 0.2707 | 0.7353 | 31.8% |
| USA | p_prior | 46 | 0.2416 | 0.6762 | 63.0% |
| USA | p_score | 46 | 0.2478 | 0.6887 | 52.2% |
| USA | p_reliability | 46 | 0.2586 | 0.7106 | 41.3% |

La probabilità storica è il controllo prequential più efficace sul MAIN in entrambi i mercati. Le differenze Brier di Reliability meno prior sono positive: EU +0,01447, USA +0,01704. Il bootstrap descrittivo a blocchi di sei mesi ha intervallo EU [−0,00354; +0,03406], USA [+0,00497; +0,02915]; gli intervalli non correggono gli oltre 70 lotti di ricerca storica.

## 2. Quanto vale il consenso dei tre esperti?
Gli head ET/XGB sono convertiti in percentili esattamente come in OLC19, mentre Return usa il suo score originale. “Unanimità” significa tre voti concordi sulla direzione relativa tra gli stessi due ETF contestuali. Non significa consenso indipendente: gli head condividono informazioni.

| Mercato | Periodo | Mesi maturi | Mesi unanimi | Direzione corretta quando unanimi | Frequenza vittoria ETF1 |
|---|---|---:|---:|---:|---:|
| EU | MAIN | 48 | 13 | 6/13 | 52.1% |
| EU | 2024 | 12 | 3 | 0/3 | 33.3% |
| EU | 2025 | 12 | 1 | 0/1 | 41.7% |
| EU | 2026_PART | 6 | 2 | 1/2 | 66.7% |
| USA | MAIN | 48 | 17 | 9/17 | 62.5% |
| USA | 2024 | 12 | 3 | 2/3 | 83.3% |
| USA | 2025 | 12 | 3 | 2/3 | 50.0% |
| USA | 2026_PART | 6 | 2 | 0/2 | 33.3% |

Nel 2021–2024, la precisione del voto unanime è 6/13 per Europa e 9/17 per USA. Nel 2026 parziale USA è 0/2: campione minuscolo, ma non a favore di un tilt automatico. La media dei margini e gli score dei seed non sostituiscono una prova di calibrazione predittiva.

## 3. Cinque policy di peso continuo: backtest contabile nativo
Stessi Top2 `TOP2_CONTEXT_REVALUE` del motore OLC19, stessi stop V6/FAST_LOCK3 e convenzioni costo legacy 0,001; confronto a timing IMMEDIATE identico.

| Pesi / Regola | EU CAGR MAIN | USA CAGR MAIN | EU CAGR FULL | USA CAGR FULL | EU MaxDD FULL | USA MaxDD FULL |
|---|---:|---:|---:|---:|---:|---:|
| OLC19 50/50 | 23.20% | 50.77% | 19.76% | 39.48% | -28.61% | -26.12% |
| Consenso unanime 65/35 | 24.37% | 51.05% | 19.89% | 39.21% | -29.23% | -26.54% |
| Logit score FUSION | 22.81% | 51.47% | 19.54% | 39.26% | -28.78% | -26.12% |
| Logit affidabilità | 23.31% | 50.78% | 19.66% | 39.27% | -29.09% | -26.12% |
| Logit selettivo | 23.36% | 50.53% | 19.85% | 39.59% | -28.50% | -26.12% |

Tutti i 40 percorsi (cinque pesi × due timing × EU/USA × due tariffe) sono stati realmente eseguiti con il motore OLC19. La policy 65/35 di puro consenso può apparire leggermente favorevole in EU MAIN, ma è sfavorevole nel 2024/2025 EU e sul FULL USA. Il peso selettivo è quasi 50/50 e porta solo differenze marginali: non ha skill probabilistica aggiuntiva. **Nessuna policy supera il gate preregistrato.**

### Singoli anni critici con ingresso immediato, 0,001

| Mercato, anno | 50/50 | Consenso 65/35 | Affidabilità continua | Affidabilità selettiva |
|---|---:|---:|---:|---:|
| EU 2024 | 22.44% | 19.89% | 21.79% | 22.22% |
| EU 2025 | 17.95% | 14.37% | 17.19% | 17.95% |
| EU 2026* | 16.51% | 15.81% | 16.08% | 16.51% |
| USA 2024 | 78.61% | 79.04% | 80.12% | 78.41% |
| USA 2025 | 13.57% | 16.42% | 13.37% | 14.29% |
| USA 2026* | 62.44% | 53.96% | 60.81% | 63.33% |
*2026 comprende soltanto gennaio–prima apertura di luglio, rendimento cumulato non annualizzato.*

Nel 2024 USA il primo ETF batte il secondo in 10/12 mesi; nel 2025 soltanto 6/12 e nel 2026 2/6. Il modello Reliability attribuisce in media probabilità al primo ETF USA rispettivamente 0,553, 0,627 e 0,620: si trova dalla parte sbagliata quando cambia il regime. Non abbiamo un segnale ex ante che riconosca questa inversione.

### Robustezza a costo legacy 0,003

| Mercato, FULL | HALF | RELIABILITY_P | RELIABILITY_SELECTIVE |
|---|---:|---:|---:|
| EU | 16.18% | 16.06% | 16.25% |
| USA | 31.34% | 31.09% | 31.40% |

## 4. Intervento nel simulatore, NON causalità economica identificata
Il motore OLC19 modifica i pesi delle due posizioni selezionate, tenendo fissi OHLC, selection e contratti stop. Come OLC74, questo fornisce un effetto causale **entro il simulatore, a prezzi esogeni**, ma non stabilisce che il segnale di consenso causi la sovraperformance futura del titolo. Resta inoltre la dipendenza dei prezzi da market impact, fill alle aste e qualità degli adjusted returns, non verificati.

## 5. Informazioni ortogonali: fattibilità delle fonti
Nei 180 eventi (90 per mercato) sono rappresentati 42 ETF EU distinti e 48 ETF USA distinti, quindi un pilot di composizione può concentrarsi sui titoli effettivamente selezionati senza ricostruire per ora l’intera matrice di 314 ETF ogni mese.
- Nelle fonti ZIP originali di OLC74/16/19 non esiste un archivio verificato di composizioni/valutazioni/flussi **point-in-time**. Non abbiamo quindi calcolato overlap, flussi, valutazioni né regressioni con tali dati: sarebbe metodologicamente scorretto retrodatare holdings correnti.
- **Pista iShares USA:** lo scraper open-source di talsan/ishares documenta download mensili e storici di fondi iShares; va verificato ticker per ticker, licenza e data di pubblicazione: https://github.com/talsan/ishares
- **Pista vendor storica per US e UCITS:** ORTEX documenta holdings per data, inclusi ISIN, pesi e i limiti di freschezza dei file del fondo: https://docs.ortex.com/reference/etf_holdings_retrieve ; Intrinio richiede un abbonamento storico e un campo as_of_date: https://docs.intrinio.com/documentation/web_api/get_etf_holdings_v2
- **Pista SEC N-PORT USA:** fondi idonei hanno filing storici; devono essere usati soltanto dopo la data di pubblicazione effettiva, non dalla fine del trimestre di riferimento. La copertura UCITS non è sovrapponibile a quella USA.
Il prossimo test dovrebbe essere anzitutto un **pilot di source coverage** su tutte le coppie selezionate dei mesi 2024, 2025 e gennaio–giugno 2026, con mappatura ticker→ISIN, fonte/issuer, reporting_date, publication_date, age days, report currency e share-class. Se la copertura PIT supera un minimo preregistrato, calcolare overlap delle partecipazioni e differenziali settoriali/fattoriali; non addestrare o ottimizzare un modello usando soltanto gli ETF per cui il dato è disponibile dopo aver visto il target.

## 6. QA, stato e riproduzione
**QA indipendente PASS:** 180 decisioni, 87 label mature EU e 89 USA, 40 replay nativi, 360 calcoli di CAGR/drawdown e 320 rendimenti annuali verificati indipendentemente. B0 HALF IMMEDIATE coincede **bit per bit** su sette matrici con OLC19; HALF DELAY3 e fee=.001/.003 coincidono con OLC74. Le fonti etichettate includono due buchi EU 2020 e il mese finale non osservato 2026, non imputati.

L’implementazione richiede i quattro ZIP originali che sono già nella Library. `prepare_native.py` ripristina le dipendenze OLC19 senza modificarle; `run_olc75.py` ripete modelli e contabilità; `verify_olc75_independent.py` ricalcola le metriche senza importare il motore. I digest sono in `results/OLC75_QA.json` e `MANIFEST.json`. Nessuna nuova esecuzione su agosto–ottobre 2026 è stata effettuata.
**Decisione: OLC75 non promosso.** L’evidenza corrente non giustifica né uno switch 25/75 né una nuova concentrazione 65/35 guidata dall’unanimità. L’informazione necessaria per prevedere il vincitore relativo resta non dimostrata. OLC19 baseline e OLC67 candidato di ricerca invariati.