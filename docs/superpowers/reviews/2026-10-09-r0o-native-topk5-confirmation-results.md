# R0-O — Independent Data validation rejects naive native topk=5 replacement
**2026-10-09 | Superpowers + Data | TEST ONLY | NO financial XGB fit / NO V2 backtest**

**Preregistration made before any R0-O fit:** [R0-O frozen test protocol](2026-10-09-r0o-native-topk5-confirmation-prereg.md), GitHub commit `5b3608267f875546d45d54582e0a6cb3ca1fb248`.

## Decision

**NO GO: do NOT replace canonical XGBoost `rank:pairwise` default pair sampling with `lambdarank_num_pair_per_sample=5`.** A prior two-world **exploratory** R0-N test looked promising for top1 tail selections; this third hard/noisy synthetic data-seed **20261213**, with **60 wholly new synthetic inference groups**, reproduced a stability improvement but **lost 6/60 first-choice-in-true-Top5 captures** and lowered the mean synthetic selected return. It failed two of five preregistered joint gates. **No search of topk=2/3/10 or leaf/round parameter rescue** on these same fixtures or historical Original149.

This is a falsification of a particularly simple training stability avenue on these toy data. It is **not** evidence that topk=5 will perform worse in real future ETF markets, nor that the canonical 360 rounds are optimal, nor that a trained-model instability problem is resolved.

## Audit and experiment contract

- Original XGBoost 3.1.3 `rank:pairwise`, 125 ordered synthetic features, original depth4 / eta .035 / subsample .85 / cols .8 / min_child Hessian 8 / lambda 8 / alpha .1 / `hist`, group sizes 32, **360 rounds**, seed ensemble **101/202/303**.
- Exactly ONE parameter changed for challenger `lambdarank_num_pair_per_sample=5`. Actual model configuration serialized in each saved NPZ `lambdarank_param` and checked by independent auditor: default `4294967295` vs `5`, with `lambdarank_pair_method='topk'`.
- Hard-world B **new RNG training seed 20261213** (not used in R0M/N), 32 train groups×32 = 1,024 rows. Held evaluation = independent generated test draws from seeds 20261213/14/15, combined **60 groups ×32 =1,920 rows**. These groups are mathematical artificial trials, NOT markets.
- Same train X/y, group keys, held eval and true latent values across both pair-count policies. Three training channels: baseline, small train-feature `X_only` additive jitter sd 2.5e-6 with y fixed; true one-intra-group pair-reversing `Y_only` return 0.1bp gap with X fixed and exactly two grade rows changed.
- Exactly **18 genuinely new 360-round fits** = 2 policies × 3 channels × 3 XGB seeds. Every model produced finite (60,32) held scores stored as `.npz`, each checked against input identities. **No Original149, EU120, Golden, Yahoo or real ETF price input** used for the new model training.
- 4 focused TDD unit tests first RED with missing implementation, then GREEN. Python source compilation passed. Independent read-only `data_audit.py` verified hashes of **all 18** prediction files, counted decisions, recomputed X/Y agreement and selected-return statistics. No partial/restarted model fit or hidden parameter sweep.

## Exact metrics — synthetic common-input comparison

| Metric on 60 independent held synthetic groups | Original native default | Native pair topk=5 |
|---|---:|---:|
| Baseline Top1 within latent true Top5 | **43/60** | 37/60 |
| Exact latent winner Top1 | 13/60 | **15/60** |
| X-only refit Top1 agreement to each baseline | 56/60 | **58/60** |
| Y-only true rank-reversal refit Top1 agreement | 46/60 | **53/60** |
| Baseline NDCG@5 | **0.8710014** | 0.8670299 |
| Baseline synthetic mean selected return | **0.03271988** | 0.03170756 |
| Baseline synthetic mean oracle regret | **0.01872962** | 0.01974195 |

**Three-seed ensemble is the evaluation unit**; don't treat 18 boosters as independent market observations.

