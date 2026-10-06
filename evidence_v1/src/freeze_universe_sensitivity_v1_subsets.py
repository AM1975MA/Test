#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

SALT = "evidence-v1-universe-sensitivity-v1"
ANCHOR = "SPY"
SIZES = (120, 100, 70)


def htext(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hfile(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    u = pd.read_csv(args.universe)
    if list(u.columns) != ["ticker", "macro_category"]:
        raise RuntimeError("unexpected universe schema")
    u["ticker"] = u.ticker.astype(str).str.upper()
    u["macro_category"] = u.macro_category.astype(str)
    u = u.drop_duplicates().sort_values(["macro_category", "ticker"]).reset_index(drop=True)
    if len(u) != 149 or u.ticker.nunique() != 149:
        raise RuntimeError(f"expected frozen Original149, got {len(u)} rows")
    if ANCHOR not in set(u.ticker):
        raise RuntimeError(f"mandatory calendar anchor {ANCHOR} missing")

    total = len(u)
    cat_sizes = u.groupby("macro_category").size().to_dict()
    by_cat: dict[str, list[str]] = {}
    digest: dict[str, str] = {}
    for cat, g in u.groupby("macro_category", sort=True):
        rows = []
        for t in g.ticker.astype(str):
            d = htext(f"{SALT}|{t}")
            digest[t] = d
            rows.append((d, t))
        by_cat[str(cat)] = [t for _, t in sorted(rows)]

    anchor_cat = str(u.loc[u.ticker.eq(ANCHOR), "macro_category"].iloc[0])
    order = [ANCHOR]
    selected_by_cat = {c: 0 for c in sorted(by_cat)}
    selected_by_cat[anchor_cat] = 1
    cursors = {c: 0 for c in sorted(by_cat)}
    # Advance the anchor category cursor past SPY while preserving the hash order.
    while cursors[anchor_cat] < len(by_cat[anchor_cat]) and by_cat[anchor_cat][cursors[anchor_cat]] != ANCHOR:
        cursors[anchor_cat] += 1
    if cursors[anchor_cat] >= len(by_cat[anchor_cat]):
        raise RuntimeError("anchor not found inside its category")
    cursors[anchor_cat] += 1

    # Nested, category-balanced deterministic priority. At each prefix length k,
    # choose the category with the largest proportional deficit versus Original149;
    # ties are broken by category name. Within category, use salted SHA256 order.
    while len(order) < total:
        k = len(order) + 1
        candidates = []
        for cat in sorted(by_cat):
            remaining = [t for t in by_cat[cat] if t not in set(order)]
            if not remaining:
                continue
            deficit = k * cat_sizes[cat] / total - selected_by_cat[cat]
            candidates.append((deficit, cat))
        if not candidates:
            raise RuntimeError("priority construction exhausted early")
        _, chosen_cat = max(candidates, key=lambda z: (z[0], -ord(z[1][0]) if z[1] else 0, z[1]))
        # Deterministic category tie-break explicitly by lexicographic minimum among max deficit.
        max_def = max(x[0] for x in candidates)
        chosen_cat = sorted(c for d, c in candidates if abs(d - max_def) <= 1e-15)[0]
        remaining = [t for t in by_cat[chosen_cat] if t not in set(order)]
        chosen = remaining[0]
        order.append(chosen)
        selected_by_cat[chosen_cat] += 1

    if len(order) != 149 or len(set(order)) != 149:
        raise RuntimeError("priority order is not a permutation of Original149")
    if order[0] != ANCHOR:
        raise RuntimeError("anchor is not first")

    meta = u.set_index("ticker")["macro_category"].to_dict()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    priority = pd.DataFrame({
        "priority": range(1, len(order) + 1),
        "ticker": order,
        "macro_category": [meta[t] for t in order],
        "salted_sha256": [digest[t] for t in order],
    })
    priority.to_csv(out / "PRIORITY_ORDER.csv", index=False)

    subset_files = {}
    category_counts = {}
    previous: set[str] | None = None
    for n in SIZES:
        sub = priority.head(n)[["ticker", "macro_category"]].copy()
        path = out / f"U{n}.csv"
        sub.to_csv(path, index=False)
        subset_files[f"U{n}"] = hfile(path)
        category_counts[f"U{n}"] = sub.groupby("macro_category").size().astype(int).to_dict()
        cur = set(sub.ticker)
        if ANCHOR not in cur:
            raise RuntimeError(f"{ANCHOR} missing from U{n}")
        if previous is not None and not previous.issuperset(cur):
            raise RuntimeError("subsets are not nested")
        previous = cur

    manifest = {
        "protocol": "universe_sensitivity_v1",
        "source_universe": "Original149 frozen metadata only",
        "source_universe_rows": 149,
        "selection_uses_prices_or_performance": False,
        "salt": SALT,
        "mandatory_calendar_anchor": ANCHOR,
        "method": "nested proportional-deficit category balancing; salted SHA256 order within category",
        "sizes": list(SIZES),
        "category_counts_original149": {k: int(v) for k, v in cat_sizes.items()},
        "category_counts_subsets": category_counts,
        "priority_order_sha256": hfile(out / "PRIORITY_ORDER.csv"),
        "subset_sha256": subset_files,
    }
    (out / "SUBSET_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
