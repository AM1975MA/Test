#!/usr/bin/env python3
from pathlib import Path

p = Path('regeneration/regenerate_live_package.py')
s = p.read_text()
old = "    baskets, cats = v5.make_baskets(base, pred, args.n_baskets);idx, EB, ED, ER, active, margin, cond, bs, bw, ds, dw = v5.simulate_all(baskets, pred, opp_pred, clusters, mats, cal)"
new = '''    import random as _random
    _tickers = sorted(pred.ticker.astype(str).unique())
    _categories = sorted({base.TICKER_CATEGORY[t] for t in _tickers if t in base.TICKER_CATEGORY})
    if len(_categories) != 6:
        raise RuntimeError(f'Canonical V23 requires six categories, got {_categories}')
    _category_tickers = {c: sorted([t for t in _tickers if base.TICKER_CATEGORY.get(t) == c]) for c in _categories}
    _insufficient = {c: len(v) for c, v in _category_tickers.items() if len(v) < 4}
    if _insufficient:
        raise RuntimeError(f'Insufficient V23 tickers by category: {_insufficient}')
    _rng = _random.Random(20260721)
    baskets, _seen, _attempts = [], set(), 0
    while len(baskets) < args.n_baskets and _attempts < 500000:
        _attempts += 1
        _selected = []
        for _c in _categories:
            _selected.extend(_rng.sample(_category_tickers[_c], 4))
        _basket = tuple(sorted(_selected))
        if _basket not in _seen:
            _seen.add(_basket)
            baskets.append(_basket)
    if len(baskets) != args.n_baskets:
        raise RuntimeError(f'Could not construct canonical V23 membership: {len(baskets)}')
    cats = _categories
    _v23 = pd.DataFrame([{'basket': i, 'ticker': t} for i, b in enumerate(baskets) for t in b])
    _sizes = _v23.groupby('basket').ticker.nunique()
    if len(_sizes) != args.n_baskets or not _sizes.eq(24).all():
        raise RuntimeError(f'Canonical V23 membership validation failed: baskets={len(_sizes)}, range=({_sizes.min()},{_sizes.max()})')
    _v23.to_csv(root/'panels'/'V23_BASKET_MEMBERSHIP.csv', index=False)
    idx, EB, ED, ER, active, margin, cond, bs, bw, ds, dw = v5.simulate_all(baskets, pred, opp_pred, clusters, mats, cal)'''
if old not in s:
    if "V23_BASKET_MEMBERSHIP.csv" in s and "Random(20260721)" in s:
        print('canonical V23 patch already present')
    else:
        raise SystemExit('Target generator line not found; refusing non-certified patch')
else:
    p.write_text(s.replace(old, new, 1))
    print('canonical V23 patch applied')
