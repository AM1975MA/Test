#!/usr/bin/env python3
"""Restore the minimal byte-identical OLC19 engine, decision state and frozen reference needed by OLC75."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parent
SRC=Path('/mnt/data/etf_source/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
PFX='olc19_combined_risk_20261102/'
DST=ROOT/'native'
EXPECTED='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
h=hashlib.sha256(SRC.read_bytes()).hexdigest();assert h==EXPECTED,h
with zipfile.ZipFile(SRC) as z:
    selected=[]
    for n in z.namelist():
        if not n.startswith(PFX) or n.endswith('/'):continue
        v=n[len(PFX):]
        ok=(v=='src/combined_engine.py' or
            v=='restore/olc18_execution_20261102/parent_archive/src/validated_engine.py' or
            v.startswith('restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/src/') and v.endswith('.py') or
            v.startswith('restore/olc18_execution_20261102/src/') or
            v in ('restore/olc18_execution_20261102/inputs/EU_TOP2_CONTEXT_REVALUE.npz',
                  'restore/olc18_execution_20261102/inputs/USA_TOP2_CONTEXT_REVALUE.npz') or
            v=='restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/src/portfolio_metrics_parent.py' or
            v in [f'results/paths/{m}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz' for m in ('EU','USA')])
        if ok:
            dest=DST/v;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n));selected.append(v)
print('OLC19 source parity OK, files extracted',len(selected),'source SHA',h)
(ROOT/'INPUT_SHA256.json').write_text(json.dumps({'OLC19':h,'extracted_files':selected},indent=2))