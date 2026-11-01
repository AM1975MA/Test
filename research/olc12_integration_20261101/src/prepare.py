"""Authenticate parent objects, export portable inference inputs and verify score parity."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd
from integration import build_scores,VARIANTS
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'parents/olc11';I=ROOT/'inputs';O=ROOT/'results'
I.mkdir(exist_ok=True);O.mkdir(exist_ok=True)

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    d=pd.read_csv(p,float_precision='round_trip')
    for c in d:
        if c.endswith('date') or c.startswith('exit_date_'):d[c]=pd.to_datetime(d[c])
    return d

def verify_manifests():
    verified=[]
    for obj in [P/'COMPLETE.json',*list((P/'models').rglob('COMPLETE.json'))]:
        d=json.loads(obj.read_text())
        for ent in d['files']:
            p=obj.parent/ent['path']
            if not p.is_file() or p.stat().st_size!=ent['bytes'] or digest(p)!=ent['sha256']:raise ValueError(f'Hash verification failed: {p}')
            verified.append(str(p.relative_to(ROOT)))
    (O/'PARENT_FILE_VERIFICATION.json').write_text(json.dumps({'files_checked':len(verified),'paths':verified},indent=2))

def main():
    verify_manifests();parity=[];meta=[]
    for market in ['EU','USA']:
        frames=[]
        for seed in [101,211,307]:
            nm='R_RSI_DOMAIN' if seed==101 else f'REF42_S{seed}'
            ref=read(P/'inputs'/f'{market}_{nm}_FORECASTS.csv.gz')
            pred=read(P/'results'/f'{market}_S{seed}_PREDICTIONS.csv.gz')
            f=ref.rename(columns={'ET_RAW':'ARCH_ET','XGB_RAW':'ARCH_XGB'}).merge(pred,on=['signal_date','ticker'],how='left',validate='one_to_one').sort_values(['signal_date','ticker']).reset_index(drop=True)
            assert (f.source_date.dropna()<=f.loc[f.source_date.notna(),'signal_date']).all()
            # Independent seed scorecards retained for layer stability, not separate performance selection.
            f.to_csv(I/f'{market}_S{seed}_INPUTS.csv.gz',index=False,compression='gzip');frames.append(f)
        mean=frames[0].copy()
        for col in ['ARCH_ET','ARCH_XGB','ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK']:
            a=np.stack([f[col].to_numpy() for f in frames]);ok=np.isfinite(a).all(0)
            mean[col]=np.where(ok,np.where(np.isfinite(a),a,0).mean(0),np.nan)
        mean.to_csv(I/f'{market}_MEAN3_INPUTS.csv.gz',index=False,compression='gzip')
        scores=build_scores(mean);arch=build_scores(frames[0]);scores['ARCHIVE_S101']=arch.ARCHIVE_S101
        # Full score equality against frozen OLC11 rows, including NaN masks.
        for variant,oldname in [('MATCHED_REG','MATCHED_REG'),('NAIVE_CLASS','XGB_CLASS')]:
            old=read(P/'results'/f'{market}_{oldname}_MEAN3_OUTPUTS.csv.gz')
            z=scores.merge(old[['signal_date','ticker','FUSION']],on=['signal_date','ticker'],validate='one_to_one')
            a=z[variant].to_numpy();b=z.FUSION.to_numpy();assert np.array_equal(a,b,equal_nan=True),(market,variant,np.nanmax(abs(a-b)))
            parity.append({'market':market,'variant':variant,'rows':len(z),'max_abs_error':0.0})
        scores.to_csv(O/f'{market}_INTEGRATED_SCORES.csv.gz',index=False,compression='gzip')
        shutil.copy2(P/'inputs'/f'{market}_LAYER_LABELS.csv.gz',I)
        # Freeze exact risk/execution inputs from source checkpoint; no additional pickle needed.
        parent=ROOT/'parents/olc06/olc06_timing_20261101/vendor/olc05_transitions_20261031/source/lifecycle_execution_20261031/inputs'
        for name in [f'{market}_STATE_HALF.npz',f'{market}_CALENDAR.csv']:shutil.copy2(parent/name,I/name)
        meta.append({'market':market,'forecast_rows':len(scores),'months':scores.signal_date.nunique(),'current_common_rows':int(scores.MATCHED_REG.notna().sum())})
    pd.DataFrame(parity).to_csv(O/'SCORE_PARITY.csv',index=False)
    manifest=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(I.rglob('*')) if p.is_file()]
    (O/'INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    (O/'PREPARED.json').write_text(json.dumps({'markets':meta,'variants':VARIANTS,'base_fits':0,'scope':'new integration scores on frozen out-of-time predictions'},indent=2))
    print(json.dumps(meta,indent=2));print('Exact score controls:',len(parity))
if __name__=='__main__':main()
