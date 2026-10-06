# COMPACT21 orthogonal feature-ablation — training result V1

## Status

**NO ADOPTION.** The feature-selection line is valid and informative, but no frozen subset passes every preregistered stability + predictive-quality gate.

Feature-selection run: `37524219056`  
Subset-training run: `37525303093`  
Reference BASE: independently verified canonical benchmark run `37167010405`, BENCHMARK blob `f0d85116b1b8691913a967e820a35de483966b50`.

The BASE125 cell of run 37525303093 was still executing when this result was frozen. The reference BASE is the already independently verified canonical BASE on the same three frozen TI_COMPACT snapshots, 2017-2026 folds and unchanged ranker configuration.

## Results

| Variant | N feat | Rank MAD | Improvement vs BASE | Top1 disagreement | Stability Spearman | NDCG@5 | NDCG vs BASE | Top5 realized | Top5 vs BASE | Advance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BASE | 125 | 0.053456 | — | 49.44% | 0.964491 | 0.546566 | 100.00% | 12.51% | 100.00% | Control |
| K8 | 8 | 0.034070 | **36.27%** | **37.50%** | **0.985252** | 0.504909 | 92.38% | 9.70% | 77.53% | No |
| K12 | 12 | 0.039457 | **26.19%** | **40.28%** | **0.981003** | 0.526814 | **96.39%** | 10.13% | 80.99% | No |
| K16 | 16 | 0.045780 | 14.36% | 43.61% | 0.974334 | 0.521210 | **95.36%** | **12.54%** | **100.27%** | No |
| K24 | 24 | 0.047106 | 11.88% | 41.94% | 0.972879 | 0.504884 | 92.37% | 10.67% | 85.26% | No |
| K32 | 32 | 0.049825 | 6.79% | 41.11% | 0.969572 | 0.526792 | **96.38%** | 11.53% | 92.18% | No |
| K40 | 40 | 0.046513 | 12.99% | 42.50% | 0.973685 | 0.523063 | **95.70%** | 11.81% | 94.40% | No |
| FAMILY46 | 46 | 0.047609 | 10.94% | **40.00%** | 0.972678 | **0.537745** | **98.39%** | **12.06%** | **96.36%** | No |

Frozen gate: Rank-MAD improvement >=25%, stability Spearman no worse, Top1 disagreement no worse, NDCG@5 >=95% of BASE, Top5 realized overlap >=95% of BASE, maturity PASS and deterministic repeated fit PASS.

All completed subset jobs pass maturity and deterministic-fit checks.

## Interpretation

### K8
Excellent stability improvement, but predictive loss is too large. Reject.

### K12 — stability frontier
This is the first important positive result. It reduces Rank-MAD by **26.19%** and Top1 disagreement by **9.17 percentage points**, while retaining **96.39%** of BASE NDCG@5. However Top5 realized overlap falls by about **19%**, so it does not meet the predictive preservation objective.

### K16 — Top5-preserving compact frontier
It keeps Top5 realized overlap essentially unchanged (**100.27% of BASE**) and retains **95.36%** of NDCG@5. Top1 disagreement improves to 43.61%, but Rank-MAD improves only **14.36%**. Useful trade-off, but insufficient stability convergence.

### FAMILY46 — quality-preserving frontier
This is the best information-preserving ablation. It retains **98.39%** of NDCG@5 and **96.36%** of Top5 realized overlap while lowering Top1 disagreement from 49.44% to **40.00%**. However Rank-MAD improves only **10.94%**, far below the frozen 25% target.

## Conclusion

The experiment supports the original hypothesis only partially:

1. Reducing redundant inputs **does materially reduce training instability**.
2. The strongest stability gains occur with very small feature sets, but predictive Top5 quality then falls.
3. Preserving broad orthogonal information with one champion per semantic family substantially improves Top1 convergence with only modest quality loss.
4. There is **no current feature subset that simultaneously achieves the required stability reduction and preserves Top5 capability**.

Therefore **no production adoption** and negative feedback remains unchanged.

The next research line should not simply test more arbitrary feature counts. The useful boundary is now identified: investigate the incremental features between **K12 -> K16 -> FAMILY46**, specifically which additions restore Top5 information and which reintroduce rank instability. This should be a targeted conditional ablation / forward-selection around the K12 core, with the same frozen gates and no CAGR-based selection.
