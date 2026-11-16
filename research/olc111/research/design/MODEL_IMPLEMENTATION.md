# OLC111 action-advantage learner

Implemented16 November2026 in `olc111/src/advantage_model.py`. This module fits one action head from supplied native net labels; it does not build counterfactual accounts, change a trading policy, subtract transaction fees, or run financial returns. The root investigator owns labels, feature generation, the account runner and the final frozen protocol.

## API

```python
fit_head(
    Xprice, Xlegacy, Xterm, y, signal_idx, terminal_idx, cutoff,
    min_dates=504, min_blocks=24, n_boot=100, seed=111, penalty=1.0,
)
```

The three feature arrays have shape `(rows, features)`. Targets and session-index arrays are one-dimensional. A successful fit returns:

```python
{
    "models": {"MEAN": model, "PRICE": model, "VIX": model, "TERM": model},
    "meta": {...},
}
```

It returns `None` until both readiness conditions pass. Each model supports `predict(price, legacy, term)` on one-dimensional feature vectors, returning `{"mean": float, "lower": float}`. `lower` is the10th percentile of100 block-bootstrap conditional-mean predictions. `to_dict()` exports transforms, coefficients, all bootstrap coefficients, feature counts and metadata as JSON-serializable values. No fee or additional hurdle is subtracted in prediction.

## Chronology and common support

The mask is applied **before** any standardization, projection or target fitting. All four arms use exactly the same finite observations across price, legacy, term and net labels. Signal/terminal indices must be finite integers, the terminal must be at least21 sessions after the signal, and `terminal_idx < cutoff` is strict. A boundary label ending at the cutoff is excluded.

Readiness requires504 distinct valid signal dates and at least24 nonoverlapping outcome intervals. Each date contributes one interval, with its latest required terminal endpoint if several state rows share the date. The greedy interval count sorts by ending session; intervals can meet at their boundary because return increments after that boundary do not overlap. Longer declared maturity intervals are respected.

Every date has total training weight one before normalization, divided among its surviving state rows. A date with many hypothetical states cannot acquire more market-history weight than a date with one state. Metadata reports both rows and dates, including `n_rows`, `n_dates`, `n_nonoverlap_blocks` and `max_terminal_idx`.

## Nested information and Ridge scaling

PRICE features are standardized with date weights on the mature training sample. Legacy VIX features are first projected on PRICE plus an intercept using weighted least squares; only their standardized residuals enter the VIX arm. TERM features are similarly projected on PRICE and LEGACY plus an intercept. The standardized residual basis for LEGACY spans the same additional information as the original legacy columns; this keeps the TERM projection numerically stable.

Numerical residuals from an exactly collinear block are set to zero rather than inflated into artificial unit-variance features. The tolerance is `1e-10 * max(1, original_column_max_abs)`; active-column flags and scaling statistics are saved in the fitted artifact.

For each arm, the solver minimizes:

`sum(normalized_date_weight * squared_error) + penalty * sum(nonintercept_coefficients**2)`.

Thus `penalty=1.0` is on **mean** weighted squared error, not an unnormalized sum over ETF rows. The intercept is unpenalized. MEAN uses only that intercept. The labels are native **net** log-wealth advantages, without clipping, a fee offset or a second cost subtraction.

## Bootstrap contract and practical limits

Fixed blocks use `signal_idx // 63`, anchored to the supplied global exchange-session index. For each of100 replicates, the implementation draws the available blocks with replacement, retaining all rows and date-balanced weights within each selected block. It normalizes weights within the replicate. The same block draw matrix is used for MEAN, PRICE, VIX and TERM within a head. Its SHA256 is stored as `bootstrap_counts_sha256`.

All transformations remain fixed from the complete mature training sample during this coefficient bootstrap, as directed by the root investigator. This is a **conditional coefficient uncertainty heuristic**, not a calibrated confidence interval: it excludes uncertainty in standardization/projection, depends on a small number of market blocks, and does not undo the extensive reuse of this historical sample. Separate heads may have different supported dates and therefore different available blocks; pairing is guaranteed across the four information arms of each head.

The module rejects nonfinite required prediction features. PRICE can still predict when external option features are unavailable because it does not inspect unused LEGACY/TERM inputs; VIX similarly does not require TERM. The runner remains responsible for explicit fallback logging and actual-account support checks.

## Verification

The14 behavioral tests were written first and initially failed because the learner did not exist. After implementation they passed. They cover:

- Strict outcome maturity and future-label mutation invariance.
- Prefix/future-feature invariance of complete fitted artifacts.
- Distinct-date readiness and nonoverlapping21-session interval counts.
- Equal date influence under duplicated rows.
- Common finite support across all information arms.
- No artificial signal from collinear residual blocks.
- Analytically known Ridge shrinkage under mean-loss normalization.
- Preservation of already-net, unclipped action-advantage labels.
- Whole63-session block resampling, deterministic seeds and pairing.
- Complete finite JSON exports and valid lower-information fallbacks.

Focused command: `python -m unittest discover -s olc111/tests -p test_advantage_model.py`.

Full project command: `python -m unittest discover -s olc111/tests`.

All test data are synthetic. No financial-label fit, performance optimization or portfolio-return simulation was run by this implementation agent.
