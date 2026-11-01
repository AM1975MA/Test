"""Post-observation registered extension: paired task-trained fusion without CAGR selection."""
from pathlib import Path
import numpy as np,pandas as pd,json,hashlib
from scipy.special import logit
from prepare import read
from meta_fusion import mature_groups,fit_meta,predict_meta
from evaluate_layers import period_ok
from layer_metrics import ranking_metrics,opportunity_metrics
from portfolio_adapter import adapt_state
from vector_engine import simulate
from portfolio_metrics_parent import metrics,policy_args
from accounting import decompose
R=Path(__file__).resolve().parents[1];I=R/'inputs';O=R/'results';M=O/'meta_models';M.mkdir(exist_ok=True)

def main():
    audit=[];tm=[];om=[];probrows=[];port=[];checks=[]
    for market in ['EU','USA']:
        s=read(O/f'{market}_INTEGRATED_SCORES.csv.gz');f=read(I/f'{market}_MEAN3_INPUTS.csv.gz')
        f=f[['signal_date','ticker','RETURN','XGB_CLASS']].merge(s[['signal_date','ticker','MATCHED_REG']],on=['signal_date','ticker'],validate='one_to_one')
        f['H_SIGNAL']=(f.MATCHED_REG-.475*f.RETURN)/.525
        f['C_LOGIT']=logit(f.XGB_CLASS.clip(1e-6,1-1e-6))
        labels=read(I/f'{market}_LAYER_LABELS.csv.gz')
        f=f.merge(labels,on=['signal_date','ticker'],validate='one_to_one')
        valid=np.isfinite(f[['RETURN','H_SIGNAL','C_LOGIT']]).all(1)
        f=f[valid].copy();f['META2']=f.MATCHED_REG;f['META3']=f.MATCHED_REG
        f['META2_PROB']=np.nan;f['META3_PROB']=np.nan
        for year in range(2019,2027):
            tr=mature_groups(f,year)
            active=tr.signal_date.nunique()>=18 and year>=2021
            if not active:
                audit.append({'market':market,'year':year,'model':'both','status':'fallback_insufficient_history','months':int(tr.signal_date.nunique())});continue
            y=(tr.groupby('signal_date').TARGET.rank(method='average',pct=True)>.8).astype(float).to_numpy()
            pred=f.signal_date.dt.year==year
            for name,cols in [('META2',['RETURN','H_SIGNAL']),('META3',['RETURN','H_SIGNAL','C_LOGIT'])]:
                model=fit_meta(tr[cols].to_numpy(),y,tr.signal_date.to_numpy())
                model.update({'market':market,'year':year,'model':name,'columns':cols,'rows':len(tr),'max_signal':str(tr.signal_date.max()),'max_exit':str(tr.exit_date_63.max()),'training_key_sha256':hashlib.sha256(tr[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()})
                assert tr.exit_date_63.max()<pd.Timestamp(year,1,1)
                p=predict_meta(model,f.loc[pred,cols].to_numpy());f.loc[pred,name]=p;f.loc[pred,name+'_PROB']=p
                (M/f'{market}_{year}_{name}.json').write_text(json.dumps(model,indent=2));audit.append(dict(model,status='fitted'))
        out=s[['signal_date','ticker','MATCHED_REG']].merge(f[['signal_date','ticker','META2','META3','META2_PROB','META3_PROB']],on=['signal_date','ticker'],how='left',validate='one_to_one')
        out.to_csv(O/f'{market}_META_SCORES.csv.gz',index=False,compression='gzip')
        for date,g in f.groupby('signal_date'):
            for name in ['META2','META3']:
                if np.isfinite(g.TARGET).all() and g.exit_date_63.notna().all():
                    stats=ranking_metrics(g.TARGET.to_numpy(),g[name].to_numpy())
                    target=(g.TARGET.rank(pct=True,method='average')>.8).astype(float).to_numpy()
                    p=g[name+'_PROB'].to_numpy()
                    for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                        if period_ok(date,g.exit_date_63.max(),period):
                            tm.append(dict(market=market,seed='MEAN3',variant=name,date=date,period=period,n=len(g),**stats))
                            if np.isfinite(p).all():probrows.append(dict(market=market,variant=name,date=date,period=period,brier=float(np.mean((p-target)**2)),logloss=float(np.mean(-target*np.log(p)-(1-target)*np.log1p(-p)))))
                for h in [21,42,63]:
                    r=g[f'fwd_ret_{h}'];ex=g[f'exit_date_{h}']
                    if not np.isfinite(r).all() or ex.isna().any():continue
                    stats=opportunity_metrics(r.to_numpy(),g[name].to_numpy())
                    for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                        if period_ok(date,ex.max(),period):om.append(dict(market=market,seed='MEAN3',variant=name,date=date,period=period,horizon=h,n=len(g),**stats))
        q=dict(np.load(I/f'{market}_STATE_HALF.npz',allow_pickle=False));cal=read(I/f'{market}_CALENDAR.csv')
        for name in ['META2','META3']:
            st,ev,_=adapt_state(q,cal,out,name)
            for policy in ['IMMEDIATE','DELAY3','PHASE5']:
                for fee in [.001,.003]:
                    key=f'{market}_{name}_{policy}_FULL_C{round(fee*10000)}';rr=simulate(st,ev,fee=fee,**policy_args(policy));aa=decompose(st,rr)
                    capital=np.einsum('ij,ij->i',rr['primary_units'][:-1]+rr['defensive_units'][:-1],st['O'][1:])+rr['free_cash'][:-1]
                    err=float(np.max(abs(capital-rr['nav'][:-1])));assert err<1e-10
                    np.savez_compressed(O/f'paths/{key}.npz',dates=st['dates'],tickers=st['tickers'],**rr)
                    port.extend(dict(market=market,variant=name,policy=policy,mode='FULL',fee=fee,config=key,**z) for z in metrics(st,rr))
                    checks.append({'config':key,'nav_error':err,'intervals':len(st['dates'])-1});print('META_PATH',key,flush=True)
        print('META_MARKET_DONE',market,flush=True)
    (O/'META_TRAINING_AUDIT.json').write_text(json.dumps(audit,indent=2))
    pd.DataFrame(tm).to_csv(O/'META_LAYER_MONTHS.csv',index=False);pd.DataFrame(om).to_csv(O/'META_OPPORTUNITY_MONTHS.csv',index=False);pd.DataFrame(probrows).to_csv(O/'META_PROBABILITY_MONTHS.csv',index=False)
    pd.DataFrame(port).to_csv(O/'META_SCORECARD.csv',index=False);pd.DataFrame(checks).to_csv(O/'META_PATH_VERIFICATION.csv',index=False)
    for parent,extra,out in [('LAYER_MONTHS.csv','META_LAYER_MONTHS.csv','ALL_LAYER_MONTHS.csv'),('OPPORTUNITY_MONTHS.csv','META_OPPORTUNITY_MONTHS.csv','ALL_OPPORTUNITY_MONTHS.csv'),('SCORECARD.csv','META_SCORECARD.csv','ALL_SCORECARD.csv')]:pd.concat([read(O/parent),read(O/extra)],ignore_index=True).to_csv(O/out,index=False)
    t=read(O/'ALL_LAYER_MONTHS.csv');metrics_=['ndcg2','ndcg5','ic','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']
    t.groupby(['market','seed','variant','period']).agg(months=('date','nunique'),**{m:(m,'mean') for m in metrics_}).reset_index().to_csv(O/'ALL_LAYER_SUMMARY.csv',index=False)
    (O/'META_COMPLETE.json').write_text(json.dumps({'fits':sum(x['status']=='fitted' for x in audit),'paths':len(checks),'base_fits':0,'extension':'declared after fixed candidate outcomes; no independent validation claim'},indent=2))
if __name__=='__main__':main()
