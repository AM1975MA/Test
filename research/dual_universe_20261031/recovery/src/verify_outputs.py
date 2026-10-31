"""Independent all-path arithmetic and real-input prefix checks after simulation."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from engine import run_portfolio
from replay import ROOT,BASELINE
from common import atomic_json,atomic_bytes
O=ROOT/'results'
s=pd.read_csv(O/'SCORECARD.csv');cfg=json.loads((O/'CONFIGURATIONS.json').read_text());byid={x['id']:x for x in cfg}
chosen=json.loads((O/'RESEARCH_CHOICE.json').read_text())['chosen']
windows={'DEV_2019_2024':('2019-01-01','2024-12-31'),'DEV_2021_2024':('2021-01-01','2024-12-31'),'2019_2020':('2019-01-01','2020-12-31'),'2021_2022':('2021-01-01','2022-12-31'),'2023_2024':('2023-01-01','2024-12-31'),'2025':('2025-01-01','2025-12-31'),'2026_PARTIAL':('2026-01-01','2026-07-01'),'FULL':('2019-01-01','2026-07-01')}
checks=[];prefix=[];inputcheck=[];paths=0
for market in ['USA','EU']:
    for fee in [10,30]:
        with np.load(O/f'{market}_NAV_{fee}BP.npz',allow_pickle=False) as archive:
            dates=pd.DatetimeIndex(archive['dates']);nav=archive['nav'];ids=list(archive['configs']);ledger=archive['ledger']
        assert np.isfinite(nav).all() and (nav>0).all() and nav.shape[1]==840
        assert np.max(np.abs(nav-ledger[:,:,8]))==0
        paths+=nav.shape[1]
        for period,(first,last) in windows.items():
            ix=np.flatnonzero((dates>=first)&(dates<=last));n=len(ix)
            assert n>=2
            base=nav[ix[0]-1] if ix[0]>0 else np.ones(nav.shape[1])
            eq=nav[ix]/base
            growth=np.power(eq[-1],252./n)-1
            peak=np.maximum.accumulate(np.vstack([np.ones((1,len(ids))),eq]),axis=0)[1:]
            dd=np.min(eq/peak-1,axis=0)
            saved=s[(s.market==market)&(s.fee_bps==fee)&(s.period==period)].set_index('config').loc[ids]
            assert np.all(saved.days.to_numpy()==n)
            e1=float(np.max(abs(saved.cagr.to_numpy()-growth)));e2=float(np.max(abs(saved.maxdd.to_numpy()-dd)))
            assert max(e1,e2)<1e-12
            checks.append({'market':market,'fee_bps':fee,'period':period,'curves':len(ids),'max_CAGR_error':e1,'max_MaxDD_error':e2})
    with np.load(O/f'{market}_REPLAY_INPUTS.npz',allow_pickle=False) as z: inp={key:z[key] for key in z.files}
    names=list(inp['selectors']);dates=pd.DatetimeIndex(inp['dates']);event=np.flatnonzero(inp['event_day']>=0)
    eventids=inp['event_day'][event]
    assert np.array_equal(eventids,np.arange(len(event)))
    assert len(set(dates[event].to_period('M')))==len(event)
    for key in ['O','L','C']:
        a=inp[key];assert not np.isinf(a).any() and np.nanmin(a)>0
    for name in [BASELINE,chosen,'MULTI_H_K2_EQ_B0_R1_S1']:
        c=byid[name];si=names.index(c['selector'])
        score=inp['scores'][si].copy();vol=inp['vols'].copy();reg=inp['regime'].copy()
        args=dict(k=c['k'],weight_mode={'EQ':0,'INV':1,'MARG':2}[c['weight']],buffer=c['buffer'],half=c['half'],stops=c['stops'],fee=.001,slip=.001)
        original,l0=run_portfolio(inp['O'],inp['L'],inp['C'],inp['event_day'],score,vol,reg,**args)
        boundary=pd.Timestamp('2023-01-01');keep=dates<boundary;n=int(keep.sum());affected=dates>=boundary
        oo=inp['O'].copy();ll=inp['L'].copy();cc=inp['C'].copy()
        oo[affected]*=2;ll[affected]*=.1;cc[affected]*=3
        es=dates[event]>=boundary;score[es]=score[es,::-1];vol[es]*=4;reg[es]=~reg[es]
        changed,l1=run_portfolio(oo,ll,cc,inp['event_day'],score,vol,reg,**args)
        assert np.array_equal(original[:n],changed[:n]) and np.array_equal(l0[:n],l1[:n])
        with np.load(O/f'{market}_NAV_10BP.npz',allow_pickle=False) as ar: recorded=ar['nav'][:,list(ar['configs']).index(name)]
        np.testing.assert_array_equal(recorded,original)
        prefix.append({'market':market,'config':name,'future_boundary':str(boundary.date()),'past_sessions_unchanged':n,'exact_prefix_and_saved_path_match':True})
    inputcheck.append({'market':market,'calendar_first':str(dates[0].date()),'calendar_last':str(dates[-1].date()),'sessions':len(dates),'entry_events':len(event),'feature_scores_names':len(names),'executable_open_imputed':False})
checkpoint=[]
for f in sorted((ROOT/'checkpoints').glob('*/*/*.json')):
    m=json.loads(f.read_text());data=f.with_suffix('.csv.gz')
    assert hashlib.sha256(data.read_bytes()).hexdigest()==m['output_sha256']
    assert pd.Timestamp(m['max_label_exit'])<pd.Timestamp(m['cutoff'])
    checkpoint.append({'market':m['market'],'year':m['year'],'model':m['model'],'sha256':m['output_sha256'],'predictions':m['prediction_rows'],'maturity_pass':True})
assert len(checkpoint)==112
pd.DataFrame(checks).to_csv(O/'INDEPENDENT_NAV_CHECKS.csv',index=False)
pd.DataFrame(prefix).to_csv(O/'REAL_INPUT_PREFIX_CHECKS.csv',index=False)
pd.DataFrame(checkpoint).to_csv(O/'CHECKPOINT_INTEGRITY.csv',index=False)
summary={'paths_independently_reconciled':paths,'period_metric_checks':len(checks)*840*2,'max_cagr_error':max(x['max_CAGR_error'] for x in checks),'max_dd_error':max(x['max_MaxDD_error'] for x in checks),'real_input_prefix_checks':len(prefix),'checkpoint_digests_checked':len(checkpoint),'markets':inputcheck,'scope':'Numerical verification and prefix tests of declared simulator, NOT validation of real fills, adjustment factors, absence of survivor bias or prospective profitability.'}
atomic_json(O/'INDEPENDENT_VERIFICATION.json',summary)
print(json.dumps(summary,indent=2))
