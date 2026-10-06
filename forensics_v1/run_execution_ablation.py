#!/usr/bin/env python3
from __future__ import annotations
import argparse,importlib.util,json,os,shutil
from pathlib import Path
import numpy as np
import pandas as pd


def load_module(path):
    sp=importlib.util.spec_from_file_location('exec_forensic_compare',path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-root',required=True);ap.add_argument('--compare-script',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    rr=Path(a.raw_root).resolve(); ref=rr/'_repeat2'; out=Path(a.out).resolve();cmp=Path(a.compare_script).resolve()
    os.environ['FROZEN_149_ROOT']=str(rr);os.environ['FROZEN_HOLDOUT70_ROOT']=str(rr)
    mod=load_module(cmp);mod.FROZEN149=ref;mod.FROZEN70=ref;mod.OUT=out/'ref_work'
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True)
    state=mod.build_source_only_state('original149',ref);native2=mod.replay_full_universe(state)
    z=np.load(state['base']/'FULL_UNIVERSE_PATH.npz'); ds=pd.DatetimeIndex(z['dates']);d1=z['d1'];d2=z['d2'];w=z['weight1'];alt=z['alt_idx'];tickers=state['candidate_tickers']
    def inputs(raw):
        cand,_,_=mod.load_ticker_csv_folder(raw); em,et=mod.append_execution_refs(cand,tickers);ti={t:i for i,t in enumerate(et)}
        Odf=em['Open'].reindex(columns=et).ffill().bfill().reindex(ds);Ldf=em['Low'].reindex(columns=et).ffill().bfill().reindex(ds);Cdf=em['Close'].reindex(columns=et).ffill().bfill().reindex(ds)
        gross=np.asarray(mod.ddfirst.sync_c95_m75_gross(Cdf[tickers]),float);g=mod.stage19.risk_gross_transform(gross)
        ex=mod.ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
        return ex,g,ti
    ex2,g2,ti2=inputs(ref)
    results={}
    for r in [1,2,3]:
        ex,gd,ti=inputs(rr/f'_repeat{r}')
        if ti!=ti2: raise RuntimeError('ticker order mismatch')
        O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]
        row={}
        for mode,g in [('frozen_repeat2_risk',g2),('destination_risk',gd)]:
            G=np.tile(g,(d1.shape[0],1))
            E,T,_,_=mod.stage19.simulate_arch(d1,d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],G,g,alt,True,.001)
            met=mod.stage19.metrics(E,np.ones(len(ds),bool))
            row[mode]={'cagr':float(met['cagr']),'maxdd':float(met['maxdd']),'sharpe':float(met['sharpe']),'terminal_equity':float(E[0,-1]),'turnover_ann':float(T.mean()*252)}
        results[str(r)]=row
    spans={}
    for mode in ['frozen_repeat2_risk','destination_risk']:
        vals=[results[str(r)][mode]['cagr'] for r in [1,2,3]];spans[mode]={'cagr_span_pp':100*(max(vals)-min(vals)),'cagrs':vals}
    native=[0.29753447746605766,0.30843704925646037,0.346770790748319]
    res={'status':'EXECUTION_ABLATION_COMPLETE','reference_decisions':'repeat2 exact canonical d1/d2/weight1/alt_idx','native_cagr_span_pp':100*(max(native)-min(native)),'cross_execution':results,'spans':spans,'repeat2_native_parity':{'expected':native2['v2_full_universe']['cagr'],'cross_exec':results['2']['destination_risk']['cagr'],'abs_diff':abs(native2['v2_full_universe']['cagr']-results['2']['destination_risk']['cagr'])}}
    (out/'RESULT.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2),flush=True)
if __name__=='__main__':main()
