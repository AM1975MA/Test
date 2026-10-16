# Neural CAGR and residual sensitivity Implementation Plan

> For agentic workers: execute inline using superpowers:executing-plans; one final bounded review.

**Goal:** obtain verified neural portfolio CAGR and characterize low-variance residuals.
**Architecture:** reuse tested Flatten representation and saved-control replay; expose only PCA variance threshold as a sensitivity parameter.
**Tech Stack:** existing Python/NumPy/Pandas, frozen Actions runtime.
**Spec:** raw_patterns_v1/FULL_PROTOCOL.md and linear_pca_v1/RESIDUAL_PROTOCOL.md.

## Global Constraints
Only AM1975MA/Test. Production untouched. Sources read-only. Three frozen downloads, no Yahoo refresh. No repeated completed fits, no hidden hyperparameter tuning.

## Review Focus
Unknown last labels must not alter input eligibility; raw tensor provenance must not impersonate125feature training; replay coverage exact; covariance threshold must use subtraining only; validation and scaler use past only.

## Task 1: residual thresholds
- [ ] Test configurable90/95/99PCA complementary spaces; run RED then GREEN.
- [ ] Add threshold parameter keeping95default unchanged, derive distinct variant IDs.
- [ ] Matrix Actions90/99only,30fits+3replays per threshold; reuse95results.

## Task 2: neural economic extension
- [ ] Test unknown future labels and pre2011 exclusion, then generalize existing raw panel builder.
- [ ] New full runner90fits, saved checkpoint reconstruction and raw-only provenance audit; exact canonical coverage gate.
- [ ] Distinct strict branch in replay input audit for raw recipe; preserve original125feature fingerprint checks.
- [ ] Full runtime Actions, three replays and existing metric/selection calculations; unit tests and one bounded static review.

## Task 3: evidence
- [ ] Verify Actions success and artifact digests, independently reconcile portfolio paths, persist results and report all outcomes.

Ledger: prior95residual and pre2017pilot completed; do not rerun. User authorizes both extensions. Threshold follow-up90/99is exploratory after seeing95; no independent confirmation claim.
