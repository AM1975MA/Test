#!/usr/bin/env python3
"""OLC35: fixed retrospective attribution, without modifying portfolios or training.

Inputs & computations frozen by GitHub protocol 93d7a799. Requires numpy,pandas,matplotlib.
"""
from __future__ import annotations
import zipfile,io,gzip,hashlib,json,os,sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SRC=Path(__file__).resolve().parents[1]
D32=SRC/'input'/'OLC32_RESULTS.zip'
D17=SRC/'input'/'OLC17_Validazione_Risultati_20261102.zip'
D19=SRC/'input'/'OLC19_Rischio_Rientro_Risultati_20261102.zip'
DEST=SRC
(DEST/'results').mkdir(parents=True,exist_ok=True)
(DEST/'figures').mkdir(parents=True,exist_ok=True)
EXPECTED={
 str(D32):'aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d',
 str(D17):'b780ef1e43c756c5649898ca37170ac66391730a13f8649403a1b68426f5c04f',
 str(D19):'f574339c8c7ab25e159e83d8fb55fc4be2dc44bdc0ed06a9fbf96e6b24f4a021'
}
def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
for f,expected in EXPECTED.items():
    actual=sha(Path(f).read_bytes())
    assert actual==expected,(f,expected,actual)
with zipfile.ZipFile(D32) as z:
    dfraw=z.read('results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz')
    assert sha(dfraw)=='83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16'
    df=pd.read_csv(io.BytesIO(gzip.decompress(dfraw)))
assert len(df)==27191
assert not df.duplicated(['market','signal_date','ticker']).any()
assert (pd.to_datetime(df.loc[df.source_date.notna(),'source_date'])<=pd.to_datetime(df.loc[df.source_date.notna(),'signal_date'])).all()
assert (~df.loc[df.source_date.isna(),'feature_available_asof']).all()
main=df[(df.signal_date>='2021-01-01')&(df.signal_date<='2024-12-31')].copy()
assert set(main.market)=={'EU','USA'}
for market in ['EU','USA']:
    assert main[main.market.eq(market)].signal_date.nunique()==48
    assert main[main.market.eq(market)].groupby('signal_date').size().min()>=145
assert main.loc[main.eligible_label,'r_o2o_bp'].notna().all()
valid=main[main.eligible_label & main.r_o2o_bp.notna()].copy()
missing=main.groupby(['market','signal_date']).agg(n_universe=('ticker','size'),n_eligible=('eligible_label','sum'),month_quality=('month_quality','min')).reset_index()
missing['n_missing']=missing.n_universe-missing.n_eligible
missing.to_csv(DEST/'results'/'OLC35_LABEL_COVERAGE.csv',index=False)
with zipfile.ZipFile(D17) as z:
    proposal=pd.concat([pd.read_csv(io.BytesIO(z.read(f'results/PROPOSALS_{m}.csv'))) for m in ['EU','USA']],ignore_index=True)
    score17=pd.read_csv(io.BytesIO(z.read('results/COMBINED_SCORECARD.csv')))
with zipfile.ZipFile(D19) as z:
    pref='olc19_combined_risk_20261102/results/'
    score19=pd.read_csv(io.BytesIO(z.read(pref+'SCORECARD.csv')))
proposal=proposal[(proposal.variant=='TOP2_CONTEXT_REVALUE')&(proposal.signal_date>='2021-01-01')&(proposal.signal_date<='2024-12-31')]
assert len(proposal)==96
rank=main[main.auth_rank<=2].sort_values(['market','signal_date','auth_rank']).groupby(['market','signal_date'],sort=True).agg(t1=('ticker','first'),t2=('ticker','last'),count=('ticker','size')).reset_index()
assert (rank['count']==2).all()
pair=proposal.merge(rank,on=['market','signal_date'],how='outer',validate='one_to_one',indicator=True)
pair['set_match']=pair.apply(lambda r:{r.ticker1,r.ticker2}=={r.t1,r.t2},axis=1)
assert pair._merge.eq('both').all() and pair.set_match.all(),pair.loc[~pair.set_match]
pair[['market','signal_date','ticker1','ticker2','t1','t2','set_match']].to_csv(DEST/'results'/'OLC35_TOP2_RECONCILIATION.csv',index=False)

