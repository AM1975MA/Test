"""Decision-level and exact additive accounting audit of frozen OLC16 portfolios."""
from pathlib import Path
import sys,json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'parent/olc16_contextual_rank_20261102'
sys.path.append(str(P/'src'))
from experiment import load_groups
C='TOP2_CONTEXT_REVALUE';B='TOP2_STATIC_REVALUE'

def main():
 groups,_,_=load_groups();gm={(g['market'],pd.Timestamp(g['date'])):g for g in groups}
 summaries=[];months=[];decisions=[];timestamp=[];cis=[]
 components=['primary','defensive','stop_effect','rebalance_fees','stop_fees','stop_slippage']
 rng=np.random.default_rng(20261102);starts=rng.integers(0,48,(4000,8));ix=((starts[:,:,None]+np.arange(6))%48).reshape(4000,48)
 for m in ['EU','USA']:
  q=dict(np.load(P/f'inputs/{m}_STATE_HALF.npz'));obs=q.get('observed',np.ones_like(q['O'],bool))
  dg=abs(q['gap'][1:]-(q['O'][1:]/q['PC'][1:]-1));timestamp.append(dict(market=m,prior_close_error=float(abs(q['PC'][1:]-q['C'][:-1]).max()),observed_gap_error=float(dg[obs[1:]].max()),nonobserved_gap_differences=int(((dg>1e-10)&~obs[1:]).sum()),missing_quote_mask_available='observed'in q))
  props=pd.read_csv(ROOT/f'results/PROPOSALS_{m}.csv',parse_dates=['signal_date','entry_date']);cand=props[props.variant.eq(C)].set_index('signal_date');base=props[props.variant.eq(B)].set_index('signal_date')
  dat={}
  for mode in ['LEGACY','ALL_PREOPEN']:
   for v in [C,B,'CUM_FIT','ORIGINAL']:
    f=pd.read_csv(ROOT/f'results/daily/{m}_{v}_{mode}_10.csv.gz',parse_dates=['date','interval_start']);dat[mode,v]=f
   for b in [B,'CUM_FIT','ORIGINAL']:
    f=dat[mode,C];o=dat[mode,b];assert np.array_equal(f.date,o.date)
    mask=f.date.between('2021-01-01','2024-12-31');dif=f.loc[mask,components].to_numpy()-o.loc[mask,components].to_numpy()
    logs=f.loc[mask,'log_return'].to_numpy()-o.loc[mask,'log_return'].to_numpy();assert np.max(abs(dif.sum(1)-logs))<2e-12
    ann=dif.sum(0)*252/mask.sum();tot=logs.sum()*252/mask.sum()
    summaries.append(dict(market=m,scenario=mode,baseline=b,annual_log_difference=tot,**dict(zip(components,ann))))
    pair=pd.DataFrame({'month':f.loc[mask,'month'],'delta_log':logs});mon=pair.groupby('month').delta_log.sum().reindex(pd.period_range('2021-01','2024-12',freq='M').astype(str),fill_value=0.)
    z=mon.to_numpy();bs=z[ix].mean(1)*12;lo,hi=np.quantile(bs,[.025,.975]);top=mon.nlargest(3)
    cis.append(dict(market=m,scenario=mode,baseline=b,annual_log=12*z.mean(),lower=lo,upper=hi,winning_months=int((z>1e-12).sum()),losing_months=int((z<-1e-12).sum()),unchanged_months=int((abs(z)<=1e-12).sum()),top3_log=top.sum(),total_log=z.sum(),without_top3_annual_log=12*mon.drop(top.index).mean(),top3_months=';'.join(top.index)))
    for month,val in mon.items():months.append(dict(market=m,scenario=mode,baseline=b,month=month,delta_log=val))
  for n,(date,row) in enumerate(cand.iterrows()):
   if not pd.Timestamp('2021-01-01')<=date<=pd.Timestamp('2026-06-30'):continue
   br=base.loc[date];setc={row.ticker1,row.ticker2};setb={br.ticker1,br.ticker2}
   if setc==setb:continue
   nxt=cand.iloc[n+1].entry_date if n+1<len(cand) else pd.Timestamp(q['dates'][-1]);entry=row.entry_date
   g=gm.get((m,date));r=dict(market=m,signal_date=date,entry_date=entry,exit_boundary=nxt,candidate_pair=' / '.join(sorted(setc)),static_pair=' / '.join(sorted(setb)))
   if g and g['full']:
    ci=[list(g['tickers']).index(t) for t in setc];bi=[list(g['tickers']).index(t) for t in setb]
    r['native_U_difference']=float(g['u'][ci].mean()-g['u'][bi].mean())
    for j,h in enumerate([21,42,63]):r[f'native_return_{h}_difference']=float(g['returns'][ci,j].mean()-g['returns'][bi,j].mean())
   for mode in ['LEGACY','ALL_PREOPEN']:
    cf=dat[mode,C];bf=dat[mode,B];ok=(cf.interval_start>=entry)&(cf.interval_start<nxt)
    r[mode+'_paired_log']=float(cf.loc[ok,'log_return'].sum()-bf.loc[ok,'log_return'].sum())
    for v,ff in [('candidate',cf),('static',bf)]:
     r[f'{mode}_{v}_return']=float(np.expm1(ff.loc[ok,'log_return'].sum()))
     r[f'{mode}_{v}_stops']=int(ff.loc[ok,'stops'].sum());r[f'{mode}_{v}_systemic']=int(ff.loc[ok,'systemic'].sum())
    for comp in components:r[mode+'_'+comp]=float(cf.loc[ok,comp].sum()-bf.loc[ok,comp].sum())
   decisions.append(r)
 pd.DataFrame(summaries).to_csv(ROOT/'results/ATTRIBUTION.csv',index=False)
 pd.DataFrame(months).to_csv(ROOT/'results/MONTHLY_DIFFERENCES.csv',index=False)
 pd.DataFrame(cis).to_csv(ROOT/'results/UNCERTAINTY_CONCENTRATION.csv',index=False)
 pd.DataFrame(decisions).to_csv(ROOT/'results/CHANGED_DECISIONS.csv',index=False)
 (ROOT/'results/INPUT_TIME_AUDIT.json').write_text(json.dumps(timestamp,indent=2))
 print('ATTRIBUTION');print(pd.DataFrame(summaries).round(7).to_string(index=False))
 print('CONCENTRATION');print(pd.DataFrame(cis).round(6).to_string(index=False))
 print('DECISIONS',pd.DataFrame(decisions).groupby('market').size().to_dict())
 print(pd.DataFrame(decisions).sort_values('LEGACY_paired_log').iloc[np.r_[0:3,-3:0]].round(6).to_string(index=False))
if __name__=='__main__':main()
