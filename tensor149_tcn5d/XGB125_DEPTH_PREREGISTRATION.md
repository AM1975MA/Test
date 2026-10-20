# Original149 XGB125 — preregistrazione della profondità alberi (20 ottobre 2026)

Ramo isolato: research/original149-xgb125-depth-sweep-20261020. Produzione immutata.

## Ipotesi
Test controllato dell'impatto di max_depth sul ranker XGBoost originale con **esattamente 125 Compact21 feature**, NO RMT e NO R1/R2. Non confondere max_depth con limite obbligatorio: un albero binario con profondità d ha **al massimo** 2^d foglie, talvolta molte meno per regolarizzazione/min_child_weight.

Profondità predefinite **2,3,4,5,6,7**, foglie massime nominali **4,8,16,32,64,128**. No selezione di altre iperparametri dopo risultati intermedi. Controllo di replicazione: d=4 vs run archivio immutabile **39479754815** (XGB125, RankIC ~.0590978, CAGR netto 15.5726%, MaxDD -41.5696%), incluse Top5 identiche a ogni data e, se deterministico, punteggi numerici.

## Costanti
Frozen dataset Original149 (149 ETF, hash manifesto verificato), segnale close(t), target futuro OPEN(t+1)→OPEN(t+6) percentile cross-sectional, 476 settimane dal 2017 a giugno 2026, controllo maturazione del target e fold annuale expanding purged. Allenamento **giornaliero**, validazione **settimanale** anno precedente, test settimanale; calendario e eligibility della run XGB originale, Top5 long-only equal weight, costo conservativo di 20bp a turnover completo ogni 5 sedute.

XGBRanker objective rank:pairwise, eval_metric rmse, n_estimators=240, learning_rate=.035, subsample=.85, colsample_bytree=.8, min_child_weight=8, reg_lambda=8, reg_alpha=.1, tree_method=hist, n_jobs=2, verbosity=0, random_state=20261020; **max_depth è l'unico parametro che cambia**. Librerie pinned come run precedente (XGBoost 3.1.3).

## Audits
- Tutti gli esperimenti devono coprire identiche 476 date OOS con identical ticker roster, original eligibility mask, target e prezzi disponibili; ogni fold salva modello, hash modello, score per ogni ETF, Top5, NAV daily.
- Registro numero **effettivo** medio e massimo di foglie per albero (non soltanto teorico 2^d), numero alberi, date di maturazione training/validazione.
- La ripetizione d4 riproduce esattamente il baseline XGB125 congelato: se la stessa profondità produce Top5 o risultati diversi, BLOCCARE ogni attribuzione causale alla profondità.
- Audit indipendente RankIC medio globale, RankIC per anno, Top5 oracle overlap, rendimento nominale a 5 sedute, CAGR netto, MaxDD, Sharpe, confronti paired bootstrap circolare a blocchi di 5 settimane sui delta vs d4. Mostrare gli intervalli; attenzione ai confronti multipli tra sei modelli e alla selezione retrospettiva dello storico 2017–2026.
- Selezione del 'vincitore' a posteriori può essere soltanto esplorativa: occorre conferma su dataset cronologico o universo disgiunto realmente mai utilizzato.

**Attenzione**: aumento di capacità può aumentare la memorization dei fattori di rischio/survivorship; RankIC non basta a dimostrare convenienza Top5. Valutare rischio al ribasso e drawdown. Nessun deploy automatico.
