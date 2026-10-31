"""Reproduce CL01 baselines and audit opportunity/size/switch decisions.
No trading policy is fitted or modified. Forward outcomes are diagnostics only.
"""
from pathlib import Path
import sys,os,json,hashlib,warnings
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import numpy as np
import pandas as pd
from opportunity_core import topk,shortlist,horizon_returns,switch_gain,actual_incumbents
R=Path(__file__).resolve().parents[1];F=R/'inputs/frontier';OUT=R/'results';(OUT/'references').mkdir(exist_ok=True)
sys.path.insert(0,str(F/'src'))
from native_screen import load,state_with_score,simulate,metrics,SOURCE
from calendar_replay import crop


def phash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    opportunities=[];sizes=[];switches=[];events=[];parities=[];input_manifest=[];temporal=[]
    source_stats=pd.read_csv(F/'results/rebuilt/SCORECARD.csv')
    for market in ['EU','USA']:
        q,half_state,C,_,_,_,_,_=load(market);q=crop(q,'2019-02-01')
        T=list(C.columns);N=len(T)
        score=pd.read_csv(F/f'results/rebuilt/{market}_LEGACY_SCORES.csv',index_col=0,parse_dates=True,float_precision='round_trip').reindex(columns=T)
        rr=pd.read_csv(F/f'results/rebuilt/{market}_R_ONLY_SCORES.csv',index_col=0,parse_dates=True,float_precision='round_trip').reindex_like(score)
        hy=pd.read_csv(F/f'results/rebuilt/{market}_H_ONLY_SCORES.csv',index_col=0,parse_dates=True,float_precision='round_trip').reindex_like(score)
        preds=pd.read_csv(F/f'results/calendar/{market}_FORECASTS.csv.gz',parse_dates=['signal_date','source_date'])
        assert (preds.source_date<=preds.signal_date).all()
        assert ((preds.signal_date-preds.source_date).dt.days<=5).all()
        et=preds.pivot(index='signal_date',columns='ticker',values='ET').reindex_like(score)
        xx=preds.pivot(index='signal_date',columns='ticker',values='XGB').reindex_like(score)
        cal=pd.read_csv(F/f'results/calendar/{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
        cal=cal[cal.signal_date.isin(score.index)].sort_values('signal_date').reset_index(drop=True)
        assert np.array_equal(cal.signal_date.to_numpy(),score.index.values)
        assert (cal.signal_date<cal.entry_date).all()
        ds=pd.DatetimeIndex(q['dates'])
        if market=='EU':rawO=pd.read_pickle(SOURCE/'inputs/EU_Open.pkl').reindex(columns=T)
        else:rawO=pd.DataFrame({t:pd.read_csv(SOURCE/'raw/_repeat1'/f'{t}.csv',index_col=0,parse_dates=True,float_precision='round_trip').Open for t in T})
        rawO=rawO.loc[:'2026-07-01'];O=rawO.to_numpy()
        c=C.ffill();mom63=c/c.shift(63)-1;mom252=c/c.shift(252)-1
        vol=np.log(c).diff().rolling(63,min_periods=42).std();ma200=c.rolling(200,min_periods=200).mean()
        # Prefix invariance: features for the last pre2024 date must not depend on later prices.
        cutoff=pd.Timestamp('2023-12-31');cut=c.index<=cutoff
        d1=c/c.shift(63)-1;d2=c.loc[cut]/c.loc[cut].shift(63)-1
        np.testing.assert_allclose(d1.loc[cut],d2,equal_nan=True)
        for col in [rr,hy,score]:assert col.index.is_monotonic_increasing and col.index.is_unique
        temporal.append({'market':market,'forecast_source_dates_checked':len(preds),'all_sources_before_signal':True,'all_signals_before_entry':True,'momentum_prefix_equal':True})
        states={};runs={}
        for weight,ishalf in [('ORIGINAL',False),('HALF',True)]:
            st=state_with_score(q,C.copy(),score,et,xx,cal,market,ishalf)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');E,_,_,_,L=simulate(st,np.ones(len(ds)),.001,market)
            nav=E[0];ld=L[0]
            assert np.max(np.abs(ld[:-1,46]))<1e-10
            # Independent cash-PnL reconstruction, not reuse of simulator metrics.
            rebuild=np.cumprod(1+ld[:-1,38]/ld[:-1,0])
            assert np.max(abs(rebuild-nav[:-1]))<1e-10
            config=f'REBUILT_LEGACY_PLAIN_{weight}_NONE_C10'
            recomputed=metrics(nav,ld,ds)
            for row in recomputed:
                ref=source_stats[(source_stats.market==market)&(source_stats.config==config)&(source_stats.period==row['period'])]
                assert len(ref)==1
                for key in ['cagr','maxdd','period_return']:
                    err=abs(row[key]-ref[key].iloc[0]);assert err<1e-12,(market,weight,row['period'],key,err)
                    parities.append({'market':market,'weight':weight,'period':row['period'],'metric':key,'error':err})
            states[weight]=st;runs[weight]=ld
            np.savez_compressed(OUT/'references'/f'{market}_CL01_{weight}.npz',dates=ds.values,nav=nav,ledger=ld,tickers=st['tickers'])
        print('REPRODUCED',market,'reference metrics',len(parities),flush=True)
        for i,row in enumerate(cal.itertuples(index=False)):
            sd=row.signal_date;ed=row.entry_date
            d=ds.get_indexer([ed])[0];e=rawO.index.get_indexer([ed])[0]
            assert d>=0 and e>=0
            # Final archived NAV row has no following trading interval.
            if d==len(ds)-1:continue
            a=score.loc[sd].to_numpy();support=np.isfinite(a)
            pool=shortlist([rr.loc[sd].to_numpy(),hy.loc[sd].to_numpy(),mom63.loc[sd].to_numpy(),mom252.loc[sd].to_numpy()],support,5)
            samek=topk(a,len(pool));volk=topk(np.where(support,vol.loc[sd].to_numpy(),np.nan),len(pool));baseids=topk(a,2)
            exact=[int(states['ORIGINAL']['d1'][0,d]),int(states['ORIGINAL']['d2'][0,d])]
            assert set(exact)==set(baseids),(market,sd,'Top2 tie')
            for h in [21,42,63]:
                y=horizon_returns(O,e,h);has_eval=e+h<len(rawO)
                labeldate=rawO.index[e+h] if has_eval else pd.NaT
                eligible=np.flatnonzero(support);valid=np.isfinite(y)&support
                winners=topk(np.where(valid&(y>0),y,np.nan),5)
                def recall(ids):return len(set(ids)&set(winners))/len(winners) if winners else np.nan
                med=float(np.nanmedian(np.where(valid,y,np.nan))) if valid.any() else np.nan
                actual=float(np.mean(y[baseids])) if np.isfinite(y[baseids]).all() else np.nan
                best_pool=topk(np.where(valid&np.isin(np.arange(N),pool),y,np.nan),2)
                oracle_pool=float(np.mean(y[best_pool])) if len(best_pool)==2 else np.nan
                # Hindsight ceiling is not an executable portfolio or an alpha estimate.
                opportunities.append(dict(market=market,signal_date=sd,entry_date=ed,label_exit=labeldate,horizon=h,eligible=len(eligible),available_outcomes=int(valid.sum()),shortlist_size=len(pool),future_positive_top5=len(winners),recall_actual2=recall(baseids),recall_pool=recall(pool),recall_sameK=recall(samek),recall_highvolK=recall(volk),uniform_expected_recall=len(pool)/len(eligible),actual2_return=actual,universe_median_return=med,hindsight_best2_pool_return=oracle_pool,pool_missing_labels=int(sum(not np.isfinite(y[j]) for j in pool)),shortlist='|'.join(T[j] for j in pool),actual_pair='|'.join(T[j] for j in baseids),realized_top5='|'.join(T[j] for j in winners)))
                j,k=exact;w=float(states['ORIGINAL']['weights'][0,d]);finite=np.isfinite(y[[j,k]]).all()
                sizes.append(dict(market=market,signal_date=sd,entry_date=ed,label_exit=labeldate,horizon=h,ticker1=T[j],ticker2=T[k],weight1=w,score_gap=float(a[j]-a[k]),valid=bool(finite),return1=y[j],return2=y[k],first_minus_second=y[j]-y[k],original_minus_half=(w-.5)*(y[j]-y[k]),original_pair_return=w*y[j]+(1-w)*y[k],equal_pair_return=.5*(y[j]+y[k])))
            for weight in ['ORIGINAL','HALF']:
                ld=runs[weight];prev=ld[d-1] if d>0 else np.zeros(48)
                if d==0:prev[25:28]=-1
                old=actual_incumbents(prev)
                new=list(dict.fromkeys(int(ld[d,j]) for j,v in [(25,28),(26,29)] if ld[d,j]>=0 and ld[d,v]>1e-12))
                out=[j for j in old if j not in new];inc=[j for j in new if j not in old]
                # Tie matching declared from current ranks, not realized future wealth.
                out.sort(key=lambda j: (a[j] if j<N and np.isfinite(a[j]) else -np.inf,j))
                inc.sort(key=lambda j: (-a[j] if j<N and np.isfinite(a[j]) else np.inf,j))
                events.append(dict(market=market,weight=weight,signal_date=sd,entry_date=ed,actual_incumbents='|'.join(T[j] for j in old if j<N),actual_new='|'.join(T[j] for j in new if j<N),outgoing=len(out),incoming=len(inc),matched_replacements=min(len(out),len(inc)),rebalanced=int(ld[d,4]),systemic_at_open=int(ld[d,17]),planned_pair='|'.join(T[j] for j in exact)))
                if ld[d,4]==0:continue
                for oldj,newj in zip(out,inc):
                    if oldj>=N or newj>=N:continue
                    for h in [21,42,63]:
                        y=horizon_returns(O,e,h);valid=np.isfinite(y[[oldj,newj]]).all()
                        le=rawO.index[e+h] if e+h<len(rawO) else pd.NaT
                        for cost in [.001,.003]:
                            delta=switch_gain(y[newj],y[oldj],cost) if valid else np.nan
                            switches.append(dict(market=market,weight=weight,signal_date=sd,entry_date=ed,label_exit=le,horizon=h,cost_bps_side=int(cost*10000),old_ticker=T[oldj],new_ticker=T[newj],valid=bool(valid),old_return=y[oldj],new_return=y[newj],gross_advantage=y[newj]-y[oldj],net_advantage=delta,score_gap=a[newj]-a[oldj],old_mom63=mom63.loc[sd].iloc[oldj],new_mom63=mom63.loc[sd].iloc[newj],old_above_ma200=bool(c.loc[sd].iloc[oldj]>=ma200.loc[sd].iloc[oldj]),old_in_pool=oldj in pool,new_in_pool=newj in pool,systemic_at_open=int(ld[d,17])))
        for name in [f'{market}_FORECASTS.csv.gz',f'{market}_CALENDAR.csv']:
            p=F/'results/calendar'/name;input_manifest.append({'source':str(p.relative_to(R)),'sha256':phash(p)})
    for name,rows in [('OPPORTUNITY_MONTHS',opportunities),('SIZING_MONTHS',sizes),('ACTUAL_SWITCHES',switches),('ACTUAL_DECISION_EVENTS',events),('BASELINE_RECONCILIATION',parities)]:
        pd.DataFrame(rows).to_csv(OUT/f'{name}.csv',index=False)
    (OUT/'INPUTS_AND_TEMPORAL_CHECKS.json').write_text(json.dumps({'inputs':input_manifest,'checks':temporal,'new_models':0,'new_strategy_variants':0,'reference_replays':4,'scope':'Static opportunity/capital/replacement diagnostics on reconstructed CL01. Not new portfolio improvements.'},indent=2))
    print('DONE','opportunity rows',len(opportunities),'size rows',len(sizes),'static switch rows',len(switches),'events',len(events),flush=True)
if __name__=='__main__':main()
