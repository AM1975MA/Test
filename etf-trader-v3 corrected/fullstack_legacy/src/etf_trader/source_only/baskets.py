"""Deterministic canonical Super Gold basket generation from ETF universe metadata."""
from __future__ import annotations

import random
from typing import Iterable

import pandas as pd

BASKET_SEED = 20260721
BASKET_COUNT = 500
PER_CATEGORY = 4
EXPECTED_CATEGORY_COUNT = 6


def build_canonical_baskets(
    universe: pd.DataFrame,
    available_tickers: Iterable[str],
    *,
    seed: int = BASKET_SEED,
    basket_count: int = BASKET_COUNT,
    per_category: int = PER_CATEGORY,
) -> pd.DataFrame:
    """Rebuild the authentic 500x24 membership from source-defined RNG logic.

    Only universe/category metadata and the raw-data ticker set are consumed.
    The historical membership CSV is not required.
    """
    if "ticker" not in universe.columns:
        raise KeyError("universe missing column: ticker")
    category_col = (
        "macro_category"
        if "macro_category" in universe.columns
        else ("category" if "category" in universe.columns else None)
    )
    if category_col is None:
        raise KeyError(
            "universe missing category column: expected macro_category or category"
        )

    available = set(map(str, available_tickers))
    u = universe.copy()
    u["ticker"] = u["ticker"].astype(str)
    u = u[u["ticker"].isin(available)].copy()

    categories = sorted(u[category_col].dropna().unique())
    if len(categories) != EXPECTED_CATEGORY_COUNT:
        raise RuntimeError(f"Expected six macro categories, found {categories}")

    category_tickers = {
        category: sorted(
            u.loc[u[category_col].eq(category), "ticker"].unique()
        )
        for category in categories
    }
    insufficient = {
        category: len(names)
        for category, names in category_tickers.items()
        if len(names) < per_category
    }
    if insufficient:
        raise RuntimeError(f"Insufficient tickers by category: {insufficient}")

    rng = random.Random(seed)
    baskets: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    attempts = 0
    while len(baskets) < basket_count and attempts < 500000:
        attempts += 1
        selected: list[str] = []
        for category in categories:
            selected.extend(rng.sample(category_tickers[category], per_category))
        basket = tuple(sorted(selected))
        if basket not in seen:
            seen.add(basket)
            baskets.append(basket)

    if len(baskets) != basket_count:
        raise RuntimeError(f"Created only {len(baskets)} unique baskets")

    return pd.DataFrame(
        [
            {"basket": basket_id, "ticker": ticker}
            for basket_id, basket in enumerate(baskets)
            for ticker in basket
        ]
    )
