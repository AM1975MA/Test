# Meta-ranker ETF-level — historical research checkpoint (2026-10-21)

## Status
**Exploratory only; not independently validated or approved for production.**

Source scores were exported through the workflow `.github/workflows/meta-ranker-export.yml` on branch `research/meta-ranker-asset-oos-20261021` (GitHub Actions run **39506868766**, artifact **12304560383**). The five source model streams originate from run **39492170319** (XGB125 depth 7) and run **39489526724** (B/C/D/E RMT ablations).

### Data integrity
- 149 ETFs × 476 weekly decisions = **70,924** ETF-date rows per source prediction stream.
- All five streams have identical (date, ETF), `t_idx`, realized 5-day forward returns and target percentiles.
- Reconstructed XGB depth-7 Top 5 weekly selections match original run output for all 476 weeks, with max absolute mean-return mismatch below 1.4e-8.
- Dates: **2017-01-05 through 2026-06-18**.
- Meta evaluation: **325 weeks in 2020–2026**; yearly expanding training on matured historic OOS predictions only (`t_idx + 6 <= test_first_t_idx`).
- 2017–2019 pre-test history, inner nested validation on 35 earlier decision weeks; inputs retain their original annual OOS model provenance.
- **XGB depth 7 is not the exact ETF Trader V2 frozen 127-leaf model.** RMT information is supplied by OOS expert scores, not raw RMT feature columns.

### Primary comparison — Top 5, gross weekly-equity simulation
| Variant | CAGR | MaxDD |
|---|---:|---:|
| Fixed RMT ETF model | **27.23%** | -39.19% |
| Alpha meta on XGB depth7 | 18.54% | -37.91% |
| XGB125 depth7 baseline | 12.16% | -39.94% |
| Meta with RMT and downside penalty | 4.74% | **-24.74%** |
| Meta with downside penalty, XGB only | 4.70% | -27.59% |

The global cost-sensitive re-ranking materially sacrifices alpha; **do not promote it**.

### Secondary alpha-preserving risk overlay — costed weekly equity
Cost convention: estimated 20 bps × fraction of equal-weight ETF names replaced per week, *not actual trading costs*.

| Top-K | Variant | Estimated net CAGR | Net weekly MaxDD |
|---|---|---:|---:|
| Top 1 | RMT ETF fixed | 13.82% | -50.37% |
| Top 1 | Veto predicted risk percentile above 95% | 25.58% | -31.85% |
| Top 1 | Nested-selected constrained risk rule | 9.82% | -35.13% |
| Top 3 | RMT ETF fixed | **20.35%** | -41.31% |
| Top 3 | Veto 95% | 20.10% | -37.77% |
| Top 5 | RMT ETF fixed | **20.20%** | -39.76% |
| Top 5 | Veto 95% | 18.62% | -37.67% |

The 95% rule was inspected retrospectively on researched periods and must **not** be treated as fresh OOS confirmation. Nested-selected overlay lowered CAGR relative to fixed RMT model.

Paired 8-week moving-block bootstrap, 4000 repetitions, 95% intervals for estimated net weekly mean difference of veto95 minus RMT fixed: Top 1 **[-0.456,+0.649] percentage points**, Top 3 **[-0.278,+0.215] pp**, Top 5 **[-0.217,+0.149] pp**. All intervals include zero and are uncorrected for exploratory multiple comparisons.

### Follow-up / promotion gate
Freeze a very small pre-registered set of candidate veto rules and evaluate on truly unseen later observations. Verify actual 127-leaf frozen producer, original basket/roster, eligible ETF universe, maturity-safe target timing, realized execution costs, turnover and daily MaxDD. Keep higher portfolio risk layers disabled until this alpha/risk ablation is independently supported.

**Reproducibility:** The conversation artifact `ETF_Meta_Ranker_Asset_20261021.zip` contains the complete research Python harness, identical source score CSV streams, nested folds, weekly selections, annual scorecards, audits and robustness script. No code besides the exporter workflow has been written into the research GitHub branch in this checkpoint.
