# RMT come feature diretta del Machine Learning — risultati finali Original149 (20 ottobre 2026)

**Stato:** COMPLETO. Tutte le quattro nuove configurazioni XGBoost, confronto A congelato e audit indipendente hanno terminato con successo nel run GitHub Actions **39489526724**. Nessuna modifica in produzione. Il periodo 2017–giugno 2026 è stato ampiamente esplorato in precedenza: questi risultati sono di ricerca retrospettiva, NON evidenza live indipendente.

## Domanda testata
È migliore fornire RMT/PCA direttamente a XGBRanker come feature contemporanee, anziché usarle in un selettore HMM di modelli? Nuove feature calcolate giornalmente **solo** con i 126 rendimenti logaritmici precedenti/incluso il giorno t; controlli di causalità tramite troncamento temporale passati. Due famiglie separate: indicatori globali identici per tutti ETF e quote/ricostruzioni della varianza del singolo ETF; confronto con semplici statistiche di correlazione.

**QA e cache**: action https://github.com/AM1975MA/Test/actions/runs/39489049420 (SUCCESS), 5.680 sedute, 149 ETF, 5.535 sedute RMT globali utilizzabili, 716.550 osservazioni ETF con loadings PCA; checksum cache 8afb27b013646843e5d411499eb947923851b8c73479d8df190be5d997246128. File sorgente rmt_direct_features.py e test_rmt_direct.py. Il primo avvio training 39489266133 fallì esclusivamente per un errore nel percorso della cache scaricata, prima di addestrare; corretto workflow senza alterare feature o iperparametri.

## Protocollo
Baseline A IMMUTABILE: originale XGBRanker 125 feature, run https://github.com/AM1975MA/Test/actions/runs/39479754815 (E_XGB_BASE). Medesima Original149, eligibility originale, 476 settimane OOS, stessi anni/fold training expanding, validazione annuale, maturazione rigorosa target open(t+1) → open(t+6), XGB rank:pairwise 240 alberi, profondità 4 e identici iperparametri, costo per turnover settimanale 20bp su Top5 equal-weight; data annuale portfolio path.

Varianti addizionali B–E (nessun tuning):
- B_RMT_GLOBAL: 125+5 lambda1/trace, lambda2/trace, effective rank normalizzato, delta21 lambda1, delta21 rango.
- C_RMT_ETF: 125+5 |loading PC1|, varianza PC2–4, residuo PC1–4 idiosincratico, delta21 |PC1|, momentum log21 residuo proiezione PC1.
- D_RMT_BOTH: 125+10 sommando B+C.
- E_SIMPLE_CORREL: 125+5 media/dispersione correlazione ETF, corr/beta con SPY, rapporto volatilità vs SPY; controllo non-RMT.

## Risultati completi: 476 decisioni settimanali 2017–giugno 2026

| Modello | Feature | RankIC medio | CAGR netto | MaxDD | Sharpe | Coincidenza con vera Top5 |
|---|---:|---:|---:|---:|---:|---:|
| **A — XGB125** | 125 | **+0.05910** | +15.5726% | −41.5696% | 0.7115 | **10.6723%** |
| B — RMT globale | 130 | +0.03216 | +5.6089% | **−40.0344%** | 0.3485 | 9.3697% |
| C — RMT individuale | 130 | +0.05659 | **+15.9691%** | −45.7546% | **0.7161** | 10.5042% |
| D — RMT globale + ETF | 135 | +0.05513 | +10.7125% | −44.2547% | 0.5232 | 9.8319% |
| E — sole correlazioni tradizionali | 130 | +0.05770 | +11.3514% | −40.9953% | 0.5415 | 10.2941% |

**Nessuna variante migliora il RankIC globale** rispetto ad A, e nessuna migliora stabilmente il compromesso rendimento/drawdown. C ha CAGR maggiore di soli +0.3965 punti percentuali annui, ma MaxDD peggiora di **4.185 punti** ed il RankIC scende.

