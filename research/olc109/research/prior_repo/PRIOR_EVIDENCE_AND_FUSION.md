# OLC109 — Repository archaeology and implications for a bounded new study

Read-only research on 15 November 2026. No repository, production model, branch or automation was changed. The current default `main` was observed at `a87e84bc4e53e94a4a4e4c5ecc157e338f2716a3` (4 November 2026); the supplied source commit `f46670a473b9d9ce325593634bc802c7bdfdb505` is the OLC106 delivery checkpoint of 14 November. Immutable source URLs and remote blob SHAs for all fetched text files are in `SOURCE_MANIFEST.json`.

All historical performance below belongs to its original source universe, price feed, accounting and execution contract. It is **not directly comparable** with OLC108 V3. Every proposed OLC109 arm must be recomputed on the same cleaned V3 support. These are repeatedly explored historical samples, not pristine holdouts.

## 1. Most decision-relevant evidence

| Study | Matched experiment and actual result | Interpretation for OLC109 | Local evidence |
|---|---|---|---|
| OLC99 A/B/C | EU FULL DELAY3 baseline 22.05% CAGR; Top10 economic Ridge 80/20 rerank 19.24%; all-universe training 20.49%; same-state native utility target 20.44%, DD 35.55% versus 28.65%. 1,780 native individual counterfactuals. Economic rank IC +.046 versus original +.105; native-target IC +.029 versus original +.160. | Repeating a small-feature return Ridge as a second-stage selector is already well covered. More ETF rows did not solve weak independent monthly information. | OLC99_REPORT_IT.md |
| OLC74 A/B/C | Pairwise Ridge/Logit on fixed Top2; extension to all 45 Top10 pairs/month with swap symmetry and monthly weights; then same-state on-policy 25/50/75 labels. All learners worse than trivial forecasts in both markets in 2021–24. EU A MSE .00556 versus .00469; B .00489 versus .00462; C 126,474 versus 108,215 bp². FULL EU 19.76% HALF, 19.39% pair Ridge, 19.79% Top10 Ridge, 19.62% same-state. | This closely matches a proposed mature-label pairwise model. It can be a falsification control, but does not deserve priority simply because the new panel has 2,096 funds. | OLC74_REPORT_IT.md |
| OLC73 fixed allocation | EU FULL 50/50 19.76%, 25/75 favouring second 22.43%, MinVar63 20.84%; DELAY3 22.05%, 26.08%, 22.61%. USA preferred first ETF instead. All reported FULL block CIs include zero; no common EU/USA gate passed. USA first-heavy annual return 115.91% in 2024 but 1.92% in 2025 versus 50/50 78.61% and 13.57%. | Weight choice matters; winning order is unstable. Neither Top1 concentration nor favouring Top2 is an established universal rule. | OLC73_REPORT_IT.md |
| OLC51 residual risk allocation | EU FULL baseline 19.76%, total MinVar63 cap25/75 20.84%, residual MinVar2F 20.08%, inverse residual vol2F 20.62%. MAIN 2021–24 23.20%, 29.31%, 26.68%, 25.45%. Later-period and USA evidence weaker. | Fixed risk allocation is a known modest EU candidate, not a proven path to 30% or an untested invention. A matched new-data control is sensible. | OLC51_CHECKPOINT_IT.md |
| OLC52 learned regime | Risk-feature Ridge FULL EU 21.05% versus baseline 19.76%, but forecast RMSE 142.0bp versus historical mean 135.6bp; 6-feature RMSE147.8 versus135.3. Risk-only gate still chose the adverse min-var policy in 9/12 months of 2025. | Positive backtest without forecast skill does not establish that a regime learner identifies the right state. | OLC52_RESULTS_IT.md |
| OLC102 daily smoothing | Same third-open timing: EU original22.19% → 50/30/20 rank average16.17%; USA42.81% →33.53%. Conservative80/15/05 also lost in both.76 native replay paths. | Daily averaging/confirmation is already negative evidence; no reason to add another smoothing grid. | OLC102_REPORT_IT.md |
| OLC103 stability | Adding Top2 retention worsened all four prequential errors. EU loss-Brier .118444 → .121090, USA .142237 → .148757. Cap75 if unstable EU22.19% →18.68% and DD28.65% →23.09%; unconditional cap also reduces DD. | Risk reduction largely follows lower exposure. Retention has no demonstrated incremental prediction value. | OLC103_REPORT_IT.md |
| OLC105 frozen ML transfer | 165 contextual anchors, 29 new investable ISIN, 80 complete cycles Mar2020–Nov2026. Original-model HALF immediate5.20% CAGR/DD29.94%; HALFdelay2.45%; MinVar immediate1.47%; MinVar delay−1.62%/DD40.76%. Same-source World14.50%, Mom252Top2 16.12%. Gross ML8.42% versus Mom17.36%. | Frozen FUSION transfer to a different investable universe has already failed in one meaningful matched experiment. A new 2,096-fund transfer is a distinct research hypothesis, not an obviously superior baseline. | OLC105_REPORT_IT.md |
| EU165 economic sectors | 36-group naive between-group advantage +.742pp per interval was singleton-biased. Anti-singleton grouping: +.340pp group / +.299pp within; increment versus broad six groups +.160pp, CI[−.093,+.435]. Limited sector coverage. | Cluster-level scoring must avoid giving each singleton a retrospective “sector victory”. Group-size and wrapper effects need explicit controls. | EU165_SECTOR_README.md |
| EU165 V5 hierarchy | Factor→ETF LightGBM2021–24 CAGR22.03%; no-native-expert22.06%, factor-only20.99%; original V3protected15.67%. Expert increment−.032 annual log-pp CI[−.764,+.698]. Residual21d IC−.0133;94.4% of forecast from factors. V5 CAGR1.44% in2021–22,43.96% in2023–24. | Apparent hierarchy success mainly captured factor exposure; it was not demonstrated residual selection alpha. The annual/regime decomposition matters more than the peak CAGR. | EU165_V5_README.md, EU165_V5_AUDIT.md |
| F4/F9 leadership | F9 Ridge multi15.68% / DD25.50 versus F9equal16.12% /DD17.90 and Mom126Top3 15.97% /DD22.23 in2021–24. Ridge+Kalman15.83% /DD26.50. Forecast improvements not robust. F9 set chosen after2023. | A small factor-level learner and Kalman layer are also already negative evidence. | EU165_FACTOR_4V9_README.md |

