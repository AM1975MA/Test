# OLC43/E2 — Nuovi CAGR su EU e USA ampliati (3 novembre 2026)

**Stato: completato — ricerca esplorativa, NON promuovere.** Risultati riprodotti localmente con lo **stesso motore economico** di OLC19 FAST_LOCK3 e dati quote nuove osservati; la regola con cui si assegnano i **nuovi ETF** è un *challenger semplice per momentum*, **non il ranking nativo OLC19 riaddestrato**. Pertanto nessuno dei CAGR in questa pagina può essere presentato come `OLC19 expanded native`. Nessun file di produzione modificato.

## Risultati principali: 2021–2024, fee legacy .001 e stop friction .001

| Metrica | EU originale | EU + nuovi, MOM63 | EU + nuovi, MOM63+126 | USA originale | USA + nuovi, MOM63 | USA + nuovi, MOM63+126 |
|---|---:|---:|---:|---:|---:|---:|
| **CAGR %** | **23.1999** | **13.7614** | **14.6647** | **50.7722** | **39.5703** | **36.7213** |
| Max DD % | −28.6084 | −34.2946 | −31.1183 | −20.2260 | −18.6849 | −20.3890 |
| Turnover annuo (×) | 12.410 | 13.083 | 12.689 | 23.317 | 22.235 | 22.492 |
| Stop | 10 | 11 | 10 | 40 | 39 | 40 |

**Rispetto all'originale il CAGR EU scende di −9.44 pp (MOM63) e −8.54 pp (MOM63+126); quello USA di −11.20 pp e −14.05 pp.** Ampliamento non promosso. Tutti i numeri sono **CAGR economici simulati**, non i massimi opportunistici ex-post dell'E1.

### Stress commissione 0.003 (frizione stop 0.001)

| Strategia | EU CAGR % | USA CAGR % |
|---|---:|---:|
| OLC19 congelato | 19.8841 | 42.7325 |
| MOM63 | 10.5252 | 32.4015 |
| MOM63+126 | 11.5148 | 29.6025 |

### Febbraio 2019–1 luglio 2026, costo .001

| Strategia | EU CAGR % | EU MaxDD % | USA CAGR % | USA MaxDD % |
|---|---:|---:|---:|---:|
| OLC19 congelato | 19.7635 | −28.6084 | 39.4845 | −26.1202 |
| MOM63 | 18.9081 | −34.2946 | 43.0883 | −28.2442 |
| MOM63+126 | 16.4467 | −31.1184 | 40.4906 | −28.8247 |

La variante MOM63 su USA cresce nel *FULL* ma peggiora sul periodo principale 2021–24: esito fortemente **dipendente dal calendario**, non generalizzabile e con drawdown FULL peggiore. Non selezionare la variante in base al solo massimo FULL.

## Perché fallisce la sostituzione semplice

La regola non *predice il futuro*: usa log-rendimento cumulato passato su 63 e 126 sedute, calcolato soltanto fino alla **chiusura precedente** all'apertura di trading. Richiede almeno 500 Open effettivamente osservati nella storia del candidato e almeno 120/126 e 60/63 presenze nel periodo per i prezzi. Mantiene il primo titolo del Top2 originale, sostituisce soltanto il secondo, nominalmente 50/50:
- `MOM63`: candidato con 63d positivo e superiore al massimo 63d dei due titoli originali di `0.05` in log-rendimento;
- `MOM63_126`: entrambi 63d e 126d positivi e media dei due rendimenti superiore alla media migliore dei due originali di `0.05`.
Soglie dichiarate prima di leggere questi CAGR. Nessun grid-search successivo.

Nel 2021–24 gli interventi distinti:
- EU: 21/48 mesi MOM63; 17/48 mesi MOM63+126;
- USA: 24/48 mesi MOM63; 23/48 mesi MOM63+126.
Per la coppia nuovo-vs-secondo originale, sui mesi con switch il differenziale **futuro Open→Open** medio in **log-bp** è:
- EU MOM63 **−301.20 bp** (positivo 10/21); EU confermato **−524.70 bp** (positivo 4/17).
- USA MOM63 **−313.45 bp** (positivo 8/24); USA confermato **−353.99 bp** (positivo 9/23).

