"""Transparent first-actual-order windows and complete saved-prediction audit."""
import numpy as np,pandas as pd,json
from io_utils import ROOT,MARKETS,readcsv,dump
from core import CONTEXT,predict_gate,mix_scores
from replay import adaptive_metrics

def main():
 scorecard=readcsv(ROOT/'results/SCORECARD.csv');scorecard=scorecard[~scorecard.period.str.startswith('ADAPTIVE_FIRST_TRADE')];new=[];trace=readcsv(ROOT/'results/GATE_TRACE.csv');aud=[];maxerror=0.;rowchecks=0
 for m in MARKETS:
  q=dict(np.load(ROOT/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(ROOT/f'inputs/{m}_CALENDAR.csv');scores=readcsv(ROOT/f'results/{m}_SCORES.csv.gz');parent=readcsv(ROOT/f'inputs/{m}_MEAN3_SCORES.csv.gz')
  for key,ss in scorecard[scorecard.market.eq(m)].groupby('config'):
   rr=dict(np.load(ROOT/'results/paths'/f'{key}.npz'));s=ss.iloc[0];meta={k:s[k] for k in ['market','variant','policy','mode','fee','config']}
   for r in adaptive_metrics(q,rr):
    if r['period'].startswith('ADAPTIVE_FIRST_TRADE'):new.append(dict(**meta,**r))
  for fused,fn in [(False,'GATE_PANEL.csv'),(True,'FUSION_GATE_PANEL.csv')]:
   p=readcsv(ROOT/'inputs'/fn);p=p[p.market.eq(m)].set_index('date').sort_index();lag=p[CONTEXT].shift(1)
   selected=trace[trace.market.eq(m)&trace.variant.str.startswith('F_').eq(fused)]
   for t in selected.itertuples():
    g=t.g;inp=p.loc[[t.date]].copy();name=t.variant[2:] if fused else t.variant;name=name.replace('_LAG','')
    if t.adaptive:
     path=ROOT/f'models/{t.date.year}_{"F_" if fused else ""}{name}.json';model=json.loads(path.read_text())['model']
     if t.variant.endswith('_LAG'):inp.loc[:,CONTEXT]=lag.loc[[t.date]].to_numpy()
     pr=predict_gate(model,inp);e=abs(g-pr['g'][0]);maxerror=max(maxerror,e);assert e<1e-14
    elif name not in ['CUM_FIXED','CUM_FIT','HALF']:assert g==1.
    a=parent[parent.signal_date.eq(t.date)];b=scores[scores.signal_date.eq(t.date)]
    want=mix_scores(a.CUM_FIXED_MAPPED,a.CUM_FIT_MAPPED,g)
    np.testing.assert_allclose(want,b[t.variant+'_CURRENT'],rtol=0,atol=2e-15,equal_nan=True);rowchecks+=len(a)
   active=trace[(trace.market==m)&trace.adaptive];d=active.date.min();entry=cal.loc[cal.signal_date.eq(d),'entry_date'].iloc[0]
   assert entry==pd.Timestamp('2023-02-01');aud.append(dict(market=m,target='FUSION' if fused else 'CURRENT',first_signal=str(d.date()),first_order=str(entry.date())))
 out=pd.concat([scorecard,pd.DataFrame(new)],ignore_index=True);out.to_csv(ROOT/'results/SCORECARD.csv',index=False)
 dump(ROOT/'results/TRACE_AND_COVERAGE_VERIFICATION.json',dict(first_order=aud,saved_gate_prediction_max_error=maxerror,score_row_checks=rowchecks,added_period_rows=len(new),init_month_not_claimed_adaptive=True))
 print('TRACE_COVERAGE_COMPLETE',rowchecks,len(new),maxerror)
if __name__=='__main__':main()
