#!/usr/bin/env python3
"""Independent quality checks for OLC63 from original source ZIPs and output tables.
Different route from run_olc63: recompute original-score Top2 directly and Shapley
by 24 PLAYER PERMUTATIONS rather than by subset factorial coefficient formula.
"""
from __future__ import annotations
import argparse, itertools, zipfile, gzip, io, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT14='olc14_fitted_ranking_20261101/results/'
ROOT16='olc16_contextual_rank_20261102/inputs/'
ORIG='olc19_combined_risk_20261102/restore/olc18_execution_20261102/inputs/'

def twov(s):
    s=np.asarray(s,float);order=np.sort(s);th=order[-2]
    above=s>th;equal=s==th
    return (above.astype(float)+equal.astype(float)*(2-above.sum())/equal.sum())/2

def rd(z,path):return pd.read_csv(io.BytesIO(gzip.decompress(z.read(path))))

def check(a):
    dst=Path(a.out)
    facts=pd.read_csv(dst/'OLC63_MONTHLY_FACTORIAL.csv')
    saved=pd.read_csv(dst/'OLC63_MONTHLY_SHAPLEY.csv')
    annual=pd.read_csv(dst/'OLC63_SUMMARY.csv')
    audit={}
    for market in ('EU','USA'):
        with zipfile.ZipFile(a.olc14) as z14,zipfile.ZipFile(a.olc16) as z16,zipfile.ZipFile(a.olc19) as z19:
            a14=rd(z14,ROOT14+market+'_MEAN3_SCORES.csv.gz')
            f16=rd(z16,ROOT16+market+'_FITTING_FRAME.csv.gz')
            d19=pd.read_csv(io.BytesIO(z19.read(ORIG+market+'_ORIGINAL_DECISIONS.csv')))
        original=a14.merge(f16[['signal_date','ticker','fwd_ret_21','fwd_ret_42']],on=['signal_date','ticker'],validate='one_to_one')
        bad=0;errors=[];paired=[]
        for d,g0 in original.groupby('signal_date',sort=True):
            g=g0[g0.ORIGINAL_CURRENT.notna()].copy().sort_values('ticker')
            if not (2021<=int(str(d)[:4])<=2025):continue
            if g[['fwd_ret_21','fwd_ret_42']].isna().any().any():continue
            rows=facts[(facts.market==market)&(facts.date==d)]
            assert len(rows)==16
            s=g.ORIGINAL_FUSION.to_numpy(float);w=twov(s)
            x21=float(w@g.fwd_ret_21.to_numpy(float));x42=float(w@g.fwd_ret_42.to_numpy(float))
            y21=float(rows.loc[rows['mask']==15,'mean21'].iloc[0]);y42=float(rows.loc[rows['mask']==15,'mean42'].iloc[0])
            errors.extend([abs(x21-y21),abs(x42-y42)])
            assert np.isclose(rows.loc[rows['mask']==0,'mean21'].iloc[0],g.fwd_ret_21.mean(),atol=1e-14)
            assert np.isclose(rows.loc[rows['mask']==0,'mean42'].iloc[0],g.fwd_ret_42.mean(),atol=1e-14)
            paired.append((d,x21,x42))
        assert len(paired)==(58 if market=='EU' else 60)
        assert max(errors)<1e-14
        audit[market]={'months_with_complete_labels':len(paired),'frozen_baseline_mean_max_abs_error':max(errors),
                       'original_olc19_decisions':len(d19)}
        for date,g0 in a14.groupby('signal_date'):
            g=g0[g0.ORIGINAL_FUSION.notna()].sort_values('ORIGINAL_FUSION',ascending=False,kind='stable').head(2)
            row=d19.loc[d19.signal_date==date]
            assert len(row)==1
            assert set(g.ticker)=={row.iloc[0].ticker1,row.iloc[0].ticker2},(market,date)
        for per,years in [('MAIN',list(range(2021,2025))),('LATE',[2025])]:
            x=pd.DataFrame(paired,columns=['date','v21','v42']);x=x[x.date.str[:4].astype(int).isin(years)]
            z=annual[(annual.market==market)&(annual.period==per)&(annual['mask']==15)]
            assert len(z)==1
            assert np.isclose(x.v21.mean(),z.avg21.iloc[0],atol=1e-14)
            assert np.isclose(x.v42.mean(),z.avg42.iloc[0],atol=1e-14)
            audit[market][per]={'nmonths':len(x),'mean21':float(x.v21.mean()),'mean42':float(x.v42.mean())}
    # Permutation-path Shapley, independent of the factorial-weight calculation.
    maxerr=0.;n=0
    players=('R','E','X','M')
    perms=list(itertools.permutations(range(4)))
    assert len(perms)==24
    for (market,date),grp in facts.groupby(['market','date']):
        grp=grp.set_index('mask')
        s=saved[(saved.market==market)&(saved.date==date)]
        assert len(s)==8 and len(grp)==16
        for metric in ('mean21','mean42'):
            val=grp[metric].to_dict();result={p:0. for p in players}
            for seq in perms:
                used=0
                for j in seq:
                    nex=used|(1<<j)
                    result[players[j]]+=(val[nex]-val[used])/len(perms)
                    used=nex
            assert used==15
            x=s[s.horizon==metric].set_index('component').shapley_return.to_dict()
            for p in players:
                d=abs(result[p]-x[p]);maxerr=max(maxerr,d)
                assert d<1e-13,(market,date,metric,p,d)
                n+=1
            assert abs(sum(result.values())-(val[15]-val[0]))<1e-13
    audit['permutation_independent_verification']={'shapley_values_checked':n,'max_abs_error':maxerr,'status':'PASS'}
    # Compare the very same original fusion baseline against old OLC60 reproducibility checkpoint if supplied.
    if a.olc60:
        with zipfile.ZipFile(a.olc60) as z:
            old=pd.read_csv(io.BytesIO(z.read('OLC60_Upstream_20261107/results/OLC60_MAIN_SUMMARY.csv')))
        old=old[(old.period=='MAIN')&(old.method=='B0_FUSION_CONTEXT')].set_index('market')
        new=annual[(annual.period=='MAIN')&(annual['mask']==15)].set_index('market')
        assert np.allclose(old.loc[['EU','USA'],'avg_fwd21'],new.loc[['EU','USA'],'avg21'],atol=1e-14,rtol=0)
        assert np.allclose(old.loc[['EU','USA'],'avg_fwd42'],new.loc[['EU','USA'],'avg42'],atol=1e-14,rtol=0)
        audit['olc60_original_baseline_reconciliation']='EXACT'
    (dst/'OLC63_INDEPENDENT_QA.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--olc14',required=True);ap.add_argument('--olc16',required=True);ap.add_argument('--olc19',required=True);ap.add_argument('--olc60');ap.add_argument('--out',required=True)
    check(ap.parse_args())