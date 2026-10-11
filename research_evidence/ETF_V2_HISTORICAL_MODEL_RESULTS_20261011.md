# ETF V2 historical model results reconciled (2026-10-11)

**Source-only recovery, no fitting.** Historical GitHub Actions jobs were read directly for PR #43 (run 37530406442), #47 (37933994472), and #48 (37934815636), and their numerical gates were re-extracted from run logs. Context: pre-downvol-cleanup Original149 Compact21, NOT the subsequently corrected downvol and MAD alpha full V2 runs. Do not mix vintages, scoring protocols or train/inference definitions.

## 1. Completed 3 × 3 full economic model comparison — PR #48

Source: successful GitHub Actions [37934815636](https://github.com/AM1975MA/Test/actions/runs/37934815636), read-only recovery of nine previously completed raw Original149 model/strategy replays from run 37195399755. The original nine fits were BASE/RIDGE/LGBM_LAMBDARANK × three Original149 acquisition vintages.

| Variant | Mean strategy CAGR | Max-minus-min CAGR across three vintages | Top1 disagreement | Joint promotion gate |
|---|---:|---:|---:|---|
| BASE | 31.7580772490% | 4.9236313282 pp | 31.37503522% | FAIL |
| Ridge | 26.1583999781% | 4.9071039697 pp | 16.39898563% | FAIL |
| LightGBM LambdaRank | 36.9646841570% | 9.2075492750 pp | 25.51422936% | FAIL |

**Interpretation:** Ridge approximately halves disagreement, but mean CAGR falls by ~5.60 percentage points versus BASE. LightGBM boosts mean CAGR ~5.21pp but increases between-vintage CAGR span by ~4.28pp. The very small 0.0165pp spread reduction for Ridge is economically negligible. **No model passed the full registered gate.** These reported Top1 disagreement metrics are from the PR #48 learner-specific protocol, not the daily portfolio Top1 disagreement from the later PR #59.

## 2. K12–K16 conditional forward feature selection — PR #43

Source: [run 37530406442](https://github.com/AM1975MA/Test/actions/runs/37530406442), 16 successful candidate benchmark jobs and successful summary. The archived summary explicitly declares `"winner": null`, with **16/16 `ADVANCE: false`**. Baseline: rank MAD 0.05345555, stability Spearman 0.96449138, Top1 disagreement 0.49444444, NDCG@5 0.54656572, Top5 realized overlap 0.12511111. K12: rank MAD 0.03945693 (26.19% improvement), stability Spearman 0.98100295, Top1 disagreement 0.40277778, NDCG@5 0.52681376 (~96.39% of BASE), realized Top5 overlap 0.10133333 (~80.99% BASE); **fails Top5 realized overlap preservation** despite better stability. No candidate passed all joint requirements. Do not blindly revisit K12, orthogonal selection or forward add-on search.

## 3. Prespecified 75% XGBoost / 25% Ridge model blending — PR #47

Source: successful run [37933994472](https://github.com/AM1975MA/Test/actions/runs/37933994472). Baseline and hybrid NDCG@5 0.551994 vs 0.589707, respectively, but **STABILITY_PILOT_PASS=false, QUALITY_CONSERVATION_PASS=false, NEAR_REPEATABILITY_PASS=false, FULL_IMPROVEMENT=false**. Specifically, neither ≥25% required common-rank-MAD reduction nor ≥25% native-Top1 disagreement reduction was attained. Precision@5 conservation and one-sided CI noninferiority checks failed. Full strategy CAGR was **NOT COMPUTED** for the hybrid because predictive/stability gates failed. Do not conflate the distinct pure Ridge PR #48 CAGR with this hybrid.

## 4. Previous hypothesis tests and relevance

- [PR #41](https://github.com/AM1975MA/Test/pull/41) orthogonal feature ablation already exists. Branch workflow run 37530392176 failed; execution-only child [PR #42](https://github.com/AM1975MA/Test/pull/42) needs separate artifact verification before attributing complete joint numerical outcomes.
- [PR #45](https://github.com/AM1975MA/Test/pull/45) training-source 2×2 feature/label factorial and frozen inference previously tested; recovery run 37931212920 SUCCESS, original outer workflow 37916159772 FAIL because of downstream summary, not necessarily missing per-year fitting. Exact full numerical factorial needs extracted summary/artifacts, not repeated fitting.
- [PR #46](https://github.com/AM1975MA/Test/pull/46) source-fixed inference Top1 flip vs ex-post 21d returns was successfully run 37933141010; does NOT compute or validate CAGR. Treat near-tie filtering as already investigated descriptively, not newly tested with full execution.
- [PR #48](https://github.com/AM1975MA/Test/pull/48) full 3×3 alternative learner economic test was already performed; there is no reason to propose the same experiment.
- Current source audit [PR #51](https://github.com/AM1975MA/Test/pull/51) still has an explicit NOT CERTIFIED gate including corporate actions and anomalous bars. Subsequent corrected-downvol α=1.0 full V2 [PR #58](https://github.com/AM1975MA/Test/pull/58) yields mean CAGR 32.9901%, between-vintage spread 4.8802pp, which must **not** be evaluated as if it were a pure learner swap on the earlier PR #48 data definition.

## Decision memo

All re-extracted alternatives either fail joint stability/quality criteria or materially sacrifice one objective. **No historical learner candidate is justified for production.** The best immediate *non-duplicate* action is not model tuning: finish source data validity and mathematical/causal feature completeness certification, then reassess predictive metrics on certified snapshots. There are already 1,665 otherwise eligible incomplete Compact21 rows per vintage after MAD stabilisation; source-only issues also include 123 observations >20% daily price moves and 1,905 zero-volume bars, neither classified as erroneous without raw corporate action reconciliation.

**Remaining scope of this recovery:** The full paired bootstrap distributions, per-vintage CAGR tables and exact numeric outcomes of #41, #45, #46 were not re-extracted in this pass. They should be marked `NOT YET VERIFIED` rather than inferred. These are archival recovery tasks, not invitations to rerun training.

No model fit, no production modification, no merger into Etf_trader.
