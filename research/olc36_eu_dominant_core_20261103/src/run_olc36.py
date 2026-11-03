#!/usr/bin/env python3
"""OLC36: prespecified, EU-only stateful dominance core diagnostic.

Preregistration: https://github.com/AM1975MA/Test/commit/6cc8790fec75154dc3a71f1e48e34b2744901166
Historical month labels are used ONLY for evaluation, never for decision-making.
"""
from __future__ import annotations
import hashlib, zipfile, gzip, io, math, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'input'/'OLC32_RESULTS.zip'
OUT=ROOT/'results';FIG=ROOT/'figures'
OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
EXPECTED_ARCHIVE='aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d'
EXPECTED_TABLE='83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16'
assert sha(SRC.read_bytes())==EXPECTED_ARCHIVE,'source archive hash mismatch'
with zipfile.ZipFile(SRC) as z:
    payload=z.read('results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz')
assert sha(payload)==EXPECTED_TABLE,'table sha mismatch'
df=pd.read_csv(io.BytesIO(gzip.decompress(payload)))
assert not df.duplicated(['market','signal_date','ticker']).any()
assert len(df)==27191
src_date=pd.to_datetime(df.source_date,errors='coerce')
sig_date=pd.to_datetime(df.signal_date)
assert (src_date.dropna() <= sig_date[src_date.notna()]).all()
assert (~df.loc[src_date.isna(),'feature_available_asof']).all()
eu=df[df.market.eq('EU')].copy(); assert eu.signal_date.nunique()==90
DATES=sorted(eu.signal_date.unique())

ASOF=['signal_date','ticker','auth_rank','ret_21','ret_63','ret_126','ret_252','feature_available_asof','source_date']

