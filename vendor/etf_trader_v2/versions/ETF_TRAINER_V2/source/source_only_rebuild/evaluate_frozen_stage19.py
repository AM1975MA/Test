#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent

# Prospective campaigns execute against the source snapshot copied into the new
# campaign directory. Preload the exact modules before importing Stage19 because
# the historical Stage19 research file contains a legacy /mnt/data sys.path hint.
_campaign_root=os.environ.get('ETF_TRAINER_V2_CAMPAIGN_ROOT')
if _campaign_root:
    _source_root=(Path(_campaign_root).resolve()/'src').resolve()
    if not _source_root.is_dir():
        raise FileNotFoundError(f'campaign source snapshot missing: {_source_root}')
    sys.path.insert(0,str(_source_root))
    import etf_trader.source_only.raw_io as _raw_io_preload
    import etf_trader.source_only.baskets as _baskets_preload
    import etf_trader.ma3.producer as _producer_preload
    import etf_trader.ma3.ddfirst as _ddfirst_preload
    import etf_trader.ma3.v6 as _v6_preload
    import etf_trader.ma3.highcagr24 as _highcagr24_preload
    for _module in (
        _raw_io_preload,_baskets_preload,_producer_preload,
        _ddfirst_preload,_v6_preload,_highcagr24_preload,
    ):
        _module_path=Path(_module.__file__).resolve()
        if _source_root not in _module_path.parents:
            raise RuntimeError(
                f'prospective evaluator imported {_module.__name__} outside '
                f'campaign source snapshot: {_module_path}'
            )

STAGE19=HERE.parent/'stage19_architecture.py'
spec=importlib.util.spec_from_file_location('stage19_frozen',STAGE19)
s19=importlib.util.module_from_spec(spec);spec.loader.exec_module(s19)

from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets
from etf_trader.ma3 import producer, ddfirst, v6, highcagr24

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',required=True,help='fresh raw per-ticker ETF CSV folder')
    ap.add_argument('--titanium',required=True,help='fresh TIT_R_SOURCE_ONLY.csv')
    ap.add_argument('--predictions',required=True,help='fresh ENSEMBLE_TAIL_OOS.csv')
    ap.add_argument('--baseline-path',required=True,help='fresh baseline PATH.npz from the same rebuild')
    ap.add_argument('--output',required=True)
    a=ap.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)

    mats,cats,_=load_ticker_csv_folder(a.data)
    tickers=list(map(str,mats['Open'].columns));ti={t:i for i,t in enumerate(tickers)}
    membership=build_canonical_baskets(pd.read_csv(Path(a.data)/'universe.csv'),tickers)
    BM,BOK=producer.basket_arrays(membership,tickers,n_baskets=500)

    tit=pd.read_csv(a.titanium,parse_dates=['signal_date','entry_date','exit_date'])
    cal=tit[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    pred=pd.read_csv(a.predictions,parse_dates=['signal_date'])
    score=s19.score_matrix(pred,cal,tickers)
    pm=s19.pred_matrices(pred,cal,tickers)

    Odf=mats['Open'].reindex(columns=tickers).ffill().bfill()
    Ldf=mats['Low'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    Cdf=mats['Close'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    end=pd.Timestamp(cal.exit_date.max());start=pd.Timestamp(cal.entry_date.min())
    Odf=Odf.loc[:end];Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index)
    st=int(Odf.index.get_loc(start));en=int(Odf.index.get_loc(end));ds=Odf.index[st:en+1]

    ddgross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float)
    g_risk=s19.risk_gross_transform(ddgross)
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k][st:en+1] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]
    base=producer.allocations_from_score(score,cal,ds,BM,BOK,continuous=True)
    s6=v6.build_v6_state(Cdf.loc[ds,tickers],base.d1,base.d2,base.weight1,ddgross)
    _,agree_models,_=s19.daily_monthly_state(score,pm,cal,ds,BM,BOK)

    ghb,wb=highcagr24.apply_highcagr24(ddgross,base.weight1,base.margin)
    Eb,Tb,_,_=v6.simulate_with_alt(base.d1,base.d2,wb,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],ghb,s6.alt_idx,True,.001)

    # Frozen candidate: current behavior at full gross; in existing risk-off states
    # only, hard top1 if margin >=3% and ET+XGB both rank top1 above top2.
    wc=s19.confidence_weights(base,g_risk,agree_models,np.zeros_like(agree_models),mode='current_plus_models_riskoff')
    G=np.tile(g_risk,(BM.shape[0],1))
    Ec,Tc,Xc,_=s19.simulate_arch(base.d1,base.d2,wc,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],G,g_risk,s6.alt_idx,True,.001)

    fresh=np.load(a.baseline_path,allow_pickle=True)
    parity={
        'baseline_equity_max_abs_diff':float(np.max(np.abs(Eb-fresh['equity']))),
        'baseline_turnover_max_abs_diff':float(np.max(np.abs(Tb-fresh['turnover']))),
        'direct_gross_schedule_max_abs_diff':float(np.max(np.abs(ghb-g_risk))),
    }
    if (
        parity['baseline_equity_max_abs_diff']>1e-10
        or parity['baseline_turnover_max_abs_diff']>1e-10
        or parity['direct_gross_schedule_max_abs_diff']>1e-12
    ):
        raise RuntimeError(parity)

    periods={
      'dev_2018_2020':(ds>=pd.Timestamp('2018-01-01'))&(ds<pd.Timestamp('2021-01-01')),
      'rep_2021_2022':(ds>=pd.Timestamp('2021-01-01'))&(ds<pd.Timestamp('2023-01-01')),
      'diag_2023_2026':ds>=pd.Timestamp('2023-01-01'),
      'hist_2017_2022':ds<pd.Timestamp('2023-01-01'),
      'full':np.ones(len(ds),bool),
    }
    result={'status':'FROZEN_STAGE19_SOURCE_ONLY_EVALUATION','candidate':'RISKOFF_HARD_MODELS','baseline_parity':parity,'metrics':{},'turnover_ann':{'baseline':float(Tb.mean()*252),'candidate':float(Tc.mean()*252)},'mean_effective_gross':{'baseline':float(np.asarray(fresh['exposure']).mean()),'candidate':float(Xc.mean())}}
    for name,mask in periods.items():
        b=s19.metrics(Eb,mask);c=s19.metrics(Ec,mask)
        result['metrics'][name]={'baseline':b,'candidate':c,'delta':{k:float(c[k]-b[k]) for k in b}}
    result['breadth']={}
    for name in ('dev_2018_2020','rep_2021_2022'):
        result['breadth'][name]=s19.basket_boot_delta(Ec,Eb,periods[name])
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    np.savez_compressed(
        out/'STAGE19_FROZEN_PATH.npz',
        dates=ds.values,
        baseline=Eb,
        candidate=Ec,
        turnover_baseline=Tb,
        turnover_candidate=Tc,
        effective_gross_candidate=Xc,
        direct_gross_baseline=ghb,
        direct_gross_candidate=g_risk,
    )
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
