# L11.S1/S2 — sigma shock e filtro di tendenza discendente persistente

22 ottobre 2026; studio locale esplorativo a **cinque panieri**, NON test sui 500, NON promozione in produzione. Il filtro di trend è stato richiesto dall'utente prima della sua valutazione; la variante conservativa solo-nuovi-acquisti è stata esaminata dopo aver constatato l'eccesso di falsi positivi della vendita automatica: pertanto considerarla verifica esplorativa, non conferma statistica indipendente.

## Protocollo e provenienza

Originale ETF_TRAINER_V2 full-stack source-only con produttore Hybrid24, smoothing, Top2 dinamico, DD-first, V6 e HighCAGR24, snapshot RAW 149 ETF dal run 39482809691, sorgenti/predizioni Stage19 dal run 39836842157 e NAV originali di riferimento. I cinque panieri canonici pre-selezionati dal CAGR della V2 sono 227, 69, 327, 301 e 220. 2.366 sedute 2017-02–2026-07; commissione originale 10bps. Replay locale di V6 originale verificato con errore assoluto massimo giornaliero **6.04e−14** sul NAV Stage19 dei cinque; il modello originale e i riferimenti V2 e V3 non sono stati modificati. La verifica del riferimento su 500 è già documentata in FS03, ma le **nuove politiche S1/S2 sono testate solo su cinque**.

[Protocollo congelato nel ramo di ricerca prima dei primi outcomes](https://github.com/AM1975MA/Test/blob/research-v3-l11-sigma-shock-reentry-20261022/etf-trader-v3%20corrected/reports/FULLSTACK/20261022_L11S1_ROBUST_SIGMA_SHOCK_REENTRY_PREREG.md).

## Esclusione lenta S2 — singolo criterio esplicito

Alla chiusura *precedente* l'apertura d'esecuzione, l'ETF è considerato in discesa persistente soltanto se: (i) almeno **5 sedute negative nelle ultime 7**, (ii) perdita logaritmica cumulativa degli ultimi 10 giorni <= **−0.8×√10×sigma robusto 21 giorni**, (iii) close precedente < SMA10 precedente. Il sigma robusto è 1.4826×mediana del valore assoluto dei 21 log-rendimenti già completati. Evita il gonfiamento della misura da un singolo outlier estremo. Per riabilitare: almeno **due close consecutive sopra la rispettiva SMA10**, più momentum 5-giorni positivo. In assenza di dati validi la protezione aggiuntiva si astiene.

Per **DOWNTREND_ONLY** il veto liquida anche posizioni già detenute alla successiva apertura (10bps costi originali) e parcheggia in BIL/SHV; per **DOWNTREND_NEW_BUYS_ONLY** vieta soltanto nuovi acquisti, rispettando una posizione ancora detenuta. Il ranker originale sceglie mensilmente gli stessi Top1/Top2; non si forza un nuovo rank3 senza un nuovo protocollo, e la quota esclusa non viene aggiunta all'altro titolo. Il veto può intervenire qualunque giorno, senza attendere la revisione settimanale.

## Shock S1 — definizione fissa

Stop intraday individuale se low attraversa close del giorno prima ×(1−max(6.5%,3.5×max(sigma robusto21,sigma robusto252))). Sigma calcolati su periodi terminati il giorno precedente; mediana delle ampiezze per non contaminare la stima con lo shock. Gap sotto stop eseguito al prezzo effettivo di apertura, altrimenti soglia stop con originale slip 0.1%; nuova commissione originale. Blocco nuovo acquisto dello stesso ETF fino a un recupero di metà della perdita fra chiusura pre-evento e prezzo reale di esecuzione. Gli stop V6 preesistenti restano attivi; zero doppie esecuzioni. Tutti i risultati hanno origine da OHLC; l'ordine intraday dei prezzi non è osservato e rimane un limite della simulazione.

## Backtest sui soli cinque

| Braccio | CAGR medio | MaxDD medio | Δ CAGR vs originale | Δ MaxDD vs originale |
|---|---:|---:|---:|---:|
| ETF_TRAINER_V2 originale | **22.447%** | −33.761% | — | — |
| Solo stop sigma robusto | 19.697% | −34.976% | −2.750 pp | −1.215 pp |
| Trend: vendere posizioni già detenute | 16.707% | −33.776% | −5.740 pp | −0.015 pp |
| Trend: vietare SOLO nuovi acquisti | 18.995% | **−32.681%** | −3.452 pp | +1.080 pp |
| Stop sigma + vendita per trend | 15.853% | −33.583% | −6.594 pp | +0.177 pp |
| Stop sigma + veto soltanto nuovi acquisti | 16.768% | −34.155% | −5.679 pp | −0.394 pp |

Se usiamo il trend solo per i nuovi acquisti, migliora il MaxDD medio di ~1.08pp ma perde ben 3.45pp di CAGR: risultato insufficiente. Nel paniere 69 il DD migliora +6.62pp ma il CAGR scende 3.70pp; nel paniere 227 il CAGR migliora +3.08pp, ma i panieri 301 e 327 perdono rispettivamente 6.71 e 7.74pp di CAGR. Il filtro generalista esclude riprese vincenti. Il sigma-only ha prodotto 31 nuovi stop sui cinque; il blocco+trend non ha dimostrato convessità positiva.

Le misure di turnover riportate dal V6 originale tracciano principalmente ribilanciamenti programmati: il nuovo script conserva anche il nozionale separato degli stop forzati. Il dato economico NAV comprende le commissioni applicate agli stop.

## Diagnosi e decisione

La richiesta è tecnicamente corretta: **anche un trend discendente persistente può deteriorare un ETF senza un singolo giorno oltre soglia sigma**, e un filtro di idoneità al nuovo acquisto è differente da uno stop. Tuttavia l'applicazione cieca a tutti i Top2 sopprime l'alpha della V2 nei rimbalzi, e le soglie fissate non sono un buon modello. Non bisogna retro-ottimizzare queste soglie sui cinque o lanciare 500 test dopo un fallimento dell'esplorazione.

Prossima ipotesi da preregistrare separatamente: applicare il veto **al momento della scelta mensile** e, prima di parcheggiare in strumenti sicuri, verificare se esiste un candidato successivo del **ranking V2 originale nello stesso paniere**, non in declino, con premio predittivo sufficiente e rischio/correlazione inferiore. In alternativa costruire un classificatore cronologico di drawdown idiosincratico e costo del falso veto. Il filtro relativo a mercato/settore serve a distinguere downtrend statistico da ritracciamento di un titolo forte. Queste sono ipotesi non ancora testate qui. Nessuna promozione, 500 rinviato in attesa di un meccanismo migliore.

Codice/test economici e dati della riproduzione locale disponibili in un archivio di studio allegabile dalla sessione corrente: ETF_L11_S1_S2_sigma_e_trend_5_panieri.zip. Per riprodurre servono gli stessi artefatti raw/FS02 citati. La commit sul ramo di ricerca contiene la pre-registrazione S1/S2; questo report conserva anche gli esiti negativi senza alterarli a posteriori.