from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

def loadmod(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',type=Path,required=True); ap.add_argument('--v6',type=Path,required=True); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    base=loadmod(a.base,'titanium_base_prodpar'); v6=loadmod(a.v6,'titanium_v6_prodpar')
    mats=v6.load_mats(a.data_dir); dates,compact,tail0,D=base.build_features(mats); D=v6.enhance_feature_dictionary(base,mats,dates,D); tail=v6.rebuild_tail_long(base,D,dates,mats['Close'].columns)
    compact=base.add_labels(compact,mats['Open'],dates); tail=base.add_labels(tail,mats['Open'],dates); macro,macro_feats=v6.build_macro_panel(base,D,compact,base.TICKER_CATEGORY)
    cols=['signal_date','cluster_id','label_exit_date_21']
    for spec in v6.OPPORTUNITY_SPECS: cols += [spec['target']] + list(spec['features'])
    cols=list(dict.fromkeys(cols)); rows=[]
    for d in [pd.Timestamp('2015-12-31'),pd.Timestamp('2026-06-30')]:
        r={c:np.nan for c in cols}; r['signal_date']=d; r['cluster_id']=0; r['label_exit_date_21']=pd.NaT; rows.append(r)
    opp=pd.DataFrame(rows)
    pred,opp_pred,audit,macro_pred=v6.fit_predict(base,compact,tail,macro,macro_feats,opp,[2026],360)
    available=sorted(pd.to_datetime(pred.signal_date.unique())); requested=pd.Timestamp('2026-06-30'); checkpoint=max([d for d in available if d<=requested],default=available[-1])
    chk=pred[pred.signal_date.eq(checkpoint)].sort_values('titanium_score',ascending=False).copy(); chk['rank']=np.arange(1,len(chk)+1)
    colsout=[c for c in ['rank','signal_date','ticker','compact_raw','compact_rank','tail_raw','tail_rank','titanium_score_pre_macro','macro_category','top_macro','macro_gap_z','macro_bonus','titanium_score'] if c in chk]
    chk[colsout].head(50).to_csv(a.output/'CHECKPOINT_TOP50.csv',index=False); audit.to_csv(a.output/'FIT_AUDIT_2026.csv',index=False); macro_pred.to_csv(a.output/'MACRO_PRED_2026.csv',index=False)
    compact[base.F2D_FEATURES].notna().mean().sort_values().rename('nonmissing_rate').to_csv(a.output/'COMPACT_FEATURE_NONMISSING.csv')
    report={'checkpoint':str(checkpoint.date()),'top1':str(chk.iloc[0].ticker),'top2':str(chk.iloc[1].ticker),'top1_score':float(chk.iloc[0].titanium_score),'top2_score':float(chk.iloc[1].titanium_score),'margin':float(chk.iloc[0].titanium_score-chk.iloc[1].titanium_score),'known_target':['USO','PALL'],'matches_known':bool(chk.iloc[0].ticker=='USO' and chk.iloc[1].ticker=='PALL'),'n_scored':int(len(chk)),'n_train_months':int(audit.iloc[0].compact_train_dates),'n_train_rows':int(audit.iloc[0].compact_train_rows)}
    (a.output/'CHECKPOINT_REPORT.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2)); print(chk[colsout].head(20).to_string(index=False))
if __name__=='__main__': main()
