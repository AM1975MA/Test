"""Prespecified standalone learner diagnostics, before percentile fusion."""
from evaluate import *

def main():
    rows=[];op=[]
    for market in ['EU','USA']:
        label=readcsv(I/f'{market}_LAYER_LABELS.csv.gz').drop(columns=['source_date'])
        for seed,f in records(market).items():
            f=f[np.isfinite(f.ARCH_ET)&np.isfinite(f.ARCH_XGB)].merge(label,on=['signal_date','ticker'],validate='one_to_one')
            f['REG_RAW_BLEND']=.6*f.ET_REG+.4*f.XGB_REG
            f['CLASS_PROB_BLEND']=.6*f.ET_CLASS+.4*f.XGB_CLASS
            f['UNIFORM']=1.
            for date,g in f.groupby('signal_date'):
                good=np.isfinite(g.TARGET).all() and g.exit_date_63.notna().all()
                for learner in ['ARCH_ET','ARCH_XGB','ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK','REG_RAW_BLEND','CLASS_PROB_BLEND','UNIFORM']:
                    score=g[learner].to_numpy()
                    if good:
                        stats=ranking_metrics(g.TARGET.to_numpy(),score)
                        for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                            if period_ok(date,g.exit_date_63.max(),period):rows.append(dict(market=market,seed=seed,learner=learner,period=period,date=date,n=len(g),**stats))
                    for h in [21,42,63]:
                        r=g[f'fwd_ret_{h}'];e=g[f'exit_date_{h}']
                        if not np.isfinite(r).all() or e.isna().any():continue
                        stats=opportunity_metrics(r.to_numpy(),score)
                        for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                            if period_ok(date,e.max(),period):op.append(dict(market=market,seed=seed,learner=learner,period=period,date=date,horizon=h,n=len(g),**stats))
        print('NATIVE_EVALUATED',market,flush=True)
    f=pd.DataFrame(rows);g=pd.DataFrame(op);f.to_csv(O/'NATIVE_LEARNER_MONTHS.csv',index=False);g.to_csv(O/'NATIVE_OPPORTUNITY_MONTHS.csv',index=False)
    keys=['market','seed','learner','period'];metrics=['ndcg2','ndcg5','ic','target_regret','selected_target','target_top_quintile_precision','target_bottom_quintile_fraction']
    f.groupby(keys).agg(months=('date','nunique'),**{m:(m,'mean') for m in metrics}).reset_index().to_csv(O/'NATIVE_LEARNER_SUMMARY.csv',index=False)
    metrics=['top2_return','top2_excess','top2_regret','selected_negative_return','bottom_quintile_fraction','top5_capture']
    g.groupby(keys+['horizon']).agg(months=('date','nunique'),**{m:(m,'mean') for m in metrics}).reset_index().to_csv(O/'NATIVE_OPPORTUNITY_SUMMARY.csv',index=False)
if __name__=='__main__':main()
