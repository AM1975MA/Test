"""Transparent descriptive comparisons; all financial paths remain separate."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd

PAIRS=[('CLUSTER_DUAL21','LIQ_DUAL21','primary_stage1_liquidity_matched'),
       ('CLUSTER_DUAL21','DUAL21','primary_stage1_previous'),
       ('LIQ_DUAL21','DUAL21','liquidity_only'),
       ('DEDUP_DUAL21','LIQ_DUAL21','adaptive_stage2_correlation'),
       ('DEDUP_DUAL21','CLUSTER_DUAL21','adaptive_stage2_individual_rank'),
       ('DEDUP_DUAL_TREND_OPP','DEDUP_DUAL21','adaptive_stage2_challenger_trend'),
       ('DEDUP_DUAL_TREND_OPP','DUAL21','adaptive_stage2_previous'),
       ('CLUSTER_DUAL_PEERS2','CLUSTER_DUAL21','stage1_peer_confirmation'),
       ('CLUSTER_PEERS2_RISK20','CLUSTER_DUAL_PEERS2','adaptive_stage2_risk'),
       ('CAPITAL_3H','HORIZON252','adaptive_stage3_capital_blend'),
       ('CAPITAL_3H_TILT','CAPITAL_3H','adaptive_stage3_allocation'),
       ('HORIZON63','HORIZON252','adaptive_stage3_recent_horizon'),
       ('HORIZON126','HORIZON252','adaptive_stage3_medium_horizon'),
       ('HORIZON63_TOP1','HORIZON63','adaptive_stage3_concentration63'),
       ('HORIZON126_TOP1','HORIZON126','adaptive_stage3_concentration126'),
       ('HORIZON252_TOP1','HORIZON252','adaptive_stage3_concentration252')]

def read(path):return pd.read_csv(path,float_precision='round_trip')

def analyze(root):
    root=Path(root).resolve();out=root/'analysis';out.mkdir(exist_ok=True)
    scores=[];annual=[];segments=[];paths={};monthly={}
    for stage,directory in enumerate(('results','results_stage2','results_stage3'),1):
        res=root/directory
        if not(res/'SCORECARD.csv').exists():continue
        frame=read(res/'SCORECARD.csv');frame['stage']=stage;frame['result_directory']=directory;scores.append(frame)
        for filename,store in [('ANNUAL_RETURNS.csv',annual),('DESCRIPTIVE_SEGMENTS.csv',segments)]:
            q=read(res/filename);q['stage']=stage;store.append(q)
        for row in frame.itertuples():
            d=read(res/row.path_id/'DAILY.csv.gz');dates=pd.to_datetime(d.date)
            series=pd.Series(d.nav_close.to_numpy(),index=dates)
            end=series.groupby(series.index.to_period('M')).last()
            logs=np.diff(np.log(np.r_[10000.,end.to_numpy()]))
            monthly[(row.arm,row.scenario)]=dict(dates=end.index.astype(str).tolist(),log_returns=logs)
            if row.scenario=='BASE':paths[row.arm]=d
    score=pd.concat(scores,ignore_index=True);yr=pd.concat(annual,ignore_index=True);seg=pd.concat(segments,ignore_index=True)
    # Current user objective applies to every stage; preserve legacy frozen fields.
    score['current_cagr_target_pass']=score.cagr>=.30
    score['current_drawdown_limit_active']=False
    score.to_csv(out/'ALL_SCORECARD.csv',index=False);yr.to_csv(out/'ALL_ANNUAL_RETURNS.csv',index=False);seg.to_csv(out/'ALL_SEGMENTS.csv',index=False)
    rng=np.random.default_rng(109);n=len(next(iter(monthly.values()))['log_returns']);block=6
    starts=rng.integers(0,n,size=(10000,int(np.ceil(n/block))))
    resample=((starts[:,:,None]+np.arange(block)[None,None,:])%n).reshape(10000,-1)[:,:n]
    comparisons=[];contributions=[]
    base=score[score.scenario=='BASE'].set_index('arm')
    for a,b,label in PAIRS:
        if a not in base.index or b not in base.index:continue
        x,y=monthly[(a,'BASE')],monthly[(b,'BASE')]
        assert x['dates']==y['dates']
        diff=x['log_returns']-y['log_returns']
        boot=diff[resample].mean(axis=1)*12
        lo,hi=np.quantile(boot,[.025,.975])
        comparisons.append(dict(candidate=a,control=b,comparison=label,months=n,
                    delta_cagr_pp=100*(base.loc[a,'cagr']-base.loc[b,'cagr']),
                    delta_sampled_dd_pp=100*(base.loc[a,'maxdd_sampled']-base.loc[b,'maxdd_sampled']),
                    relative_terminal_wealth=base.loc[a,'end_equity']/base.loc[b,'end_equity'],
                    annualized_log_relative_return=12*diff.mean(),
                    block_bootstrap_log95_low=lo,block_bootstrap_log95_high=hi,
                    block_months=6,replications=10000,seed=109,
                    positive_months=int((diff>0).sum()),negative_months=int((diff<0).sum())))
        years=np.array([int(t[:4]) for t in x['dates']])
        for year in sorted(set(years)):
            value=diff[years==year].sum()
            contributions.append(dict(candidate=a,control=b,year=int(year),relative_log_wealth_contribution=value,
                                      share_of_total_log_advantage=value/diff.sum() if abs(diff.sum())>1e-12 else np.nan))
    pd.DataFrame(comparisons).to_csv(out/'PAIRED_COMPARISONS.csv',index=False)
    pd.DataFrame(contributions).to_csv(out/'ANNUAL_RELATIVE_CONTRIBUTIONS.csv',index=False)
    pd.DataFrame([dict(arm=a,scenario=s,month=date,log_return=float(value),simple_return=float(np.expm1(value)))
                  for (a,s),q in monthly.items() for date,value in zip(q['dates'],q['log_returns'])]).to_csv(out/'MONTHLY_RETURNS.csv',index=False)
    # Pareto flags are descriptive, not ex-ante model selection or a deployment.
    frontier=[]
    for row in base.reset_index().itertuples():
        other=base[(base.cagr>=row.cagr)&(base.maxdd_sampled>=row.maxdd_sampled)&
                   ((base.cagr>row.cagr)|(base.maxdd_sampled>row.maxdd_sampled))]
        if other.empty:frontier.append(row.arm)
    summary=dict(paths=int(len(score)),configurations=int(score.arm.nunique()),stages=int(score.stage.nunique()),
                 legacy_numeric_passes=int(score.numeric_target_pass.sum()),
                 legacy_full_passes=int((score.numeric_target_pass&score.operational_pass).sum()),
                 current_objective='CAGR>=30%;drawdownandCalmarreportednotgates;protectiondeferredbyuser',
                 base_return_target_passes=int((base.cagr>=.30).sum()),
                 base_return_target_arms=base[base.cagr>=.30].index.tolist(),
                 cagr_at_least_30=int((score.cagr>=.30).sum()),drawdown_at_most_25=int((score.maxdd_sampled>=-.25).sum()),
                 calmar_at_least_one=int((score.calmar>=1.).sum()),
                 base_best_cagr=base.sort_values('cagr',ascending=False).head(1).reset_index().to_dict('records')[0],
                 base_pareto_frontier=frontier,
                 bootstrap_note='Circular moving-block6months,10000replications,seed109; descriptive, no multiplicity correction; full sample and adaptive choices already observed.',
                 all_results_exploratory=True)
    (out/'ANALYSIS_SUMMARY.json').write_text(json.dumps(summary,indent=2,default=str)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='base_best_cagr'},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root');a=ap.parse_args();analyze(a.root)
