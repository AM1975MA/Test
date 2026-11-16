# OLC112 — Protection with the monthly selector preserved

Post-OLC111 structural diagnosis,16 November2026. Uses exactly the already fitted OLC111 models; changes only the invested account's scheduled monthly default. Initial and warmup behavior remain baseline, cash accounts still wait for an ENTRY signal, and daily discretionary actions remain the frozen OLC111 rule.

Read `docs/DESIGN_AND_PROTOCOL.md` for the predeclared adaptive design and `RAPPORTO_OLC112_IT.md` for the results. OLC111's rejected options-information hypothesis and its18 paths remain unchanged and accessible in the sibling directory.

```bash
python -m unittest discover -s research/olc112/tests
python research/olc112/src/run_rotation_overlay.py --root research/olc112 --resume
```

Restore the OLC111 external inputs using its `docs/RESTORE_INPUTS.md`. OLC112 also requires all frozen OLC111 monthly fit files and its complete control paths. No new source download, fitting, parameter search, trade or production workflow is part of this experiment.
