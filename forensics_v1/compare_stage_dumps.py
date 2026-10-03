#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

FEATURES_42=(
'cluster_acc_5_21_univ_rank','cluster_acc_5_21_mean_rank','intraday_mean5_rank','mom_21_5_rank','atr_14_rank','cluster_eff_63_univ_rank','cluster_eff_63_mean_rank','jerk_rank','acc_5_21_rank','mom_63_5_rank','boll_z20_rank','vol_10_rank','slope_63_rank','cluster_ret_21_univ_rank','cluster_ret_21_mean_rank','downvol_21_rank','directional_energy_63_rank','energy_21_rank','eff_63_rank','vol_21_rank','autocorr1_21_rank','cluster_breadth63_rank','rsi14_rank','ret_21_vs_cluster_rank','volume_ratio5_20_rank','downvol_63_rank','vol_63_vs_cluster_rank','ret_21_cluster_rank','ret_5_rank','acc_21_63_rank','ret_63_rank','vol_63_rank','ret_21_rank','eff_63_cluster_rank','energy_63_rank','dominant_energy64_rank','slope_21_rank','vol_126_rank','volume_ratio20_63_rank','atr_ratio_rank','eff_63_vs_cluster_rank','dd_21_rank')


def pair_numeric(a,b,keys,value):
    x=a[keys+[value]].merge(b[keys+[value]],on=keys,suffixes=('_a','_b'),how='inner')
    u=pd.to_numeric(x[value+'_a'],errors='coerce').to_numpy(float); v=pd.to_numeric(x[value+'_b'],errors='coerce').to_numpy(float)
    m=np.isfinite(u)&np.isfinite(v); d=np.abs(u-v); den=max(int(m.sum()),1)
    return {'n':int(m.sum()),'changed_fraction_gt1e12':float(np.sum(m&(d>1e-12))/den),'mean_abs':float(np.nanmean(d[m])) if m.any() else None,'p99_abs':float(np.nanquantile(d[m],.99)) if m.any() else None,'max_abs':float(np.nanmax(d[m])) if m.any() else None}


def mean_daily_spearman(a,b,value):
    z=a[['signal_date','ticker',value]].merge(b[['signal_date','ticker',value]],on=['signal_date','ticker'],suffixes=('_a','_b'))
    vals=[]
    for _,g in z.groupby('signal_date'):
        x=g[value+'_a']; y=g[value+'_b']; m=x.notna()&y.notna()
        if m.sum()>=3: vals.append(x[m].rank().corr(y[m].rank()))
    return float(np.nanmean(vals)) if vals else None


def load(root):
    return {
      'panel':pd.read_parquet(root/'RAW_FEATURE_PANEL.parquet'),
      'tit':pd.read_parquet(root/'TIT_R.parquet'),
      'pred':pd.read_parquet(root/'PREDICTIONS.parquet'),
      'score':pd.read_parquet(root/'FINAL_SCORE.parquet'),
      'leaders':pd.read_csv(root/'DAILY_LEADERS.csv'),
      'result':json.loads((root/'RESULT.json').read_text()),
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    base=Path(a.root); outp=Path(a.out); outp.parent.mkdir(parents=True,exist_ok=True)
    roots={i:base/f'repeat{i}' for i in (1,2,3)}; R={i:load(roots[i]) for i in roots}
    out={'status':'STAGE_AMPLIFICATION_COMPLETE','pairs':{},'cagr':{i:R[i]['result']['v2_full_universe']['cagr'] for i in R}}
    for aa,bb in [(1,2),(1,3),(2,3)]:
        A,B=R[aa],R[bb]; q={}
        # Feature panel exact model inputs
        pa,pb=A['panel'],B['panel']; common=[c for c in FEATURES_42 if c in pa.columns and c in pb.columns]
        fstats={c:pair_numeric(pa,pb,['signal_date','ticker'],c) for c in common}
        cluster_cols=[c for c in common if 'cluster' in c]
        noncluster=[c for c in common if c not in cluster_cols]
        def agg(cols):
            if not cols:return {}
            return {'columns':len(cols),'mean_cell_changed_fraction':float(np.mean([fstats[c]['changed_fraction_gt1e12'] for c in cols])),'mean_feature_mean_abs':float(np.mean([fstats[c]['mean_abs'] for c in cols])),'max_feature_max_abs':float(np.max([fstats[c]['max_abs'] for c in cols]))}
        q['FEATURES_42']={'all':agg(common),'cluster_derived':agg(cluster_cols),'noncluster':agg(noncluster),'per_feature':fstats}
        if 'cluster_id' in pa.columns and 'cluster_id' in pb.columns:
            x=pa[['signal_date','ticker','cluster_id']].merge(pb[['signal_date','ticker','cluster_id']],on=['signal_date','ticker'],suffixes=('_a','_b'))
            m=x.cluster_id_a.notna()&x.cluster_id_b.notna(); q['cluster_id']={'n':int(m.sum()),'disagreement_fraction':float((x.loc[m,'cluster_id_a']!=x.loc[m,'cluster_id_b']).mean())}
        q['TIT_R']=pair_numeric(A['tit'],B['tit'],['signal_date','ticker'],'TIT_R'); q['TIT_R']['mean_daily_spearman']=mean_daily_spearman(A['tit'],B['tit'],'TIT_R')
        pred_cols=[c for c in ['ET_TAIL','XGB_TAIL','TAIL_HYBRID'] if c in A['pred'].columns]
        q['predictions']={c:{**pair_numeric(A['pred'],B['pred'],['signal_date','ticker'],c),'mean_daily_spearman':mean_daily_spearman(A['pred'],B['pred'],c)} for c in pred_cols}
        q['FINAL_SCORE']={**pair_numeric(A['score'],B['score'],['signal_date','ticker'],'FINAL_SCORE'),'mean_daily_spearman':mean_daily_spearman(A['score'],B['score'],'FINAL_SCORE')}
        la=A['leaders'].merge(B['leaders'],on='date',suffixes=('_a','_b'))
        q['decisions']={'days':len(la),'top1_disagreement_fraction':float((la.top1_a!=la.top1_b).mean()),'top2_disagreement_fraction':float((la.top2_a!=la.top2_b).mean()),'either_top1_top2_disagreement_fraction':float(((la.top1_a!=la.top1_b)|(la.top2_a!=la.top2_b)).mean()),'first_top1_divergence':str(la.loc[la.top1_a!=la.top1_b,'date'].iloc[0]) if (la.top1_a!=la.top1_b).any() else None}
        q['economic']={'cagr_a':out['cagr'][aa],'cagr_b':out['cagr'][bb],'cagr_abs_gap_pp':100*abs(out['cagr'][aa]-out['cagr'][bb])}
        out['pairs'][f'{aa}-{bb}']=q
    outp.write_text(json.dumps(out,indent=2,default=str)+'\n')
    print(json.dumps(out,indent=2)[:30000])
if __name__=='__main__':main()
