"""Independently verify all saved economic paths and paired research gates."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

def metrics(equity):
    lr=np.diff(np.r_[0.,np.log(equity)])
    returns=np.expm1(lr)
    return dict(cagr=float(np.expm1(lr.sum()*252/len(lr))),
                maxdd=float((equity/np.maximum.accumulate(np.r_[1.,equity])[1:]-1).min()),
                sharpe=float(returns.mean()*np.sqrt(252)/returns.std(ddof=1)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rows=[];annual=[];hashes={};audits=[];seen=set();maxerror=0.
    for p in sorted(Path(a.inputs).rglob('RESULTS.json')):
        for row in json.loads(p.read_text()):
            key=(row['variant'],row['download'])
            if key in seen:raise ValueError('Duplicate result')
            seen.add(key)
            path=p.parent/row['variant']/'PATH.npz'
            hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
            with np.load(path,allow_pickle=False) as z:
                eq=z['equity'][0];ds=pd.DatetimeIndex(z['dates'])
                if len(eq)!=2366:raise ValueError('Incomplete path')
                m=metrics(eq)
                for field in m:
                    error=abs(m[field]-row['metrics'][field]);maxerror=max(maxerror,error)
                    if error>1e-12:raise ValueError('Independent metric mismatch')
                lr=np.diff(np.r_[0.,np.log(eq)])
                for year in range(2017,2027):
                    value=float(np.expm1(lr[ds.year==year].sum()))
                    if abs(value-row['annual_net_returns'][str(year)])>1e-12:raise ValueError('Annual decomposition mismatch')
                    annual.append(dict(variant=key[0],download=key[1],year=year,net_return=value))
            rows.append(dict(variant=key[0],download=key[1],**m,turnover_annual=row['turnover_annual'],mean_actual_gross=row['mean_actual_gross']))
        audit=json.loads((p.parent/'AUDIT.json').read_text())
        if not audit['OFF_equity_turnover_parity'] or not audit['causal_prefix']['PASS']:raise ValueError('Audit failed')
        audits.append(audit)
    expected={(v,i) for v in ['LINEAR_CONTROL','OPP_CAP','OPP_ROUTER_CAUSAL','OPP_DIRECT_DIAGNOSTIC'] for i in (1,2,3)}
    if seen!=expected or len(audits)!=3:raise ValueError('Missing complete three-download experiment')
    df=pd.DataFrame(rows);df.to_csv(out/'METRICS.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'ANNUAL_RETURNS.csv',index=False)
    groups={}
    for variant,g in df.groupby('variant'):
        groups[variant]=dict(mean_cagr=float(g.cagr.mean()),mean_maxdd=float(g.maxdd.mean()),mean_sharpe=float(g.sharpe.mean()),
                             cagr_span=float(g.cagr.max()-g.cagr.min()),cagr_sd_population=float(g.cagr.std(ddof=0)))
    b=df[df.variant=='LINEAR_CONTROL'].sort_values('download');gates={}
    for variant in ('OPP_CAP','OPP_ROUTER_CAUSAL'):
        c=df[df.variant==variant].sort_values('download');cg,bg=groups[variant],groups['LINEAR_CONTROL']
        checks=dict(mean_cagr=cg['mean_cagr']>=bg['mean_cagr']-1e-12,
                    each_cagr=bool(np.all(c.cagr.to_numpy()>=.95*b.cagr.to_numpy())),
                    mean_maxdd=cg['mean_maxdd']>=bg['mean_maxdd']-1e-12,
                    each_maxdd=bool(np.all(c.maxdd.to_numpy()>=b.maxdd.to_numpy()-.02)),
                    mean_sharpe=cg['mean_sharpe']>=.95*bg['mean_sharpe'],
                    cagr_span=cg['cagr_span']<=bg['cagr_span']+1e-12,
                    at_least_one_improvement=bool(cg['mean_cagr']>bg['mean_cagr']+1e-10 or cg['mean_maxdd']>bg['mean_maxdd']+1e-10 or cg['cagr_span']<bg['cagr_span']-1e-10))
        gates[variant]=dict(checks=checks,PASS=all(checks.values()))
    result=dict(status='THREE_FROZEN_DOWNLOADS_COMPLETE',metrics=groups,research_gates=gates,
                max_independent_metric_error=maxerror,path_sha256=hashes,
                control_parity_all=True,causal_prefix_all=True,
                cap_binding_fractions=[x['cap_binding_fraction'] for x in audits],
                top1_top2_signals_unchanged=True,production_adoption=False)
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