def select(asof:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    """Decision function is intentionally unable to see any future-return or label column."""
    assert set(asof.columns)==set(ASOF),f'unsupported columns {set(asof)-set(ASOF)}'
    dates=sorted(asof.signal_date.unique())
    feats=[]; state=[]; prev_core=None; bymonth={}
    for ix,d in enumerate(dates):
        m=asof[asof.signal_date.eq(d)].copy()
        assert m.ticker.is_unique and m.auth_rank.is_unique
        m=m.sort_values(['auth_rank','ticker'])
        leader,second=m.iloc[0].ticker,m.iloc[1].ticker
        ready=m.feature_available_asof.fillna(False).astype(bool) & m.source_date.notna()
        ready &= m[['ret_21','ret_63','ret_126','ret_252']].notna().all(axis=1)
        ready &= np.isfinite(m[['ret_21','ret_63','ret_126','ret_252']].to_numpy()).all(axis=1)
        ready &= (m.source_date <= d)
        valid=m.loc[ready].copy()
        n=len(valid)
        for key in ['ret_63','ret_126','ret_252']:
            valid=valid.sort_values([key,'ticker'],ascending=[False,True])
            valid['rank_'+key.split('_')[1]]=np.arange(1,n+1,dtype=int)
        valid['n_t']=n
        dfval=valid.set_index('ticker',drop=False)
        bymonth[d]=dfval
        old=prev_core;reason='NONE';chosen=None
        if old is not None and old in dfval.index:
            row=dfval.loc[old]
            if row.rank_126<=math.ceil(.20*n) and row.rank_252<=math.ceil(.20*n) and row.ret_63>0 and row.ret_21>-.05:
                chosen=old;reason='RETAIN'
        if chosen is None and ix>=2:
            qualifier=[]
            for _,row in dfval.iterrows():
                if not (row.rank_126 <= math.ceil(.10*n) and row.rank_252 <= math.ceil(.10*n)
                        and row.rank_63 <= math.ceil(.25*n) and row.ret_21 > -.05):
                    continue
                his=[]
                for prevdate in dates[ix-2:ix+1]:
                    prevmonth=bymonth[prevdate]
                    good=row.ticker in prevmonth.index and prevmonth.loc[row.ticker].rank_126<=math.ceil(.10*len(prevmonth))
                    his.append(bool(good))
                if sum(his)>=2:qualifier.append((row.rank_126/n+row.rank_252/n,-row.ret_252,row.ticker))
            if qualifier:
                chosen=min(qualifier)[2]
                reason='NEW' if chosen!=old else 'REACQUIRE'
        prev_core=chosen
        slot2=chosen if chosen and chosen!=leader else second
        changed=slot2!=second
        record={'signal_date':d,'auth_top1':leader,'auth_top2':second,'dom_top1':leader,
                'dom_top2':slot2,'core':chosen,'reason':reason,'n_feature_valid':n,
                'changed':changed,'core_is_auth_top1':bool(chosen==leader),'core_as_second':bool(chosen==slot2)}
        if chosen and chosen in dfval.index:
            row=dfval.loc[chosen]
            record.update({'core_rank_63':int(row.rank_63),'core_rank_126':int(row.rank_126),
                           'core_rank_252':int(row.rank_252),'core_ret_126':float(row.ret_126),'core_ret_252':float(row.ret_252)})
        state.append(record)
        feats.append(valid[['signal_date','ticker','rank_63','rank_126','rank_252','n_t']].copy())
    return pd.DataFrame(state),pd.concat(feats,ignore_index=True)

dec,ranks=select(eu[ASOF].copy())
assert len(dec)==90 and dec.auth_top1.ne(dec.dom_top2).all()
assert dec.auth_top1.ne(dec.auth_top2).all()
assert (dec.dom_top1==dec.auth_top1).all()
assert dec.signal_date.is_unique
assert dec[dec.signal_date.between('2021-01-01','2024-12-31')].shape[0]==48
# Pure-asof path with perturbed label columns is unchanged by design.
perturbed=eu.copy();perturbed.loc[perturbed.signal_date>='2023-01-01','r_o2o_bp']*=100
perturbed.loc[perturbed.signal_date>='2023-01-01','eligible_label']=False
redec,_=select(perturbed[ASOF].copy())
assert dec.fillna('NA').equals(redec.fillna('NA'))

# Evaluation labels: source-observed only; never fed into select().
labels=eu.set_index(['signal_date','ticker'])[['eligible_label','r_o2o_bp','entry_price_observed','exit_price_observed','entry_date','exit_date']]
rows=[];prevs={}
for _,r in dec.iterrows():
    row={'signal_date':r.signal_date,**r.to_dict()}
    for policy,pair in [('AUTH',[r.auth_top1,r.auth_top2]),('DOM',[r.dom_top1,r.dom_top2])]:
        weights={pair[0]:.5,pair[1]:.5}
        previous=prevs.get(policy,{})
        half_turnover=.5*sum(abs(weights.get(t,0)-previous.get(t,0)) for t in set(weights)|set(previous))
        prevs[policy]=weights
        vals=[labels.loc[(r.signal_date,t)] for t in pair]
        valid=all(bool(v.eligible_label) and bool(v.entry_price_observed) and bool(v.exit_price_observed)
                  and np.isfinite(v.r_o2o_bp) for v in vals)
        row[f'{policy}_label_valid']=valid
        row[f'{policy}_half_turnover']=half_turnover
        if valid:
            returns=[float(np.expm1(v.r_o2o_bp/10000)) for v in vals]
            simple=.5*sum(returns)
            net=simple-.002*half_turnover
            assert net>-1
            row[f'{policy}_gross_simple_return']=simple
            row[f'{policy}_net_log_bp']=float(10000*np.log1p(net))
            row[f'{policy}_net_simple_return']=net
        else:
            row[f'{policy}_gross_simple_return']=np.nan
            row[f'{policy}_net_log_bp']=np.nan
            row[f'{policy}_net_simple_return']=np.nan
    rows.append(row)
monthly=pd.DataFrame(rows)
monthly['paired_valid']=monthly.AUTH_label_valid & monthly.DOM_label_valid
monthly['net_delta_bp']=monthly.DOM_net_log_bp-monthly.AUTH_net_log_bp
monthly.loc[~monthly.paired_valid,'net_delta_bp']=np.nan

# Future six-month elite designation, evaluation only. Vectorized contiguous windows.
future_records=[]
fx=eu[['signal_date','ticker','eligible_label','r_o2o_bp']].copy()
fx['date_pos']=fx.signal_date.map({d:i for i,d in enumerate(DATES)})
fx=fx.sort_values(['ticker','date_pos']).reset_index(drop=True)
fx['r_observed']=fx.r_o2o_bp.where(fx.eligible_label & np.isfinite(fx.r_o2o_bp))
fx['future6_r_bp']=fx.groupby('ticker',sort=False).r_observed.transform(lambda s: s.rolling(6,min_periods=6).sum().shift(-5))
fx['pos_end']=fx.groupby('ticker',sort=False).date_pos.shift(-5)
fx.loc[fx.pos_end!=fx.date_pos+5,'future6_r_bp']=np.nan
choices=dec.set_index('signal_date')
for date,grp in fx.groupby('signal_date',sort=True):
    future6=dict(zip(grp.loc[grp.future6_r_bp.notna(),'ticker'],grp.loc[grp.future6_r_bp.notna(),'future6_r_bp']))
    n=len(future6)
    if n<100:continue
    threshold=math.ceil(.10*n)
    order=sorted(future6,key=lambda t:(-future6[t],t))
    topset=set(order[:threshold]); record=choices.loc[date]
    for policy in ('AUTH','DOM'):
        prefix='auth' if policy=='AUTH' else 'dom'
        pair=[record[f'{prefix}_top1'],record[f'{prefix}_top2']]
        for slot,ticker in enumerate(pair,1):
            future_records.append({'signal_date':date,'policy':policy,'slot':slot,'ticker':ticker,
                'forward6_scoreable':ticker in future6,'future6_topdecile':ticker in topset if ticker in future6 else np.nan,
                'n_forward6':n,'future6_r_bp':future6.get(ticker,np.nan)})
future=pd.DataFrame(future_records)

M=monthly[monthly.signal_date.between('2021-01-01','2024-12-31')].copy()
assert len(M)==48
paired=M[M.paired_valid].copy()
P=future[future.signal_date.between('2021-01-01','2024-12-31')].copy()
assert P.signal_date.nunique()==48
hit={}
for policy in ('AUTH','DOM'):
    group=P[P.policy.eq(policy)]
    hit[policy]={ 'slots':len(group),'label_available':int(group.forward6_scoreable.sum()),
                  'hit_rate_matched':float(group.loc[group.forward6_scoreable,'future6_topdecile'].mean()),
                  'hits':int(group.loc[group.forward6_scoreable,'future6_topdecile'].sum())}
# Matched 2x48 slot records, failure to evaluate is reported.
pivot=P.pivot(index=['signal_date','slot'],columns='policy',values=['forward6_scoreable','future6_topdecile'])
matched=pivot['forward6_scoreable']['AUTH'].astype(bool)&pivot['forward6_scoreable']['DOM'].astype(bool)
hit_matched={policy:float(pivot.loc[matched,('future6_topdecile',policy)].astype(float).mean()) for policy in ('AUTH','DOM')}

# Circular six-month block bootstrap (paired by calendar month) for mean log excess, not data-snooping adjusted.
rng=np.random.default_rng(36001)
a=paired.net_delta_bp.to_numpy(dtype=float)
ci=[np.nan,np.nan];draws=[]
if len(a)==48:
    for _ in range(2000):
        ix=np.concatenate([(np.arange(6)+rng.integers(0,len(a)))%len(a) for _ in range(math.ceil(len(a)/6))])[:len(a)]
        draws.append(float(a[ix].mean()))
    ci=list(map(float,np.quantile(draws,[.025,.975])))
else:
    # preserve fixed 48-month blocks without silently dropping months from bootstrap
    draws=[np.nan]*2000

# Monthly proxy compounded continuously for matched 2021–2024 cases (not actual strategy NAV).
nav={};maxdd={};proxy_cagr={}
for policy in ('AUTH','DOM'):
    vec=M[f'{policy}_net_simple_return'].to_numpy(float)
    if np.isfinite(vec).all():
        nav[policy]=np.cumprod(1+vec)
        maxdd[policy]=float(np.min(nav[policy]/np.maximum.accumulate(np.r_[1.,nav[policy]])[1:]-1))
        proxy_cagr[policy]=float(np.prod(1+vec)**(12/len(vec))-1)
    else:
        nav[policy]=np.full(len(M),np.nan)
        maxdd[policy]=np.nan;proxy_cagr[policy]=np.nan

changed=int(M.changed.sum());valid_chg=int(M[M.changed].paired_valid.sum());coverage=float(M.paired_valid.mean())
mean=float(paired.net_delta_bp.mean())
hit_delta=hit_matched['DOM']-hit_matched['AUTH']
ci_low=ci[0]
passes={'changes_ge_12':changed>=12,'paired_coverage_ge_95pct':coverage>=.95,
    'mean_net_excess_gt_0':mean>0,'bootstrap_95pct_lower_gt_0':np.isfinite(ci_low) and ci_low>0,
    'forward_6m_topdecile_hits_increase_ge_5pp':hit_delta>=.05,
    'monthly_proxy_MaxDD_degradation_le_3pp':np.isfinite(maxdd['DOM']) and (maxdd['DOM']-maxdd['AUTH']>=-.03)}
# Missing forward6 paired slot fraction is audited and exposed.
summary={
    'study':'OLC36_DOM_CORE','preregistered_commit':'6cc8790fec75154dc3a71f1e48e34b2744901166',
    'scope':'EU only; USA frozen, no USA evaluation or write','primary_period':'2021-2024',
    'n_months':int(len(M)),'n_months_changed':changed,'n_months_changed_label_valid':valid_chg,
    'n_paired_label_months':len(paired),'coverage':coverage,
    'mean_monthly_delta_net_bp':mean,'bootstrap_ci95_bp':ci,'mean_monthly_abs_delta_bp':float(paired.net_delta_bp.abs().mean()),
    'cumulative_net_log_advantage_bp':float(paired.net_delta_bp.sum()),
    'proxy_cagr':proxy_cagr,'proxy_maxdd':maxdd,
    'future6_topdecile_rates_all':hit,'future6_matched_slots':int(matched.sum()),
    'future6_topdecile_rate_matched':hit_matched,'future6_hit_rate_delta_pp':100*hit_delta,
    'n_core_active':int(M.core.notna().sum()),'n_core_chosen_as_second':int(M.core_as_second.sum()),
    'n_core_new':int(M.reason.eq('NEW').sum()),'n_core_retained':int(M.reason.eq('RETAIN').sum()),
    'gates':passes,'decision':'GO_TO_INDEPENDENT_REPLAY_ONLY' if all(passes.values()) else 'STOP',
    'reference_usa_olc17_cagr':.523006,'reference_usa_olc19_cagr':.507722,
    'caveat':'Retrospective, same history extensively explored; monthly two-ETF equal-weight proxy is not OLC19 NAV, stops/V6/fees/fill are not replicated.'}

# Per-year table & key illustrative ticker diagnostic.
annual=[]
for y,g in M.groupby(M.signal_date.str[:4]):
    valid=g[g.paired_valid]; sub=P[P.signal_date.str[:4].eq(y)]
    annual.append({'year':y,'months':len(g),'changed':int(g.changed.sum()),'paired_valid':len(valid),
        'mean_net_delta_bp':valid.net_delta_bp.mean(), 'total_net_delta_bp':valid.net_delta_bp.sum(),
        'core_months':int(g.core.notna().sum())})
annual=pd.DataFrame(annual)
quote=eu[(eu.ticker=='QDVE.DE')&(eu.signal_date.between('2019-01-01','2026-06-30'))]
qdve=dec[['signal_date','core','auth_top1','auth_top2','dom_top1','dom_top2','changed','reason']].copy()
qdve['qdve_auth_rank']=qdve.signal_date.map(quote.set_index('signal_date').auth_rank)
qdve['qdve_selected_auth']=qdve.auth_top1.eq('QDVE.DE')|qdve.auth_top2.eq('QDVE.DE')
qdve['qdve_selected_dom']=qdve.dom_top1.eq('QDVE.DE')|qdve.dom_top2.eq('QDVE.DE')
qdve['qdve_core']=qdve.core.eq('QDVE.DE')

# Write outputs.
dec.to_csv(OUT/'OLC36_EU_CORE_DECISIONS.csv',index=False)
ranks.to_csv(OUT/'OLC36_EU_ASOF_RANKS.csv',index=False)
monthly.to_csv(OUT/'OLC36_MONTHLY_PROXY.csv',index=False)
future.to_csv(OUT/'OLC36_FUTURE6_RETENTION_DIAGNOSTIC.csv',index=False)
annual.to_csv(OUT/'OLC36_ANNUAL.csv',index=False)
qdve.to_csv(OUT/'OLC36_QDVE_DIAGNOSTIC.csv',index=False)
pd.DataFrame({'draw_id':range(2000),'mean_excess_bp':draws}).to_csv(OUT/'OLC36_BOOTSTRAP.csv',index=False)
(OUT/'OLC36_SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False))

# Annual change and core signal overview.
fig,ax=plt.subplots(figsize=(8,4.5));X=np.arange(len(annual));ax.bar(X,annual.changed.to_numpy(),label='Sostituzioni Top2');ax.plot(X,annual.core_months.to_numpy(),marker='o',label='Mesi con ETF core');ax.set_xticks(X,annual.year);ax.set_ylim(bottom=0);ax.set_title('OLC36 EU: attivazioni del core dominante');ax.set_ylabel('Numero mesi');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(FIG/'OLC36_EU_ACTIONS.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5));if_ok=all(np.isfinite(nav[k]).all() for k in ['AUTH','DOM']);
if if_ok:
    ax.plot(pd.to_datetime(M.signal_date),np.r_[100,100*nav['AUTH']][1:],label='AUTH Top2 (proxy)')
    ax.plot(pd.to_datetime(M.signal_date),np.r_[100,100*nav['DOM']][1:],label='DOM_CORE (proxy)')
    ax.set_ylabel('Indice proxy (base 100 prima di gennaio 2021)')
else:
    ax.plot(pd.to_datetime(paired.signal_date),paired.net_delta_bp.cumsum(),label='Cumulato log-bp netto, matched')
    ax.set_ylabel('Differenziale log-bp matched')
ax.set_title('OLC36 EU: confronto mensile Open→Open; non è NAV operativo');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(FIG/'OLC36_EU_PROXY_CURVES.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4));ax.plot(pd.to_datetime(qdve.signal_date),qdve.qdve_auth_rank,label='AUTH rank QDVE.DE',lw=1.2);ax.scatter(pd.to_datetime(qdve[qdve.qdve_core].signal_date),qdve[qdve.qdve_core].qdve_auth_rank,label='Core QDVE (diagnostico)',s=30,marker='o');ax.set_ylim(165,0);ax.set_title('OLC36: traiettoria rank FUSION QDVE.DE (diagnostica ex post)');ax.set_ylabel('Rango AUTH (1 = migliore)');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(FIG/'OLC36_EU_QDVE_RANK.png',dpi=160);plt.close(fig)

manifest={'input':{'OLC32_RESULTS.zip':EXPECTED_ARCHIVE,'OLC32_corrected_data_sha256':EXPECTED_TABLE},'out':{}}
for f in sorted([*OUT.iterdir(),*FIG.iterdir()]):
    if f.name=='OLC36_MANIFEST.json':continue
    manifest['out'][str(f.relative_to(ROOT))]={'sha256':sha(f.read_bytes()),'bytes':f.stat().st_size}
(OUT/'OLC36_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print('SUMMARY\n',json.dumps(summary,indent=2));print('ANNUAL\n',annual.to_string(index=False));print('QDVE per year\n',qdve.assign(year=qdve.signal_date.str[:4]).groupby('year')[['qdve_selected_auth','qdve_selected_dom','qdve_core']].sum().to_string());print('changed rows\n',M.loc[M.changed,['signal_date','auth_top1','auth_top2','dom_top2','core','reason','net_delta_bp']].to_string(index=False))
