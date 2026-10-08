# L2-G — risultati: stabilizzazione non lineare con distillazione causale (8 ottobre 2026)

**Esito: COMPLETATO, VERIFICATO, MA DUE CANDIDATI RESPINTI.** Unica repository modificata: `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. `Etf_trader` invariato. Confronto **sperimentale su Original149 già esplorato**, non holdout incontaminato né indicazione di rendimento prospettico.

## Protocollo / provenienza

- [L2-G preregistrazione](L2G_PREREGISTRATION.md), commit `e5161c37dd59e9ee80a720ce8629e1417ef4e945`, anteriore alla lettura degli esiti L2-G.
- Yahoo 3 acquisizioni congelate: GitHub Actions run [37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact `11272972639`, raw ZIP SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`.
- Fonte delle predizioni XGBoost (teacher) e Ridge: rapporto [L2-D](L2D_RESULTS.md) e relativo archivio locale controllato SHA256 `fd4be40a868d8c521122047c83e389351fd7b1c2f865333409d75d4c358c78ad`.
- 149 ETF, 125 feature Compact21 canoniche, 2019-01–2026-06: **90 segnali mensili maturi**. Tre vintage di Yahoo sono tre versioni degli *stessi periodi*, non tre mercati indipendenti.
- **48 fit** = 2 learner × 8 cut-off annuali 2019–2026 × 3 vintage. 40.677 righe di score native e altrettante a common input (includono 2026-07 senza label matura), delle quali **40.230 osservazioni mature** per modello usate nella qualità. Validation [INDEPENDENT_AUDIT.json] del pacchetto allegato: **PASS**; refit indipendente vintage2/2024 riproduce entrambi i modelli entro 8.33e-17.
- Teacher target = score percentile cross-sectionally di **previsioni XGB veramente OOS del passato**; il nuovo student si fitta al 1° gennaio di ogni anno su soli dati con `signal_date < cutoff`, `exit_date_21 < cutoff`, senza teacher attuale o futuro. Non compare BIL come benchmark etichetta (può essere negoziato come ETF normale dell'universo).

## Modelli testati: stessi iperparametri, unica variabile il target

- `HGB_DIRECT`: `SimpleImputer(median, keep_empty_features=True)` + `HistGradientBoostingRegressor(max_iter=120, learning_rate=.05, max_leaf_nodes=7, max_depth=3, min_samples_leaf=100, l2_regularization=10, max_bins=127, early_stopping=False, random_state=42)`, target percentile ritorno O2O reale 21 sedute.
- `HGB_TEACHER50`: identico fit/features/iperparametri/coorte, target **50% percentile ritorno maturato + 50% rank percentile teacher XGB OOS antecedente**.
- Controlli `XGB` source-only canonico e `RIDGE` alpha30, predizioni precedenti L2-D fisse. Nessun fit modificato dopo le metriche.

## Risultati matched su 90 date (media prima sulle 3 vintage per mese)

| Modello | NDCG@5 | Rank IC | Top1 tra Top5 effettivo | Return netto 21 sedute ETF scelto | Top1 exact winner |
|---|---:|---:|---:|---:|---:|
| XGB originale | 0.555209 | 0.065641 | **21.4815%** | **+2.7002%** | **7.0370%** |
| Ridge alpha30 | **0.565574** | **0.106594** | 10.0000% | +2.2410% | 6.6667% |
| HGB_DIRECT | 0.519513 | 0.057895 | 6.6667% | +1.1074% | 1.8519% |
| HGB_TEACHER50 | 0.559551 | 0.063223 | 11.8519% | +1.9505% | 4.4444% |

Il teacher migliora HGB_DIRECT di 0.0400 NDCG, 5.19 pp hit Top5 e 0.84 pp di ritorno medio per decisione. Gli intervalli bootstrap sulle differenze **NON sono conclusivi** (vedere sotto). NDCG migliore di teacher non implica migliore selezione dell'ETF Top1.

## Robustezza training-only: stesso identico input di Repeat2 per tutti i modelli indipendentemente fittati

| Modello | Pairwise Top1 agreement (min–max) | Pairwise mean percentile Rank-MAD (min–max) |
|---|---:|---:|
| XGB | 43.33–60.00% | 0.05135–0.05347 |
| Ridge | **100%** | **0.00082–0.00100** |
| HGB_DIRECT | 65.56–68.89% | 0.04519–0.04640 |
| HGB_TEACHER50 | 64.44–66.67% | 0.03209–0.03815 |

L'ultima variante rende l'intera classifica più stabile di HGB_DIRECT (Rank-MAD), ma NON la singola scelta Top1, su tutte le tre coppie di acquisizioni. Le differenze sono generate soprattutto dal fit, non dal valore dell'input alla predizione. Gate predefiniti: Top1 common-input >=90% **per coppia**, native Rank-MAD <0.01, Top5 realized >=15%, return medio >=Ridge. **Entrambi falliscono tutti i principali requisiti. Non fare tuning ex post.**

## Incertezza statistica: block bootstrap descrittivo, 10.000 repliche, blocchi di 3 mesi

Delle 90 date si calcola prima la media delle tre acquisizioni; gli intervalli a 95% NON sono corretti per test multipli e, soprattutto, **non sostituiscono un holdout nuovo**.

- Teacher50 meno Ridge: rendimento medio `-0.002905` per scelta (−0.291 pp); intervallo `[-0.021628, +0.016997]`; hit Top5 `+0.018519`, intervallo `[-0.048148,+0.088889]`.
- Teacher50 meno XGB: rendimento medio `-0.007496` (−0.750 pp), intervallo `[-0.027221,+0.013208]`; hit Top5 `-0.096296` (−9.63 pp), intervallo `[-0.192593, circa 0]`.
- Teacher50 meno HGB_DIRECT: rendimento `+0.008431` (+0.843 pp), intervallo `[-0.009018,+0.028007]`; NDCG `+0.040039`, intervallo `[-0.007988,+0.090457]`.

**Nessuna prova robusta che la distillazione aumenti i rendimenti Top1 attesi.**

## Econofisica: regimi, dipendenza temporale, code

Segmentazione *diagnostica non operativa*, in HIGH/LOW volatilità recente SPY: rolling annualizzata log-vol 21 sedute, soglia mediana degli **ultimi 36 month-end vol21 precedenti**. 45 mesi high e 45 low, tre acquisizioni ciascuno. Nelle date low-vol, il rendimento 21d medio selezionato dal teacher50 è solo **+0.055%** vs Ridge **+1.410%** e XGB **+2.353%**; nel regime high-vol teacher50 è **+3.846%** vs Ridge **+3.072%** e XGB **+3.048%**. La *differenza osservata* NON autorizza una nuova soglia di switch: questo dataset è stato usato per esplorare il fenomeno e l'incertezza per regime è ampia. Nel 2022 teacher50 realizza +8.6% per decisione, mentre nel 2023 fa -2.0% per decisione; il risultato è molto dipendente dal calendario. Le tre vintage non moltiplicano il numero di mercati osservati.

## Replay economico Top1 coerente, NON strategia completa Hybrid24

Solo **89 periodi mensili contigui**, 2019-02–2026-07. Acquisto OPEN seduta dopo signal date, vendita in occasione del successivo OPEN se cambio ticker; commissioni `0.1%` su capitale negoziato a ogni acquisto/vendita, buy iniziale e liquidazione finale inclusi, **nessun trade terminale fittizio**, nessun governor/stop/basket/MA3. Drawdown calcolato sui **soli saldi mensili**, sottostima plausibile dell'intraperiodo.

| Yahoo repeat | Ridge CAGR proxy | XGB CAGR proxy | HGB_DIRECT CAGR | HGB_TEACHER50 CAGR | Ridge DD | XGB DD | Teacher50 DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 22.22% | 22.28% | 4.39% | **25.57%** | -24.65% | -52.68% | -42.72% |
| 2 | 22.22% | 23.31% | 11.52% | **23.63%** | -24.65% | -41.88% | -43.94% |
| 3 | 22.22% | **33.91%** | 7.39% | 15.26% | -24.65% | -46.84% | -42.72% |

Non confrontare questi CAGR con il L2-D **2017–2026**, perché i periodi non coincidono. Questi sono comunque **replay semplificati** e non ricostruiscono Hybrid24 né real execution e taxes.

## QA: checks indipendenti

- Match esatto baseline source XGB e labels per ogni `(vintage,signal_date,ticker)`, nessun duplicato, 149 per mese e vintage.
- Maturità di training prima di cutoff in tutti i 48 fits; segnali di inferenza appartenenti all'anno corretto.
- Identity common Repeat2 predictions = native Repeat2 predictions.
- Top1 ricalcolato per date da score grezzi, stessi ticker.
- Aperture successive e concatenazione dei 89 periodi, compound wealth ricalcolata.
- **Refit indipendente di 2024 Repeat2** verifica HGB_DIRECT e HGB_TEACHER50 contro le predizioni pubblicate a precisione `~1e-16`. Indipendenza metodologica parziale: usa stessa formula feature L2-C come riferimento per la ricostruzione.

Codice `l2g_fit_one.py`, `l2g_aggregate.py`, `l2g_proxy.py`, `l2g_independent_audit.py`, output numerici e audit completi sono nel file ZIP allegato alla conversazione (non dati Yahoo raw, ripresi dall'artifact originale). In questa branch Test restano report, protocollo e links di provenienza.

## Decisione degli specialisti — NO GO

Le correzioni strutturali che impongono solo meno complessità o fanno imitare un teacher instabile **non bastano**. Non c'è prova di superiorità di resa della proposta, e il modello rimane molto lontano dal vincolo di robustezza Top1. **Non adottare il candidato HGB**.

Prossimo studio distinto e preregistrato: stimare un modello *smooth* a punteggi continui, con penalità esplicita di **consistency agli input di training**, perturbazioni simulate causalmente da volatilità acquisizioni Yahoo, e vincoli di raggruppamento mensile; gestire esplicitamente l'eventualità **abstain / stay stable** quando margine fra candidati è fragile. Distinguere calibrazione delle decisioni da smoothing del fit. Nessuna selezione dei suoi pesi usando L2-G dopo l'esito; un test realmente fresco è obbligatorio per qualificare il risultato. 
