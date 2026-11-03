# OLC36 — EU-only persistent dominant core (research, not trading)

Protocol frozen pre-outcome: https://github.com/AM1975MA/Test/commit/6cc8790fec75154dc3a71f1e48e34b2744901166

Requires Python 3.11+, pandas, numpy, matplotlib; the source archive `OLC32_RESULTS.zip` in `input/`, SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d`.

```
python src/run_olc36.py
python src/verify_olc36.py
```

The first script may overwrite **research outputs in this experiment only**. No modification to live strategies or GitHub `main`; no USA decisions made. Run with working directory anywhere, scripts resolve paths relative to package root. Both use original OLC32 corrected labels and as-of score columns, not future labels for candidate selection. `results/OLC36_MANIFEST.json` records SHA256 of output files (excluding the independent verification file because it is written afterward). The diagnostic's annual compounding is a hypothetical monthly equal-weight 50/50 Open-to-Open account **without** V6 and intramonth stop logic; it is not the OLC19 NAV.

Keep `PROTOCOL_PRE_OUTCOME.md` immutable. Refer to `RESULTS_IT.md` for complete result and limitations. The 2019–2026 data have been investigated many times; only genuinely later signals, frozen before outcomes, would provide new independent evidence.
