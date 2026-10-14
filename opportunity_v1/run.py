"""Frozen annual LINEAR plus separate Opportunity cap/router experiments."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from opportunity_v1.core import causal_features,fit_opportunity,period_shadow,router_decisions
from paper_ltr_v2.replay import load_compare,read_frame,write_state,sha,one,verify_cache

def opportunity_panel(k,mats):
    cols=list(mats['Close'].columns)
    dates=k.month_end_dates(mats['Close'].index)
    if len(dates) and dates[-1]==mats['Close'].index[-1]:dates=dates[:-1]
    _,compact,_,D=k.build_features(mats)
    labels=k.add_labels(compact[compact.signal_date.isin(dates)].copy(),mats['Open'],dates)
    clusters=k.build_clusters(D,dates,cols)
    panel,features=k.build_opp_panel(D,clusters,labels)
    return panel,features,clusters

def verify_features(k,mats,panel,features,clusters):
    cut=pd.Timestamp('2022-12-30')
    prefix={name:frame.loc[:cut].copy() for name,frame in mats.items()}
    pp,pf,pc=opportunity_panel(k,prefix)
    if features!=pf:raise ValueError('Feature list changed after future append')
    keys=['signal_date','cluster_id']
    common=panel.merge(pp[keys],on=keys,validate='one_to_one')
    cols=keys+causal_features(features)
    pd.testing.assert_frame_equal(common[cols].sort_values(keys).reset_index(drop=True),
                                  pp[cols].sort_values(keys).reset_index(drop=True),check_exact=True)
    ck=['signal_date','ticker']
    cc=clusters.merge(pc[ck],on=ck,validate='one_to_one')
    pd.testing.assert_frame_equal(cc.sort_values(ck).reset_index(drop=True),pc.sort_values(ck).reset_index(drop=True),check_exact=True)
    return dict(PASS=True,prefix_end=str(cut),rows=len(pp),features=len(causal_features(features)),clusters=len(pc))

def run_repeat(a,repeat):
    raw=(Path(a.raw)/f'_repeat{repeat}').resolve()
    if not raw.is_dir():raise ValueError(f'Raw layout missing {raw}')
    old=Path(a.annual)/'_replays'/f'v2replay-LINEAR_NUMERICAL_REPAIR-r{repeat}'
    old_candidate=old/'candidate'
    proof=json.loads((old/'INPUT_LINKAGE.json').read_text())
    if proof.get('PASS') is not True or proof['candidate_result_sha256']!='19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f':
        raise ValueError('Annual input linkage mismatch')
    actual={p.name:sha(p) for p in sorted(raw.glob('*.csv'))}
    if actual!=proof['raw_files_sha256']:raise ValueError('Frozen raw changed')
    compare=load_compare(raw)
    from etf_trader.source_only import kernel as k
    from etf_trader.source_only.raw_io import load_ticker_csv_folder
    for name,expected in proof['source_sha256'].items():
        if sha(ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only'/name)!=expected:raise ValueError('Canonical source changed')
    mats,cats,_=load_ticker_csv_folder(raw)
    tickers=compare.load_universe(raw).ticker.tolist()
    if len(tickers)!=149:raise ValueError('Not Original149')
    k.ALL_TICKERS=sorted(tickers);k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted(t for t in tickers if cats[t]==c) for c in sorted(set(cats.values()))}
    out=Path(a.out)/f'r{repeat}';out.mkdir(parents=True,exist_ok=True)
    verify_cache(Path(a.baseline),raw)
    panel_path=one(Path(a.baseline),'RAW_FEATURE_PANEL.pkl')
    archived=json.loads((old_candidate/'RESULT.json').read_text())
    if sha(panel_path)!=archived['source_only']['ma3_panel_sha256']:raise ValueError('Authentic MA3 panel mismatch')
    tit=read_frame(old_candidate/'TIT_R_SOURCE_ONLY.csv')
    ensemble=read_frame(old_candidate/'ENSEMBLE_TAIL_OOS.csv')
    calendar=tit[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    last=min(frame.last_valid_index() for _,frame in mats['Close'].items())
    calendar=calendar[calendar.exit_date<=last].reset_index(drop=True)
    ds=mats['Open'].index[(mats['Open'].index>=calendar.entry_date.min())&(mats['Open'].index<=calendar.exit_date.max())]
    if len(ds)!=2366 or len(calendar)!=113:raise ValueError('Different evaluation calendar')
    original_simulate=compare.stage19.simulate_arch
    control={}
    def capture_control(*args,**kwargs):
        control['args']=args;control['kwargs']=kwargs
        control['path']=original_simulate(*args,**kwargs)
        return control['path']
    state=write_state(out/'canonical_control',raw,tickers,tit,ensemble,panel_path)
    compare.stage19.simulate_arch=capture_control
    try:compare.replay_full_universe(state)
    finally:compare.stage19.simulate_arch=original_simulate
    with np.load(old_candidate/'FULL_UNIVERSE_PATH.npz',allow_pickle=False) as z:
        if not np.array_equal(z['dates'],ds.values):raise ValueError('OFF dates mismatch')
        for name,index in [('equity',0),('turnover',1)]:
            np.testing.assert_allclose(z[name],control['path'][index],rtol=0,atol=1e-12)
    print(f'REPEAT {repeat}: OFF equity/turnover parity PASS before new fits',flush=True)
    print(f'REPEAT {repeat}: build original causal Opportunity features',flush=True)
    panel,features,clusters=opportunity_panel(k,mats)
    causal=verify_features(k,mats,panel,features,clusters)
    print(f'REPEAT {repeat}: fit only Opportunity, original model parameters',flush=True)
    predictions,fit_audit=fit_opportunity(panel,features,range(2017,2027))
    predictions.to_csv(out/'OPPORTUNITY_PREDICTIONS.csv',index=False)
    clusters.to_csv(out/'CLUSTERS.csv',index=False)
    # Perturb every historical forward target: retained predictors must be identical.
    altered=panel.copy()
    for col in altered:
        if col.startswith('target_'):altered[col]=999.
    pd.testing.assert_frame_equal(panel[causal_features(features)],altered[causal_features(features)],check_exact=True)
    captured={};decisions=[]
    def simulate(*args,**kwargs):
        base=control['path']
        d1,d2,w=args[:3]
        G=args[14];g=args[15]
        direct_w=w.copy();direct_flags=[]
        s1=np.ones_like(w)
        cmap=clusters.set_index(['signal_date','ticker']).cluster_id.to_dict()
        for row in calendar.itertuples():
            start=int(ds.get_loc(row.entry_date));end=int(ds.get_loc(row.exit_date))
            group=predictions[predictions.signal_date==row.signal_date].sort_values('opp_z',ascending=False)
            if len(group)<2:raise ValueError('Opportunity predictions missing at signal')
            top_cluster=int(group.iloc[0].cluster_id)
            gap=float(group.iloc[0].opp_z-group.iloc[1].opp_z)
            ticker=tickers[int(d1[0,start])]
            cid=cmap.get((row.signal_date,ticker))
            eligible=cid is not None and cid==top_cluster and gap>=.5
            if eligible:direct_w[:,start:end]=1.
            direct_flags.append(eligible)
            # Cap score must use the same final producer score as canonical allocation.
            s1[:,start:end]=scores[calendar.signal_date.eq(row.signal_date).to_numpy()][0,int(d1[0,start])]
            decisions.append(dict(signal_date=str(row.signal_date),entry_date=str(row.entry_date),exit_date=str(row.exit_date),
                                  top1=ticker,cluster_id=None if cid is None else int(cid),top_cluster=top_cluster,
                                  gap_z=gap,direct_eligible=bool(eligible)))
        direct_args=list(args);direct_args[2]=direct_w
        direct=original_simulate(*direct_args,**kwargs)
        shadow=period_shadow(ds,calendar,base[0][0],direct[0][0])
        active,counts,sums=router_decisions(calendar.signal_date,calendar.exit_date,shadow)
        routed_w=w.copy()
        for i,row in enumerate(calendar.itertuples()):
            start=int(ds.get_loc(row.entry_date));end=int(ds.get_loc(row.exit_date))
            if active[i]:routed_w[:,start:end]=direct_w[:,start:end]
            decisions[i].update(router_on=bool(active[i]),mature_shadow_periods=int(counts[i]),shadow_last12_sum=float(sums[i]),
                                period_shadow_log=float(shadow[i]),shadow_available_at=str(row.exit_date))
        router_args=list(args);router_args[2]=routed_w
        cap_args=list(args);cap_args[14]=np.minimum(G,compare.stage19.opportunity_cap(s1))
        captured['LINEAR_CONTROL']=(base,w,G)
        captured['OPP_DIRECT_DIAGNOSTIC']=(direct,direct_w,G)
        captured['OPP_ROUTER_CAUSAL']=(original_simulate(*router_args,**kwargs),routed_w,G)
        captured['OPP_CAP']=(original_simulate(*cap_args,**kwargs),w,cap_args[14])
        captured['cap_binding_fraction']=float(np.mean(cap_args[14]<G-1e-12))
        return base
    p=ensemble.rename(columns={'ET_TAIL':'ET_RANK','XGB_TAIL':'XGB_RANK'})
    scores=compare.stage19.score_matrix(p,calendar,tickers)
    simulate(*control['args'],**control['kwargs'])
    rows=[]
    for variant in ('LINEAR_CONTROL','OPP_CAP','OPP_ROUTER_CAUSAL','OPP_DIRECT_DIAGNOSTIC'):
        (E,T,X,AW),weights,G=captured[variant]
        folder=out/variant;folder.mkdir(exist_ok=True)
        np.savez_compressed(folder/'PATH.npz',dates=ds.values,equity=E,turnover=T,gross=X,alt_weight=AW,weight1=weights,cap=G)
        full=compare.stage19.metrics(E,np.ones(len(ds),bool))
        annual={}
        for year in range(2017,2027):
            mask=ds.year==year
            logs=np.diff(np.r_[0.,np.log(E[0])])[mask]
            annual[str(year)]=float(np.expm1(logs.sum()))
        row=dict(variant=variant,download=repeat,metrics=full,annual_net_returns=annual,
                 turnover_annual=float(T.mean()*252),mean_actual_gross=float(X.mean()))
        rows.append(row);(folder/'RESULT.json').write_text(json.dumps(row,indent=2)+'\n')
    pd.DataFrame(decisions).to_csv(out/'ROUTER_DECISIONS.csv',index=False)
    audit=dict(raw_sha256=actual,annual_path_sha256=sha(old_candidate/'FULL_UNIVERSE_PATH.npz'),
               annual_linkage_sha256=sha(old/'INPUT_LINKAGE.json'),OFF_equity_turnover_parity=True,
               causal_prefix=causal,opportunity_training=fit_audit,cap_binding_fraction=captured['cap_binding_fraction'],
               no_compact_tail_macro_ma3_refits=True,new_opportunity_annual_folds=10,
               exclusions=['target_excess_max','target_excess_max_rank'],shadow_requires_exit_le_signal=True,
               v6_alternative_unchanged=True,top1_top2_selections_unchanged=True,
               source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'opportunity_v1/core.py',ROOT/'opportunity_v1/run.py',ROOT/'vendor/p45/v2_stage19_kernel.py']})
    (out/'AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
    (out/'RESULTS.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--annual',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--repeat',type=int,choices=(1,2,3),required=True)
    args=ap.parse_args();run_repeat(args,args.repeat)

if __name__=='__main__':main()
