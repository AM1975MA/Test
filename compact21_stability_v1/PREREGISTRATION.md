# COMPACT21_STABILITY_V1

## Frozen scope and provenance
Opened 2026-10-04 from Test commit bdb5b277e999e7fb7a066f858b8b9c51d0e334a4.
Original149 is burned development evidence. This is an engineering robustness
experiment, not investment validation or permission to deploy a strategy.
Canonical source, Compact21 rank:pairwise parameters, seeds 101/202/303,
Compact63, Tail, macro, MA3 and Stage19 allocation/risk/execution stay frozen.
Execution-only deterministic control: MA3/ExtraTrees n_jobs=1 for every new full replay; historical Q4 used n_jobs=2. Compare candidates with the new BASE and report historical parity separately. Negative feedback remains unchanged. No parameter selection from CAGR.

Benchmark: three frozen TI_COMPACT panels from run 37150436612. They are only
for the local ranker diagnostic, not permissible inputs to full raw replay.
Full replay: three raw snapshots from run 37121749852, regenerated features,
labels, Titanium, MA3 and final decisions. Historical outputs are comparison
references only. Exact input SHA256 and runtime versions are recorded.

## Frozen factorial matrix
| Variant | Feature inputs for Compact21 | Target |
| --- | --- | --- |
| BASE | canonical | round(target_rank_21 * 100) |
| Q4 | round(x,4) | canonical |
| ORDINAL | canonical | per-query dense ordinal from canonical percentile |
| ECON1BP | canonical | forward21 return at fixed 0.0001 grid, then dense rank |
| Q4_ECON1BP | Q4 | economic1bp |
| SCALE | scale-aware | canonical |
| SCALE_ECON1BP | scale-aware | economic1bp |

No variant or grid is added/removed after reading these results. All outcomes
including failed variants are retained. ORDINAL isolates the artificial rank
binning, but cannot remove near-tie return reordering. Economic1bp preserves
within-bin ties; it changes economic resolution and is not a vendor noise
estimate. No ticker-based target tiebreak. Fixed-grid boundaries remain.

Scale-aware: zero-anchored dyadic nearest-even quantization with 4096 nominal
cells. Documented bounded feature domains use kernel-defined width; other
features use training IQR with declared constant/empty-feature fallbacks.
The dyadic step is rounded upward. No clipping, no full-history scale, no
future labels, no pooled snapshots and no tuning against validation or CAGR.
Each snapshot fits its own transform on its own strictly mature annual
Compact21 training frame. This is a scale-resolution proxy, not a measured
noise floor. Annual IQR/dyadic boundaries and derived percentile rank flips
remain potential fragility, explicitly audited.

## Benchmark
All annual folds 2017-2026; inference ends June30 2026. Signal_date and
exit_date_21 must both be strictly before Jan1 of fit year. Model quality
uses only outcomes matured by July1 2026; future targets cannot affect fit,
transforms, predictions or cohort membership. Feature validity follows
canonical >=30 nonmissing features. Native training rows are not intersected
across snapshots. Sorted (signal_date,ticker), unique keys, original seeds,
360 rounds and single-thread isolated workers.

Primary: all three pairs (1-2,1-3,2-3), common Repeat2 input per pair under each
model's own fitted transform. Measure monthly percentile rank MAD, Spearman,
Top1 disagreement and Top5 Jaccard. This isolates training/transform effects.
Secondary: each snapshot's native inference, same metrics on common keys.
Report coverage, native unquantized target NDCG@5/@10, target IC, Top1 realized
percentile, pairwise label relation disagreement (including tie transitions),
and integer-label difference (which can overstate dense-label changes).
Repeat2 fit is independently repeated every year: exact prediction equality.
Annual metrics and each pair are retained; aggregates weight years and pairs
equally, so these are not sample-weighted pooled estimates.

## Frozen advancement gate
For a challenger to proceed to full replay, all must hold against BASE:
- common-input mean rank MAD falls >=25%;
- common-input mean Top1 disagreement does not worsen;
- common-input mean Spearman does not worsen;
- native-input mean Top1 disagreement does not worsen;
- native quality mean NDCG@5 >=95% of BASE;
- all annual maturity and deterministic-repeat checks PASS.

BASE and Q4 always receive full replay controls. Q4_LEGACY also runs as a
historical parity control: global Q4 affected both Compact21 and Compact63,
although the reported baseline blend does not consume Compact63. No other
challenger proceeds unless this gate is met. This gate is fixed before any
COMPACT21_STABILITY_V1 result; it is not a production promotion gate.

Full economic assessment reports all three CAGR/MaxDD/Sharpe/turnover values,
CAGR max-min span and cross-snapshot daily Top1/Top2 disagreement. A span
reduction alone is insufficient. No full-replay rerouting/tuning by CAGR;
independent later untouched evidence is needed for adoption.

Full outcome screen (development only, fixed before results): CAGR span <=75% new BASE, daily mean Top1 disagreement <= new BASE and mean CAGR >=95% new BASE. These are reported jointly, never optimized, and do not authorize production.
