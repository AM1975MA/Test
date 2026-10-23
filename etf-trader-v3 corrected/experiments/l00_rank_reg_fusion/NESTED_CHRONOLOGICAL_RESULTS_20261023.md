# V3 L00 — Nested meta-tree time-ordered model selection: validated results (2026-10-23)

**Remote verification: PASS** — [GitHub Actions 40032282233](https://github.com/AM1975MA/Test/actions/runs/40032282233), [exact versioned output 12535227212](https://github.com/AM1975MA/Test/actions/runs/40032282233/artifacts/12535227212).

Research-only, original fixed 149 ETFs, original 500 overlapping baskets ×24, 101 monthly 2018-Jan through 2026-May observations with fully matured next-open forward-21D outcome. No first-stage retraining, no production or original V2 modification.

## What is genuinely chronological

This study does NOT choose the one best-of-36 tree on the full historical period. For every evaluation signal date t, consider only each tree's independently past-out-of-sample predictions and realized outcomes at dates **strictly earlier than t minus 60 calendar days**. Treat the entire 500 basket sample within a month as a single metric observation. Evaluate all 36 already-chronologically-trained decision tree settings (expanding or last 36 meta-training months, tree depth 1/2/3, min unique pairs per leaf 100/300, correction probability 0.55/0.6/0.65).

Five deterministic meta-model selection strategies, evaluated as a layer distinct from first-stage ranking:
- NESTED_24_EXCESS: past 24 eligible months' mean forward selected excess; choose only positive.
- NESTED_24_TOP1_GUARD: choose past 24 months' best positive selected excess *subject to historical basket Top1 hit-rate not degrading*.
- NESTED_36_TOP1_GUARD: same rule with last 36 months.
- NESTED_24_CONSERVATIVE and NESTED_36_CONSERVATIVE: accept only when mean past selected excess difference minus 1.64 times its month-level standard error is positive; otherwise no intervention.
- All require at least 24 eligible matured months. When not enough history, fall back to the original ranker; no economic/CAGR tuning.
- The 2018–26 historical span itself and the decision to compare these five meta-selection rules are **not virgin holdout**; this is a strictly chronological exploratory extension, not independent final proof.

## Matched 101-month results, selected forward excess is NOT CAGR

| Rule | Top1 hit | Top3 coverage | nDCG3 | selected 21D forward excess | future loss <=-10% | changed | correction better/worse |
|---|---:|---:|---:|---:|---:|---:|---:|
| Frozen ranker CORRECTED | 14.5525% | 35.4713% | .542279 | +.7122% | 9.2614% | — | — |
| NESTED_24_EXCESS | 14.3465% | 35.4713% | .543059 | +.8193% | 8.5089% | 2800 / 50500 | 1501/1299 |
| **NESTED_24_TOP1_GUARD** | **14.5446%** | **35.4713%** | **.543408** | **+.8554%** | **8.5743%** | **2209 / 50500** | **1326/883** |
| NESTED_36_TOP1_GUARD | 14.4653% | 35.4713% | .543030 | +.8296% | 8.8040% | 2371 / 50500 | 1332/1039 |
| NESTED_24_CONSERVATIVE | 14.4535% | 35.4713% | .542424 | +.7442% | 9.0673% | 488 / 50500 | 266/222 |
| NESTED_36_CONSERVATIVE | 14.5465% | 35.4713% | .542478 | +.7602% | 9.1802% | 407 / 50500 | 252/155 |

The matched Top3 coverage is identical **by construction**, since each meta learner only reorders the frozen Top3. For the guarded 24-month choice, 2209/50500 = 4.37% changes and 1326/2209 = 60.03% of those changes improve the ETF's realized next-open forward-21D return relative to original Top1. Top1 absolute hit-rate difference -0.0079 percentage points (essentially unchanged), mean forward selected excess +0.14320 percentage points, nDCG3 +0.001128 and conditional loss at least 10% reduced -0.6871 percentage points.

## Paired bootstrap uncertainty and stress

Six-calendar-month circular paired bootstrap, 3000 re-samples, **month as independent sampling unit, NOT baskets**. For NESTED_24_TOP1_GUARD vs frozen ranker:
- selected 21D excess difference +0.14320 percentage points, conditional exploratory 95% interval **[+0.0180,+0.2803] percentage points**.
- Top1 difference -0.0079 pp, 95% interval **[-0.2990,+0.2734] pp** (no evidence of Top1 improvement).
- Frequency of losses >=10% difference -0.6871 pp, 95% interval **[-1.2000,-0.2455] pp**.
- Exclude 2026 entirely (96 months): excess improvement **+0.11081 pp**. A separate circular-block bootstrap over those 96 months gives **[+0.00173,+0.24484] pp** using seed 321; lower bound barely positive.
- Exclude both **2022 and 2026** (84 months): improvement drops to **+0.05851 pp**. Exclude 2022, 2025, and 2026 (72 months): only +0.02123 pp. This is a **major regime-concentration caveat**.
- Results by year (pp improvement forward selected excess): 2018 0, 2019 0, 2020 +.0810, 2021 -.0186, 2022 +.4769, 2023 +.1055, 2024 -.0406, 2025 +.2822, Jan–May 2026 +.7651.

The 101 evaluation months are fully matched to baseline, but the same historical calendar was used over many prior ETF-Trader experiments. **Multiple-testing/selection bias remains**, and conditional bootstraps do not correct it. The 500 overlapping baskets cannot be counted as independent trades. These interval estimates are exploratory rather than evidence of a guaranteed positive future alpha.

## Decision

The 24-month guarded nested tree is a promising *candidate postranking correction layer*, not a replacement for first-stage ranker, and not production-qualified. The conservative rule has negligible advantage. It would be unsound to claim a 14.81% Top1 hit-rate now; that number came from choosing the best tree over all 101 months. The chronologically selected version has 14.54% and smaller but more believable improvement in selected 21D mean excess.

Only AFTER functional checks passed may an independent market-next-open, 10-bp one-way, 500-basket Top1/Top2/Top3 economic replay be performed, using existing source-only execution, with original ranking gap for Top2 policy and no risk/Tail changes. That output must match every prior monthly choice before calculating any CAGR. See `nested_economic.py`, `.github/workflows/v3-nested-tree-economic.yml`; the economic step must not change this model selection or tune it by CAGR.

### Traceable artifacts

- `nested_tree_selector.py` — exact train-past-only selection and six-month bootstrap.
- `.github/workflows/v3-meta-nested-tree-validation.yml` — successful independent GitHub CI.
- Source tree OOS predictions from 40031144599; rankers/regressors first stage 40016809498, raw canonical archive 39482809691.
- [Verified nested results zip](https://github.com/AM1975MA/Test/actions/runs/40032282233/artifacts/12535227212).
