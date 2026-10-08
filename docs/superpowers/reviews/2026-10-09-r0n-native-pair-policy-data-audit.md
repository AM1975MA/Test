# ETF Trader V2 — Data × Superpowers audit of R0-M and R0-N (2026-10-09)

**Status: complete read-only verification and independent decision-level recomputation; no new XGB fits or ETF financial backtests in this audit.** Repository **`AM1975MA/Test`**, isolated branch **`research/v2-xgb-immutable-checkpoints-20261008`**. No changes to `Etf_trader`, `Trader_selector` or source-only canonical V2.

## Result and decision

**R0-M: NO GO** on the 20bp hard-masked custom objective. **R0-N: RESEARCH-ONLY FOLLOW-UP**, *not* promotion: native XGBoost `rank:pairwise` using `lambdarank_num_pair_per_sample=5` held or improved synthetic Top1-in-realized-Top5 and maintained/improved agreement on two toy worlds, but **degraded full NDCG@5 in world B**. The user has not been shown a valid full-V2 CAGR improvement because **none has been measured**. Do not optimize XGB pair count using repeatedly explored Original149/Golden/Repeat1–3.

**Methodological caveat:** The R0-N protocol and scripts came from a pre-existing conversation-local archived bundle. This reviewer verified the archived hashes and the exact source code but **did not locate a timestamped GitHub pre-training preregistration for R0-N**, so do not describe this as an independently preregistered confirmatory test. It is an exploratory two-fixture result; no fresh prospective market holdout.

## Material from already-completed experiments

### R0-M hard 20bp mask (new code changes many loss properties)

Two artificial worlds A/B, 32 groups ×32 training candidates, 20 groups ×32 eval, 125 features, **seed 101 only**, 360 trees. `custom_fullpairs` vs `custom_20bp` is the valid matched contrast: both use all eligible within-group pairs, diagonal Hessian approximation; native `rank:pairwise` uses different pair selection, curvature and scaling.

| Metric (40 groups) | Custom all pairs, no mask | Custom pairs, 20bp hard mask |
|---|---:|---:|
| Baseline selected Top1 in latent best 5 | 33/40 | 33/40 |
| Exact latent best Top1 | 13/40 | **12/40** |
| Common-test Top1 agreement under X-only | **40/40** | 39/40 |
| Common-test Top1 agreement under y-only | 38/40 | **40/40** |
| Mean synthetic NDCG@5 | **0.917695** | 0.915921 |
| Mean artificial realized selection return | **0.040492** | 0.039421 |

The Y-only test deliberately swapped **one tiny 0.1bp pair entirely within the 20bp excluded region**, leaving the membership mask exactly unchanged. Thus exact score stability on Y-only for this custom objective is partly **by construction**, not an observed universal cure of Yahoo adjustments or X-only feature drift. The original R0-M Data audit verdict is `FAIL_JOINT_GATE`. Both synthetic worlds have negative selected-return delta for hard mask vs same custom fullpairs baseline. No alternative threshold search or model promotion warranted.

### R0-N native `rank:pairwise` one-parameter change (more informative)

Archived synthetic code retains `rank:pairwise`, 360 trees, 125 features, 3 canonical seeds `101/202/303`, `max_depth=4`, original learning rate and regularization. The **only** changed XGB parameter is `lambdarank_num_pair_per_sample: default (serialized as 4294967295 with `lambdarank_pair_method=topk`) → 5`. Same 2 artificial worlds A/B, 32 train groups ×32, 20 untouched evaluation groups ×32 per world; baseline, X-only, y-only variants; **2 × 2 × 3 × 3=36 saved fit prediction artifacts**, each from a 360-round XGB booster. R0-N is **NOT** financial Compact21, not actual 149 ETFs and not the full MA3/V6 risk engine.

| Measure | World A default | World A topk5 | World B default | World B topk5 |
|---|---:|---:|---:|---:|
| Baseline Top1 within realized synthetic Top5 | 18/20 | 18/20 | 15/20 | **17/20** |
| Exact latent top1 | 7/20 | 7/20 | 4/20 | 4/20 |
| Same Top1 under X-only train perturbation | 20/20 | 20/20 | 17/20 | **20/20** |
| Same Top1 under y-only single pair reversal | 20/20 | 20/20 | 16/20 | **19/20** |
| NDCG@5 of full synthetic ranking | 0.936017 | 0.940739 | **0.903391** | 0.878490 |
| Baseline mean selected synthetic return | 0.040789 | 0.042097 | 0.035385 | 0.037073 |

