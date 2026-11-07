#!/usr/bin/env python3
"""OLC66. Tie OLC19 contextual choices to original OLC14 selected ETF labels,
without modifying/rerunning the market engine or pretending future returns are fills.
Archive scoreboard is retrieved from original OLC19, not newly simulated.
"""
import io,zipfile,argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

BASE='olc19_combined_risk_20261102/'
INPUT=BASE+'restore/olc18_execution_20261102/inputs/'


def archive_npz(z,name):
 return dict(np.load(io.BytesIO(z.read(INPUT+name+'.npz')),allow_pickle=False))

def validate_event_pair(a,b):
 assert a['events'].shape==b['events'].shape
 assert np.array_equal(a['events'],b['events'])
 assert np.array_equal(a['dates'],b['dates'])
 assert np.array_equal(a['tickers'],b['tickers'])


def main(olc19,olc11,panel,sel,out):
 dst=Path(out);dst.mkdir(parents=True,exist_ok=True)
 pp=pd.read_csv(panel)
 if not pp.signal_date.dtype==object:pp.signal_date=pp.signal_date.astype(str)
 ss=pd.read_csv(sel)
 rows=[];archive=[];qa=[]
 with zipfile.ZipFile(olc11) as z11,zipfile.ZipFile(olc19) as z19:
  for market in ('EU','USA'):
   # Entry day comes from original source, not derived by adding one calendar day.
   source=pd.read_csv(io.BytesIO(z11.read(f'results/{market}_XGB_CLASS_MEAN3_OUTPUTS.csv.gz')),compression='gzip',usecols=['signal_date','ticker','entry_date'])
   # Some EU instruments have different first actually observed entry session
   # on Whit Monday 2020. Every observed candidate date maps to its known
   # signal month; never substitute a synthetic/common entry quote.
   ent=source[['signal_date','entry_date']].drop_duplicates()
   assert ent.groupby('entry_date').signal_date.nunique().eq(1).all(),(market,'nonunique entry->signal mapping')
   to_signal=dict(zip(ent.entry_date,ent.signal_date))
   p=pp[pp.market==market].set_index(['signal_date','ticker'])
   for variant in ('ORIGINAL','CUM_FIT','TOP2_STATIC_REVALUE','TOP2_CONTEXT_REVALUE'):
    q=archive_npz(z19,f'{market}_{variant}')
    original=archive_npz(z19,f'{market}_ORIGINAL')
    validate_event_pair(q,original)
    ticks=q['tickers'].astype(str)
    for k in np.flatnonzero(q['events']):
     entry=str(q['dates'][k])[:10]
     if entry not in to_signal:raise AssertionError(('Event not in input',market,variant,entry))
     signal=to_signal[entry]
     names=[ticks[int(q['d1'][0,k])],ticks[int(q['d2'][0,k])]]
     assert names[0]!=names[1]
     group=p.loc[signal]
     yes=[name in group.index for name in names]
     assert all(yes),(market,variant,signal,names,yes)
     rr=group.loc[names]
     valid=rr[['fwd21','fwd42']].notna().all().all()
     rows.append(dict(market=market,variant=variant,signal_date=signal,entry_date=entry,year=int(signal[:4]),
        ticker1=names[0],ticker2=names[1],valid_label=bool(valid),
        mean21=float(rr.fwd21.mean()) if valid else float('nan'),
        mean42=float(rr.fwd42.mean()) if valid else float('nan')))
   for fee_tag,fee in [('10',.001),('30',.003)]:
    path=BASE+f'results/SCORECARD_{market}_{fee_tag}_0.csv'
    d=pd.read_csv(io.BytesIO(z19.read(path)))
    assert np.isclose(d.fee,fee).all() and d.stress.eq(False).all()
    archive.append(d)
   qa.append(dict(market=market,entry_dates=len(to_signal),native_events=90,variants=4))
 metrics=pd.DataFrame(rows)
 assert len(metrics)==4*90*2
 sels=ss[ss.method=='B0_FUSION'].groupby(['market','signal_date']).ticker.apply(lambda x:tuple(sorted(x))).rename('b0')
 orig=metrics[metrics.variant=='ORIGINAL'].copy()
 orig['pair']=orig.apply(lambda r:tuple(sorted((r.ticker1,r.ticker2))),axis=1)
 chk=orig.set_index(['market','signal_date']).join(sels)
 assert len(chk)==len(orig)==180
 observed=chk[chk.b0.notna()]
 assert len(observed)==118 and (observed.pair==observed.b0).all(), 'OLC19 ORIGINAL != B0_FUSION pair on the 118 evaluated dates'
 x=metrics.pivot(index=['market','signal_date'],columns='variant',values=['ticker1','ticker2','mean21','mean42','valid_label'])
 changes=[]
 for m in ('EU','USA'):
  a=metrics[metrics.market==m]
  b=a[a.variant=='ORIGINAL'].set_index('signal_date')
  c=a[a.variant=='TOP2_CONTEXT_REVALUE'].set_index('signal_date')
  assert len(b)==len(c)==90
  same=[set((b.loc[dt,'ticker1'],b.loc[dt,'ticker2']))==set((c.loc[dt,'ticker1'],c.loc[dt,'ticker2'])) for dt in b.index]
  w=pd.DataFrame({'date':b.index,'original_pair':b.ticker1+'|'+b.ticker2,'context_pair':c.ticker1+'|'+c.ticker2,
      'same_pair':same,'year':b.year,'orig21':b.mean21,'context21':c.mean21,'orig42':b.mean42,'context42':c.mean42})
  w['market']=m
  changes.append(w)
 changes=pd.concat(changes,ignore_index=True)
 avgs=[]
 for m in ('EU','USA'):
  w=changes[changes.market==m]
  for period,years in [('MAIN',range(2021,2025)),('LATE',(2025,)),('FULL_21_25',range(2021,2026))]:
   # Match exactly the whole-market complete-label months used by OLC66.
   valid_dates=set(sels.loc[m].index)
   s=w[w.year.isin(years)&w.date.isin(valid_dates)&w[['orig21','context21','orig42','context42']].notna().all(axis=1)]
   avgs.append(dict(market=m,period=period,months=len(s),pair_changed_count=int((~s.same_pair).sum()),
       original21=float(s.orig21.mean()),context21=float(s.context21.mean()),delta21=float((s.context21-s.orig21).mean()),
       original42=float(s.orig42.mean()),context42=float(s.context42.mean()),delta42=float((s.context42-s.orig42).mean())))
 comp=pd.concat(archive,ignore_index=True)
 keep=['market','variant','contract','fee','period','cagr','maxdd','turnover_annual','actual_risk_exposure','stops','rebalances','worst21','cvar05','period_return']
 comp=comp[keep].sort_values(['market','variant','contract','fee','period'])
 # Risk comparison is archived original native engine, never a new OLC66 NAV.
 baseline=comp[(comp.variant=='TOP2_CONTEXT_REVALUE')&(comp.contract.isin(['BASE','ALARM','FAST_NOLOCK','FAST_LOCK3']))&(comp.period.isin(['ACTIVE2021_2024','2025','2026','FULL','CRASH2020']))]
 metrics.to_csv(dst/'OLC66_NATIVE_EVENT_SELECTIONS.csv',index=False)
 changes.to_csv(dst/'OLC66_NATIVE_CONTEXT_PAIR_CHANGES.csv',index=False)
 pd.DataFrame(avgs).to_csv(dst/'OLC66_NATIVE_CONTEXT_STATIC_COMPARISON.csv',index=False)
 comp.to_csv(dst/'OLC66_OLC19_ARCHIVED_SCORECARDS.csv',index=False)
 baseline.to_csv(dst/'OLC66_CONTEXT_RISK_CHOICES.csv',index=False)
 q=dict(market_checks=qa,archive_rows=len(comp),native_event_rows=len(metrics),old_original_parity=180,context_comparison=avgs,
      selection_comparison_is_static_only=True,engine_rerun=False)
 (dst/'OLC66_NATIVE_RECOMPOSITION_QA.json').write_text(json.dumps(q,indent=2,ensure_ascii=False))
 print('OLC19 ORIGINAL vs CONTEXT:',pd.DataFrame(avgs).to_string(index=False,float_format=lambda a:f'{a:.5f}'))
 print('CONTEXT RISK CHOICES MAIN fee .001:')
 print(baseline[(baseline.period=='ACTIVE2021_2024')&(baseline.fee==.001)][['market','contract','cagr','maxdd','turnover_annual','stops']].to_string(index=False,float_format=lambda a:f'{a:.5f}'))

if __name__=='__main__':
 parser=argparse.ArgumentParser()
 for k in ('olc19','olc11','panel','sel','out'):parser.add_argument('--'+k,required=True)
 a=parser.parse_args();main(a.olc19,a.olc11,a.panel,a.sel,a.out)