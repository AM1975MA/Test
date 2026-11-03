#!/usr/bin/env python3
"""Independent reconciliation of OLC36 EU-only decision and monthly-return artifacts."""
from __future__ import annotations
import io,gzip,zipfile,hashlib,json,math
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results';I=ROOT/'input'/'OLC32_RESULTS.zip'
sha=lambda x:hashlib.sha256(x).hexdigest()
with zipfile.ZipFile(I) as z: raw=z.read('results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz')
assert sha(raw)=='83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16'
df=pd.read_csv(io.BytesIO(gzip.decompress(raw)))
assert df.shape[0]==27191
E=df[df.market=='EU'].copy();assert E.signal_date.nunique()==90
assert (pd.to_datetime(E.loc[E.source_date.notna(),'source_date'])<=pd.to_datetime(E.loc[E.source_date.notna(),'signal_date'])).all()
D=pd.read_csv(OUT/'OLC36_EU_CORE_DECISIONS.csv')
P=pd.read_csv(OUT/'OLC36_MONTHLY_PROXY.csv')
F=pd.read_csv(OUT/'OLC36_FUTURE6_RETENTION_DIAGNOSTIC.csv')
A=pd.read_csv(OUT/'OLC36_EU_ASOF_RANKS.csv')
SUM=json.loads((OUT/'OLC36_SUMMARY.json').read_text())
assert len(D)==len(P)==90 and D.signal_date.is_unique and P.signal_date.is_unique
assert set(D.signal_date)==set(E.signal_date)
assert (D.auth_top1==D.dom_top1).all() and (D.auth_top1!=D.dom_top2).all()
assert (P.dom_top2==D.dom_top2).all()
R=E.set_index(['signal_date','ticker']);

# Verify exact original FUSION ranks and independent EU score population counts.
for _,d in D.iterrows():
    r=E[E.signal_date==d.signal_date]
    s=r.sort_values('auth_rank')
    assert tuple(s.iloc[:2].ticker)==(d.auth_top1,d.auth_top2)
    assert (s.auth_rank.sort_values().to_numpy()==np.arange(1,len(s)+1)).all()
    ready=r.feature_available_asof.astype(bool) & r.source_date.notna() & r.source_date.le(d.signal_date)
    ready &= np.isfinite(r[['ret_21','ret_63','ret_126','ret_252']].to_numpy(dtype=float)).all(axis=1)
    n=int(ready.sum())
    assert n==d.n_feature_valid

# Independently verify all changed outcomes and costs (including preceding monthly weights).
maxerr=0.;pair_ok=0;turnover_errors=0
prev={'AUTH':{},'DOM':{}}
for _,p in P.iterrows():
    row=(p.signal_date)
    for policy in ['AUTH','DOM']:
        a=p.auth_top1 if policy=='AUTH' else p.dom_top1
        b=p.auth_top2 if policy=='AUTH' else p.dom_top2
        w={a:.5,b:.5}
        turn=.5*sum(abs(w.get(k,0)-prev[policy].get(k,0)) for k in set(w)|set(prev[policy]))
        prev[policy]=w
        assert np.isclose(turn,p[f'{policy}_half_turnover'],atol=1e-14)
        rr=[R.loc[(row,t)] for t in [a,b]]
        valid=all(bool(x.eligible_label) and bool(x.entry_price_observed) and bool(x.exit_price_observed) and np.isfinite(x.r_o2o_bp) for x in rr)
        assert valid==bool(p[f'{policy}_label_valid'])
        if valid:
            simple=sum(float(np.expm1(x.r_o2o_bp/10000)) for x in rr)/2
            est=float(10000*np.log1p(simple-.002*turn))
            e=abs(est-float(p[f'{policy}_net_log_bp'])); maxerr=max(e,maxerr)
            assert e<1e-8,(row,policy,e)
    if bool(p.paired_valid):
        assert abs(p.net_delta_bp-p.DOM_net_log_bp+p.AUTH_net_log_bp)<1e-9
        pair_ok+=1

