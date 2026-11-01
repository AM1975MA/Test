"""Authenticate parent cache and build a compact, self-contained matched input set."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd,joblib
from recovery_core import sha256,atomic_json,complete_checkpoint
from objectives import mature_months,top_event,query_sizes
ROOT=Path(__file__).resolve().parents[1]

def readcsv(p):
    f=pd.read_csv(p,float_precision='round_trip')
    for c in ['signal_date','source_date','entry_date','exit_date_21','exit_date_42','exit_date_63']:
        if c in f:f[c]=pd.to_datetime(f[c])
    return f

def main():
    src=ROOT/'parents/olc09';lab=ROOT/'parents/olc10/inputs';dest=ROOT/'inputs';(dest/'annual').mkdir(exist_ok=True)
    manifest=json.loads((src/'DELIVERY_MANIFEST.json').read_text());known={e['path']:e for e in manifest['files']}
    records=[]
    for market in ['EU','USA']:
        labels=readcsv(lab/f'{market}_LAYER_LABELS.csv.gz')
        for year in range(2019,2027):
            p=src/'cache'/f'{market}_{year}.joblib';assert sha256(p)==known[str(p.relative_to(src))]['sha256']
            d=joblib.load(p);cutoff=pd.Timestamp(year,1,1)
            tr=labels[(labels.signal_date<cutoff)&(labels.exit_date_63<cutoff)&np.isfinite(labels.TARGET)].sort_values(['signal_date','ticker']).reset_index(drop=True)
            keyhash=hashlib.sha256(tr[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()
            assert keyhash==d['metadata']['train_keys']
            np.testing.assert_array_equal(tr.TARGET.to_numpy(),d['y']);np.testing.assert_array_equal(tr.signal_date.to_numpy(),d['train_dates'])
            good=mature_months(labels,cutoff);mask=tr.signal_date.isin(good).to_numpy();matched=tr.loc[mask].reset_index(drop=True)
            matched['event']=matched.groupby('signal_date').TARGET.transform(lambda s:top_event(s.to_numpy())).astype(np.int8)
            sizes=query_sizes(matched.signal_date.to_numpy());assert sizes.min()>1
            X,XP=d['matrices']['REF42'];assert X.shape[1]==42
            row={'market':market,'year':year,'cutoff':str(cutoff),'original_train_rows':len(tr),'matched_train_rows':int(mask.sum()),'removed_rows':int((~mask).sum()),'original_months':int(tr.signal_date.nunique()),'matched_months':int(matched.signal_date.nunique()),'predict_rows':len(XP),'original_keys_sha256':keyhash,'matched_keys_sha256':hashlib.sha256(matched[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest(),'last_label_exit':str(matched.exit_date_63.max()),'prior_event_rate':float(matched.event.mean()),'parent_cache_sha256':sha256(p)}
            obj={'X_original':X,'y_original':d['y'],'X':X[mask],'XP':XP,'y':matched.TARGET.to_numpy(),'binary':matched.event.to_numpy(),'groups':sizes,'train_keys':matched[['signal_date','ticker','exit_date_63']], 'predict_keys':d['predict_keys'],'reference':d['reference'],'columns':d['metadata']['columns42'],'metadata':row}
            out=dest/'annual'/f'{market}_{year}.joblib';joblib.dump(obj,out,compress=3)
            row['prepared_sha256']=sha256(out);records.append(row)
            print('PREPARED',market,year,'original',len(tr),'matched',len(matched),'months',row['matched_months'],flush=True)
        for suffix in ['LAYER_LABELS.csv.gz','R_RSI_DOMAIN_FORECASTS.csv.gz','REF42_S211_FORECASTS.csv.gz','REF42_S307_FORECASTS.csv.gz']:
            shutil.copy2(lab/f'{market}_{suffix}',dest/f'{market}_{suffix}')
    atomic_json(ROOT/'results/INPUT_AUDIT.json',records)
    complete_checkpoint(ROOT,'OLC11_INPUTS',[str(p.relative_to(ROOT)) for p in dest.rglob('*') if p.is_file()]+['results/INPUT_AUDIT.json'],{'annual_inputs':16,'new_models':0})
if __name__=='__main__':main()