Data independent *group-level* reconstruction from 36 saved per-seed arrays:
- World A: **9/20** baseline first choices change when replacing default pair count with topk5; **2** prior missed-Top5 decisions improve, **2** previously Top5 hits degrade, net 0.
- World B: **11/20** first choices change; **4** former misses enter realized Top5, **2** prior Top5 hits are lost, net +2.
- Paired mean synthetic *selected-return* topk5−default: **+0.00130814** (A; descriptive group-bootstrap 95% **[−0.0027485,+0.0063559]**) and **+0.00168743** (B; **[−0.0033098,+0.0065255]**); both intervals include 0. **No demonstrated improvement in expected return** even on these artificial groups.
- Paired mean synthetic NDCG@5 topk5−default: **+0.0047229** (A, CI [−0.0088585,+0.0209052]), **−0.0249011** (B, CI [−0.0515901,−0.0007892]); B degrades broader-ranking quality despite improved synthetic Top1 tail capture.
- Note sample size: only **20 query groups per world**; bootstrap over same generated groups is descriptive, not independent proof. It is not correct to treat 36 booster files as 36 independent economic periods.

**Guard evaluation:** A simple originally coded headline guard `no worse Top5, selected-return, X and Y agreements in each world` passes. **However the stricter scientific objective of preserving complete ranking quality is not demonstrated** because world-B NDCG@5 drops appreciably. Do not suppress this caveat or use the headline guard alone as a deployment verdict.

## Audit executed in this turn, no fitting

- Extracted existing ZIP `ETF_Trader_V2_R0N_NativePair_Superpowers_Data.zip`, SHA256 **`f2864210192dd4c4cd4c450549d3e45b1f9debb3aa1ed594a9292e9a3d2ea6f8`**.
- ZIP CRC integrity PASS; **all 53 member-file SHA256** match the archived `MANIFEST_SHA256.json`.
- `PYTHONPATH=r0n:dependency pytest -q r0n/test_r0n.py` **5/5 PASS**.
- `PYTHONPATH=r0n:dependency python r0n/data_audit.py` **AUDIT_PASS; all 36 prediction arrays present, native pair-method metadata verified, model-specific hashes match, independent recomputation exact**.
- New **no-fit** group-decision audit `r0n/data_decision_impact.py` generated `r0n/model_artifacts/decision_impact_audit.json`, reproducing all Top5 and exact-best counts and quantifying the 9 and 11 changed decisions. No native fitted model tree `.ubj` is archived, only per-seed predictions.
- **No Original149, EU120 or Yahoo financial data accessed for new fitting** in this audit. All metrics here are synthetic and no V2 CAGR is claimed.

## Data-led next development decision (one axis, explicit stop)

**At most one further strict native-pair sampling replication is justified**, rather than adding more custom losses, reducing trees, or tuning 5 against the old ETF history. Test the **exact same pre-chosen topk5 vs native-default** on a new artificial generator with *more independent query groups* (rather than doing additional parameter sweeps), retaining all 3 seeds, source exact 360 rounds and separate X/Y/joint perturbations. Add an explicit *ranking-quality/non-inferiority guard* and an extreme-positive-tail recall guard before seeing results; **stop immediately** if either fails. This would only support engineering feasibility, NOT authorize an ETF fit or a financial strategy recommendation.

Actual economic learning needs a new causally archived point-in-time ETF dataset, genuine as-of membership/MA3 model state and a **prelocked single challenger** with same-day full V2 cash/fees/stops and per-vintage CAGR / daily MaxDD / extreme-winner capture. Do not search `lambdarank_num_pair_per_sample` values (e.g. 2,3,10) on Original149; avoid historical optimization and artificial economic claims.

**Recommendation now:** original `rank:pairwise` stays canonical; `topk5` is an exploratory native-parameter candidate with genuine engineering simplicity and an unresolved ranking-quality trade-off. The custom masked loss hard 20bp remains **NO GO**. Maintain separate lineage P0/A1 and MA3 state-freezing work to ensure the next future test can be interpreted.

## Archived sources

- `ETF_Trader_V2_R0M_Data_20261009.zip`: `r0m/R0M_DATA_REPORT.md`, `r0m/data_analysis.json`, training code, 18-fit log, TDD.
- `ETF_Trader_V2_R0N_NativePair_Superpowers_Data.zip`: `r0n/r0n.py`, `test_r0n.py`, `data_audit.py`, 36 saved NPZ prediction vectors and manifests.
- GitHub archived: `docs/superpowers/reviews/2026-10-09-r0m-pair-band-results.md` and corresponding R0-M frozen protocol. This report adds independently recomputed, source-verifiable R0-N evidence.
