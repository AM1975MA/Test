#!/usr/bin/env python3
"""OLC71D: native EU Return XGBoost grouped feature perturbation.

Exploratory only. The 46 groups are jointly permuted RAW/PCT/DEV per date.
No training, no change to OLC19 risk, no new CAGR, no trade recommendation.
Requires the original user Library source archives in OLC71_SOURCE_DIR.
"""
from __future__ import annotations
import gzip, hashlib, io, json, os, tempfile, warnings
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pandas as pd
import xgboost as xgb

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
INPUT=Path(os.environ.get('OLC71_SOURCE_DIR','/mnt/data/etf_source'))
SEEDS=(71101,71102)
YEARS=range(2021,2026)


def load_booster(z,year,seed):
    with tempfile.NamedTemporaryFile(suffix='.ubj',delete=False) as f:
        f.write(z.read(f'fits/EU/R_RSI_DOMAIN/{year}/RETURN_{seed}.ubj'))
        filename=f.name
    try:
        return xgb.Booster(model_file=filename)
    finally:
        os.unlink(filename)


def tie_rank(x,dates):
    return pd.DataFrame({'date':dates,'value':x}).groupby('date').value.rank(pct=True).to_numpy()


def selected_return(scores, tickers, ret21, ret42, groups):
    out={}
    for signal_date,ix in groups.items():
        idx=np.array(ix,dtype=int)
        idx=idx[np.isfinite(scores[idx])]
        # Predicted score is computed on ALL eligible rows, independent of known future return.
        ord_=idx[np.lexsort((tickers[idx],-scores[idx]))[:2]]
        a=ret21[ord_];b=ret42[ord_]
        out[signal_date]=(tuple(tickers[ord_]), float(np.mean(a)) if np.all(np.isfinite(a)) else np.nan,
                          float(np.mean(b)) if np.all(np.isfinite(b)) else np.nan)
    return out


