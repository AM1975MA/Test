# OASIS149 — G5 forecast del rischio delle singole posizioni, protocollo FROZEN prima della prima Action
18 ottobre 2026. Universi: SOLO esatti `evidence_v1/data/original149`, R2 sei classi originali nel file immutabile `oasis149/results/R2_ONE_PER_GROUP_EQUAL.csv`, CBOE five official indexes in `oasis149/cboe_g4b/results/source/`.

**Ipotesi primaria distinta da G4b.** G4b CBOE predictor paired switching ha FALLITO il Brier gate: non va usato come trading alpha. Un indice di implied volatility può però avere informazione sulla distribuzione di rischio forward, non sulla direzione/rendimento relativo. Testare SOLO validità di una varianza as-of ex ante, non rendimento o switch.

Per ogni *ancora NON sovrapposta di 21 sedute* 2021-2026 (64), congelare una istantanea delle SEI posizioni effettivamente detenute nel R2 (una per ciascuna delle sei macro classi) al primo Open. Su 21 sedute successive, etichetta `RV21=sum_{k=1..21} log(Open_{t+k}/Open_{t+k-1})²` per singolo ETF, non volatilità di una strategia ribilanciata. Le etichette diventano disponibili solo al Close del giorno di fine orizzonte; per rigore fit ogni model ratio da anchor finiti strettamente prima della data del nuovo segnale.

Previsioni FROZEN, tutte non negative e >1e-9, nessun rendimento futuro nelle feature:
- K0: somma prevista RV21 da media quadratica dei rendimenti Open-to-Open dei precedenti 63 giorni `21*mean(r²)`.
- K1: precedente 126d EWMA `lambda=.97` del rendimento squared giornaliero, `21*EWMA(r²)`.
- K2: volatilità ATM options pubblicata CBOE as-of con margine 7 gg calendario; `21/252*(IV/100)^2`, calibrata con *mediana* del rapporto `observed RV21 / IV forecast` dei soli precedenti eventi maturati PER macro categoria, clip [.10,10]. Fonte opzioni mappata per C01/C02/C03=VIX, C04=VXEEM, C06=media geometrica OVX e GVZ. La categoria C05 bond/cash **non ha** opzioni obbligazionarie adeguate tra questi dati: K2 e K3 NON EVALUABLE per C05, MAI simularla con VIX.
- K3: combinazione senza fit `sqrt(K0*K2)` dei due stimatori nei 5 gruppi mappati.

GATE di qualità informativa, nessun trading:
Scoring primario su 5 categorie mappate e 64 anchor = 320 righe: QLIKE = `realized/pred - log(realized/pred) - 1` (minimo 0, più basso migliore), più MSE log-RV e rapporto calibrato predicted/actual. Studentizzazione bootstrap 1500 round, blocchi circolari di 3 anchor/63 sedute e **unità di resampling=anchor**, non 320 campioni indipendenti. K2/K3 migliorano K0 e K1 in QLIKE aggregata, CI 95% per riduzione vs K0 positiva, QLIKE migliore in entrambe 2021–23 e 2024–26; altrimenti FAIL. Report per categoria, per epoca, e risultato particolare sui gap di shock; no param grid. Per C05 valutare solo K0/K1 e riportare non mappata.
I dati CBOE fanno riferimento a volatilità implicita, con premio assicurativo/correlation skew, quindi non sono direttamente previsioni imparziali di volatilità realizzata; la calibrazione maturity-only mira a provare o falsificare contributo rispetto a EWMA.

I risultati di G5 NON autorizzano uscita o gestione cash: servirà un vero expected-shortfall/scenario condizionato per portafoglio e correlazione di coda, con test proporzionale di esposizione vs benchmark passivo. Dati URL CBOE e universi storici restano NON PIT-certificati per delisting/spread; valutazione 2017–2026 già esplorata e non nuovo holdout. Salvare 384 previsioni/etichette, sorgenti hash, QLIKE, CI, esito nel repo branch indipendente. `etf_trader` intatto.