Additional Data validation, using independently reconstructed latent outcomes:
- Original vs topk5 select **different first candidates on 31/60 synthetic groups**, same candidate 29/60.
- Among changed selections: **3** false-negative Top5 decisions become true Top5 hits, but **9** former correct Top5 hits are lost, net **−6**. Thus an apparent improvement of exact winner from 13 to 15 does **not** compensate for significant loss of broader top-tail capture under the locked gate.
- Average synthetic selected-return difference topk5 minus default = **−0.00101232** in decimal return units, equivalent to **−0.1012 percentage points per synthetic decision**; paired bootstrap of 60 *artificial* groups, 5,000 samples, fixed seed 20261009, descriptive 95% interval **[−0.0055555,+0.0037841]** (contains 0). Do **not** read as real 21-session financial return or CAGR.
- Difference in Top1-in-true-Top5 rate = **−0.1000** (6/60 fewer), synthetic group-resampled 95% CI **[−0.2167,+0.0167]** (contains 0). No population inference to ETF markets.
- Mean NDCG@5 difference = **−0.00397155**, which is inside preregistered -0.01 loss guard, but other two economic-quality gates fail.

## Prespecified conjunctive gates and actual verdict

| Gate fixed before seeing results | Verdict |
|---|---|
| Top1-in-latent-Top5 capture not less than canonical | **FAIL**, 37 < 43 |
| Selected synthetic mean return not less than canonical | **FAIL**, 0.031708 < 0.032720 |
| X-only training perturbation Top1 agreement not less | PASS, 58 ≥ 56 |
| Y-only training perturbation Top1 agreement not less | PASS, 53 ≥ 46 |
| NDCG@5 not >0.01 below native default | PASS, loss 0.00397 |

**Joint verdict: NO_GO** (2 failed). The priors R0-M hard 20bp loss and R0-N first two toy worlds are useful for mechanism discovery, but are not substitute for this preregistered independent fixture. **R0-N lacked a verifiable GitHub timestamped preregistration**, so it is labelled exploratory instead of falsely promoted to confirmatory.

## Scientific interpretation

- **Narrowing the pair sampler can reduce sensitivity** of the trained model to isolated X and y perturbations without changing objective name, tree parameters or seed ensemble, but may reallocate model capacity away from other true tail opportunities. Pure increased Top1 agreement is not sufficient.
- Hard-masking all return-difference pairs below 20bp in a **custom non-native loss** (R0-M) also achieved made-to-order y-noise stability while failing quality, illustrating why a benign mathematical stability property cannot be taken as improved alpha.
- Evidence still supports investigating **model-data version provenance and actual economically important switch attribution**, with separate feature-X numerical instability and label pair/tie gradients. Do not mask real winners with hard filters; do not optimise pair topk on repeatedly mined 2017–26 history.
- The user asked for a genuine actionable path. The **next meaningful step is not another synthetic hyperparameter trial**: it is P0 data/model versioning and a **single matched and genuinely future point-in-time full V2 economic comparison**, but only after a new candidate is justified by mechanisms in authentic as-of data. No currently tested pairwise variant merits that challenger status.

## Deliverables and provenance

- User-conversation ZIP `ETF_Trader_V2_R0O_Data_20261009.zip`, 18 immutable synthetic prediction NPZ arrays, `r0o.py`, unit tests, `data_audit.py`, `results.json`, `model_manifest.json`, no-fit QA and SHA256 file manifest. The ZIP is downloadable separately in the conversation.
- Original underlying comparative bundle `ETF_Trader_V2_R0N_NativePair_Superpowers_Data.zip`, 36 saved synthetic XGB score artifacts, input/model hashes; verified CRC and **53 file SHA-256**, 5 unit tests PASS.
- Original R0-M source `docs/superpowers/reviews/2026-10-09-r0m-pair-band-results.md` plus `ETF_Trader_V2_R0M_Data_20261009.zip` archive; matched custom fullpairs vs mask20 NO GO.
- **No risk engine, MA3 source, `Etf_trader`, `Trader_selector`, V2 executable, or original production repo modified**.

**Caveats:** synthetic 1,024-row training world, 60 test query groups, one original world mechanism and one controlled pair inversion, no true ETF return data, no historical frozen original annual boosters. There is **no measured V2 CAGR** for these parameter choices; this paper records negative evidence to prevent wasted repeats.
