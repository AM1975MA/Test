# OLC22 — fixed target hysteresis results

2 November 2026. Exploratory historical control; no new ETF learner or risk parameter.

## Coverage
Seven margins on exact OLC20 AUTH FUSION: 0, .005, .01, .02, .04, .08, .12. Same margin in EU and USA. Candidate-specific V6, ALARM/FAST_LOCK3, fees .001/.003. Margin0 reproduces AUTH account arrays exactly. Three local tests pass.

Positive margins suppress replacements as designed. Over the full 90 signal dates, suppressed replacements range from 4 EU / 9 USA at margin .005 to 67 EU / 72 USA at margin .12.

## Primary result
No positive margin improves CAGR over margin0 in both universes. Every tested positive margin is economically worse in both markets on the 2021–2024 primary window.

FAST_LOCK3, fee .001:
- margin0: EU 23.200%, USA 50.772%, MaxDD -28.608% / -20.226%
- margin .005: EU 19.986%, USA 41.211%
- margin .01: EU 17.079%, USA 43.552%
- margin .02: EU 20.027%, USA 29.811%
- margin .04: EU 21.939%, USA 28.387%
- margin .08: EU 17.673%, USA 22.144%
- margin .12: EU 10.162%, USA 19.356%

The sign remains adverse under fee .003 and on the full 2019–2026 history. Turnover falls, but the lost opportunity from delayed replacements dominates the saved turnover cost.

## Interpretation
A fixed keep-buffer is rejected as a common improvement. The result does not imply that every held ticker should always be replaced; it shows that persistence must be conditional. This supports the next roadmap item: a differential residual-value model trained only on mature past replacement outcomes, while leaving AUTH ranking itself frozen.

The hysteresis rule used the previous proposed target, not the actual post-stop holding. This limitation is explicit and does not explain the broad negative result by itself.
