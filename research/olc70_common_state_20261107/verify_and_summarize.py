#!/usr/bin/env python3
"""Independent checks and summary, OLC70A/B. Does not fit any model."""
from __future__ import annotations
import io,json,zipfile
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
SOURCE=(ROOT/'inputs/OLC67_Strategia_ETF_Verificata.zip' if (ROOT/'inputs/OLC67_Strategia_ETF_Verificata.zip').exists() else Path('/mnt/data/OLC69_Adaptive_Opportunity_20261107/OLC67_Strategia_ETF_Verificata.zip'))


def dat(name):return pd.read_csv(OUT/name)

def control():
    with zipfile.ZipFile(SOURCE) as z:
        annual=pd.read_csv(io.BytesIO(z.read('OLC67/results/OLC67_ANNUAL.csv')))
        scores=pd.read_csv(io.BytesIO(z.read('OLC67/results/OLC67_SCORECARD.csv')))
    orig=annual[(annual.risk=='FAST_LOCK3')&(np.isclose(annual.fee,.001))&(((annual.weight=='HALF')&(annual.timing=='IMMEDIATE'))|((annual.weight=='MINVAR63')&(annual.timing=='DELAY3')))].copy()
    orig['policy']=np.where(orig.weight=='HALF','OLC19','OLC67')
    score=scores[(scores.risk=='FAST_LOCK3')&(np.isclose(scores.fee,.001))&(((scores.weight=='HALF')&(scores.timing=='IMMEDIATE'))|((scores.weight=='MINVAR63')&(scores.timing=='DELAY3')))].copy()
    score['policy']=np.where(score.weight=='HALF','OLC19','OLC67')
    return orig,score

def check_scorecard(tag,scorepath,dailypath):
    sc=dat(scorepath);daily=dat(dailypath);d=pd.to_datetime(daily.date)
    count=0; maxc=maxd=0.0
    assert sc.shape[0]==20
    for z in sc.itertuples():
        mask=(daily.market==z.market)&(np.isclose(daily.fee,z.fee))&(d>=z.first_valuation)&(d<=z.last_valuation)
        r=daily.loc[mask,'logr'].to_numpy(float)
        assert r.size==z.n and len(r)>1
        cagr=np.expm1(r.mean()*252)
        nav=np.exp(np.cumsum(r));maxdd=(nav/np.maximum.accumulate(np.r_[1.,nav])[1:]-1).min()
        maxc=max(maxc,abs(cagr-z.cagr));maxd=max(maxd,abs(maxdd-z.maxdd))
        assert abs(cagr-z.cagr)<1e-10,(tag,z.market,z.fee,z.period,'CAGR')
        assert abs(maxdd-z.maxdd)<1e-10,(tag,z.market,z.fee,z.period,'DD')
        count+=1
    return {'periods_recalculated':count,'max_abs_cagr_error':maxc,'max_abs_maxdd_error':maxd}

