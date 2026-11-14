# OLC106 — USA source-scale bridge, before economic outcomes

The first price preparation stopped at the source-parity gate; no strategy replay was produced. OLC104 historical USA prices and the OLC100 captured append use differing fixed economic-unit scales on overlapping June/July 2026 dates. Example DIA: ratio 1.0002188 across all eight common dates. SOXX ratio approximately 3.0. This is not a reason to ignore a discontinuity or widen a tolerance.

Diagnostic across all 149 tickers: compute one positive scale as median(OLC104 Close / capture adjusted Close) across the existing overlap. After that one constant rescaling, worst relative error is 2.1341e-7 for Close and Open; all 149 pass a fixed 1e-5 acceptance gate. If the ratios are not constant on both Open and Close within that tolerance, preparation fails.

Implementation: leave OLC104 history and raw archives untouched; multiply only the appended O/C economic-price proxies by that per-ticker constant. This preserves all within-append returns and reconciles economic units; it does NOT certify corporate actions, broker physical shares, total return or an original point-in-time vintage. The raw and scaled diagnostics and regression tests are included. No split ratio is inferred from an isolated return and no outcome is clipped.

All trading rules and primary dates remain unchanged. Data are retrospective. This source-unit correction is recorded before any OLC106 portfolio result.
