"""Post-result descriptive oracle attribution of OLC60 frozen 42-feature panel.
For diagnostics ONLY: future labels never used in a live selection.
"""
import argparse
import pandas as pd
import numpy as np


def run(path, out):
    df=pd.read_csv(path,compression='gzip')
    rows=[]
    for (market,date),allg in df.groupby(['market','signal_date'],sort=True):
        if not 2021 <= int(str(date)[:4]) <= 2025: continue
        valid=allg[(allg.ORIGINAL_CURRENT.notna())&(allg.ORIGINAL_FUSION.notna())&(allg.fwd_ret_21.notna())&(allg.fwd_ret_42.notna())]
        if len(valid)<50:continue
        for base in ['ORIGINAL_CURRENT','ORIGINAL_FUSION']:
            scores=valid[base].to_numpy(float)
            cut2=np.sort(scores)[-2]
            above=scores>cut2; ties=scores==cut2
            weights=above.astype(float)
            weights[ties]=(2-above.sum())/ties.sum()
            weights/=2
            assert np.isclose(weights.sum(),1)
            for h in [21,42]:
                future='fwd_ret_'+str(h)
                op=valid.nlargest(2,future)
                allv=float(op[future].mean())
                selectedv=float(np.dot(weights,valid[future].to_numpy(float)))
                for k in [5,10]:
                    cut=valid[base].nlargest(k).iloc[-1]
                    shortlist=valid[valid[base]>=cut]
                    best=shortlist.nlargest(2,future)
                    rows.append(dict(market=market,date=date,year=int(str(date)[:4]),base=base,horizon=h,k=k,
                        nvalid=len(valid),nshort=len(shortlist),oracle_any=float(allv),oracle_short=float(best[future].mean()),
                        selected=float(selectedv),best2_intersection=len(set(op.ticker)&set(shortlist.ticker)),
                        shortlist_gain=float(best[future].mean()-selectedv),universe_gain=float(allv-selectedv)))
    diag=pd.DataFrame(rows)
    diag.to_csv(out,index=False)
    m=diag[diag.year.between(2021,2024)].groupby(['market','base','horizon','k']).agg(
        months=('date','count'),universe_oracle=('oracle_any','mean'),shortlist_oracle=('oracle_short','mean'),
        native=('selected','mean'),hit_true_top2=('best2_intersection','mean'),shortlist_avail_gain=('shortlist_gain','mean'),
        universe_avail_gain=('universe_gain','mean')).reset_index()
    m['fraction_upper_gap_in_shortlist']=m.shortlist_avail_gain/m.universe_avail_gain
    print(m.to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    m.to_csv(out.replace('.csv','_SUMMARY.csv'),index=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--infile',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.infile,a.out)