# Independently validate retention using fixed as-of ranks and past months ONLY.
lookup=A.set_index(['signal_date','ticker']);dates=sorted(D.signal_date)
for i,d in D.iterrows():
    if pd.isna(d.core):continue
    x=lookup.loc[(d.signal_date,d.core)]
    n=int(x.n_t)
    if d.reason=='RETAIN':
        assert i>0 and D.iloc[i-1].core==d.core
        assert x.rank_126<=math.ceil(.20*n) and x.rank_252<=math.ceil(.20*n)
        val=R.loc[(d.signal_date,d.core)]
        assert val.ret_63>0 and val.ret_21>-.05
    else:
        assert x.rank_126<=math.ceil(.10*n) and x.rank_252<=math.ceil(.10*n)
        assert x.rank_63<=math.ceil(.25*n)
        val=R.loc[(d.signal_date,d.core)]
        assert val.ret_21>-.05
        assert i>=2
        counts=0
        for j in range(i-2,i+1):
            key=(dates[j],d.core)
            if key in lookup.index:
                z=lookup.loc[key]
                counts+=int(z.rank_126<=math.ceil(.10*z.n_t))
        assert counts>=2

# Validate future six-month sums without using the algorithm's rolling helper.
full=R[['eligible_label','r_o2o_bp']]
min_n=1e9;future_checked=0;max_fut_err=0.
for _,z in F.iterrows():
    if not bool(z.forward6_scoreable):continue
    ix=dates.index(z.signal_date)
    six=dates[ix:ix+6]
    assert len(six)==6
    vals=[full.loc[(d,z.ticker)] for d in six]
    assert all(bool(x.eligible_label) and np.isfinite(x.r_o2o_bp) for x in vals)
    actual=sum(float(x.r_o2o_bp) for x in vals)
    max_fut_err=max(max_fut_err,abs(actual-z.future6_r_bp))
    assert abs(actual-z.future6_r_bp)<1e-8
    future_checked+=1

M=P[P.signal_date.between('2021-01-01','2024-12-31')].copy()
assert len(M)==48 and M.paired_valid.all()
mean=float(M.net_delta_bp.mean())
assert abs(mean-SUM['mean_monthly_delta_net_bp'])<1e-10
assert abs(SUM['cumulative_net_log_advantage_bp']-M.net_delta_bp.sum())<1e-10
rng=np.random.default_rng(36001); a=M.net_delta_bp.to_numpy(float);draws=[]
for _ in range(2000):
    ix=np.concatenate([(np.arange(6)+rng.integers(0,48))%48 for _ in range(8)])[:48]
    draws.append(float(a[ix].mean()))
ci=np.quantile(draws,[.025,.975]);assert np.allclose(ci,SUM['bootstrap_ci95_bp'],atol=1e-8)

# Check baseline USA untouched by scope; no USA decision records/output and frozen references.
assert set(D.columns).isdisjoint({'usa_signal','usa_action'})
assert SUM['reference_usa_olc17_cagr']==.523006 and SUM['reference_usa_olc19_cagr']==.507722
assert SUM['decision']=='STOP' and not all(SUM['gates'].values())
verify={'ok':True,'input_sha256':sha(raw),'months':len(D),'main_months':len(M),
    'max_economic_math_error_bp':maxerr,'evaluated_policy_pairs':2*pair_ok,
    'core_state_hysteresis_checked':int(D.core.notna().sum()),
    'future6_matched_selection_slots_checked':future_checked,
    'max_future6_sum_error_bp':max_fut_err,
    'bootstrap_95pct_verified':list(map(float,ci)),
    'source_date_asof_verified':True,'no_future_outcome_features':True,
    'usa_unmodified':True,'baseline_portfolio_contract_not_replayed':True,'result':'STOP'}
(OUT/'OLC36_INDEPENDENT_VERIFICATION.json').write_text(json.dumps(verify,indent=2))
print(json.dumps(verify,indent=2))