OLC74 provides isolated associations for a simple opportunity tilt: EU difference in prior21d momentum versus next relative performance Spearman −.230 (43 months), and log relative vol63 −.441 (38 months); USA −.128 and +.046. These are retrospective, conditional Top2 associations, not validation of a residual mean-reversion rule across the whole universe.

OLC98's branch contains its preregistered layer-reordering protocol but no result artifact in the inspected tree. OLC100's frozen architecture explicitly excludes reordered OLC98 rankers from promotion. Do not invent the missing exact OLC98 outcome. OLC95's inspected branch contains a Yahoo/Eurex probing script, not a verified predictive scorecard; no futures-alpha conclusion can be drawn from that source alone.

## 2. What the original frozen FUSION actually is

**OLC106 is not the native ML pipeline.** Its local `prepare.py` explicitly never imports old scores, selected IDs, V6 states or fitted models. Its raw rules-based score is `(4*m63 + 2*m126 + m252)/3/vol63`. The original ML selector belongs to OLC19/OLC100 and its annual upstream checkpoints.

### Original versus contextual score

1. Return125: three annual XGBoost rank models (seeds101/202/303), averaged raw prediction then within-date percentile.
2. Hybrid42 original: annual ExtraTrees and XGBoost regressors, three seeds101/211/307; rank the family forecasts cross-sectionally, combine `.6 ET + .4 XGB`.
3. Original temporal memory: current/prior1/prior2 months weights `.4/.3/.3`, clip0–1 and exponent1.1; combine with Return as `.475 Return + .525 HybridMemory`.
4. OLC19 contextual variant replaces the fixed Hybrid horizon combination with separate C21/C42/C63 ET/XGB heads. Each horizon is itself `.6 rankET + .4 rankXGB`.
5. Annual context model produces a simplex of horizon weights from benchmark normalized126d trend, log(vol21/vol126), and current/prior-month forecast-rank leadership Spearman. Prior weights are .45/.35/.20.
6. At each date, apply **current** horizon weights also to the known previous two months' forecast heads, map onto each original fixed-anchor score distribution, then the same .4/.3/.3 memory, power1.1 and .475/.525 fusion. It never rewrites an old trade.

The contextual `beta21/beta42/beta63` weights are **signal mixture weights**, not capital allocation weights. Capital 50/50, MinVar, DELAY3 and protection remain separate layers.

### Chronology: evidence from actual training source

- `OLC08_train_variants.py`: per-year Return training requires signal_date < January1 and exit_date21 < January1; Hybrid requires the relevant mature63d exit < January1. Model applies to that calendar year's prediction rows.
- `OLC14_train_heads.py`: all C21/C42/C63 training cohorts have exit_date63 strictly earlier than January1; imputers fit only on training.
- `OLC16_experiment.py`: context fitting uses only complete groups with max63d exit before annual cutoff. At least18 groups per market, equal market weights; two prior annual folds choose the context penalty from .01/.1/1. Context years2021–2026; earlier/fallback use the prior.
- Therefore source code describes annual chronological models, **not one model fitted on the entire evaluated future**. Exact binaries and their annual audit/checksum files must still be verified before claiming an exact replay. Architecture choice and history reuse remain retrospective.

