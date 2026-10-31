"""Predeclared research selection and conditional joint uncertainty, not future alpha."""
from pathlib import Path
import io,json,itertools,os
import numpy as np,pandas as pd
from common import atomic_bytes,atomic_json
from replay import ROOT,BASELINE,metrics

def posterior_draws(blocks,kappa=.5,scale=.20,draws=20000,seed=20261031):
    x=np.asarray(blocks,float)
    if x.ndim!=2 or x.shape[1]!=2 or len(x)<3 or not np.isfinite(x).all():raise ValueError('At least 3 complete paired two-market blocks required')
    n,d=x.shape;mean=x.mean(0);scatter=(x-mean).T@(x-mean)
    kn=kappa+n;nu=4+n;df=nu-d+1
    mu=n*mean/kn;psi=scale**2*np.eye(2)+scatter+kappa*n/kn*np.outer(mean,mean)
    mat=psi/(kn*df);rng=np.random.default_rng(seed)
    z=rng.standard_normal((draws,2))@np.linalg.cholesky(mat).T
    z*=np.sqrt(df/rng.chisquare(df,draws))[:,None]
    return mu+z

def block_contrasts(monthly,block=6):
    a=monthly.to_numpy(float);num=len(a)//block
    if num<3:raise ValueError('Insufficient blocks')
    return a[:num*block].reshape(num,block,2).sum(1)*(12./block)

def choose_config(scorecard,period='DEV_2019_2024',fee=30):
    f=scorecard[(scorecard.period==period)&(scorecard.fee_bps==fee)]
    if len(f)!=1680:raise ValueError('Both complete 840-policy universes required')
    p=f.pivot(index='config',columns='market',values=['ann_log','maxdd','cagr'])
    b=p.loc[BASELINE]
    d=p['ann_log'].sub(b['ann_log'],axis=1)
    allowed=(p['maxdd'].ge(b['maxdd']-1e-12,axis=1)).all(axis=1)
    score=d.min(axis=1)
    table=pd.DataFrame({'worst_market_improvement_log_pp':score*100,'USA_delta_log_pp':d.USA*100,'EU_delta_log_pp':d.EU*100,'drawdown_guard_both':allowed})
    table['controls']=table.index.to_series().map(lambda s:sum(int(t[-1]) for t in s.split('_') if t.startswith(('B','R','S')) and t[-1:].isdigit())+int('_INV_' in s)+int('_MARG_' in s))
    table=table.sort_values(['drawdown_guard_both','worst_market_improvement_log_pp','controls'],ascending=[False,False,True],kind='stable')
    eligible=table[table.drawdown_guard_both]
    best=eligible.index[0] if len(eligible) and eligible.iloc[0].worst_market_improvement_log_pp>1e-10 else BASELINE
    return best,table

def monthly_returns(z,config):
    ids=list(z['configs']);nav=z['nav'][:,ids.index(config)];dates=pd.DatetimeIndex(z['dates'])
    lr=np.diff(np.log(np.r_[1.,nav]));return pd.Series(lr,index=dates).groupby(dates.to_period('M')).sum()

def probability_record(x):
    return {'p_US_mean_positive':float((x[:,0]>0).mean()),'p_EU_mean_positive':float((x[:,1]>0).mean()),'p_both_mean_positive':float((x>0).all(1).mean()),'p_both_above_0_5pp':float((x>.005).all(1).mean()),'p_any_below_minus2pp':float((x<-.02).any(1).mean()),'USA_mean_log_pp':float(x[:,0].mean()*100),'EU_mean_log_pp':float(x[:,1].mean()*100),'USA_q025_pp':float(np.quantile(x[:,0],.025)*100),'USA_q975_pp':float(np.quantile(x[:,0],.975)*100),'EU_q025_pp':float(np.quantile(x[:,1],.025)*100),'EU_q975_pp':float(np.quantile(x[:,1],.975)*100)}

