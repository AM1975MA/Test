"""Task-native evaluation; all candidates and all real-time support retained."""
from pathlib import Path
import numpy as np,pandas as pd,json
from integration import build_scores,VARIANTS
from layer_metrics import ranking_metrics,opportunity_metrics
from prepare import read
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'inputs';O=ROOT/'results'

def period_ok(date,exitdate,period):
    if pd.isna(exitdate):return False
    if period=='PRE2025':return pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01') and exitdate<pd.Timestamp('2025-01-01')
    if period=='Y2025':return date.year==2025 and exitdate<pd.Timestamp('2026-01-01')
    if period=='Y2026_PARTIAL':return date.year==2026 and exitdate<=pd.Timestamp('2026-07-01')
    if period=='ALL_ACTIVE':return date>=pd.Timestamp('2021-01-01') and exitdate<=pd.Timestamp('2026-07-01')
    raise ValueError(period)

def main():
    tm=[];om=[];ex=[]
    for market in ['EU','USA']:
        labels=read(I/f'{market}_LAYER_LABELS.csv.gz')
        for seed in ['MEAN3','101','211','307']:
            scores=read(O/f'{market}_INTEGRATED_SCORES.csv.gz') if seed=='MEAN3' else build_scores(read(I/f'{market}_S{seed}_INPUTS.csv.gz'))
            f=scores.merge(labels,on=['signal_date','ticker'],validate='one_to_one')
            for date,g0 in f.groupby('signal_date'):
                good=np.isfinite(g0[VARIANTS]).all(axis=1);g=g0[good]
                if len(g)<20:continue
                for variant in VARIANTS:
                    if seed!='MEAN3' and variant=='ARCHIVE_S101':continue
                    s=g[variant].to_numpy()
                    if np.isfinite(g.TARGET).all() and g.exit_date_63.notna().all():
                        stats=ranking_metrics(g.TARGET.to_numpy(),s)
                        for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                            if period_ok(date,g.exit_date_63.max(),period):tm.append({'market':market,'seed':seed,'variant':variant,'period':period,'date':date,'n':len(g),**stats})
                    elif seed=='MEAN3' and variant=='MATCHED_REG':ex.append({'market':market,'date':date,'n':len(g),'reason':'incomplete_target_group'})
                    for h in [21,42,63]:
                        r=g[f'fwd_ret_{h}'];exit=g[f'exit_date_{h}']
                        if not np.isfinite(r).all() or exit.isna().any():continue
                        stats=opportunity_metrics(r.to_numpy(),s)
                        for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                            if period_ok(date,exit.max(),period):om.append({'market':market,'seed':seed,'variant':variant,'period':period,'date':date,'horizon':h,'n':len(g),**stats})
        print('LAYER_DONE',market,flush=True)
    t=pd.DataFrame(tm);o=pd.DataFrame(om);t.to_csv(O/'LAYER_MONTHS.csv',index=False);o.to_csv(O/'OPPORTUNITY_MONTHS.csv',index=False)
    key=['market','seed','variant','period']
    metric=['ndcg2','ndcg5','target_regret','selected_target','target_top_quintile_precision','target_bottom_quintile_fraction','ic']
    t.groupby(key).agg(months=('date','nunique'),**{m:(m,'mean') for m in metric}).reset_index().to_csv(O/'LAYER_SUMMARY.csv',index=False)
    metric=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']
    o.groupby(key+['horizon']).agg(months=('date','nunique'),**{m:(m,'mean') for m in metric}).reset_index().to_csv(O/'OPPORTUNITY_SUMMARY.csv',index=False)
    pd.DataFrame(ex).to_csv(O/'EXCLUDED_EVALUATION_MONTHS.csv',index=False)
    # Recompute source controls on exactly the same frame and compare native source evaluations.
    old=pd.read_csv(ROOT/'oracles/OLC11_TARGET_SUMMARY.csv',float_precision='round_trip');new=pd.read_csv(O/'LAYER_SUMMARY.csv',float_precision='round_trip');checks=[]
    for mk in ['EU','USA']:
        for v,ov,stage in [('MATCHED_REG','MATCHED_REG','FUSION'),('NAIVE_CLASS','XGB_CLASS','FUSION')]:
            a=new[(new.market==mk)&(new.seed=='MEAN3')&(new.variant==v)&(new.period=='PRE2025')].iloc[0]
            b=old[(old.market==mk)&(old.seed=='MEAN3')&(old.variant==ov)&(old.stage==stage)&(old.period=='PRE2025')].iloc[0]
            err=max(abs(a[m]-b[m]) for m in ['ndcg2','target_top_quintile_precision','selected_target']);assert err<1e-12
            checks.append({'market':mk,'variant':v,'max_error':err})
    (O/'LAYER_CONTROL_VERIFICATION.json').write_text(json.dumps(checks,indent=2))
    print('LAYER_METRICS',len(t),'OPPORTUNITY_METRICS',len(o),flush=True)
if __name__=='__main__':main()
