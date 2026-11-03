# OLC33 — Condizioni *ex ante* per vantaggi economici estremi (preregistrazione)

**Data di congelamento:** 2026-11-03. **Questo file viene pubblicato PRIMA di leggere le etichette economiche OLC33 e di eseguire il test OLC33.** Esperimento nuovo, non ritaratura post-hoc di OLC32.

**Repository / base:** `AM1975MA/Test`, branch `research/olc32-quote-repair-economic-edge-20261103`, commit OLC32 `3717924ef11e58263961d0c98a0b806976a3c8fb`. `main` e portafogli/backtest originali invariati.

**Input congelato:** OLC32_RESULTS.zip (Library) SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d`; `results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz` SHA256 `83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16`. Secondo archivio opzionale per parità, `PREQUENTIAL_DIRECT_ECONOMIC_EDGE.csv.gz` SHA256 `89781f1351b50e9d30bdb98c3146053117d0288f1ff833c18a6d2aabcaaf5a1b`. Unità = ETF mensile, EU165 e USA149, 2019-06/2026-06; periodo primario 2021–2024. Tutte le statistiche sono retrospettive e soggette a ricerca pregressa sugli stessi anni.

## Domanda e ipotesi (fissate prima di esiti OLC33)

H0: a parità di calendario e disponibilità delle feature, le condizioni osservabili prima dell'ordine **non discriminano con utilità economica** il caso in cui un'alternativa AUTH Top2–Top5 supererà il leader AUTH Top1 del mese seguente con vantaggio *netto ipotetico* >=300bp. Modello nullo = frequenza storica dell'evento disponibile all'inizio dell'anno.

H1: un modello **lineare classificatore regolarizzato**, con pochi contrasti causali fra candidato e incumbent, individua una sottopopolazione più favorevole ai grandi vantaggi, senza aumento non compensato dei grandi svantaggi. Non si cerca di predire tutti gli ETF o aumentare la complessità del regressore.

## Popolazione e definizioni non negoziabili

- Per ogni mercato e segnale t, incumbent = `auth_rank==1`; quattro sfidanti = `auth_rank` in 2,3,4,5. Esattamente una previsione probabilistica per sfidante per data, costruita con le feature note a `signal_date`.
- Guadagno `spread_bp = challenger.r_o2o_bp - incumbent.r_o2o_bp`, con etichette Open→Open OLC32 corrette; costo *ipotetico e fisso* di 20bp per un'azione di sostituzione; `net_spread_bp = spread_bp - 20`. `Y_plus = 1` se `net_spread_bp >= 300`, altrimenti 0. Evento avverso `Y_minus = 1` se `net_spread_bp <= -300`, misurato ma NON usato per scegliere soglie.
- `eligible_label` vero per entrambi + Open valido osservato per EU; per USA è solo prepared, **mai certificato raw**. Tutte le righe di calendario, le date di maturazione, la qualità >=70%, e il missing LEEU rimangono invariati. Non usare `r_o2o_bp`, `r_rel_bp`, `month_median_bp`, `label_valid`, `eligible_label`, `exit_date` come feature o filtro per emettere il segnale. Sono consentiti solo come target e nella valutazione dopo la maturazione.
- Righe senza feature numeriche finite e `feature_available_asof` valido: niente switch (fallback deterministico Top1), non imputare. Nessun ticker ID, mercato ID o label futuro nelle feature. Segmentazioni fra mercati SOLO per la valutazione.
- Calcolo feature da tutti e soli i Top5 AUTH con valori numerici disponibili al segnale; se il leader non è completo, nessuna decisione di switch per quel mese. Fonte `source_date <= signal_date`; controllo duplicati e ordinamento.

## Score fissato, senza tuning

12 feature numeriche ex-ante per ogni sfidante (differenze sfidante meno incumbent, o valore cross-sectional contemporaneo): 
1. `d_FUSION`;
2. `d_ret_21`;
3. `d_ret_63`;
4. `d_ret_126`;
5. `d_ret_252`;
6. `d_dd_63`;
7. `d_vol_63`;
8. `d_eff_63`;
9. `d_sma_ratio_200`;
10. `d_acc_21_63`;
11. `top5_dispersion_ret63` (deviazione std popolazione cross-sectional dei primi cinque, calcolata prima del trade);
12. `leader_ret63`.
Non è consentito scartare feature in funzione degli esiti: si usa esclusivamente supporto finito fissato. Nessun altro predittore.

**Modello P1:** `StandardScaler()` + `LogisticRegression(C=0.1, max_iter=1000, solver="lbfgs", random_state=33001)`, un unico classificatore pooled EU/USA. Peso per riga = 1/(numero di sfidanti validi del mercato-mese), normalizzato per dare peso totale eguale ai due mercati nel training; senza `class_weight`. Il modello nullo P0 predice la frequenza positiva pesata del SOLO train. Se un train ha meno di 12 mesi maturi per mercato, meno di 20 positivi complessivi o una sola classe, P1 non viene stimato: fallback P0 e segnalazione esplicita.

**Causalità:** fit una volta per anno `Y in 2021..2026` con soli eventi aventi `exit_date < Y-01-01`; predire ogni data di quell'anno senza retraining. Nessuno split random, né train sui segnali di 2021–2024 valutati prima del loro exit. Il 2019–2020 è solo inizializzazione. 2025–2026 solo diagnosi secondaria, mai per promozione retroattiva.

## Decision rule fissata prima del test

- Per ogni mercato/mese se P1 disponibile, seleziona come unico sfidante quello con massima `P1(Y_plus)` fra rank 2..5 con feature complete (tie-break: `auth_rank` crescente, ticker alfabetico); **in assenza di P1/feature complete, resta Top1**.
- Esegui lo switch solo se `P1 >= 0.40` E `P1 - P0 >= 0.10` E tutti i controlli temporali sono passati. Nessun tuning delle soglie sull'outcome; zero switch è un risultato valido. Non fare altri switch durante il mese.
- Costo fisso 20bp sul mese di switch, zero quando Top1; per favore notare: **approssimazione diagnostica**, non un backtest bid/ask, tasse, liquidità o close/open realmente eseguibile.

## Metriche e gate di successo (PRIMARIE 2021–2024)

Per ciascuno di EU e USA, reportare tutti i denominatori (mesi, mesi con incumbent valido, challenger validi, azioni e positivi):
1. **Discriminazione:** Brier score pesato/macro-mensile P1 **inferiore** a P0 (in entrambi i mercati), con AUCPR e affidabilità per bins solo descrittivi.
2. **Precisione conditional event:** tra le decisioni attivate, `Precision(Y_plus)` >= 1.5 × frequenza Y_plus delle alternative non selezionate in TUTTI i mesi valutabili nel medesimo mercato; almeno **12 mesi azionati per mercato** per evitare conclusioni da pochi episodi.
3. **Utilità economica:** spread incrementale medio su TUTTI i mesi valutabili dopo il costo >0bp in entrambi i mercati e intervallo bootstrap **joint** a blocchi contigui di 6 mesi, 2000 campioni, seed=33001, limite inferiore al 95% >0 per la media EU+USA. Reporting anche di quota di azioni con spread netto <=-300bp, peggior mese, mediana, turnover e differenza cumulativa/log rispetto a Top1. Nessuna affermazione di CAGR/strategia live.
4. **Rischio coda:** su mesi azionati, frequenza di `Y_minus` non maggiore della frequenza alternativa in tutto il campione valutabile per entrambi i mercati. Se numero azioni insufficienti il gate FALLISCE, non si abbassa la soglia.

**Regola di arresto:** se qualsiasi gate primario fallisce o audit fallisce, STOP: nessuna ricerca su soglie, architetture o subset ex post, nessuna promozione a Top2, nessun backtest operativo. Il 2025/26 è illustrativo, non un secondo tentativo. Se tutti passano, solo allora PREREGISTRARE un successivo replay indipendente con costi, rischio, disponibilità e dato truly point-in-time; non implementarlo qui.

## Collaudo preregistrato

- SHA256 invariato input, unico (market, signal_date, ticker), `source_date <= signal_date`, maturazione del target, EU quote maschere, no 2026-06 terminal pseudo-zero e audit calendario EU 2020, missing `LEEU.DE`.
- Controllare che modifiche simulate ai return futuri dopo la data di training NON cambino modello/forecast precedenti; confronto di parità etichette/Top5 e previsione dei missing.
- Salvare codice, file dei fit annuali o coefficienti, predizioni OOF, decisioni/mancati switch, metriche mensili e per mercato, bootstrap, rapporti esiti positivi **e negativi**, SHA256, seed e ambiente. Non sovrascrivere né rinominare gli artefatti OLC32.
