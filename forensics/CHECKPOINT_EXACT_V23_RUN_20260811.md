# Titanium exact V2.3 membership — active resume checkpoint

Saved 2026-08-11 after resuming from archaeology.

## Why this test is now highest priority
The canonical regenerated package's `BASKET_MEMBERSHIP_500.csv` does not match the recovered V2.3 construction. Reconstructed V2.3 rule: six categories, exactly 4 ETFs/category, `random.Random(20260721)`, 500 unique 24-ETF baskets. Basket-by-basket sorted ticker-position agreement with current canonical membership was only 3.6583%, so membership is a material unresolved parity variable.

## Inputs held fixed
- Canonical package artifact: 9007704034
- Canonical OHLCV matrices from that package are reused; no data redownload in this isolation test.
- Verified base source SHA256: 76b5da95c865a069d967189d61b1c8df3338eacc5a0e8941e8ee7025c42caf60
- Verified V5 source SHA256: ba99f9ce08d96e6b56567d44bf18b5caa7a76ccf13a7d44546e6d1416d79d65a
- Models: 360 estimators, seed ensemble 101/202/303
- Downvol mode for this isolation run: downside_rms
- Only intended structural change: exact V2.3 basket membership.

## Execution branch and run
- Branch: `titanium-exact-v23-membership-20260811`
- Draft PR: #31, never merge to main
- Branch-only workflow: `.github/workflows/titanium-v23-canonical-push.yml`
- Execution script: `regeneration/run_exact_v23_membership_from_canonical.sh`
- Trigger commit: `bc3650ae8fdd279f2e1d3ebd50dbe66bf7cc4dbb`
- Workflow run: `31533417031`
- Job: `93918681198`
- Job name: `exact-v23`
- State at checkpoint: in_progress; dependency installation running.

## Next actions
1. Wait for run 31533417031 to complete and download artifact `TITANIUM_EXACT_V23_CANONICAL_MEMBERSHIP`.
2. Read `EXACT_V23_CANONICAL_VALIDATION.json` and compare Base/Router means to canonical current package and frozen 21.654064% / 22.742810%.
3. If membership materially closes the gap, combine exact V2.3 membership with the already-best `d42` maturity rule (the only maturity candidate matching USO/PALL and D2 within +0.2304 pp).
4. Keep Base parity as the blocking acceptance criterion before changing Opportunity/governor.
5. Once Base is recovered/closest defensible, permanently apply official live Opportunity `target_excess_max_pred`, regenerate final package, 500-basket distribution, Global150/unrestricted result, manifests/SHA256, and rerun live smoke.
