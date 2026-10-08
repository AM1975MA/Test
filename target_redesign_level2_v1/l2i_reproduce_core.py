#!/usr/bin/env python3
"""Independent compact L2-I committee reproduction from already-exported L2-D CSVs.
Not a new fit or out-of-sample test. Full executed QA/trading script is distributed
in ETF_Trader_L2I_consensus.zip, not this compact reproduction.
Run: python l2i_reproduce_core.py /path/to/l2d_delivery
"""
from __future__ import annotations
import pathlib, sys
import numpy as np
import pandas as pd

V = ['_repeat1', '_repeat2', '_repeat3']
def top(score, names):
    return np.lexsort((np.asarray(names), -np.asarray(score)))[0]
def percentile(score):
    return pd.Series(score).rank(method='average',pct=True).to_numpy(float)

def main(root):
    d = root/'l2d_results'
    x = pd.read_csv(d/'XGB_COMMON_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
    n = pd.read_csv(d/'XGB_NATIVE_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
    r = pd.read_csv(root/'l2c_reference/COMMON_INPUT_PREDICTIONS.csv.gz',
                    parse_dates=['signal_date'])
    n = n[n.vintage.eq('_repeat2') & n.signal_date.isin(x.signal_date.unique())]
    r = r[r.vintage.eq('_repeat2')]
    p = x.pivot(index=['signal_date','ticker'],columns='vintage',values='pred')[V]
    merged = p.reset_index().merge(n[['signal_date','ticker','net_ret_21','rank_pct_21','pred']],
                                  on=['signal_date','ticker'],validate='one_to_one')
    merged = merged.merge(r[['signal_date','ticker','pred_rank_pct_21']],
                          on=['signal_date','ticker'],validate='one_to_one')
    assert len(merged)==113*149 and not merged.isna().any().any()
    assert np.allclose(merged['_repeat2'],merged.pred,atol=1e-12,rtol=0)
    outcomes=[];loo=[]
    for date,z in merged.groupby('signal_date',sort=True):
        z=z.sort_values('ticker');names=z.ticker.to_numpy()
        P=z[V].to_numpy(float); ranks=np.stack([percentile(P[:,j]) for j in range(3)],axis=1)
        mean=ranks.mean(axis=1);votes=np.zeros(149,int)
        for j in range(3):
            ix=np.lexsort((names,-P[:,j]))[:5];votes[ix]+=1
        cand=np.where(votes>=2)[0]
        mean_choice=names[top(mean,names)]
        ridge_choice=names[top(z.pred_rank_pct_21,names)]
        vote_choice=names[cand[top(mean[cand],names[cand])]] if len(cand) else ridge_choice
        targets={'XGB_REPEAT2':names[top(P[:,1],names)],
                 'RIDGE_REPEAT2':ridge_choice,
                 'COMMITTEE_MEAN3':mean_choice,
                 'COMMITTEE_TOP5_VOTE2':vote_choice}
        realized_top5=set(names[np.lexsort((names,-z.net_ret_21.to_numpy()))[:5]])
        returns=dict(zip(names,z.net_ret_21))
        for key,val in targets.items():
            outcomes.append(dict(date=date,model=key,top1=val,
                                 top5_hit=int(val in realized_top5),
                                 selected_return=float(returns[val])))
        for j in range(3):
            s=ranks[:,[k for k in range(3) if k!=j]].mean(axis=1)
            loo.append(dict(date=date,omitted=V[j],choice=names[top(s,names)],ranks=s))
    a=pd.DataFrame(outcomes).groupby('model')[['top5_hit','selected_return']].mean()
    print('Mean per-month realized outcome (Repeat2):\n',a.to_string())
    agreement=[]
    for i,j in [(0,1),(0,2),(1,2)]:
        rows=[]
        for day in sorted(merged.signal_date.unique()):
            rec=[q for q in loo if q['date']==day]
            ra=rec[i]['ranks'];rb=rec[j]['ranks']
            rows.append((float(rec[i]['choice']==rec[j]['choice']),
                         np.abs(percentile(ra)-percentile(rb)).mean()))
        agreement.append(dict(pair=V[i]+' versus '+V[j],
                              top1_agreement=np.mean([q[0] for q in rows]),
                              rank_mad=np.mean([q[1] for q in rows])))
    print('LOVO model removal stress:\n',pd.DataFrame(agreement).to_string(index=False))
    assert all(q['top1_agreement']<.90 for q in agreement)
    print('RESEARCH_GATE_FAILED: model-removal consensus does not reach 90% Top1.')
if __name__=='__main__':
    main(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path('l2d_delivery'))