### Minimal reusable paths and missing dependencies

The closest existing transfer adapter is source-commit `research/olc105/anchored_transfer/src/`:

- `build_transfer_features.py` calls the original OLC07 P0 `calendar_rebuild.py`, adapting only the final calendar date, and supplies new raw frames.
- `score_transfer.py` reopens the annual frozen models, repairs EU RSI via the R_RSI_DOMAIN checkpoint, predicts all rows, then ranks within each date.
- `compose_transfer.py` uses the frozen `ANNUAL_MODELS.json` plus OLC16 `context_model.py`, `revalue_memory.py`, `core.py`.
- `settings.py` documents the required OLC104 layout and source roots.
- `data_transfer.py` is specific to 29 new ISIN and old anchors and must not be reused as an unexamined new-data loader.

Required model/source archives are OLC08_01_Pannelli_Verificati, OLC08_03_RSI_Confronto_Verificato (EU Return), OLC11_02_Modelli_Verificati (original Hybrid), OLC14_Heads_Checkpoint, OLC19_Rischio_Rientro_Checkpoint, and the legacy feature/cluster source restored in OLC104. None of the model binaries is present in current scratch. They were not fetched.

The contextual score mathematically uses Return125 plus C21/C42/C63 heads and annual context weights; the existing adapter also loads original Hybrid regressors for baseline/parity. Removing dependencies would be a new adapter change requiring an explicit parity audit, not a drop-in reuse.

Original persistent membership requires **six clusters, at least eight defensive instruments and five times eight dynamic instruments**. OLC105's29-only primary arm was blocked; anchored transfer preserved the original minimum sizes. Broad2096 clears a crude count hurdle, but still requires historical membership and macro-role construction. The generic fullstack `kernel.py` also contains an older8-cluster recipe; **it is not evidence that those generic formulas reproduce OLC07's frozen feature/cluster construction**. Saved generic files are feature-schema references only. Exact feature math comes from the OLC08/OLC07 frozen sources.

Return125 includes momentum5–252d, volatility/downvol/drawdown/efficiency, acceleration, skew/kurtosis/GKvol, volume/ADV, benchmark beta/correlation, MA/EMA/breakouts/RSI and cross-sectional percentile/robust-deviation transforms. Hybrid42 includes cluster acceleration/efficiency/return ranks, relative-to-cluster return/volatility, cluster breadth, and technical/volume/spectral features. It needs coherent OHLCV, a benchmark, native-date calculations, past cluster membership and a defined normalization universe. Changing to V3's cleaned/zero-volume-excluded support changes those features and ranks; it is a legitimate new matched-data transfer, not bitwise reproduction of the old forecasts.

## 3. Bounded next changes justified by the evidence

1. **A fixed cluster-first selection ablation on V3** is the most distinct next test. Separate the effect of duplicate/near-identical wrappers from genuinely different exposures. Compare original security-level ranking with equal cluster weighting/cluster representative selection while holding timing, allocation and protection constant. Use only trailing observed returns; require group-size and singleton diagnostics. No prior source establishes this as a winner.
2. **A small fixed residual21d opportunity weight tilt on a fixed leader pair** can isolate whether the old short-horizon reversal association has any useful transfer. Compare against equal weights and a direction-reversed tilt at identical risk budget. Keep replacing a leader with an opportunity candidate as a different selection experiment. The prior negative pairwise learners argue for a simple mechanism test before another fit.
3. **A fixed capped total-variance allocation and one residual-risk comparator** can separate allocation from selection without a regime classifier. Known OLC51/73 evidence is modest and unstable; report full history, annual2024 and delay/cost sensitivities, and avoid picking weights by the best historical CAGR.
4. **A full frozen FUSION transfer** should remain an optional separate falsification experiment once exact dependencies are restored and original-source parity is proven. OLC105 gives reason to keep a simple fixed-rank baseline alongside it. Do not call an approximate .475/.525 blend of price indicators the original FUSION.

Do not repeat another Ridge economic reranker or pairwise weighting fit just to turn many correlated ETF rows into an apparently large training set. If such a control is retained, evaluate predictive error against a training-only mean/zero baseline and count independent dates, not rows. All bootstrap results should remain descriptive after extensive research reuse, with 2024 retained and shown explicitly.

