#!/usr/bin/env python3
from pathlib import Path

# Keep the certified freezer logic untouched here; extend only fixed candidate
# orders with pre-2017 replacements. No post-2017 performance statistic is
# consulted by this wrapper.
p = Path(__file__).with_name('freeze_eu120_candidates.py')
src = p.read_text()

old_c03 = "'IQQH.DE','IQQW.DE','XMEU.DE','SXR1.DE','SXR4.DE'],\n'C04_EMERGING':"
new_c03 = "'IQQH.DE','IQQW.DE','XMEU.DE','SXR1.DE','SXR4.DE','NORW','FGM','EWUS','PGAL','EURL'],\n'C04_EMERGING':"
if old_c03 not in src:
    raise RuntimeError('C03 insertion anchor not found')
src = src.replace(old_c03, new_c03, 1)

old_c05 = "'ICOV.S','ERNE.L','ERNE.MI','IS3M.DE','ERNE.AS','ERN1.L','ERNE.S','SXRQ.DE','CE01.L','IEBB.MI','IS06.DE','IEAC.L'],\n'C06_REAL_ASSETS':"
new_c05 = "'ICOV.S','ERNE.L','ERNE.MI','IS3M.DE','ERNE.AS','ERN1.L','ERNE.S','SXRQ.DE','CE01.L','IEBB.MI','IS06.DE','IEAC.L','IBTS.L','IBTM.L','IDTL.L','SEMB.L','IHYG.L','SCHO','SCHR','SCHZ'],\n'C06_REAL_ASSETS':"
if old_c05 not in src:
    raise RuntimeError('C05 insertion anchor not found')
src = src.replace(old_c05, new_c05, 1)

exec(compile(src, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
