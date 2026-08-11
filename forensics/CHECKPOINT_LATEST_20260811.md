# METEOR Titanium V2 + Opportunity V3 — latest checkpoint

Canonical package artifact: `9007704034`, inner SHA256 `88e30296c3e610b2761bcc3d470a5259d5c16534ff0caaccec31dddde759a779`.
Frozen immutable references: Titanium V2 Full CAGR `21.6540643747%`; Opportunity Router `22.742810%`.

Final live smoke already passed on branch `titanium-final-live-smoke-20260811`, commit `97f22668060ff9f7d013a0885f0e53332f1b24eb`, run `31468039824`, artifact `9092291105`. Official Opportunity live logic is `target_excess_max_pred`. Smoke signal 2026-07-31: USL/DBO, base 75/25, direct=true, router_on=true, final 100% USL.

## Compact maturity audit
Branch `titanium-maturity-audit-run-20260811`, commit `1453929fe98ad57c9a9cbc375535041cc0bb856a`, run `31525244196`.

`d42` is the best parity candidate and the only tested maturity rule matching the deterministic USO/PALL checkpoint.
- Base mean CAGR 17.9602%; Router mean 17.8894%.
- D1 Base 12.9693% vs 15.0230% frozen: -2.0537 pp.
- D2 Base 22.8754% vs 22.6450%: +0.2304 pp.
- DEV Base 17.6962% vs 18.6170%: -0.9208 pp.
- FULL Base 17.9675% vs 21.654064%: -3.6866 pp.
- segment RMSE 1.3062 pp.
- artifact `9114935822`.

Other maturity variants:
- monthly: checkpoint USO/BNO fail; Full error -3.6711 pp; RMSE 2.3424; artifact 9114889449.
- d21: checkpoint PALL/USO fail; Full error -5.4380 pp; RMSE 2.7430; artifact 9114953329.
- signal: checkpoint PALL/USO fail; Full error -4.2466 pp; RMSE 2.3698; artifact 9114942300.

Inference: D42 maturity explains part of the historical discrepancy and nearly recovers D2, but not D1/Full. Base parity remains unresolved; do not tune Opportunity/governor to mask it.

Resume order: inspect seed ensemble -> score transform/re-ranking -> exact frozen execution -> historical F2D recovery -> exact V23 membership/data parity. Choose only variants preserving USO/PALL and causal invariants, then regenerate final package, rerun 500 baskets + unrestricted universe, permanently patch live Opportunity logic, live-smoke, manifests and SHA256.
