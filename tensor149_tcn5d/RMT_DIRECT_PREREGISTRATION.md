# Preregistrazione — RMT direttamente come feature di XGBoost125, Original149
Data: 2026-10-20; ramo: research/original149-rmt-direct-features-20261020. Nessuna produzione.

## Scopo, controllo invariato e protocollo congelato
Testare 5 configurazioni sullo stesso pannello congelato di 149 ETF e 476 date 2017–giugno 2026, prossima entrata open(t+1), uscita open(t+6), ranking di rendimento nominale futuro a 5 sedute, Top5 equal-weight, 20bp costo totale per turnover completo, walkforward expanding annuale con embargo data maturazione, allenamento ogni giorno di mercato, validazione precedente annualità solo su date ogni 5 sedute.
A baseline IMMUTABILE: XGBoost 125 originale nel run 39479754815 (RankIC 0.059097812, CAGR +15.5726%, MaxDD −41.5696%, 476 settimane).
Per B–E tenere esattamente gli stessi hyperparametri XGBRanker rank:pairwise: n_estimators 240, depth4, learning_rate .035, subsample .85, colsample_bytree .8, min_child_weight 8, lambda 8, alpha .1, tree_method hist, random_state 20261020, 2 threads, eval_metric rmse per target percentile continuo. Una configurazione per variante, niente tuning post pilot.

## Famiglie 126 sedute — stati causali disponibili alla chiusura t
B_RMT_GLOBAL = base125 più (5): quota lambda1 e lambda2 della matrice di correlazione126, effective rank normalizzato, variazione a 21 sedute quota lambda1, variazione a 21 sedute effective rank.
C_RMT_ETF = base125 più (5): modulo carico PC1 dell'ETF, quota carichi PC2..PC4, quota non spiegata da PC1..PC4, variazione modulo carico PC1 a 21 sedute, momentum residuo logaritmico 21d dopo sottrazione della componente PC1.
D_RMT_BOTH = base125 + tutte e 10.
E_SIMPLE_CORREL = base125 più (5): media e dispersione dei coefficienti inter-ETF126, correlazione con SPY126, beta SPY126, rapporto volatilità ETF/SPY126. Non RMT.

126 log rendimenti passati includono t e mai t+1. No forward fill, almeno 60 ETF con finestra completa. Autovalori e vettori SVD di Gram 126x126 anche se N>T. Carichi in modulo/quadrato per evitare flip dei segni. Segnali t-21 calcolati solo con il passato. Valori assenti nativamente NaN per XGBoost. No scaler su futuro.

## Gates e controlli
Test troncamento futuro invariato, 149 nominativi/matrice file SHA, dataset e date allineati, etichette coerenti, stessa politica portafoglio, nessuna modifica idoneità base125, registrare checkpoint annuali, scores per ETF, selezioni e curva NAV giornaliera. Pilot 2024–25 SOLO diagnostico, primario tutte 476 settimane; nessun cambio di iperparametri dopo pilot. Comparazione data-accoppiata RankIC medio e per anno, Top5 overlap, rendimento medio settimanale, CAGR netto MaxDD Sharpe. Bootstrap circolare blocchi 5 settimane descrittivo; dataset ampiamente riusato, bias di sopravvivenza. Conferma genuina richiederà nuovi periodi/universi.
