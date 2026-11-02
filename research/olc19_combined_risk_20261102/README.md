# OLC19 — ordinary alarm, emergency and explicit reentry

Research only. Read REPORT_IT.md and the preregistered protocol in AM1975MA/Test,
commit bfe8db8b2c9a3485573de1fae20c449b7f0db1d5, path
research/olc19_combined_risk_20261102/PROTOCOL.md.
No production merge or real trading. No new model fitting or stop-threshold search.

Extract OLC19_Rischio_Rientro_Checkpoint_20261102.zip. It contains the authenticated
OLC18 parent under restore/, prepared inputs, 128 paths, event/order logs and tests.
The smaller results archive is not self-contained. A GitHub source checkout alone
requires the prepared binaries at the same paths. No untrusted pickle is required
by this experiment's runner (npz uses allow_pickle=False).

From the extracted olc19_combined_risk_20261102 directory:

```
python -m pytest -q
python src/verify.py
python src/analyze.py
python src/verify_extra.py
```

Full matrix:
```
for m in EU USA; do
  for fee in .001 .003; do
    python src/run_experiment.py --market "$m" --fee "$fee"
  done
  python src/run_experiment.py --market "$m" --fee .001 --stress
done
python src/analyze.py
python src/verify.py
python src/verify_extra.py
```

Five source modules,19 tests. 96base+32stress paths,48exact OLC18 controls.
48pairs of combined/fast paths are identical: alarms use a subset of the fast
stop condition and same cooldown, so this is structural redundancy, not extraalpha.
Risk states are descriptive operational states, not bull/bear regime predictions.
Three-session ticker exclusion prevents buying that ticker until k+4 after a stop
on k. Reentry is permitted, not forced; the current proposal must still select it.
Unused target weight stays defensive, not transferred to the other primary name.

Same-day entry/stop and gaps are logged. OHLC barrier fills with10/50bp friction
are assumptions, not guaranteed executions or a maximum loss bound. Original
fractional position sizing at the printedOpen and source-data/missing-quote issues
remain. U.S. full observed-quote mask was unavailable in the parent. 2026 is partial
toJuly1;2019–20 precedes context adaptation. Larger regime-null experiments,
intraday data verification and shadow operation are not completed by this lot.

Archive MANIFEST_SHA256.json records exact files/bytes. GitHub manifests do not
substitute for Library binary uploads; final remote preservation is recorded
separately. Self-review, not external independent audit.
