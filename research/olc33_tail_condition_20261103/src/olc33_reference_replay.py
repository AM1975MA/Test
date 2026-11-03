"""OLC33 reproducible, preregistered tail classifier; see PROTOCOL_PRE_OUTCOME.md.
No tuning: fixed LogisticRegression, 2021–24 test, OLC32 corrected labels.
"""
import argparse
import hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SRC_SHA = '83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16'
DELTA = ['FUSION','ret_21','ret_63','ret_126','ret_252','dd_63',
         'vol_63','eff_63','sma_ratio_200','acc_21_63']
COLS = ['d_'+c for c in DELTA] + ['top5_dispersion_ret63','leader_ret63']


def construct(df):
    rows = []
    for (market, day), group in df[df.auth_rank<=5].groupby(['market','signal_date']):
        group = group.sort_values('auth_rank')
        assert list(group.auth_rank) == [1,2,3,4,5]
        leader = group.iloc[0]
        sd = np.std(group.ret_63.dropna(),ddof=0) if group.ret_63.notna().sum()>=2 else np.nan
        for _, cand in group.iloc[1:].iterrows():
            x = [cand[c]-leader[c] for c in DELTA] + [sd, leader.ret_63]
            usable = bool(cand.feature_available_asof and leader.feature_available_asof and np.isfinite(x).all())
            observed = bool(cand.eligible_label and leader.eligible_label)
            spread = cand.r_o2o_bp-leader.r_o2o_bp if observed else np.nan
            rows.append([market,day,day.year,int(cand.auth_rank),cand.ticker,leader.ticker,
                         cand.exit_date,leader.exit_date,usable,observed, bool(leader.eligible_label),
                         spread-20 if observed else np.nan,int(spread-20>=300) if observed else np.nan,*x])
    return pd.DataFrame(rows,columns=['market','signal_date','year','rank','challenger','incumbent',
        'exit_date','inc_exit_date','usable','observed','inc_valid','net_spread','y',*COLS])


def run(df):
    data = construct(df)
    data['p0'],data['p1'] = np.nan,np.nan
    for year in range(2021,2027):
        cutoff=pd.Timestamp(year,1,1)
        train=data[(data.usable)&(data.observed)&(data.exit_date<cutoff)&(data.inc_exit_date<cutoff)]
        months=train.groupby('market').signal_date.nunique().to_dict()
        weights=(1/train.groupby(['market','signal_date']).challenger.transform('size') /
                 train.groupby('market').signal_date.transform('nunique')).to_numpy()
        weights=weights*len(weights)/weights.sum()
        prior=np.average(train.y,weights=weights)
        data.loc[data.year==year,'p0']=prior
        predict=(data.year==year)&data.usable
        if months.get('EU',0)<12 or months.get('USA',0)<12 or train.y.sum()<20 or train.y.nunique()!=2:
            continue
        model=make_pipeline(StandardScaler(),LogisticRegression(C=.1,max_iter=1000,solver='lbfgs',random_state=33001))
        model.fit(train[COLS].to_numpy(),train.y.astype(int).to_numpy(),logisticregression__sample_weight=weights)
        data.loc[predict,'p1']=model.predict_proba(data.loc[predict,COLS].to_numpy())[:,1]
    actions=[]
    for (market,day), group in data.groupby(['market','signal_date']):
        best=group.sort_values(['p1','rank','challenger'],ascending=[False,True,True],na_position='last').iloc[0]
        has_model=np.isfinite(best.p1) and np.isfinite(best.p0)
        switch=bool(has_model and best.p1>=.40 and best.p1-best.p0>=.10)
        actions.append((market,day,best.incumbent,best.challenger if has_model else None,
                        switch,best.net_spread if switch and best.observed else (0 if not switch and best.inc_valid else np.nan)))
    return data,pd.DataFrame(actions,columns=['market','signal_date','incumbent','challenger','switch','net_gain_bp'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    with open(a.input,'rb') as f: assert hashlib.sha256(f.read()).hexdigest()==SRC_SHA
    df=pd.read_csv(a.input,parse_dates=['signal_date','exit_date','entry_date','source_date'])
    assert len(df)==len(df.drop_duplicates(['market','signal_date','ticker']))
    assert (df.source_date.dropna()<=df.loc[df.source_date.notna(),'signal_date']).all()
    data,actions=run(df)
    data[['market','signal_date','challenger','incumbent','rank','observed','net_spread','y','p0','p1']].to_csv(a.out+'_predictions.csv',index=False)
    actions.to_csv(a.out+'_actions.csv',index=False)
    for market,g in actions[actions.signal_date.dt.year.between(2021,2024)].groupby('market'):
        print(market,'actions',int(g.switch.sum()),'mean net bp',round(g.net_gain_bp.mean(),6))

if __name__=='__main__':main()