def main():
    o=ROOT/'results';s=pd.read_csv(o/'SCORECARD.csv');assert len(s)==3360*8
    chosen,table=choose_config(s)
    atomic_bytes(o/'DEVELOPMENT_RANKING.csv',table.to_csv().encode())
    atomic_json(o/'RESEARCH_CHOICE.json',{'chosen':chosen,'baseline':BASELINE,'decision_data_max':'2024-12-31','cost_stress_bps':30,'criterion':'Maximize worse-market incremental annual log-growth subject to non-worse observed MaxDD in each market','status':'RETROSPECTIVELY_SELECTED_RESEARCH_CANDIDATE_NOT_PRODUCTION','note':'No interval-zero veto; examined both universes; selection across 840 candidates on reused history can be optimistic.'})
    configs=json.loads((o/'CONFIGURATIONS.json').read_text());cf={c['id']:c for c in configs}
    # All declared elementary changes compared in both universes under all contexts.
    pairs=set()
    for c in configs:
        id=c['id']
        ctrl=f"BASE_H_K{c['k']}_{c['weight']}_B{int(c['buffer'])}_R{int(c['half'])}_S{int(c['stops'])}"
        if id!=ctrl:pairs.add(('selector',ctrl,id))
        for field,letter in [('buffer','B'),('half','R'),('stops','S')]:
            if c[field]:pairs.add((field,id.replace(f'_{letter}1',f'_{letter}0'),id))
        if c['weight']!='EQ':pairs.add(('weights',id.replace('_'+c['weight']+'_','_EQ_'),id))
        if c['k']==5:pairs.add(('positions',id.replace('_K5_','_K2_'),id))
    comparisons=[]
    for (market,fee,period),g in s.groupby(['market','fee_bps','period']):
        a=g.set_index('config')
        for kind,b,c in pairs:
            if b not in a.index:continue
            comparisons.append({'market':market,'fee_bps':fee,'period':period,'change':kind,'baseline':b,'candidate':c,'delta_ann_log_pp':100*(a.loc[c,'ann_log']-a.loc[b,'ann_log']),'delta_cagr_pp':100*(a.loc[c,'cagr']-a.loc[b,'cagr']),'dd_improvement_pp':100*(a.loc[c,'maxdd']-a.loc[b,'maxdd'])})
    atomic_bytes(o/'ALL_PAIRED_INCREMENT_COMPARISONS.csv',pd.DataFrame(comparisons).to_csv(index=False).encode())
    # Conditional probabilities for a fixed short list plus selected candidate.
    candidates={chosen,'RETURN_H_K2_EQ_B0_R1_S1','BASE_H_K5_EQ_B0_R1_S1','MOM252_K5_EQ_B0_R1_S1','CONSENSUS_H_K2_EQ_B0_R1_S1','COMMITTEE_K5_EQ_B0_R1_S1'}
    post=[]
    for fee in [10,30]:
        z={m:np.load(o/f'{m}_NAV_{fee}BP.npz',allow_pickle=False) for m in ['USA','EU']}
        for candidate in sorted(candidates):
            if candidate==BASELINE:continue
            month=pd.concat({m:monthly_returns(z[m],candidate)-monthly_returns(z[m],BASELINE) for m in ['USA','EU']},axis=1).dropna().loc[:'2024-12']
            for block in [6,3]:
                x=block_contrasts(month,block)
                variants=[(.5,.2)]
                if candidate==chosen:variants=[(kap,sc) for kap in [.1,.5,2.] for sc in [.1,.2,.4]]
                for kap,sc in variants:
                    draws=posterior_draws(x,kappa=kap,scale=sc)
                    post.append({'config':candidate,'fee_bps':fee,'block_months':block,'paired_blocks':len(x),'retained_months':len(x)*block,'omitted_trailing_months':len(month)-len(x)*block,'prior_kappa':kap,'prior_scale':sc,**probability_record(draws),'qualification':'Conditional on NIW model, block independence and stationarity; historical selection not corrected; NOT predictive future win probability'})
    atomic_bytes(o/'POSTERIOR_CONDITIONAL_DIAGNOSTICS.csv',pd.DataFrame(post).to_csv(index=False).encode())
    # Audit outcome counts and chronology, but do not overstate these as data certification.
    events=pd.read_csv(o/'EVENT_AUDIT.csv',parse_dates=['signal_date','entry_date']);assert (events.entry_date>events.signal_date).all()
    assert set(events.market)=={'USA','EU'}
    metas=[]
    for f in (ROOT/'checkpoints').glob('*/*/*.json'):
        x=json.loads(f.read_text());assert pd.Timestamp(x['max_label_exit'])<pd.Timestamp(x['cutoff']);metas.append(x)
    assert len(metas)==112
    for market in ['USA','EU']:
        for year in range(2019,2027):
            a=[x['training_key_sha256'] for x in metas if x['market']==market and x['year']==year and x['model'] in ('BASE_MATURE63','MULTI_453520','CONSENSUS_MULTI')]
            assert len(set(a))==1
    atomic_json(o/'VERIFIED_RESULTS_STATUS.json',{'status':'ECONOMIC_COMPARISONS_COMPUTED_TECHNICAL_CHECKS_PASSED','markets':['USA149','EU165'],'model_year_checkpoints':112,'new_xgb_fits':288,'new_ridge_fits':16,'paths':3360,'increment_comparison_rows':len(comparisons),'chosen_research_config':chosen,'event_chronology_pass':True,'label_maturity_pass':True,'matched_multi_sample_pass':True,'prefix_checks':'Passed compact feature-prefix and synthetic execution-prefix checks; not a complete proof of all raw data causal validity','limitations':['Recovered implementation, not original lost working-code parity','Historical universes selected in 2026; survivorship risk','Native Hybrid scores reused from original fitted archives, not refitted in this campaign','Price adjustments, spread, distributions and real fill availability not independently certified','Many tests and reused history; post-selection optimism','No live deployment'], 'router_status':'NOT_YET_EVALUATED'})
    print('RESEARCH_CHOICE',chosen,flush=True)
    print(s[(s.config.isin([chosen,BASELINE]))&(s.period.isin(['DEV_2019_2024','2025','2026_PARTIAL']))][['market','fee_bps','config','period','cagr','maxdd']].to_string(index=False),flush=True)
if __name__=='__main__':main()
