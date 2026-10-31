from pathlib import Path
import json
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'results'


def block_summary(frame,cols,block=6,reps=10000):
    frame=frame.copy();frame.index=pd.DatetimeIndex(frame.index).to_period('M').to_timestamp()
    grid=pd.date_range(frame.index.min(),frame.index.max(),freq='MS')
    a=frame.reindex(grid)[cols].to_numpy();n=len(a);rng=np.random.default_rng(20261031)
    starts=rng.integers(0,n,size=(reps,(n+block-1)//block))
    ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    means=np.nanmean(a[ix],axis=1)
    return {c:{'mean':float(np.nanmean(a[:,j])),'lo':float(np.quantile(means[:,j],.025)),'hi':float(np.quantile(means[:,j],.975))} for j,c in enumerate(cols)}


def main():
    s=pd.read_csv(O/'ACTUAL_SWITCHES.csv',parse_dates=['signal_date','label_exit','entry_date'])
    opp=pd.read_csv(O/'OPPORTUNITY_MONTHS.csv',parse_dates=['signal_date','label_exit'])
    size=pd.read_csv(O/'SIZING_MONTHS.csv',parse_dates=['signal_date','label_exit'])
    switchrows=[];sizerows=[];opprows=[];examples=[];changes=[];paired_output=[]
    for period,end in [('PRE2025','2025-01-01'),('ALL_MATURED','2026-07-02')]:
      sx=s[s.valid&s.label_exit.notna()&(s.label_exit<pd.Timestamp(end))]
      for (market,weight,cost),g in sx.groupby(['market','weight','cost_bps_side']):
        keys=['signal_date','entry_date','old_ticker','new_ticker']
        wide=g.pivot(index=keys,columns='horizon',values='net_advantage').dropna(subset=[21,42,63]);month=wide.groupby(level='signal_date').mean()
        for block in [3,6]:
          bs=block_summary(month,[21,42,63],block)
          for h in [21,42,63]:
            pairwins=wide[h]>0
            switchrows.append(dict(period=period,market=market,weight=weight,cost_bps_side=cost,horizon=h,block_months=block,pairs=len(wide),months=len(month),mean_monthly_advantage_pp=100*bs[h]['mean'],ci95_low_pp=100*bs[h]['lo'],ci95_high_pp=100*bs[h]['hi'],pair_mean_advantage_pp=100*wide[h].mean(),historical_pair_win_share=pairwins.mean()))
        if period=='PRE2025' and weight=='ORIGINAL' and cost==10:
          w=wide.reset_index();w['market']=market;paired_output.append(w)
          changes.append(dict(market=market,pairs=len(wide),negative21_positive63=int(((wide[21]<=0)&(wide[63]>0)).sum()),positive21_negative63=int(((wide[21]>0)&(wide[63]<=0)).sum()),positive_both=int(((wide[21]>0)&(wide[63]>0)).sum()),negative_both=int(((wide[21]<=0)&(wide[63]<=0)).sum())))
          for direction,select in [('worst',wide[63].nsmallest(3)),('best',wide[63].nlargest(3))]:
            for idx,value in select.items():
              row=g[(g.signal_date==idx[0])&(g.entry_date==idx[1])&(g.old_ticker==idx[2])&(g.new_ticker==idx[3])&(g.horizon==63)].iloc[0].to_dict();row['selection']=direction;examples.append(row)
      # Exactly the same signal-date sample across horizons; all shortlisted comparisons observed.
      x=opp[opp.label_exit.notna()&(opp.label_exit<pd.Timestamp(end))&(opp.available_outcomes==opp.eligible)]
      for market,g in x.groupby('market'):
        dates=g.groupby('signal_date').horizon.nunique();common=dates[dates==3].index;g=g[g.signal_date.isin(common)]
        for h,z in g.groupby('horizon'):
          z=z[z.future_positive_top5>0]
          cols=['recall_pool','recall_sameK','recall_highvolK'];means=z[cols].mean()
          paired=pd.DataFrame({'union_minus_sameK':z.recall_pool-z.recall_sameK,'union_minus_vol':z.recall_pool-z.recall_highvolK},index=z.index);paired.index=z.signal_date
          b=block_summary(paired,['union_minus_sameK','union_minus_vol'],6)
          opprows.append(dict(period=period,market=market,horizon=h,months=len(z),mean_pool_size=z.shortlist_size.mean(),recall_actual2_pct=z.recall_actual2.mean()*100,recall_pool_pct=means.recall_pool*100,recall_sameK_pct=means.recall_sameK*100,recall_highvolK_pct=means.recall_highvolK*100,uniform_expected_pct=z.uniform_expected_recall.mean()*100,union_minus_sameK_pp=b['union_minus_sameK']['mean']*100,union_minus_sameK_lo=b['union_minus_sameK']['lo']*100,union_minus_sameK_hi=b['union_minus_sameK']['hi']*100))
      x=size[size.valid&size.label_exit.notna()&(size.label_exit<pd.Timestamp(end))]
      for market,g in x.groupby('market'):
        valid=g.groupby('signal_date').horizon.nunique();common=valid[valid==3].index;g=g[g.signal_date.isin(common)]
        for h,z in g.groupby('horizon'):
          zz=z.set_index('signal_date');b=block_summary(zz,['original_minus_half','first_minus_second'],6)
          sizerows.append(dict(period=period,market=market,horizon=h,months=len(z),mean_first_weight=z.weight1.mean(),original_minus_half_pp=b['original_minus_half']['mean']*100,ci95_lo_pp=b['original_minus_half']['lo']*100,ci95_hi_pp=b['original_minus_half']['hi']*100,first_minus_second_pp=b['first_minus_second']['mean']*100,first_wins_fraction=(z.first_minus_second>0).mean()))
    for name,rows in [('SWITCH_SUMMARY',switchrows),('SIZING_SUMMARY',sizerows),('OPPORTUNITY_SUMMARY',opprows),('HORIZON_REVERSALS',changes),('SWITCH_EXAMPLES',examples)]:
        pd.DataFrame(rows).to_csv(O/f'{name}.csv',index=False)
    pd.concat(paired_output).to_csv(O/'MATCHED_ACTUAL_SWITCH_OUTCOMES.csv',index=False)
    events=pd.read_csv(O/'ACTUAL_DECISION_EVENTS.csv')
    refs=pd.read_csv(O/'BASELINE_RECONCILIATION.csv')
    summary={'markets':['EU','USA'],'reference_replays':4,'new_predictive_models':0,'new_strategy_variants':0,'reference_aggregate_metrics_checked':len(refs),'max_reference_metric_error':float(refs.error.max()),'opportunity_rows':len(opp),'sizing_rows':len(size),'switch_rows_including_cost_horizon_weight_repeats':len(s),'decision_events_including_two_weights':len(events),'horizon_reversals':changes,'method':'Common identical replacement pairs across21/42/63; labels matured before window cutoff. Means first average pairs within calendar month. Static holding-at-horizon outcomes, not portfolio CAGR. Block bootstrap6 and3 months,10000,seed20261031,exploratory only.'}
    (O/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print('SWITCHES\n',pd.DataFrame(switchrows).query('period=="PRE2025" and weight=="ORIGINAL" and cost_bps_side==10 and block_months==6').to_string(index=False))
    print('SIZING\n',pd.DataFrame(sizerows).query('period=="PRE2025"').to_string(index=False))
    print('OPPORTUNITIES\n',pd.DataFrame(opprows).query('period=="PRE2025"').to_string(index=False))
    print('REVERSALS',changes)
if __name__=='__main__':main()
