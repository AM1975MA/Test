#!/usr/bin/env python3
from pathlib import Path

# Keep the certified freezer logic untouched here; extend only the fixed C03
# candidate order with pre-2017 developed-Europe country/factor ETFs. No
# post-2017 performance statistic is consulted by this wrapper.
p = Path(__file__).with_name('freeze_eu120_candidates.py')
src = p.read_text()
old = "'IQQH.DE','IQQW.DE','XMEU.DE','SXR1.DE','SXR4.DE'],\n'C04_EMERGING':"
new = "'IQQH.DE','IQQW.DE','XMEU.DE','SXR1.DE','SXR4.DE','NORW','FGM','EWUS','PGAL','EURL'],\n'C04_EMERGING':"
if old not in src:
    raise RuntimeError('C03 insertion anchor not found')
src = src.replace(old, new, 1)
exec(compile(src, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
