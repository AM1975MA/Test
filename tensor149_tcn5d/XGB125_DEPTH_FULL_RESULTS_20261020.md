# Original149 XGBoost125 — test completo delle foglie, 20 ottobre 2026

**Esito: COMPLETATO E CONTROLLATO.** Ricerca esclusivamente su `research/original149-xgb125-depth-sweep-20261020`, nessun rilascio in produzione.

## Protocollo bloccato prima dei risultati

- 149 ETF Original149 con roster e dati congelati; 125 feature originali Compact21, **nessuna** RMT, R1 o R2.
- XGBRanker objective rank:pairwise, n_estimators 240, learning rate .035, colsample_bytree .8, subsample .85, min_child_weight 8, alpha .1, lambda 8, hist, seed 20261020, XGBoost 3.1.3. L'**unica** variabile modificata è max_depth 2,3,4,5,6,7, corrispondenti a 4,8,16,32,64,128 foglie teoriche massime per albero.
- 476 date originarie settimanali 2017–giugno 2026, expanding annuale, training su sedute giornaliere con label maturate prima del fold, previous-year validation, target percentile del rendimento futuro Open(t+1)→Open(t+6). Long Top5 equal-weight con costo 20bp roundtrip completo, NAV giornaliera.

## Risultati walk-forward 476 settimane

| Profondità | Massimo foglie | Foglie reali medie/albero (media fold annuali) | RankIC | CAGR netto | MaxDD | Sharpe | Top5 oracle overlap |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2 | 4 | 4.00 | **+0.06789** | +6.31% | -41.94% | .3667 | 5.88% |
| 3 | 8 | 7.97 | +0.06373 | **+17.48%** | -43.58% | **.7648** | 9.33% |
| 4 (baseline) | 16 | 15.67 | +0.05910 | +15.57% | **-41.57%** | .7115 | 10.67% |
| 5 | 32 | 29.79 | +0.05342 | +10.38% | -42.92% | .5141 | 11.47% |
| 6 | 64 | 55.57 | +0.03865 | +8.17% | -42.59% | .4418 | 11.89% |
| 7 | 128 | 98.29 (maximum observed 127) | +0.03594 | +4.37% | -46.97% | .2959 | **12.35%** |

**Osservazioni principali**
- RankIC globale *decresce strettamente* al crescere delle foglie teoriche nei sei test. Tuttavia il rendimento netto cresce da 4 a 8 foglie, raggiunge un massimo locale a 8, poi cala. Le 4 foglie hanno il RankIC più alto (+0.06789) ma rendimento relativamente basso e il peggior True-Top5 overlap (5.88%).
- Il vero Top5 overlap *cresce strettamente* da 5.88% a 12.35% aumentando la profondità da 2 a 7; quindi i modelli grandi intercettano più frequentemente almeno una vera Top5, ma non selezionano necessariamente ETF con rendimenti mediamente maggiori. Global IC, Top5 overlap e PnL sono obiettivi DISTINTI.
- Il miglior CAGR (+17.48%) e Sharpe (.7648) è depth3 (8 foglie max) rispetto al vecchio depth4 (CAGR +15.57%, Sharpe .7115), ma il MaxDD depth3 è peggiore, −43.58% contro −41.57%, e il guadagno settimanale è statisticamente incerto. **Non promuovere depth3 automaticamente**.
- Le medie effettive delle foglie dimostrano che la regolarizzazione non rende tutti gli alberi della stessa dimensione: profondità7 usa quasi 100 foglie/albero in media, profondità3 quasi tutte le 8 foglie. Il calo di RankIC alle profondità elevate non è una questione nominale.

## Audit indipendente, perfetta riproduzione depth4

Esecuzione sei modelli (SUCCESS): https://github.com/AM1975MA/Test/actions/runs/39492170319  
Audit statistico separato (SUCCESS): https://github.com/AM1975MA/Test/actions/runs/39494038161