# Ex-post oracle ceilings: all eligible labels only. NO allocation/trading strategy is simulated.
rows=[]
for (market,date),block in valid.groupby(['market','signal_date'],sort=True):
    overall=block.sort_values(['r_o2o_bp','auth_rank','ticker'],ascending=[False,True,True]).iloc[0]
    top5=block[block.auth_rank<=5]
    top2=block[block.auth_rank<=2].sort_values('auth_rank')
    assert len(top5)==5 and len(top2)==2,(market,date,len(top5),len(top2))
    top5win=top5.sort_values(['r_o2o_bp','auth_rank','ticker'],ascending=[False,True,True]).iloc[0]
    top2win=top2.sort_values(['r_o2o_bp','auth_rank','ticker'],ascending=[False,True,True]).iloc[0]
    top2proxy=top2.r_o2o_bp.mean()
    d0=float(overall.r_o2o_bp-top5win.r_o2o_bp)
    d1=float(top5win.r_o2o_bp-top2win.r_o2o_bp)
    d2=float(top2win.r_o2o_bp-top2proxy)
    total=float(overall.r_o2o_bp-top2proxy)
    assert min(d0,d1,d2)>=-1e-6 and abs(total-d0-d1-d2)<1e-7
    rows.append(dict(market=market,signal_date=date,year=int(date[:4]),n_eligible=len(block),
                     top1=top2.iloc[0].ticker,top2=top2.iloc[1].ticker,
                     top1_return_bp=float(top2.iloc[0].r_o2o_bp),top2_return_bp=float(top2.iloc[1].r_o2o_bp),
                     best_market_ticker=str(overall.ticker),best_market_rank=int(overall.auth_rank),
                     best_market_bp=float(overall.r_o2o_bp),
                     best_top5_ticker=str(top5win.ticker),best_top5_bp=float(top5win.r_o2o_bp),
                     best_top2_ticker=str(top2win.ticker),best_top2_bp=float(top2win.r_o2o_bp),
                     selected_two_logscore_bp=float(top2proxy),
                     opportunity_outside_top5_bp=d0,opportunity_within_top5_outside_top2_bp=d1,
                     opportunity_two_slot_concentration_bp=d2,oracle_total_bp=total,
                     best_market_in_top5=bool(overall.auth_rank<=5),best_market_in_top2=bool(overall.auth_rank<=2)))
det=pd.DataFrame(rows)
assert len(det)==96 and all(det.groupby('market').size()==48)
# Independent available-as-of diagnostic: prevent treating non-scoreable tickers as actionable.
asof=[]
for (market,date),group in valid.groupby(['market','signal_date'],sort=True):
    eligible=group[group.feature_available_asof & group.source_date.notna()]
    assert len(eligible)>=100
    leader=eligible.sort_values(['r_o2o_bp','auth_rank','ticker'],ascending=[False,True,True]).iloc[0]
    asof.append({'market':market,'signal_date':date,'asof_best_ticker':leader.ticker,'asof_best_rank':int(leader.auth_rank),'asof_best_bp':float(leader.r_o2o_bp),'asof_eligible_count':len(eligible)})
asof=pd.DataFrame(asof)
det=det.merge(asof,on=['market','signal_date'],validate='one_to_one')
det['oracle_availability_effect_bp']=det.best_market_bp-det.asof_best_bp
assert (det.oracle_availability_effect_bp>=-1e-8).all()
assert len(det)==96
peers=valid.groupby(['market','signal_date']).agg(market_median_bp=('r_o2o_bp','median'),market_mean_bp=('r_o2o_bp','mean'),market_dispersion_bp=('r_o2o_bp','std')).reset_index()
det=det.merge(peers,on=['market','signal_date'],validate='one_to_one')
det['top2_advantage_to_median_bp']=det.selected_two_logscore_bp-det.market_median_bp
det['top2_advantage_to_mean_bp']=det.selected_two_logscore_bp-det.market_mean_bp
det['top2_crosssectional_zscore'] = det.top2_advantage_to_mean_bp/det.market_dispersion_bp
det.to_csv(DEST/'results'/'OLC35_MONTHLY_ORACLE_DECOMPOSITION.csv',index=False)

