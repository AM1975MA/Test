# OLC61 — Protocollo preregistrato: target economico e persistenza appresi nelle 42 feature native

**7 novembre 2026 — PRIMA DELLA PRIMA ESECUZIONE DEGLI OUTCOME OLC61.** Laboratorio isolato. Nessuna modifica al ranking operativo, a OLC19 o a `main`. Nessuna ricerca di fonti esterne. Tutte le finestre storiche 2019–2026 sono state ampiamente studiate: i risultati non sono conferma OOS indipendente.

## Quesito

Un *learner a monte*, addestrato direttamente sulle 42 feature native originarie OLC14/11 senza usare score FUSION come input, riesce a selezionare Top2 economicamente migliori e più persistenti rispetto al Top2 nativo e al **riferimento più severo della fusione originale**? Non applicare alcun correttore finale, bonus momentum, gate o timing.

## Fonti e cutoffs

- **OLC14 Heads** zip SHA256 `a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458`: `annual/{EU,USA}_{year}.joblib`, matrici X e XP e chiavi, `*_LAYER_LABELS.csv.gz` di etichette storiche. Le 42 colonne originali restano identiche.
- **OLC14 Results** zip SHA256 `4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1`: `*_MEAN3_SCORES.csv.gz` con `ORIGINAL_CURRENT` (B0_NATIVE) e `ORIGINAL_FUSION` (B0_FUSION_CONTEXT). Stesso supporto di ticker e date per tutti i metodi.
- Un refit per mercato × anno 2021–2025, training expanding su SOLI gruppi mensili con `exit_date_63 < 1 gennaio anno fitting`. Non usare alcun `fwd_ret` futuro come feature; etichette future usate esclusivamente per addestramento su gruppi **interamente maturi** e per diagnostica ex-post delle predizioni successive. Comparazione primaria EU/USA 48 mesi 2021–2024; 2025 soltanto verifica di fragilità (non holdout vergine). 2026 escluso.

## Target e modellazione fissi (3 candidati; niente grid)

Per ogni ETF e segnale (tutti i membri del mese, con etichette mature), due **periodi disgiunti** di 21 sedute e 21→42 sedute: `l1 = log(1+fwd_ret_21)`, `l2 = log(1+fwd_ret_42)-log(1+fwd_ret_21)`; margini relativi mensili `g1 = 10000*(l1−mediana_j(l1_j))` e `g2 = 10000*(l2−mediana_j(l2_j))`, basis point di log rendimento. Il secondo tratto non coincide con il rendimento 0→42 cumulativo.

Tre **utilità di addestramento** alternative, non sommabili dopo l'esito:

1. `ECON21`: `u = g1` (valore economico del prossimo periodo).
2. `STAY2`: `u = min(g1, g2)` (necessità di vantaggio sia immediato sia nel successivo periodo non sovrapposto).
3. `ECO_STAY`: `u = 0.70*g1 + 0.30*min(g1,g2)` (priorità al mese corrente, premio alla persistenza).

Da ogni `u` si crea un'unica scala di *relevance* intera 0–5 mediante soglie in log-bp `[-300,-100,0,100,300]` applicate identiche ai tre bracci. È una discretizzazione economica fissata prima dei risultati. Il peso crescente (0,1,3,7,15,31) remunera gli elementi di maggiore utilità. Nessuna soglia di negoziazione.

**Stesso learner** per tutti i bracci: LightGBM `LGBMRanker(objective='lambdarank', n_estimators=180, learning_rate=0.04, num_leaves=7, min_child_samples=80, reg_lambda=10, max_bin=127, lambdarank_truncation_level=10, label_gain=[0,1,3,7,15,31], n_jobs=2, deterministic=True, force_col_wise=True, verbosity=-1, random_state=611)`. Gruppi di ranking = mese di segnale ordinato; train X/XP originali e missing native gestiti da LightGBM; nessun ticker-ID, nessuna colonna aggiunta. Punteggi di previsioni Top2 diretti dal learner, senza fusione con il vecchio score. Parità OLC14 dei Top2 con pesi frazionari in caso di pari merito.

## Metriche primarie e promozione

- Top2 **media economica Open→Open** dei rendimenti `r21` e `r42`, su coppia in pari peso (non NAV, non CAGR, nessuno stop). Rendimento relativo `g1` e `g2` su Top2 come metriche ausiliarie.
- Percentuale selezionati Top2 nel quintile migliore `rank21>=.8` e **persistenti** `rank21>=.8 AND rank42>=.8` per comparabilità OLC60; in aggiunta frequenza con `g1>0 AND g2>0` per leadership disgiunta.
- Ranking economico `NDCG@2` contro la vera rilevanza costruita per ciascun metodo, a posteriori; peggioramenti nel 2025 e quota di mesi/anni positivi, impostati già prima dell'esito. Descrittivo upper-bound oracle fuori policy.
- Intervalli di confidenza DESCRITTIVI con block bootstrap 6 mesi per differenze di `r21`, `r42`, `persist_hit` contro B0_FUSION, stesso campione mensile, semi fissi 611; evitare dipendenza falsa da migliaia di ticker.
- **Gate severo**: non considerare nemmeno un replay OLC19 se non c'è miglioramento di `r21` **in ENTRAMBI i mercati rispetto a B0_FUSION**, insieme a non peggioramento della persistenza (Top2 21&42) e del rendimento `r42` in entrambi. Il confronto con B0_NATIVE è diagnostico e non basta. Una miglioria confinata a 2025, a uno dei mercati o a un singolo anno non supera il gate. Nessuna ricerca di ulteriori parametri su questo campione dopo il risultato.

## QA

Hash ZIP, ordine/caratteristiche delle 42 feature identiche, allineamento unico chiavi train/XP, train keys maturate, `g1/g2` calcolati per data e su etichette storicamente complete, nessun lookahead in valutazione o scelta, nessuna perdita di righe/test dovuta al future label, comparazione baselines OLC60 bitwise per Top2, seed e pesi di pari merito, model serialization e riproducibilità previsioni. Reportare ogni differenza. Se fallisce fonte o contratto: nessun CAGR né promozione. 