def verify():
    qa={}
    qa['OLC70A']=check_scorecard('A','OLC70_SCORECARD.csv','OLC70_DAILY_LOGRET.csv.gz')
    qa['OLC70B']=check_scorecard('B','OLC70B_SCORECARD.csv','OLC70B_DAILY_LOGRET.csv.gz')
    orig,score=control()
    # Exact period comparability by date and number of valuations.
    combined=pd.concat([score[['policy','market','fee','period','n','cagr','maxdd']],
              dat('OLC70_SCORECARD.csv').assign(policy='OLC70A')[['policy','market','fee','period','n','cagr','maxdd']],
              dat('OLC70B_SCORECARD.csv').assign(policy='OLC70B')[['policy','market','fee','period','n','cagr','maxdd']]],ignore_index=True)
    combined=combined[combined.period.isin(['FULL','ACTIVE2021_2024','2025','2026'])]
    assert len(combined)==2*4*4+2*2*4  # OLC19 and OLC67 at .001/.003 plus A/B .001/.003
    combined.to_csv(OUT/'OLC70_COMPARISON.csv',index=False)
    # Disambiguate 2026: PARTIAL year return, never annualize it as complete calendar return.
    years=pd.concat([orig[['policy','market','fee','year','year_return']],
         dat('OLC70_ANNUAL.csv').rename(columns={'return_arithmetic':'year_return'}).assign(policy='OLC70A')[['policy','market','fee','year','year_return']],
         dat('OLC70B_ANNUAL.csv').rename(columns={'annual_return':'year_return'}).assign(policy='OLC70B')[['policy','market','fee','year','year_return']]],ignore_index=True)
    years.to_csv(OUT/'OLC70_ANNUAL_COMPARISON.csv',index=False)
    # Month-by-month record of actions from full persistent on-policy engine
    act=dat('OLC70B_ROUTE.csv');lab=dat('OLC70B_ON_POLICY_LABELS.csv')
    assert len(act)==164 and len(lab)==178
    feat=pd.read_csv(ROOT/'inputs/OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv' if (ROOT/'inputs/OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv').exists() else '/mnt/data/OLC69_Adaptive_Opportunity_20261107/OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv')
    labels=lab.merge(feat[['market','signal_month','feature_asof_date']],left_on=['market','month'],right_on=['market','signal_month'],validate='one_to_one',how='inner')
    assert len(labels)==164
    # Current signal info must be known before current entry; and training labels
    # must have matured at least two *whole* event months before current.
    originals=dat('OLC70_COMMON_STATE_LABELS.csv')
    sig=originals[['market','month','start_date']]
    labels=labels.merge(sig,on=['market','month'],validate='one_to_one')
    assert (pd.to_datetime(labels.feature_asof_date)<pd.to_datetime(labels.start_date)).all()
    bad=0
    for row in act.itertuples(index=False):
        candidates=labels[(labels.market==row.market)&(pd.PeriodIndex(labels.month,freq='M')<=pd.Period(row.month,'M')-2)]
        assert int(row.train_n)==len(candidates),(row.market,row.month,row.train_n,len(candidates))
        if row.train_n<24:assert row.action=='A'
        if row.train_n>=24:
            pred={a:float(getattr(row,'pred_'+a)) for a in 'BCD'}
            assert all(np.isfinite(list(pred.values())))
            best=max({'A':0.,**pred}.items(),key=lambda x:x[1])[0]
            if best!='A' and pred[best]>5:assert row.action==best
            else:assert row.action=='A'
    qa['chronology']={'all_164_asof_before_signal':True,'full_train_count_and_route_reconciled':True,
                     '2month_maturity_strict':True,'fallback_before_24':True}
    # On-policy reward labels: all four branches same pre-state market month.
    for d in [lab,originals]:
        for key in ['B','C','D']:
            x=d[key+'_return_logbp']-d['A_return_logbp']
            assert np.max(abs(x-d[key+'_vs_A_logbp']))<1e-9
        assert ((d[[a+'_return_logbp' for a in 'ABCD']].max(axis=1)-d['A_return_logbp'])>=-1e-10).all()
    qa['labels']={'onpolicy':len(lab),'A_base':len(originals),'four_forks_same_start':True,'arithmetic_checks':True}
    assert len(dat('OLC70_FORECAST_SKILL.csv'))==len(dat('OLC70B_FORECAST_SKILL.csv'))==342
    skill=[]
    for pol,fn,mean_col,true_col in [
        ('OLC70A','OLC70_FORECAST_SKILL.csv','mean_prior_logbp','actual_common_state_logbp'),
        ('OLC70B','OLC70B_FORECAST_SKILL.csv','prior_mean_logbp','actual_logbp')]:
        d=dat(fn)
        for (m,arm),s in d.groupby(['market','action']):
            y=s[true_col].to_numpy();p=s.predicted_logbp.to_numpy();mean=s[mean_col].to_numpy()
            skill.append(dict(policy=pol,market=m,action=arm,n=len(y),
                              ridge_rmse_logbp=float(np.sqrt(np.mean((y-p)**2))),
                              historical_mean_rmse_logbp=float(np.sqrt(np.mean((y-mean)**2))),
                              delta_rmse_logbp=float(np.sqrt(np.mean((y-p)**2))-np.sqrt(np.mean((y-mean)**2))),
                              pearson=float(np.corrcoef(y,p)[0,1]) if np.std(p)>0 else None))
    s=pd.DataFrame(skill);s.to_csv(OUT/'OLC70_FORECAST_SKILL_SUMMARY.csv',index=False)
    qa['forecast_skill']={'negative_vs_mean_n_of_6_olc70A':int((s[s.policy=='OLC70A'].delta_rmse_logbp>0).sum()),
                          'negative_vs_mean_n_of_6_olc70B':int((s[s.policy=='OLC70B'].delta_rmse_logbp>0).sum())}
    shift=dat('OLC70B_STATE_SHIFT_VS_BASELINE.csv')
    summary=shift.assign(absolute=lambda x:abs(x.drift_logbp),nonzero=lambda x:x.drift_logbp.abs()>1e-6).groupby(['market','action']).agg(events=('month','size'),nonzero_pct=('nonzero','mean'),median_abs_logbp=('absolute','median'),p95_abs_logbp=('absolute',lambda x:x.quantile(.95))).reset_index()
    summary.to_csv(OUT/'OLC70_STATE_SHIFT_SUMMARY.csv',index=False)
    act['year']=act.month.str[:4].astype(int)
    act.groupby(['market','year','action']).size().rename('n').reset_index().to_csv(OUT/'OLC70B_ACTION_COUNTS_ANNUAL.csv',index=False)
    selected=act[act.action!='A'].groupby(['market','year']).agg(
        n=('action','size'),hit_rate=('observed_chosen_common_state_logbp',lambda x:(x>0).mean()),
        chosen_excess_logbp=('observed_chosen_common_state_logbp','sum')).reset_index()
    selected.to_csv(OUT/'OLC70B_ACTION_OUTCOMES_ANNUAL.csv',index=False)
    qa['comparison']={'n_scorecard':len(combined),'n_annual':len(years),'n_forecast_skill_arms':len(s)}
    (OUT/'OLC70_INDEPENDENT_QA.json').write_text(json.dumps(qa,indent=2))
    print(json.dumps(qa,indent=2))
if __name__=='__main__':verify()