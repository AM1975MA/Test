# OLC111 — Daily cash, hold and fresh-entry research

Exploratory ETF strategy research,16 November2026. No trading API or production workflow is changed.

The new information hypothesis is the **shape of option-implied volatility across maturities**, not VIX level or another stop-loss parameter search. Four matched learned controls use historical means, price/account state, legacy VIX inputs, and the additional VIX9D/VIX and VIX/VIX3M ratios. The frozen OLC109 candidate selector remains unchanged. Daily decisions can preserve actual units, move to cash, or buy the fresh basket, including remaining cash across a monthly boundary.

The study uses the same2,096-ISIN EUR panel as OLC109/110. This is a current-catalog research universe with historical eligibility and liquidity filters; it is not a survivor-free history of every ETF that ever existed. Native account costs, source-quality and execution limitations are retained.

## Documents and outputs

- `RAPPORTO_OLC111_IT.md`: results, interpretation and limits in Italian.
- `docs/DESIGN_AND_PROTOCOL.md`: authoritative design frozen before new forecasts.
- `docs/BANK_FREEZE.json`: code/input/protocol identities before label construction.
- `docs/EXPERIMENT_FREEZE.json`: complete executable-study freeze before forecasts/accounts.
- `results/`: prequential forecast ledger, monthly fits,18 full account paths, aggregate metrics and diagnostics.
- `data/BANK_EVENTS.jsonl`: trigger-independent matched-state comparison records, including missing support and right-edge statuses.
- `data/BANK_CASH.npz`, `BANK_FRESH.npz`, `BANK_ENTRY.npz`: small model-ready banks, with explicit signal and terminal indices.
- `research/history/PRIOR_RESEARCH_REVIEW.md`: evidence from45 earlier research branches; no novelty claim for techniques already tested.
- `research/restore/PIPELINE_REVIEW.md`: independent review of label generation and causal/execution boundaries.
- `docs/RESTORE_INPUTS.md`: exact external input identities and restoration instructions.

## Reproduce

Keep `olc111` and `olc110` as sibling directories, as under `research/` in this repository. Restore the two large input panels to OLC110 and the exact Cboe source files to OLC111 using `docs/RESTORE_INPUTS.md` before executing.

```bash
python -m pip install -r research/olc111/requirements.txt
python -m unittest discover -s research/olc111/tests
python research/olc111/src/run_olc111.py --root research/olc111 --resume
```

`--resume` verifies source, code and cache provenance. It must not combine a changed dataset or changed protocol with old labels. Existing result artifacts describe the frozen run; preserve them before a deliberate independent reproduction. The primary convention is next accepted Close; normal next Open and doubled next-Close transaction costs are declared sensitivities.

## Reading performance correctly

The model needs504 mature distinct dates and24 nonoverlapping outcome intervals per head. All three heads must be ready before any learned action. Earlier performance belongs to the unchanged baseline. Report the common period starting with the first executable session after readiness separately; compare every policy on identical dates and its own preceding NAV.

Chronological fitting prevents training on unmatured future outcomes. It does not turn this heavily researched historical period into an untouched holdout. Bootstrap buffers are decision heuristics, not calibrated confidence. One-time21-session action advantages are not additive, cannot be annualized into CAGR, and do not guarantee performance of repeated daily actions.
