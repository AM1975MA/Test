#!/usr/bin/env python3
"""Package only original EU source members; no data alteration; preserve original paths and hashes."""
import zipfile,hashlib,json,argparse
from pathlib import Path

def h(b):return hashlib.sha256(b).hexdigest()
def make(a,b,dst):
 pick19=[
  '/inputs/EU_STATE_HALF.npz',
  '/results/paths/EU_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz',
  'olc19_combined_risk_20261102/results/SCORECARD.csv']
 pick32=['results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz','results/REPAIRED_CALENDAR_AUDIT.csv']
 dd={}
 with zipfile.ZipFile(a) as z:
  for k in pick19:
   names=[s for s in z.namelist() if s.endswith(k)];assert len(names)==1,(k,names)
   dd[names[0]]=z.read(names[0])
 with zipfile.ZipFile(b) as z:
  for k in pick32:
   names=[s for s in z.namelist() if s.endswith(k)];assert len(names)==1,(k,names)
   dd[names[0]]=z.read(names[0])
 dst=Path(dst);dst.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for k in sorted(dd):z.writestr(k,dd[k])
 manifest={'NOTE':'Compact original member bytes, not an independent data vendor or a replacement for the historical parent input archives.',
 'original_OLC19_zip_sha256':h(Path(a).read_bytes()),'original_OLC32_zip_sha256':h(Path(b).read_bytes()),
 'compact_snapshot_sha256':h(dst.read_bytes()),
 'members':{k:{'raw_member_sha256':h(v),'size':len(v)} for k,v in dd.items()}}
 dst.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2))
 print(json.dumps({'zip_size':dst.stat().st_size,'sha':manifest['compact_snapshot_sha256'],'members':list(dd)}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--olc19',required=True);ap.add_argument('--olc32',required=True);ap.add_argument('--out',required=True);args=ap.parse_args();make(args.olc19,args.olc32,args.out)
