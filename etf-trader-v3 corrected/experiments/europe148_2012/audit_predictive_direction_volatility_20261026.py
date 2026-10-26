#!/usr/bin/env python3
"""Frozen (no-refit) 18 head US149 vs EU148 101m direction vs amplitude
and original native 125-feature as-of volume/market regime diagnostic.
Makes no hyperparameter decisions. All merged rows checked one-to-one.
"""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

def mean_ic(df,score,target):
    a=df[score]; b=df[target]; good=a.notna()&b.notna()
    return float(spearmanr(a[good],b[good]).statistic) if good.sum()>=12 and a[good].nunique()>2 and b[good].nunique()>2 else np.nan

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--panels',type=Path,required=True)
    ap.add_argument('--heads',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    z=ap.parse_args();z.out.mkdir(parents=True,exist_ok=True)
    FEATURE=['vol21','vol63','vol126','mom21','mom63','mom126','mom252','downvol126',
             'beta_mkt63','beta_mkt126','corr_mkt126','log_adv63','volume_surprise21',
             'vol126_pct','mom21_pct','mom252_pct']
    audits=[];month=[];top5=[];quality=[];features=[]
    for market in ('US149','EU148'):
        p=pd.read_parquet(z.panels/market/'CORRECTED125_PANEL.parquet')
        assert p.ticker.nunique()==(149 if market=='US149' else 148)
        p.signal_date=pd.to_datetime(p.signal_date)
        p.exit_date_21=pd.to_datetime(p.exit_date_21)
        p=p.replace([np.inf,-np.inf],np.nan)
        fcols=[s for s in p if s.startswith('mom') or s.startswith('vol') or s.startswith('beta') or s.startswith('corr')]
        assert all(s in p for s in FEATURE)
        for window,subset in [('TRAIN_2012_2017',p[p.signal_date.between('2012-01-01','2017-12-31')]),('OOS_2018_2026',p[p.signal_date.between('2018-01-01','2026-05-31')])]:
            assert len(subset)>1000
            for feature in FEATURE:
                features.append(dict(market=market,window=window,feature=feature,
                     missing=float(subset[feature].isna().mean()),median=float(subset[feature].median()),q90=float(subset[feature].quantile(.9)),
                     nunique=int(subset[feature].nunique())))
        o=[]
        for year in range(2018,2027):
            fn=z.heads/market/str(year)/'PAIRED_127_PREDICTIONS.csv'
            assert fn.is_file(),fn
            d=pd.read_csv(fn,parse_dates=['signal_date'])
            o.append(d[['signal_date','ticker','pred','fwd_ret_21']])
        x=pd.concat(o,ignore_index=True)
        assert not x.duplicated(['signal_date','ticker']).any()
        p_o=p[p.signal_date.between('2018-01-01','2026-05-31')].copy()
        joined=x.merge(p_o[['signal_date','ticker','fwd_ret_21']+FEATURE],on=['signal_date','ticker'],validate='one_to_one',suffixes=('','_native'),indicator=True)
        assert joined._merge.eq('both').all() and len(joined)==len(x)
        assert np.allclose(joined.fwd_ret_21,joined.fwd_ret_21_native)
        assert joined.signal_date.nunique()==101
        for sd,g in joined.groupby('signal_date',sort=True):
            y=g.fwd_ret_21;mu=y.mean();sig=y.std(ddof=0)
            g=g.copy();g['future_abs_z']=(y-mu).abs()/sig
            g['future_risk_adj']=y/(g.vol126.clip(lower=1e-8)*np.sqrt(21/252))
            g['forward_rank_pct']=y.rank(pct=True)
            g['forward_abs_rank_pct']=g.future_abs_z.rank(pct=True)
            choices=g.nlargest(5,'pred'); volselect=g.nlargest(5,'vol126')
            rank99=float((g.pred.rank(pct=True)-g.vol126.rank(pct=True)).abs().mean())
            rec=dict(market=market,date=sd,n=len(g),
              ic_direction=mean_ic(g,'pred','fwd_ret_21'),
              ic_amplitude=mean_ic(g,'pred','future_abs_z'),
              ic_pastvol=mean_ic(g,'pred','vol126'),
              ic_downvol=mean_ic(g,'pred','downvol126'),
              ic_pastmom21=mean_ic(g,'pred','mom21'),
              ic_pastmom252=mean_ic(g,'pred','mom252'),
              ic_beta126=mean_ic(g,'pred','beta_mkt126'),
              ic_volume=mean_ic(g,'pred','log_adv63'),
              ic_model_risk_adj_target=mean_ic(g,'pred','future_risk_adj'),
              ic_pastvol_predicts_future_amplitude=mean_ic(g,'vol126','future_abs_z'),
              ic_mom21_target=mean_ic(g,'mom21','fwd_ret_21'),
              ic_mom252_target=mean_ic(g,'mom252','fwd_ret_21'),
              feature_missing_any=float(g[FEATURE].isna().any(axis=1).mean()),
              observed_vol_median=float(g.vol126.median()),
              model_top5_vol_pct=float(g.vol126.rank(pct=True).reindex(choices.index).mean()),
              model_top5_rank_pct=float(g.forward_rank_pct.reindex(choices.index).mean()),
              model_top5_return_excess=float(choices.fwd_ret_21.mean()-mu),
              volonly_top5_rank_pct=float(g.forward_rank_pct.reindex(volselect.index).mean()),
              volonly_top5_return_excess=float(volselect.fwd_ret_21.mean()-mu),
              model_top5_absz=float(choices.future_abs_z.mean()),
              volonly_top5_absz=float(volselect.future_abs_z.mean()),
              model_volonly_score_rank_l1=rank99)
            for title,s in [('model',choices),('volonly',volselect)]:
                yy=s.forward_rank_pct
                rec[title+'_top_decile']=float((yy>=.9).mean())
                rec[title+'_bottom_decile']=float((yy<=.1).mean())
            month.append(rec)
            top5.extend(dict(market=market,signal_date=sd,ticker=r.ticker,pred=r.pred,
                 past_vol126=r.vol126,past_vol_pct=float(g.vol126.rank(pct=True).loc[r.Index]),
                 fwd_ret_21=r.fwd_ret_21,forward_rank_pct=r.forward_rank_pct)
                for r in choices.itertuples())
    d=pd.DataFrame(month).sort_values(['market','date'])
    d.to_csv(z.out/'MONTHLY_ASOF_VOLATILITY_VS_DIRECTION.csv',index=False)
    pd.DataFrame(top5).to_csv(z.out/'TOP5_VOL_RANK_EVIDENCE.csv',index=False)
    pd.DataFrame(features).to_csv(z.out/'FEATURE_MISSINGNESS_AND_DISTRIBUTIONS_125F.csv',index=False)
    s=d.groupby('market').agg(months=('date','size'),ic_direction=('ic_direction','mean'),
          ic_amplitude=('ic_amplitude','mean'),ic_past_volatility=('ic_pastvol','mean'),
          ic_past_downvol=('ic_downvol','mean'),ic_past_mom21=('ic_pastmom21','mean'),
          ic_past_mom252=('ic_pastmom252','mean'),ic_beta126=('ic_beta126','mean'),
          ic_volume=('ic_volume','mean'),
          ic_risk_adjusted_forward=('ic_model_risk_adj_target','mean'),
          naive_mom21_ic=('ic_mom21_target','mean'),
          naive_mom252_ic=('ic_mom252_target','mean'),
          model_top5_past_volatility_pct=('model_top5_vol_pct','mean'),
          model_top5_true_outcome_pct=('model_top5_rank_pct','mean'),
          model_top5_forward_excess=('model_top5_return_excess','mean'),
          volatility_baseline_top5_outcome_pct=('volonly_top5_rank_pct','mean'),
          volatility_baseline_top5_excess=('volonly_top5_return_excess','mean'),
          model_best_decile_rate=('model_top_decile','mean'),
          model_worst_decile_rate=('model_bottom_decile','mean'),
          volonly_best_decile_rate=('volonly_top_decile','mean'),
          volonly_worst_decile_rate=('volonly_bottom_decile','mean'),
          model_forecast_absolute_move_z=('model_top5_absz','mean'),
          volonly_forecast_absolute_move_z=('volonly_top5_absz','mean')
          ).reset_index()
    s.to_csv(z.out/'MARKET_FEATURE_AND_DIRECTION_VS_VOL_SCORECARD.csv',index=False)
    (z.out/'MANIFEST.json').write_text(json.dumps(dict(
      experiment='Cross-validation of frozen annual V3 127 heads, as-of feature risk and target direction',
      OOS_months=101,models_unchanged=True,features=125,price_labels_exactly_joined=True,
      US_SPY_EU_median_market_proxy=True,
      precautions=['No training on OOS, no tuning on observations',
        'Absolute forward return is EX POST DIAGNOSTIC not as-of forecast',
        'Vol-only comparison pre-specified as a risk bias control, not tradable benchmark',
        'May be data snooped by earlier EUR v3 iteration; no untouched holdout',
        'Different target factor structures and 2012 coverage remain unresolved']),indent=2))
    print('FEATURE_VS_DIRECTION_FULL',s.to_string(index=False),flush=True)
    print('FEATURE_NULLS',pd.DataFrame(features).pivot_table(index=['market','window'],columns='feature',values='missing').round(3).to_string(),flush=True)
    print('V3_127_ASOF_RISK_FORENSIC_PASS')
if __name__=='__main__':main()