# Separate historical portfolio scorecards, paired identical fee and period per market.
a=score17[(score17.variant=='TOP2_CONTEXT_REVALUE')&(score17.scenario=='ALL_PREOPEN_V6')&(score17.fee==.001)&(score17.period=='ACTIVE2021_2024')].copy()
b=score19[(score19.variant=='TOP2_CONTEXT_REVALUE')&(score19.contract=='FAST_LOCK3')&(score19.fee==.001)&(score19.stop_friction==.001)&(score19.stress==False)&(score19.period=='ACTIVE2021_2024')].copy()
assert len(a)==2 and len(b)==2
col=['market','cagr','annual_log','maxdd','turnover_annual','actual_risk_exposure','stops','rebalances','fee_drag_sum','period_return','first_valuation','last_valuation']
a=a[col].copy();b=b[col].copy();a.insert(1,'source','OLC17_ALL_PREOPEN_V6');b.insert(1,'source','OLC19_FAST_LOCK3')
port=pd.concat([a,b],ignore_index=True).sort_values(['market','source'])
port.to_csv(DEST/'results'/'OLC35_FROZEN_PORTFOLIO_BASELINES.csv',index=False)
# Do not compare stop policies as identical. This is an in-family descriptive ledger.
contracts=score19[(score19.variant=='TOP2_CONTEXT_REVALUE')&
    (score19.contract.isin(['BASE','ALARM','FAST_LOCK3']))&
    (score19.fee==.001)&(score19.stop_friction==.001)&
    (score19.stress==False)&(score19.period=='ACTIVE2021_2024')]
assert len(contracts)==6
contracts[['market','contract','cagr','maxdd','turnover_annual','actual_risk_exposure','stops','fee_drag_sum']].to_csv(
    DEST/'results'/'OLC35_SAME_FAMILY_RISK_CONTRACTS.csv',index=False)
assert abs(float(a.loc[a.market.eq('USA'),'cagr'].iloc[0])-.523006)<1e-6
assert abs(float(b.loc[b.market.eq('USA'),'cagr'].iloc[0])-.507722)<1e-6

names=['opportunity_outside_top5_bp','opportunity_within_top5_outside_top2_bp','opportunity_two_slot_concentration_bp','oracle_total_bp']
def metrics(g):
    r={'months':len(g),'mean_n_eligible':float(g.n_eligible.mean()),
       'top5_hit_rate':float(g.best_market_in_top5.mean()),'top2_hit_rate':float(g.best_market_in_top2.mean()),
       'median_best_rank':float(g.best_market_rank.median()),
       'best_rank_p75':float(g.best_market_rank.quantile(.75)),
       'top5_oracle_vs_selected_bp':float((g.best_top5_bp-g.selected_two_logscore_bp).mean()),
       'top2_avg_logscore_bp':float(g.selected_two_logscore_bp.mean()),
       'top1_avg_logreturn_bp':float(g.top1_return_bp.mean()),
       'market_median_logreturn_bp':float(g.market_median_bp.mean()),
       'mean_top2_advantage_to_median_bp':float(g.top2_advantage_to_median_bp.mean()),
       'top2_beats_median_share':float((g.top2_advantage_to_median_bp>0).mean()),
       'top2_standardized_advantage_z':float(g.top2_crosssectional_zscore.mean()),
       'mean_crosssectional_dispersion_bp':float(g.market_dispersion_bp.mean()),
       'unscoreable_best_months':int((g.oracle_availability_effect_bp>1e-9).sum()),
       'mean_unscoreable_best_extra_bp':float(g.oracle_availability_effect_bp.mean())}
    for n in names:
        r[n+'_mean']=float(g[n].mean());r[n+'_median']=float(g[n].median());r[n+'_p90']=float(g[n].quantile(.9))
    den=sum(g[n].sum() for n in names[:3]);
    for n in names[:3]:r[n+'_share']=float(g[n].sum()/den)
    r['top5_months_share_oracle_gap']=float(g.oracle_total_bp.nlargest(5).sum()/g.oracle_total_bp.sum())
    return r
summary=pd.DataFrame([{'market':m,**metrics(g)} for m,g in det.groupby('market')]);summary.to_csv(DEST/'results'/'OLC35_MARKET_SUMMARY.csv',index=False)
byyear=pd.DataFrame([{'market':m,'year':y,**metrics(g)} for (m,y),g in det.groupby(['market','year'])]);byyear.to_csv(DEST/'results'/'OLC35_ANNUAL_SUMMARY.csv',index=False)

# For feasibility, compare simple ex-post metric vs gross without conflating actual NAV.
baskets=det.groupby('market').agg(n_month=('year','size'),avg_top1_bp=('top1_return_bp','mean'),avg_top2proxy_bp=('selected_two_logscore_bp','mean'),avg_top5oracle_bp=('best_top5_bp','mean'),avg_marketoracle_bp=('best_market_bp','mean'))
baskets['note']='These are mean individual log returns, NOT monthly portfolio NAV with fees and stops.'
baskets.to_csv(DEST/'results'/'OLC35_GROSS_LABEL_DIAGNOSTIC.csv')