L'audit conferma identità dei 149 ticker e della maschera di eligibility, 476 date e label, e soprattutto replica del modello depth4 **bit-per-bit sui punteggi archiviati**: massimo scostamento assoluto pred_score = **0**, 70.924 osservazioni ETF-data, 476 portfolio Top5 perfettamente identici, RankIC e CAGR identici. Nessuna differenza dovuta a codice, ambiente o costruzione dati.

### Intervalli di incertezza rispetto al baseline depth4 (16 foglie)

Bootstrap circolare a blocchi di 5 settimane, 2.400 replicazioni, date abbinate (non corretto per molteplici confronti e storico già ampiamente esplorato).

| Foglie max | Delta medio RankIC [IC 95%] | Delta overlap vera Top5 in punti percentuali [IC 95%] | Delta rendimento medio Top5 ogni 5 sedute in punti percentuali [IC 95%] |
|---|---|---|---|
| 4 | +.00880 [−.00138,+.01977] | −4.790 [−6.134,−3.445] | −.16688 [−.32747,−.01334] |
| 8 | +.00463 [−.00070,+.00970] | −1.345 [−2.479,−.168] | +.03096 [−.12187,+.21553] |
| 32 | −.00568 [−.01153,+.00006] | +.798 [−.588,+2.185] | −.09146 [−.24414,+.06624] |
| 64 | −.02045 [−.03275,−.00927] | +1.218 [−.294,+2.689] | −.13171 [−.31180,+.04111] |
| 128 | −.02316 [−.03903,−.00833] | +1.681 [+ .168,+3.319] | −.19760 [−.38634,−.00091] |

**Interpretazione inferenziale:** d2 e d3 hanno IC punti maggiore, ma IC95% del delta RankIC include zero. d6 e d7 hanno delta RankIC negativo con intervalli interamente negativi. Il modesto vantaggio economico nominale d3 ha un IC95% che include zero, perciò il maggior CAGR storico non basta a provarne un margine stabile. d7 ha un overlap Top5 superiore ma rendimento medio nominale inferiore. Gli intervalli non sono validazione veramente indipendente in presenza di data mining del 2017–26.

## Indicazione per la ricerca successiva

**Non aumentare ulteriormente le foglie solo per cercare RankIC**: in questo XGB125 la capacità globale di ranking è massima con i modelli più semplici; d3 è il miglior CAGR e Sharpe storico, ma d4 il miglior MaxDD. Non c'è un optimum multidimensionale unico.

L'ipotesi da verificare in un NUOVO studio, preferibilmente con universo/time holdout non ancora ottimizzato: separare modello di ordinamento generale (d2–d3) dal selettore della Top5 (d4–d7) oppure introdurre metriche economicamente orientate alle code del ranking, evitando un ensemble ottimizzato ex post su questo stesso periodo. Prima studiare cosa porta overlap ma riduce payoff medio (esposizione a code negative, momento macro, concentrazione) e verificare su nuovi dati.

## File e tracciabilità
- protocollo preliminare: tensor149_tcn5d/XGB125_DEPTH_PREREGISTRATION.md
- test isolato: tensor149_tcn5d/xgb125_depth_run.py
- audit indipendente: tensor149_tcn5d/compare_xgb125_depth.py
- archivio 6 × 10 modelli yearly, score ETF, selezioni, NAV: run 39492170319, artefatti original149-xgb125-depth-{2..7}
- audit: run 39494038161, PERFORMANCE.csv, YEARLY_COSTED.csv, REALIZED_LEAF_COUNTS_BY_YEAR.csv, REPORT.json.

**Limiti strutturali**: ETF retrospettivamente selezionati, costi semplificati e dati aggiustati, intervalli bootstrap descrittivi, ripetuto uso dello storico 2017–2026. XGB125 non è un benchmark di eseguibilità live verificata e nessuno dei modelli è stato promosso in produzione.
