"""Chronological shared annual selector; actual state carried across rule changes."""
from pathlib import Path
import inspect,importlib,sys,json
import numpy as np,pandas as pd
from common import atomic_json,atomic_bytes
from engine import run_portfolio
from replay import ROOT,BASELINE,metrics,PERIODS
from analysis import choose_config

def build_scheduled_engine():
    text=inspect.getsource(run_portfolio.py_func)
    text=text.replace('def run_portfolio(', 'def run_scheduled(')
    old='scores,vols,regime,k=2'
    assert text.count(old)==1;text=text.replace(old,'scores,vols,regime,day_config,event_selector,k=2')
    old='for d in range(days):';assert text.count(old)==1
    text=text.replace(old,'for d in range(days):\n        k=int(day_config[d,0]);weight_mode=int(day_config[d,1]);buffer=bool(day_config[d,2]);half=bool(day_config[d,3]);stops=bool(day_config[d,4])')
    text=text.replace('scores[e,j]','scores[event_selector[e],e,j]').replace('scores[e]','scores[event_selector[e],e]').replace('scores[e,chosen[0]]','scores[event_selector[e],e,chosen[0]]').replace('scores[e,chosen[1]]','scores[event_selector[e],e,chosen[1]]')
    p=Path(__file__).with_name('scheduled_engine.py');body='import numpy as np\nfrom numba import njit\nfrom engine import capped_inverse\n'+text
    if not p.exists() or p.read_text()!=body:p.write_text(body)
    mod=importlib.import_module('scheduled_engine')
    return mod.run_scheduled

def election(z,year):
    rows=[];end=f'{year-1}-12-31'
    for market in ['USA','EU']:
        d=pd.DatetimeIndex(z[market]['dates'])
        if len(set(d[d<=end].to_period('M')))<24:return BASELINE,None
        for j,config in enumerate(z[market]['configs']):
            stats=metrics(z[market]['nav'][:,j],d,'2019-01-01',end)
            rows.append({'market':market,'fee_bps':30,'config':config,'period':'HISTORY',**stats})
    selected,table=choose_config(pd.DataFrame(rows),period='HISTORY',fee=30)
    return selected,table

def main():
    o=ROOT/'results';cfg=json.loads((o/'CONFIGURATIONS.json').read_text());byid={x['id']:x for x in cfg}
    z={}
    for market in ['USA','EU']:
        with np.load(o/f'{market}_NAV_30BP.npz',allow_pickle=False) as archive:
            z[market]={key:archive[key] for key in ['dates','configs','nav']}
    choices={2019:BASELINE,2020:BASELINE,2021:BASELINE};aud=[]
    for year in range(2022,2027):
        choices[year],table=election(z,year)
        aud.append({'fit_year':year,'decision_cutoff_exclusive':f'{year}-01-01','maximum_used_outcome_date':f'{year-1}-12-31','selected_same_for_both':choices[year],'cost_for_election_bps':30})
        if table is not None:atomic_bytes(o/f'ROUTER_ELECTION_{year}.csv',table.to_csv().encode())
    # Prefix check: changes to returns after the cutoff cannot affect the election.
    synthetic={m:{k:v.copy() for k,v in z[m].items()} for m in ['USA','EU']}
    for market in synthetic:
        d=pd.DatetimeIndex(synthetic[market]['dates']);mask=d>=pd.Timestamp('2022-01-01')
        synthetic[market]['nav'][mask]*=np.linspace(2,5,mask.sum())[:,None]
    assert election(synthetic,2022)[0]==choices[2022]
    run=build_scheduled_engine();rows=[]
    for market in ['USA','EU']:
        inputs=np.load(o/f'{market}_REPLAY_INPUTS.npz',allow_pickle=False);dates=pd.DatetimeIndex(inputs['dates']);names=list(inputs['selectors'])
        active=np.empty((len(dates),5),dtype='int64')
        for i,date in enumerate(dates):
            c=byid[choices[date.year]];active[i]=[c['k'],{'EQ':0,'INV':1,'MARG':2}[c['weight']],int(c['buffer']),int(c['half']),int(c['stops'])]
        entryday=np.flatnonzero(inputs['event_day']>=0)
        which=np.array([names.index(byid[choices[dates[i].year]]['selector']) for i in entryday],dtype='int64')
        for fee in [.001,.003]:
            nav,l=run(inputs['O'],inputs['L'],inputs['C'],inputs['event_day'],inputs['scores'],inputs['vols'],inputs['regime'],active,which,fee=fee,slip=.001)
            np.savez_compressed(o/f'{market}_DUAL_SELECT_{int(fee*10000)}BP.npz',dates=dates.values,nav=nav,ledger=l,active_config=active,event_selector=which)
            for period,(a,b) in PERIODS.items():
                stats=metrics(nav,dates,a,b);mask=(dates>=a)&(dates<=b)
                rows.append({'market':market,'fee_bps':int(fee*10000),'config':'DUAL_SELECT','period':period,**stats,'turnover':float(l[mask,0].sum()*252/mask.sum()),'stops':int(l[mask,2].sum())})
    atomic_bytes(o/'ROUTER_SCORECARD.csv',pd.DataFrame(rows).to_csv(index=False).encode());atomic_json(o/'ROUTER_ELECTION_AUDIT.json',aud)
    s=json.loads((o/'VERIFIED_RESULTS_STATUS.json').read_text());s['router_status']='COMPLETE_WITH_SINGLE_ACCOUNT_STATE';s['router_paths']=4;s['router_election_prefix_test_pass']=True;atomic_json(o/'VERIFIED_RESULTS_STATUS.json',s)
    print('ROUTER_ELECTIONS',json.dumps(choices),flush=True)
    print(pd.DataFrame(rows).query("period in ['DEV_2019_2024','2025','2026_PARTIAL']").to_string(index=False),flush=True)
if __name__=='__main__':main()