# Illustrations; no hindsight strategy is presented as a backtest.
for market in ['EU','USA']:
    annual=byyear[byyear.market.eq(market)].set_index('year')
    comps=names[:3]
    labels=['Fuori Top5','Dentro Top5, fuori Top2','Concentrazione Top2']
    fig,ax=plt.subplots(figsize=(10,5))
    yrs=np.array(annual.index,dtype=int);base=np.zeros(len(yrs));
    for label,comp in zip(labels,comps):
        vals=annual[comp+'_mean'].to_numpy();ax.bar(yrs.astype(str),vals,bottom=base,label=label);base+=vals
    ax.set_title(f'OLC35 — {market}: gap mensile massimo ex-post (diagnostico)')
    ax.set_ylabel('Punti base di log-rendimento / mese')
    ax.set_xlabel('Anno del segnale')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.13),ncol=3,fontsize=9,frameon=False)
    ax.grid(axis='y',alpha=.2);fig.tight_layout()
    fig.savefig(DEST/'figures'/f'OLC35_ORACLE_GAP_{market}.png',dpi=160,bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(9,5))
width=.18;x=np.arange(2);categories=['EU','USA'];colors=None
for i,v in enumerate(['OLC17_ALL_PREOPEN_V6','OLC19_FAST_LOCK3']):
    vals=[100*float(port[(port.market==m)&(port.source==v)].cagr.iloc[0]) for m in categories]
    ax.bar(x+(i-.5)*.35,vals,width=.32,label=v.replace('_',' '))
ax.set_xticks(x,categories);ax.set_ylabel('CAGR storico netto (%)')
ax.set_title('OLC35 — Riferimenti congelati 2021–2024 (convenzioni diverse)')
ax.legend(loc='upper left',fontsize=9);ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(DEST/'figures'/'OLC35_USA_GUARDRAIL_BASELINES.png',dpi=160);plt.close(fig)

# Structural audits and no new candidate portfolio.
audit={'total_month_market_rows':len(det),'annual_months':{m:det[det.market.eq(m)].groupby('year').size().to_dict() for m in ['EU','USA']},
  'olc17_top2_pair_matches':int(pair.set_match.sum()),'olc17_top2_pair_compared':len(pair),
  'decomposition_max_residual_bp':float((det.oracle_total_bp-det[names[:3]].sum(axis=1)).abs().max()),
  'num_label_missing_by_market':main[~main.eligible_label].groupby('market').size().to_dict(),
  'unscoreable_future_best_cases':det[det.oracle_availability_effect_bp>1e-9][['market','signal_date','best_market_ticker','asof_best_ticker','oracle_availability_effect_bp']].to_dict('records'),
  'usa_portfolio_controls_unchanged':True,'live_orders_placed':0,
  'comparability_warning':'Oracle log-label opportunity, not causal/live strategy NAV attribution; different OLC17/19 execution contracts.',
  'source_sha256':EXPECTED,
  'source_olc32_label_sha256':sha(dfraw)}
(DEST/'results'/'OLC35_AUDIT.json').write_text(json.dumps(audit,indent=2,default=str))
manifest={}
for p in sorted((DEST/'results').glob('*')):
    if p.name in ('OLC35_MANIFEST.json','OLC35_INDEPENDENT_VERIFICATION.json'): continue
    manifest[p.name]={'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
for p in sorted((DEST/'figures').glob('*')):
    manifest['figures/'+p.name]={'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
(DEST/'results'/'OLC35_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
print('\nPORTFOLIO FROZEN:\n'+port.to_string(index=False))
print('\nSUMMARY:\n'+summary.to_string(index=False))
print('\nANNUAL:\n'+byyear[['market','year','months','top5_hit_rate','top2_hit_rate']+[n+'_mean' for n in names]].to_string(index=False))
print('\nTOP OPP missed EU:');print(det[det.market=='EU'].nlargest(10,'opportunity_outside_top5_bp')[['signal_date','best_market_ticker','best_market_rank','top1','top2','opportunity_outside_top5_bp','oracle_total_bp']].to_string(index=False))
print('\nTOP OPP missed USA:');print(det[det.market=='USA'].nlargest(10,'opportunity_outside_top5_bp')[['signal_date','best_market_ticker','best_market_rank','top1','top2','opportunity_outside_top5_bp','oracle_total_bp']].to_string(index=False))
print('\nAUDIT:',json.dumps(audit,indent=2,default=str)[:10000]);
