"""Compare resumed counterfactuals with full-history U27 engine replays."""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from timing28 import ROOT, assign, market_events, previous, leg_correlation


def full_run(market, q):
    config = dict(q, risk_mode=(leg_correlation(q)<.70).astype(int))
    _, path, _ = previous.run(market,"PROFIT_RAMP",15,0,config,save=False)
    return path["ledger"][:,0].copy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results",type=Path,default=ROOT/"results")
    out = parser.parse_args().results
    labels = pd.read_csv(out/"MATCHED_LABELS.csv")
    choice = pd.read_csv(out/"FEATURES.csv")
    verified = []
    causal = []
    for market in previous.MARKETS:
        q = previous.state(market)
        baseline = full_run(market,q)
        base_features = market_events(q,market)
        rows = labels.loc[labels.market.eq(market) & labels.bps.eq(15)]
        for selected in (rows.iloc[len(rows)//3],rows.iloc[len(rows)*2//3]):
            k = int(selected["index"])
            end = int(choice[choice.market.eq(market) & choice["index"].eq(k)].label_index.iloc[0])
            perturbed = dict(q,C=q["C"].copy())
            perturbed["C"][k:] *= 1.21
            old = base_features[base_features["index"]<=k]
            new = market_events(perturbed,market).loc[old.index]
            # The decision at k may use close k only to schedule future entry, not immediate entry.
            pd.testing.assert_frame_equal(old.drop(columns="rule_dynamic"),new.drop(columns="rule_dynamic"))
            np.testing.assert_array_equal(old.rule_dynamic.iloc[:-1],new.rule_dynamic.iloc[:-1])
            causal.append(dict(market=market,date=q["dates"][k]))
            for duration in (2,5):
                alt, _ = assign(q,{k:duration})
                nav = full_run(market,alt)
                np.testing.assert_array_equal(nav[:k+1],baseline[:k+1])
                gain = np.log((nav[end]/nav[k])/(baseline[end]/baseline[k]))
                err = abs(gain - selected[f"log_gain_{duration}"])
                assert err < 1e-12, (market,k,duration,err)
                verified.append(dict(market=market,date=q["dates"][k],opening=duration,log_error=err))
        print("VERIFIED",market,flush=True)
    pd.DataFrame(verified).to_csv(out/"MATCHED_FULL_PARITY.csv",index=False)
    pd.DataFrame(causal).to_csv(out/"FEATURE_CAUSALITY.csv",index=False)


if __name__ == "__main__":
    main()