## Confronto statistico indipendente (registrato, same 476 dates e stesso ETF eligible)

Workflow principale incluse *independent_audit* verde: https://github.com/AM1975MA/Test/actions/runs/39489526724 , artifact original149-rmt-direct-xgb-476week-independent-comparison.
Ci accoppiamo sempre alla stessa settimana; bootstrap circolare a blocchi di 5 settimane, 2000 estrazioni, IC 95% descrittivi, NON aggiustati per multipli esperimenti o ricerca precedente.

| Nuova variante vs A | Delta RankIC [IC95%] | Delta rendimento medio Top5 a 5 sedute in punti percentuali [IC95%] |
|---|---|---|
| B globale | **−0.02694 [−0.04630, −0.00909]** | **−0.18364 [−0.35816, −0.02011] pp** |
| C ETF | −0.00251 [−0.00870, +0.00365] | +0.00369 [−0.13341, +0.13136] pp |
| D complessiva | −0.00397 [−0.01044, +0.00235] | −0.08291 [−0.24103, +0.07383] pp |
| E correlazioni | −0.00139 [−0.00843, +0.00625] | −0.07150 [−0.22433, +0.07772] pp |

Coincidenza Top5 rispetto a baseline (percentuali):
B 9.37%, C 10.50%, D 9.83%, E 10.29%, contro base 10.67%. Nessuna variante incrementa sensibilmente Top5 oracle overlap. In B la perdita di RankIC e ritorni medi OOS sono più consistenti dell'incertezza campionaria descrittiva, ma non equivale a significatività futura prospectiva dati i molteplici test.

## Interpretazione / decisione

1. **Ipotesi RMT globale da sola respinta in questa configurazione XGB**: un calo medio netto di RankIC e di CAGR, contro la speranza che il modello interpretasse automaticamente lo stato di correlazione.
2. **RMT individuale resta una pista tecnica interessante ma non dimostrata**: modello C quasi pari A per rendimento e RankIC, CAGR lievemente superiore ma DD peggiore. Non sono risultati per dichiarare efficacia statistica.
3. **RMT completa D** inferiore alla sola C: più feature non significano più segnale.
4. **Statistiche semplici E** non ottengono miglioramento né permettono di attribuire vantaggio unico a RMT. Non fare selezione opportunistica di alcune feature con dati già esplorati.
5. Il risultato negativo del gate HMM/RMT precedente e questo risultato negativo diretto RMT sono due verifiche distinte. In nessuna delle due RMT ha dimostrato l'incremento predittivo desiderato.
6. Non promuovere modifiche in produzione. Mantenere XGBoost125 come migliore configurazione di questo ciclo, ma non superiorità live garantita rispetto a MOM21; MaxDD storico rimane alto.

**Limiti rilevanti**: 149 ETF scelti retrospettivamente (survivorship e tassonomia), Yahoo OHLCV adjusted opens non completamente eseguibili live, costi semplificati, esempi train giornalieri target5 sovrapposti, ipotesi post-mining intensivo dello storico 2017–26; bootstrap descrittivo, non vera indipendenza. Primo step più rigoroso in eventuale prosecuzione: nuovi dati/universo disgiunto e revisione della rappresentazione dei fattori su periodo non utilizzato; evitare ulteriore esplorazione della medesima OOS come se fosse una conferma pulita.

## Sorgenti e audit salvati
- Preregistrazione: tensor149_tcn5d/RMT_DIRECT_PREREGISTRATION.md
- PCA / feature cache: tensor149_tcn5d/rmt_direct_features.py, test_rmt_direct.py
- XGB expanding-WF: tensor149_tcn5d/rmt_direct_run.py
- Comparazione indipendente: tensor149_tcn5d/compare_rmt_direct.py
- 4 archivi per variante, modelli annuali e score ETF, rapporti per anno, bootstrap: GitHub Actions https://github.com/AM1975MA/Test/actions/runs/39489526724 .
