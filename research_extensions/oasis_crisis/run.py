#!/usr/bin/env python3
"""Post-result OASIS forensic skill analysis. Realized future used ONLY here."""
from __future__ import annotations
import hashlib,json,math,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from oasis.observers import prepare
BASE=ROOT/"oasis/results/frozen_daily_corrected"
RAW=ROOT/"data/eu120/raw_ticker_csv"

def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def stats(vals):
    a=np.asarray([x for x in vals if np.isfinite(x)],float)
    return dict(n=len(a),mean=float(a.mean()) if len(a) else None,
         median=float(np.median(a)) if len(a) else None,
         pct_positive=float(np.mean(a>0)) if len(a) else None,
         q10=float(np.quantile(a,.1)) if len(a) else None,
         q90=float(np.quantile(a,.9)) if len(a) else None)
def main():
    roster=pd.read_csv(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv")
    names=roster.ticker.astype(str).tolist()
    src={}
    for t in names:
        d=pd.read_csv(RAW/(t+".csv"),usecols=["date","Open","Close"],parse_dates=["date"])
        d=d.drop_duplicates("date").set_index("date").sort_index()
        src[t]=d
    opens=pd.concat({t:v.Open for t,v in src.items()},axis=1).reindex(columns=names)
    close=pd.concat({t:v.Close for t,v in src.items()},axis=1).reindex(columns=names)
    feat=prepare(close)
    p0=pd.read_csv(BASE/"P0_MONTHLY_GREEDY.csv",parse_dates=["day","signal_date"])
    p2=pd.read_csv(BASE/"P2_DAILY_ECONOMIC_HYSTERESIS.csv",parse_dates=["day","signal_date"])
    assert len(p0)==len(p2)==2389
    assert (p0.day.to_numpy()==p2.day.to_numpy()).all()
    dates=p0.day.to_list()
    events=defaultdict(lambda:defaultdict(list))
    regime_count=defaultdict(int)
    onset=defaultdict(int);prevstate=None
    for row in p0.itertuples():
        regime_count[row.regime]+=1
        if row.regime!=prevstate:onset[row.regime]+=1
        prevstate=row.regime
    for j,row in enumerate(p0.itertuples()):
        if j+21>=len(p0):break
        s=pd.Timestamp(row.signal_date);d=pd.Timestamp(row.day)
        if not s<d:raise AssertionError("forecast timestamp not before trade open")
        pred=feat["score"].loc[s]
        valid=pred.notna()
        try:
            entry=opens.loc[d]
        except KeyError:continue
        for h in (5,21):
            finish=pd.Timestamp(dates[j+h])
            ext=opens.loc[finish]
            eligible=valid & (entry>0)&(ext>0)&entry.notna()&ext.notna()
            if eligible.sum()<20:continue
            r=np.log(ext[eligible]/entry[eligible])
            score=pred[eligible]
            rho=float(score.corr(r,method="spearman"))
            top=score.nlargest(2).index
            top_mean=float(r.loc[top].mean())
            middle=float(r.median())
            group=events[row.regime]
            group[f"spearman_{h}"].append(rho)
            group[f"selected_top2_minus_median_{h}"].append(top_mean-middle)
            group[f"oracle_P90_minus_P10_{h}"].append(float(r.quantile(.9)-r.quantile(.1)))
            group[f"median_realized_{h}"].append(middle)
    switches=defaultdict(list);missed=0;single_switches=0;ambiguous=0
    for j in range(1,len(p2)-21):
        before=set(str(p2.iloc[j-1].names).split(";"))
        after=set(str(p2.iloc[j].names).split(";"))
        previous=before-after;new=after-before
        if len(previous)==len(new)==1:
            single_switches+=1
            old=next(iter(previous));candidate=next(iter(new))
            d=pd.Timestamp(p2.iloc[j].day);end=pd.Timestamp(dates[j+21])
            try:
                px0=opens.loc[d,[candidate,old]]
                px1=opens.loc[end,[candidate,old]]
                if (not np.isfinite(px0.to_numpy(float)).all() or
                    not np.isfinite(px1.to_numpy(float)).all() or
                    not (px0.to_numpy(float)>0).all() or
                    not (px1.to_numpy(float)>0).all()):
                    missed+=1;continue
                relative=float(math.log(px1[candidate]/px0[candidate])-
                               math.log(px1[old]/px0[old]))
                switches[str(p2.iloc[j].regime)].append(relative)
            except KeyError:missed+=1
        elif previous or new:ambiguous+=1
    out=dict(status="OASIS_CRISIS_OPPORTUNITY_FORENSIC_COMPLETED",
        scope="POST_RESULT_EXPOST_DIAGNOSTICS_ONLY",
        no_new_trading_policy=True,observed_days=int(len(dates)),
        regime_day_counts=dict(regime_count),
        regime_episode_onsets=dict(onset),
        conditional_forward_skill={state:{key:stats(v) for key,v in features.items()}
                                   for state,features in events.items()},
        actual_economic_switch_forward_21_log_advantage={
                k:stats(v) for k,v in switches.items()},
        one_for_one_switches_examined=single_switches,
        switches_without_complete_forward_quotes=missed,
        multi_or_nonstandard_changes=ambiguous,
        source_roster_sha256=sha(ROOT/"europe_only75/UNIVERSE_EUR_LISTED_60.csv"),
        prior_frozen_run_id=39124549957,
        limitation=["overlapping_5_21day_labels","retrospective_survivor_cohort",
           "best_expost_quantile_not_achievable",
           "quote_volume_and_currency_unverified",
           "no_independent_forward_sample"])
    path=ROOT/"research_extensions/oasis_crisis/RESULT.json"
    path.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
    print("OASIS_CRISIS_SKILL_RESULT "+json.dumps(out,allow_nan=False),flush=True)
if __name__=="__main__":main()
