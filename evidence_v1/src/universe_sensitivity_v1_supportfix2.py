#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import universe_sensitivity_v1 as base
import universe_sensitivity_v1_supportfix as supportfix


def fixed_on_evaluation_support(
    checkpoint: pd.DataFrame,
    support: pd.DataFrame,
    subset: str,
) -> pd.DataFrame:
    """Materialize anchor A only where the preregistered test evaluates it.

    B/C still train on the entire common historical support. The frozen Retriever
    checkpoint begins in 2011, while source-only panels include earlier rows.
    Anchor A is only used in the 2017-01-01..2026-06-30 evaluation window, so
    pre-evaluation keys are neither required nor silently imputed.
    """
    keys = ["signal_date", "ticker"]
    cp = checkpoint.copy()
    cp["signal_date"] = pd.to_datetime(cp.signal_date)
    cp["ticker"] = cp.ticker.astype(str)

    s = support[keys].copy()
    s["signal_date"] = pd.to_datetime(s.signal_date)
    s["ticker"] = s.ticker.astype(str)
    s = s[
        (s.signal_date >= base.EVAL_START)
        & (s.signal_date < base.EVAL_END)
    ].copy()
    if s.empty:
        raise RuntimeError(f"{subset}: empty common support in evaluation window")

    x = s.merge(
        cp[keys + ["LTR_SCORE"]],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    if x.LTR_SCORE.isna().any():
        miss = x.loc[x.LTR_SCORE.isna(), keys].head(10).to_dict("records")
        raise RuntimeError(
            f"{subset}: evaluation common-support keys missing from frozen LTR checkpoint: {miss}"
        )
    x = x.sort_values(
        ["signal_date", "LTR_SCORE", "ticker"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    x["FIXED_RANK"] = x.groupby("signal_date").cumcount() + 1
    return x[keys + ["LTR_SCORE", "FIXED_RANK"]].rename(
        columns={"LTR_SCORE": "FIXED_SCORE"}
    )


supportfix.fixed_on_support = fixed_on_evaluation_support

if __name__ == "__main__":
    raise SystemExit(supportfix.main())
