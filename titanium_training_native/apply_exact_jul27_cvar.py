#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    start=s.index('def rolling_cvar10(ret,h):')
    end=s.index('\ndef rolling_autocorr',start)
    exact=r'''def rolling_cvar10(ret, h):
    """Exact July-27 implementation: mean of the k worst observations in each window."""
    arr = ret.to_numpy(float)
    n, m = arr.shape
    out = np.full((n, m), np.nan, dtype=float)
    if n < h:
        return pd.DataFrame(out, index=ret.index, columns=ret.columns)
    windows = np.lib.stride_tricks.sliding_window_view(arr, h, axis=0)
    chunk_size = 256
    max_k = int(np.floor((h - 1) * 0.10) + 1)
    for start0 in range(0, len(windows), chunk_size):
        w = windows[start0:start0 + chunk_size]
        finite = np.isfinite(w)
        counts = finite.sum(axis=2)
        k = np.where(counts > 0, np.floor((counts - 1) * 0.10).astype(int) + 1, 0)
        safe = np.where(finite, w, np.inf)
        worst = np.partition(safe, max_k - 1, axis=2)[:, :, :max_k]
        csum = np.cumsum(worst, axis=2)
        row = np.arange(w.shape[0])[:, None]
        col = np.arange(m)[None, :]
        picked = np.where(
            k > 0,
            csum[row, col, np.maximum(k - 1, 0)] / np.maximum(k, 1),
            np.nan,
        )
        out[h - 1 + start0:h - 1 + start0 + w.shape[0]] = picked
    return pd.DataFrame(out, index=ret.index, columns=ret.columns)
'''
    s=s[:start]+exact+s[end:]
    p.write_text(s)
    print('Applied exact July-27 rolling_cvar10')

if __name__=='__main__': main()