E1 aveva mostrato **12/48** mesi EU con un ETF aggiunto come miglior titolo ex-post (USA 2/48); la variante MOM63 cattura soltanto **2** di tali 12 vincitori EU, mentre MOM63+126 ne cattura 2. Allargare il set non basta: il filtro di ammissibilità economica degli ETF nuovi deve essere **nativo allo score predittivo**, non un semplice confronto di momentum. Le statistiche sono retrospettive e non costituiscono una prova di quali nuove feature sfruttare.

## Dati e controlli

**Input originale:** Library `OLC19_Rischio_Rientro_Checkpoint_20261102.zip` (contiene source, q-state, market data, target, rischio e percorsi di riferimento per EU165 / USA149), preservato senza modifiche. Elaborazione in ambiente locale Python con gli stessi `combined_engine.simulate` e `portfolio_metrics_parent.metrics` del checkpoint.

**Identità rigorosa** su `ORIGINAL` per entrambi i mercati e tutti e sei gli array principali rispetto all'NPZ ufficiale: `nav`, `ledger`, `primary_units`, `defensive_units`, `free_cash`, `targets`; massimo errore numerico **0.0**. I CAGR 23.1999178% EU e 50.7722090% USA e il numero di stop corrispondono a OLC19.

**Input nuovi:** serie adjusted OHLC di Yahoo via yfinance, snapshot dalla GitHub Action [41724810594](https://github.com/AM1975MA/Test/actions/runs/41724810594) con `candidate_daily/` negli artifact; quote osservate 2017-01→2026-07. Il controllo di vintage [41723201482](https://github.com/AM1975MA/Test/actions/runs/41723201482) confronta 192 rendimenti originali `QDVE.DE, VVSM.DE, SMH, UNG`: nessuna differenza assoluta >50bp. Rimane storico ex-post rettificato, **non certificazione broker-grade**.

**Candidati effettivamente inclusi nei replay:** EU `G2X.DE` (minatori d'oro), `USPY.DE` (cyber), `WTIC.DE` (commodity), `2B76.DE` (robotica). USA `BOTZ`, `LIT`, `PAVE`. Il candidato `CMOD.MI` fu ammesso nel test *oracolo Open→Open E1* ma è **escluso dall'E2 con stop**: riscontrati **539/2400** giorni con OHLC intrinsecamente incoerente (129/1019 nel 2021–24); nessuna manipolazione High/Low o stop fittizio autorizzata. La popolazione E2 è quindi EU165+4 vs USA149+3, **non EU165+5**.

Nuovi ETF non erano modellati nel gate V6 storico: `g` e `alt` sono stati mantenuti congelati agli input originali OLC19, mentre i nuovi prezzi e la nuova composizione entrano nel motore FAST_LOCK3 e nel calcolo dei margini/rischio sistemico. Di conseguenza questo è un *shadow portfolio challenger*, non un port completo del classificatore, V6 e ranking originali. Serie mancanti in sede diversa vengono marcate `observed=false`; si valorizza con l'ultima quota osservata senza negoziare quote nuove in date mancanti.

**Costi:** coefficiente OLC19 legacy .001/.003 sul turnover mezzo L1 e frizione stop .001; non spread e fill live. Conserva quota iniziale, periodo, capitale composto e risk-off OLC19 per tutti gli arm.

## Validità e passo successivo

Gli anni **2019–2026 sono già stati esplorati ampiamente** nei test precedenti; la prova qui è una falsificazione retrospettiva di due challenger predefiniti, NON una nuova validazione vergine. I dati dei nuovi fondi sono quelli attuali con prezzi rettificati, non un pannello di ETF point-in-time completo comprensivo di delisting.

**Decisione: NESSUNA PROMOZIONE; mantenere OLC19 originario a 23.20% EU / 50.77% USA nel periodo principale.** Per ottenere una valutazione attendibile dell'estensione serve portare i nuovi ETF nella **catena di feature e score originali**, con walk-forward e nuovi input coerenti con il warm-up, confrontare pari esecuzione e validare prospetticamente prima del deployment. Il più alto oracle E1 non è convertibile in CAGR predicibile mediante sola regola di momentum.

Riferimenti dati: `E2_SCORECARD.csv` nello stesso ramo; `run_olc19_expansion_replay.py` e suoi output (decision log, annualità, NAV, manifest) conservati anche nel pacchetto di ricerca della Library/archivio allegato; report fonte OLC19 `/ETF_Research`.
