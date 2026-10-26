#!/usr/bin/env python3
"""Out-of-time US/EU LM Ridge and LightGBM path prediction vs frozen V3 ranker,
and net EUR same-calendar real economic Top1/3/5 on full/equity cohorts.
All thresholds fixed; NO optimization using test predictions or outcomes.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd,numpy as np
from scipy.stats import spearmanr
from paired_us149_eu148_controls import load_raw,compute_nav
START='2018-01-01';LAST='2026-05-31';END='2026-07-01'
def ic(x,y):
    mask=np.isfinite(x)&np.isfinite(y)
    if mask.sum()<10:return np.nan
    return float(spearmanr(x[mask],y[mask]).statistic)
def main():
    p=argparse.ArgumentParser()
    for flag in ('us','eu','fx','heads','v3heads','v3econ','out'):p.add_argument('--'+flag,required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(exist_ok=True,parents=True)
    U=pd.read_csv(Path(a.us)/'universe.csv')
    E=pd.read_csv(Path(a.eu)/'EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv')
    assert len(U)==149 and len(E)==148
    Uo,Uc,Uv=load_raw(a.us,U,'US149')
    Eo,Ec,Ev=load_raw(Path(a.eu)/'raw_ticker_csv',E,'EU148')
    joint=Uo['SPY'].dropna().index.intersection(Eo['DE0002635307'].dropna().index).sort_values()
    joint=joint[(joint>=pd.Timestamp('2012-01-01'))&(joint<=pd.Timestamp(END))]
    assert len(joint)>3200 and joint[-1]==pd.Timestamp(END)
    fx=pd.read_csv(a.fx,parse_dates=['date']).set_index('date').Close.reindex(joint).ffill()
    assert fx.loc['2018-01-01':].notna().all()
    USop=Uo.reindex(joint).div(fx,axis=0); EUop=Eo.reindex(joint)
    dates=pd.Series(joint,index=joint)
    dates=dates.loc[START:LAST].groupby(dates.loc[START:LAST].index.to_period('M')).last().tolist()
    assert len(dates)==101
    econ=pd.read_csv(Path(a.v3econ)/'PAIRED_V3_127_ECONOMIC_SCORECARD.csv')
    assert len(econ)==12
    refs=[];predscores=[];econrows=[];navs=[];trades=[];fits=[];examples=[]
    for market,O,V,roster in (('US149',USop,Uv.reindex(joint),U),('EU148',EUop,Ev.reindex(joint),E)):
        q=[];base=[]
        for year in range(2018,2027):
            file=Path(a.heads)/market/str(year)
            qq=pd.read_csv(file/'ANNUAL_TRAJECTORY_FORECASTS.csv',parse_dates=['signal_date'])
            fit=json.loads((file/'ANNUAL_FIT_AUDIT.json').read_text())
            assert fit['train_last_63_label_exit']<f'{year}-01-01'
            assert fit['year']==year and fit['market']==market
            q.append(qq);fits.append(fit)
            bv=pd.read_csv(Path(a.v3heads)/market/str(year)/'PAIRED_127_PREDICTIONS.csv',parse_dates=['signal_date'])
            base.append(bv[['signal_date','ticker','pred']])
        d=pd.concat(q,ignore_index=True)
        v3=pd.concat(base,ignore_index=True)
        assert not d.duplicated(['signal_date','ticker','model']).any()
        assert not v3.duplicated(['signal_date','ticker']).any()
        assert d.groupby('model').signal_date.nunique().eq(101).all()
        assert d.groupby('model').size().nunique()==1
        d=d.merge(v3,on=['signal_date','ticker'],validate='many_to_one',indicator=True)
        assert d._merge.eq('both').all()
        all_t=set(roster.ticker)
        equity=(set(roster.loc[roster.macro_category.str.startswith(('C01','C02','C03')),'ticker'])
                if market=='US149' else
                set(roster.loc[roster.macro_category.str.startswith('EU_EQUITY'),'ticker']))
        assert len(equity)>=70
        for scope,allowed in [('FULL',all_t),('EQUITY',equity)]:
            for model in ('LM_RIDGE_PATH','LGBM_MEDIAN_PATH'):
                xx=d[(d.model==model)&d.ticker.isin(allowed)].copy()
                assert xx.signal_date.nunique()==101 and xx.groupby('signal_date').ticker.nunique().min()>=20
                for strategy in ('P21','PATH','V3_RANK'):
                    scorecol=('score_'+strategy if strategy!='V3_RANK' else 'pred')
                    key=f'{model}_{strategy}' if strategy!='V3_RANK' else 'V3_FROZEN'
                    if strategy=='V3_RANK' and model!='LM_RIDGE_PATH':continue
                    picks={};skill=[]
                    for date,g in xx.groupby('signal_date'):
                        gg=g.sort_values([scorecol,'ticker'],ascending=[False,True])
                        picks[date]=list(gg.ticker)
                        actual=gg[gg.fwd_ret_21.notna()].copy()
                        assert len(actual)>=20
                        y=actual.fwd_ret_21
                        top=gg.head(5)
                        basemean=y.mean();ranks=actual.fwd_ret_21.rank(pct=True)
                        ranktop=ranks.reindex(top.index).mean()
                        skill.append(dict(market=market,scope=scope,model=key,signal_date=date,
                            spearman=ic(actual[scorecol].to_numpy(float),actual.fwd_ret_21.to_numpy(float)),
                            best_decile_frac=float((ranks.reindex(top.index)>=.9).mean()),
                            worst_decile_frac=float((ranks.reindex(top.index)<=.1).mean()),
                            top5_forward_excess=float(top.fwd_ret_21.mean()-basemean),
                            top5_future_rank_pct=float(ranktop),
                            mae_forecast21=(float((actual.forecast_21-y).abs().mean()) if strategy!='V3_RANK' else np.nan),
                            zero_forecast_mae21=float(y.abs().mean()),
                            pearson_pred21=((float(actual.forecast_21.corr(y))) if strategy!='V3_RANK' else np.nan)))
                        for h in (21,42,63):
                            actualm=gg[f'fwd_ret_{h}'].notna()
                            if strategy!='V3_RANK' and actualm.sum()>=20:
                                skill[-1][f'mae_{h}']=float(np.mean(np.abs(gg.loc[actualm,f'forecast_{h}']-
                                                           gg.loc[actualm,f'fwd_ret_{h}'])))
                                skill[-1][f'mae_baselinezero_{h}']=float(np.mean(np.abs(gg.loc[actualm,f'fwd_ret_{h}'])))
                                skill[-1][f'correlation_{h}']=ic(gg.loc[actualm,f'forecast_{h}'].to_numpy(float),
                                                       gg.loc[actualm,f'fwd_ret_{h}'].to_numpy(float))
                        for row in top.itertuples():
                            examples.append(dict(market=market,scope=scope,model=key,signal_date=date,
                                ticker=row.ticker,f21=row.forecast_21,f42=row.forecast_42,f63=row.forecast_63,
                                realized21=row.fwd_ret_21,realized42=row.fwd_ret_42,realized63=row.fwd_ret_63))
                    skills=pd.DataFrame(skill)
                    predscores.append(dict(market=market,scope=scope,model=key,
                        n_months=len(skills),mean_ic=float(skills.spearman.mean()),
                        mean_top5_excess21=float(skills.top5_forward_excess.mean()),
                        mean_top5_future_rank_pct=float(skills.top5_future_rank_pct.mean()),
                        top5_best_decile_rate=float(skills.best_decile_frac.mean()),
                        top5_worst_decile_rate=float(skills.worst_decile_frac.mean()),
                        mae_p21=float(skills.mae_forecast21.mean()) if strategy!='V3_RANK' else np.nan,
                        naive_mae_p21=float(skills.zero_forecast_mae21.mean()),
                        mean_top5_mae42=float(skills.get('mae_42',pd.Series(dtype=float)).mean()) if strategy!='V3_RANK' else np.nan,
                        mean_top5_mae63=float(skills.get('mae_63',pd.Series(dtype=float)).mean()) if strategy!='V3_RANK' else np.nan))
                    refs.append(skills)
                    if strategy=='V3_RANK':
                        vv=econ[(econ.market==market)&(econ.segment==scope)]
                        assert len(vv)==3
                        for r in vv.itertuples():
                            econrows.append(dict(market=market,scope=scope,model=key,top_n=r.top_n,
                                cagr_eur=r.cagr_eur,max_dd=r.max_dd,
                                turnover_oneway=r.turnover_oneway,zero_reported_volume_orders=r.zero_reported_volume_orders,
                                economic_source='Original frozen 40227417589, not independently rebacktested here'))
                    else:
                        for topn in (1,3,5):
                            stats,nav,tr=compute_nav(O,V,dates,picks,joint,dates,market,scope,key,topn)
                            assert stats['signal_months']==101 and stats['end']==END
                            econrows.append(stats)
                            navs.append(nav);trades.append(tr)
                            print('TRAJECTORY_RESULT',market,scope,key,'TOP',topn,
                                  'CAGR_EUR',round(stats['cagr_eur']*100,3),
                                  'MAXDD',round(stats['max_dd']*100,2),flush=True)
    info=pd.DataFrame(predscores)
    info.to_csv(out/'TRAJECTORY_PREDICTIVE_SKILL.csv',index=False)
    pp=pd.DataFrame(econrows)
    pp.to_csv(out/'TRAJECTORY_ECONOMIC_SCORECARD.csv',index=False)
    pd.concat(refs,ignore_index=True).to_csv(out/'TRAJECTORY_MONTHLY_PREDICTIVE_SKILL.csv',index=False)
    pd.concat(navs,ignore_index=True).to_csv(out/'TRAJECTORY_DAILY_NAV.csv',index=False)
    pd.concat(trades,ignore_index=True).to_csv(out/'TRAJECTORY_TRADES.csv',index=False)
    pd.DataFrame(fits).to_csv(out/'TRAJECTORY_FIT_MATURITY_AUDIT.csv',index=False)
    pd.DataFrame(examples).to_csv(out/'TRAJECTORY_TOP5_REALIZED_VS_FORECAST.csv',index=False)
    assert info.groupby(['market','scope']).model.nunique().eq(5).all()
    assert pp.groupby(['market','scope','model']).top_n.nunique().eq(3).all()
    (out/'MANIFEST.json').write_text(json.dumps(dict(
      result='same original paired EUR 101 month portfolio market comparison',
      LM='Ridge multioutput 125features forecasts true signed 21,42,63-session returns',
      nonlinear_control='LightGBM separate 21,42,63-session signed future returns L1',
      ranking_baseline='unaltered native V3 127 leaf prior certified economics',
      signal_policy=['21d forecast','predeclared path utility'],
      no_future_test_filter=True,yearly_63_day_full_maturity=True,
      caveat='Historical 2018-2026 used in previous investigations; new model not truly blind validation'),
      indent=2))
    print('TRAJECTORY_ECONOMICS_FINAL',pp[['market','scope','model','top_n','cagr_eur','max_dd']].to_string(index=False),flush=True)
    print('TRAJECTORY_SKILL_FINAL',info[['market','scope','model','mean_ic','mean_top5_excess21','mae_p21']].to_string(index=False),flush=True)
    print('TRAJECTORY_PAIRS_COMPLETE')
if __name__=='__main__':main()
