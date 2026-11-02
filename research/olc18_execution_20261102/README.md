# OLC18 stop-contract validation

Research only. Read PROTOCOL.md, NET_TARGET_EXTENSION.md and final report. Neither stop fills nor same-auction proportional sizing are certified by daily OHLC. No new ranking fit. All four ranking controls and both markets remain paired.

Extract the delivered checkpoint into one directory. It includes parent_archive (authenticated OLC17), prepared states, all192paths, events, source and tests. A GitHub text checkout alone does not contain the input binaries. No arbitrary joblib/pickle should be loaded.

Run from project root:
```
python -m pytest -q
python src/verify.py
python src/analyze.py
```

Full rebuild:
```
python src/run_experiment.py --prepare
for m in EU USA; do
  for fee in .001 .003; do
    python src/run_experiment.py --market "$m" --fee "$fee"
    python src/run_experiment.py --market "$m" --fee "$fee" --net
  done
  python src/run_experiment.py --market "$m" --fee .001 --stress
done
python src/verify.py
python src/analyze.py
```

192distinctpaths:128base+32fillstress+32post-observationnetcontrols. Zero-cost verification adds16paired diagnostics,not new selected strategies. Replay filename S100/S500 is a historical internal tag: authoritative friction is the decimal field in SCORECARD/AUDIT (.001/.005); those tags are NOT basis-point units.

Original reference32paths exactly reproduce OLC17V6consistent outputs. New31tests and inherited30tests pass in their roots. Parent has3known initial-history warnings. The complete historical repository is not declared green. Review by the author,not external audit.

EOD_LOW/CLOSE pay proceeds at next opening boundary before ordinary rebalance; ledger units there are post-exit valuation quantities. NET keeps overnight units and trades once at next open. Same NAV at zero frictions; conventional recorded intraday position metrics are not interchangeable. Stop price is a trigger,not guaranteed fill. 2026endsJuly1 and is not a full year. Codes,nominal costs and all priordata limits are explained in report.
