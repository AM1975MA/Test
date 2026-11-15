"""Read-only independent checks of analytical aggregation and paired bootstrap.

This script never imports the analysis implementation or a trading strategy.
The monthly series are summed from daily log changes. Bootstrap replicate
means are obtained from per-month multiplicities rather than sampled arrays.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd


def run(root):
    root = Path(root)
    analysis, output = root / "analysis", root / "validation"
    score = pd.read_csv(analysis / "ALL_SCORECARD.csv", float_precision="round_trip")
    published_months = pd.read_csv(analysis / "MONTHLY_RETURNS.csv", float_precision="round_trip")
    published_years = pd.read_csv(analysis / "ALL_ANNUAL_RETURNS.csv", float_precision="round_trip")
    comparisons = pd.read_csv(analysis / "PAIRED_COMPARISONS.csv", float_precision="round_trip")
    contributions = pd.read_csv(analysis / "ANNUAL_RELATIVE_CONTRIBUTIONS.csv", float_precision="round_trip")
    assert len(score) == 200 and score.arm.nunique() == 40
    cache, annual, metrics = {}, {}, {}
    monthly_checks = annual_checks = 0
    max_monthly_error = max_annual_error = 0.
    for row in score.itertuples(index=False):
        frame = pd.read_csv(root / row.result_directory / row.path_id / "DAILY.csv.gz", float_precision="round_trip")
        dates = pd.to_datetime(frame.date)
        nav = frame.nav_close.to_numpy(float)
        changes = np.log(nav / np.r_[10000., nav[:-1]])
        period = dates.dt.to_period("M")
        independent = pd.Series(changes).groupby(period).sum()
        published = published_months.loc[(published_months.arm == row.arm) & (published_months.scenario == row.scenario)].sort_values("month")
        assert published.month.tolist() == independent.index.astype(str).tolist()
        error = float(np.max(np.abs(independent.to_numpy() - published.log_return.to_numpy())))
        assert error < 1e-12, ("MONTHLY_AGGREGATION", row.path_id, error)
        assert np.allclose(np.expm1(independent), published.simple_return, rtol=0, atol=1e-12)
        monthly_checks += len(independent)
        max_monthly_error = max(max_monthly_error, error)
        cache[(row.arm, row.scenario)] = independent
        previous = 10000.
        for year in sorted(dates.dt.year.unique()):
            end = float(nav[np.flatnonzero(dates.dt.year.to_numpy() == year)[-1]])
            value = end / previous - 1
            published = published_years[(published_years.arm == row.arm) & (published_years.scenario == row.scenario) & (published_years.year == year)]
            assert len(published) == 1
            error = abs(value - float(published.annual_return.iloc[0]))
            assert error < 1e-12, ("ANNUAL_AGGREGATION", row.path_id, year, error)
            annual[(row.arm, row.scenario, int(year))] = value
            previous = end
            annual_checks += 1
            max_annual_error = max(max_annual_error, error)
        elapsed_days = (dates.iloc[-1] - dates.iloc[0]).days + 1
        cagr = float(np.exp(np.log(nav[-1] / 10000.) * 365.2425 / elapsed_days) - 1)
        sampled = np.r_[10000., np.column_stack([frame.nav_open.to_numpy(), nav]).ravel()]
        drawdown = float(np.min(sampled / np.maximum.accumulate(sampled) - 1))
        metrics[(row.arm, row.scenario)] = dict(cagr=cagr, maxdd=drawdown, terminal=float(nav[-1]))
    assert monthly_checks == len(published_months) == 16000
    assert annual_checks == len(published_years) == 1400
    assert len(published_years[published_years.year == 2024]) == 200
    n = len(next(iter(cache.values())))
    assert n == 80
    rng = np.random.default_rng(109)
    starts = rng.integers(n, size=(10000, (n + 5) // 6))
    multiplicity = np.zeros((10000, n), dtype=np.int16)
    replica = np.arange(10000)
    for position in range(n):
        month = (starts[:, position // 6] + position % 6) % n
        multiplicity[replica, month] += 1
    assert np.all(multiplicity.sum(axis=1) == 80)
    findings = []
    for row in comparisons.itertuples(index=False):
        a, b = cache[(row.candidate, "BASE")], cache[(row.control, "BASE")]
        assert a.index.equals(b.index)
        delta = (a - b).to_numpy()
        means = np.asarray(multiplicity @ delta) * (12 / n)
        lower, upper = np.percentile(means, [2.5, 97.5])
        ma, mb = metrics[(row.candidate, "BASE")], metrics[(row.control, "BASE")]
        expected = dict(annualized_log_relative_return=float(delta.sum() * 12 / n),
                        block_bootstrap_log95_low=float(lower), block_bootstrap_log95_high=float(upper),
                        delta_cagr_pp=100 * (ma["cagr"] - mb["cagr"]),
                        delta_sampled_dd_pp=100 * (ma["maxdd"] - mb["maxdd"]),
                        relative_terminal_wealth=ma["terminal"] / mb["terminal"])
        for field, value in expected.items():
            assert np.isclose(getattr(row, field), value, rtol=0, atol=1e-11), ("PAIRED_ANALYSIS", row.candidate, row.control, field, getattr(row, field), value)
        assert row.block_months == 6 and row.replications == 10000 and row.seed == 109 and row.months == n
        for year in range(2020, 2027):
            value = float(delta[np.asarray(a.index.year) == year].sum())
            actual = contributions[(contributions.candidate == row.candidate) & (contributions.control == row.control) & (contributions.year == year)]
            assert len(actual) == 1 and np.isclose(actual.relative_log_wealth_contribution.iloc[0], value, rtol=0, atol=1e-12)
        findings.append(dict(candidate=row.candidate, control=row.control, **expected,
                             interval_contains_zero=bool(lower <= 0 <= upper), status="PASS"))
    assert len(findings) == 16 and len(contributions) == 112
    example_years = {str(year): {arm: annual[(arm, "BASE", year)] for arm in ("DEDUP_DUAL_TREND_OPP", "DUAL21")}
                     for year in (2024, 2025, 2026)}
    result = dict(status="PASS_ALL_ANALYSIS_AND_BOOTSTRAP_CHECKS", financial_paths=200,
                  monthly_return_rows_checked=monthly_checks, annual_return_rows_checked=annual_checks,
                  annual_2024_rows_retained=200, paired_comparisons_checked=len(findings),
                  annual_relative_contribution_rows_checked=112,
                  max_monthly_log_return_error=max_monthly_error, max_annual_return_error=max_annual_error,
                  paired_ci_interpretation="95% descriptive interval for annualized mean paired monthly log-relative return; not a confidence interval for the CAGR percentage-point difference.",
                  multiplicity_corrected=False, adaptive_choices_holdout_valid=False,
                  current_objective_reconciled="CAGR>=30%; drawdown and Calmar are reported, not exclusion gates.",
                  comparisons=findings, example_annual_returns=example_years,
                  analysis_code_sha256=hashlib.sha256((analysis / "analyze_results.py").read_bytes()).hexdigest())
    (output / "BOOTSTRAP_ANALYSIS_REVIEW.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
