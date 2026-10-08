# R0-M — controlled masked-pair ranking objective: next experimental design (NOT YET EXECUTED)
**2026-10-09 | ETF Trader V2 | Superpowers + Data | AM1975MA/Test**
**Branch** `research/v2-xgb-immutable-checkpoints-20261008`
**State:** TECHNICAL DESIGN / FUTURE PREREGISTRATION. No new fitting or financial validation is implied.

## Why this plan exists

R0-J discovered eight *Compact21 strict ordinal pair reversals*, all at <=0.0115991 **basis points** of future return distance on archived Repeat1/3 history. It also showed that a 20 bp candidate mask would remove ~3.78885% of all theoretical monthly ETF pairs, leave no strict reversals among included pairs, and change inclusion status of fourteen near-boundary pairs. This is *historical descriptive source evidence, not investor performance*. The 20 bp band is NOT scientifically justified merely by 0.1%/side transaction fees, which are largely common to comparing two alternative ETF positions. The native XGB pair sampling distribution was not audited.

R0-K tested a native `rank:ndcg` competitor on synthetic fixtures and found synthetic Top5 quality degradation in World A, despite improved output stability. World B native `rank:pairwise` fitted scores were not saved; its matched comparison is unavailable. Do not repeat the already completed nine baseline fits merely to claim completeness.

R0-L shipped only a research custom pairwise loss with exact signed-pair masking and a *positive diagonal Hessian approximation*, with tests for finite-difference gradient and a QuantileDMatrix smoke fit. It is NOT mathematically identical to `rank:pairwise`, and an objective substitution could itself explain any eventual outcome. With 149 candidates, naive full-pairs sampling is O(149²) per month and can be prohibitively costly across years ×360 rounds ×3 seeds ×2 horizons; this needs cost/performance verification before portfolio testing.

Original 125-feature Compact21 has training-X-only instability independent of labels (four-year forensic ~62.5% Top1 disagreement). Thus even a perfect label-pair correction would solve *only one channel*.

## Single strict factorial design to isolate real mechanism

All comparisons use identical **new artificial grouped ranking fixtures** and held inference inputs; no Original149 or EU120 actual ETF model fitting, no repeated historical full V2 test.

| Arm | Exact loss implementation | Pair treatment | Purpose |
|---|---|---|---|
| C0 native reference | `rank:pairwise` source-configured | Native pair sampler | Contextual external canonical baseline, **not** an ablation-matched masking control |
| C1 all-pair custom control | Exact R0-L implementation, `fee_band=0` | Retain all non-tied raw-return pairs | **Required matched control** for changes to objective/gradient scaling |
| C2 pre-locked masked custom | Same exact R0-L implementation, `fee_band=b` | Exclude only pairs below b | Isolated effect of band, C2−C1 |

**The band b must be chosen once before fitting or observing heldout predictive outcomes, from an independent point-in-time noise/uncertainty specification.** A mechanical choice of b=20bp because trade fee is 0.1%/side is not an independently valid justification. If a defendable b is unavailable, **STOP before C2 fitting**, retain R0-L as feasibility and do not sweep several b values. The names `fee_band`/`cost-aware` in the prototype are historical research nomenclature, not proof that the band is a true marginal trading-cost cutoff.

### Training/data contracts

- New synthetic fixture generator seeds distinct from R0-E/F/H/K; two mathematically distinct latent generators each with 125 ordered features, monthly-sized query groups, explicit `group_ptr`, rare extreme positive observations and realistically sparse within-group near-ties. Do not use Yahoo price return realizations to choose objective parameters.
- Fit two horizons only if horizon-specific targets and mature `exit_date_h < cutoff` can be tested in an annual synthetic as-of panel; otherwise **only one horizon with explicit scope limitation**, no false 'full V2 stable' claim.
- Fix 360 boosting iterations per seed, seeds 101/202/303 and other canonical XGB settings; hold training X and y/group/relevance/pair sampling equal across C1/C2 except the pair band.
- Scenarios per fixture/objective: same exact baseline, X-only tiny feature perturbation, Y-only one STRICT rank reversal with magnitude <b (if b>0), X+Y. Same held-inference X across fits. Also measure one large-positive-tail rank reversal with magnitude >b, so C2 must remain responsive to economically material pairs; this is a *separate preregistered control*, not a new hyperparameter option.
- For target Y, preserve raw 21d/63d forward returns in custom objective and map 0–100 integer relevance to native baseline identically; note the custom objective necessarily uses richer continuous target information than native, a further interpretive difference. Use actual mature labels from synthetic prices only where dates are genuine.
- Do not promote candidate if poor in *either* X-only or Y-only channel, or if ranking's true extreme-positive tail suffers, even if Top1 agreement improves.

### Engineering and methodological tests (TDD before fitting)

1. **Math:** exact gradient finite-diff for masked and unmasked C1/C2, stable `logaddexp` form for extreme scores, Hessian finite/nonnegative diagonal approximation, no zero-Hessian crash, group sums, permutation invariance under ticker and row reordering, all-tied/empty pair pool.
2. **Training:** same xgboost 3.1.3 runtime, QuantileDMatrix group sanity, source nthread/seed and true 360 rounds, correct test-label maturity.
3. **Masked control:** zero band and positive band share every math/normalization/curvature path; explicit count of pairs retained and separately the sum of **effective gradient/Hessian weight** removed (theoretical pair fraction alone is not informative).
4. **Cost:** benchmark an objective call per fixed group count and extrapolate wall time under annual cohorts; if full all-pair objective would be unreasonable, pre-register a deterministic pair-sampling scheme **for both C1 and C2 identically** before continuing. A computationally different candidate needs a *new* design and matched control; do not silently switch.
5. **Economic skill (toy only):** Top1 exact synthetic winner, Top5/top-decile capture, highest-positive-tail false negatives, NDCG@5, native/common inference Top1 agreement, rank-MAD, score differences, per-group exposure-like decision changes. No synthetic CAGR.
6. **Validity:** original untouched; no R0-E leaf or R0-H round count sweep, no post-hoc b tuning, no ranks/targets from future accepted into training. If quality degrades => NO GO. Multiple existing Yahoo vintages are burned and not independent out-of-sample.

### Real investment outcome requires a *different* later gate

Do not run real ETF training before a signed, causal, genuinely NEW date/universe snapshot, candidate frozen and full-V2 matched event schedule. Validate complete 21/63, 3 seeds/MA3 clustering/imputation, Stage19/HighCAGR24/V6/fees/daily risk, paired per-vintage drawdown/turnover, per-ticker exposure and positive-tail capture. In a short future period, report daily/cumulative P&L rather than annualized CAGR. A worse challenger is rejected; incumbent V2 is unaffected.

**No remote GitHub production writes or independent agent dispatch**. The scope of this document is design of the *next* discriminating test, not its execution. It does not supersede earlier no-tune constraints.