def main():
    zz=ZipFile(INPUT/'OLC08F_01_FeaturePack_20261101.zip')
    zm=ZipFile(INPUT/'OLC08_03_RSI_Confronto_Verificato_20261101.zip')
    z19=ZipFile(INPUT/'OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
    cp=pd.read_pickle(io.BytesIO(zz.read('inputs/EU_RSI_COMPACT.pkl')))
    pfx='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'
    orig=pd.read_csv(io.BytesIO(z19.read(pfx+'EU_MEAN3_SCORES.csv.gz')),compression='gzip',parse_dates=['signal_date'],float_precision='round_trip')
    q=cp.loc[cp.eligible & cp.signal_date.dt.year.between(2021,2025)].merge(orig[['signal_date','ticker','RETURN','ORIGINAL_SMOOTH','ORIGINAL_FUSION']],on=['signal_date','ticker'],how='inner',validate='one_to_one')
    q=q.sort_values(['signal_date','ticker']).reset_index(drop=True)
    assert q[['signal_date','ticker']].duplicated().sum()==0
    out=[];audit=[]
    for yr in YEARS:
        df=q[q.signal_date.dt.year==yr].copy().reset_index(drop=True)
        f=json.loads(zm.read(f'fits/EU/R_RSI_DOMAIN/{yr}/audit.json'))['return_features']
        assert len(f)==125
        # Exact 46 economic families: one raw, optional pct and optional dev.
        families={}
        for k,n in enumerate(f):
            root=n.removesuffix('_pct').removesuffix('_dev')
            families.setdefault(root,[]).append(k)
        assert len(families)==46
        cols=df[f].replace([np.inf,-np.inf],np.nan).to_numpy(dtype=np.float32)
        dates=df.signal_date.dt.strftime('%Y-%m-%d').to_numpy(dtype=str)
        tickers=df.ticker.astype(str).to_numpy()
        r21=df.fwd_ret_21.to_numpy(dtype=float);r42=df.fwd_ret_42.to_numpy(dtype=float)
        bydate={date:np.flatnonzero(dates==date) for date in np.unique(dates)}
        boosters=[load_booster(zm,yr,s) for s in (101,202,303)]
        dmat=xgb.DMatrix(cols,nthread=1)
        meanpred=np.mean([b.predict(dmat) for b in boosters],axis=0)
        returnrank=tie_rank(meanpred,dates)
        err=np.max(np.abs(returnrank-df.RETURN.to_numpy()))
        assert err<1e-13,(yr,'native model Return rank parity',err)
        rebuilt=.475*returnrank+.525*df.ORIGINAL_SMOOTH.to_numpy(float)
        assert np.nanmax(np.abs(rebuilt-df.ORIGINAL_FUSION.to_numpy(float)))<1e-12
        baseline=selected_return(rebuilt,tickers,r21,r42,bydate)
        # Original standalone original rank parity against the actual archived R_RSI_DOMAIN predictions.
        cp_pred=pd.read_csv(io.BytesIO(gzip.decompress(zm.read(f'fits/EU/R_RSI_DOMAIN/{yr}/predictions.csv.gz'))),parse_dates=['signal_date'])
        check=pd.DataFrame({'signal_date':df.signal_date,'ticker':df.ticker,'rebuilt':meanpred}).merge(cp_pred[['signal_date','ticker','RETURN_RAW']],on=['signal_date','ticker'],validate='one_to_one')
        rawerr=float(np.max(abs(check.rebuilt-check.RETURN_RAW)))
        assert rawerr<1e-6,(yr,rawerr)
        audit.append({'year':yr,'n_months':len(bydate),'n_tickers':len(df),'exact_original_return_rank_parity':bool(err<1e-13),
                      'max_raw_score_diff':rawerr,'max_return_rank_diff':float(err),'original_fusion_parity':True})
        for family,ixcols in sorted(families.items()):
            for seed in SEEDS:
                altered=cols.copy()
                for dt,ix in bydate.items():
                    if len(ix)<2: continue
                    h=hashlib.sha256(f'{seed}|{yr}|{dt}|{family}'.encode()).hexdigest()
                    rng=np.random.default_rng(int(h[:16],16))
                    altered[np.ix_(ix,ixcols)]=cols[np.ix_(ix[rng.permutation(len(ix))],ixcols)]
                dm=xgb.DMatrix(altered,nthread=1)
                changed=np.mean([b.predict(dm) for b in boosters],axis=0)
                rank=tie_rank(changed,dates)
                fused=.475*rank+.525*df.ORIGINAL_SMOOTH.to_numpy(float)
                result=selected_return(fused,tickers,r21,r42,bydate)
                for dt in bydate:
                    origsel,old21,old42=baseline[dt]
                    mutsel,new21,new42=result[dt]
                    valid=np.isfinite(old21) and np.isfinite(new21) and np.isfinite(old42) and np.isfinite(new42)
                    out.append({'market':'EU','year':yr,'month':dt[:7],'family':family,'n_group_columns':len(ixcols),
                                'rep_seed':seed,'original_top2':';'.join(origsel),'permuted_top2':';'.join(mutsel),
                                'top2_changed':int(origsel!=mutsel),
                                'original_payoff21':old21,'perturbed_payoff21':new21,
                                'original_payoff42':old42,'perturbed_payoff42':new42,
                                'payoff21_loss_if_scrambled_pp':100*(old21-new21) if valid else np.nan,
                                'mean_abs_return_rank_move':float(np.mean(np.abs(rank-returnrank))),
                                'valid_outcomes':bool(valid)})
        print('NATIVE FAMILY',yr,'months',len(bydate),'inputrows',len(df),'max_rank_error',err,flush=True)
    dat=pd.DataFrame(out)
    dat.to_csv(OUT/'OLC71D_NATIVE_FAMILY_MONTHLY.csv',index=False)
    key=['family','n_group_columns','rep_seed']
    summaries=[]
    for period,years in [('MAIN_2021_2024',[2021,2022,2023,2024]),('LATE_2025',[2025])]:
        d=dat[dat.year.isin(years)]
        for k,sub in d.groupby(key,sort=True):
            valid=sub[sub.valid_outcomes]
            summaries.append({'market':'EU','period':period,'family':k[0],'n_group_columns':k[1],'rep_seed':k[2],
              'n_months':len(sub),'n_valid':len(valid),'top2_change_rate':sub.top2_changed.mean(),
              'mean_abs_return_rank_move':sub.mean_abs_return_rank_move.mean(),
              'original_payoff21':valid.original_payoff21.mean(),'permuted_payoff21':valid.perturbed_payoff21.mean(),
              'delta_original_minus_scramble_payoff21_pp':valid.payoff21_loss_if_scrambled_pp.mean()})
    pd.DataFrame(summaries).to_csv(OUT/'OLC71D_NATIVE_FAMILY_SUMMARY.csv',index=False)
    (OUT/'OLC71D_NATIVE_FAMILY_QA.json').write_text(json.dumps({'source':'EU original XGBoost R_RSI_DOMAIN; original native OLC19 FUSION',
      'status':'research_only_no_promotion','years':list(YEARS),'families':46,'permutation_seeds':list(SEEDS),
      'all_years_return_rank_parity':True,'all_years_fusion_parity':True,'records':len(dat),'audit':audit,
      'warning':'Off-manifold causal model sensitivity, not true feature conditional importance or alpha, USA original models not present'},indent=2))
    print('DONE',len(dat),'rows', flush=True)

if __name__=='__main__':
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=pd.errors.PerformanceWarning)
        main()