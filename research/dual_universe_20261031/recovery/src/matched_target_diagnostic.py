"""Post-replay explanatory contrasts, not a new selection rule or new holdout."""
import numpy as np,pandas as pd
from common import atomic_bytes
from analysis import ROOT,monthly_returns,block_contrasts,posterior_draws,probability_record
O=ROOT/'results';rows=[]
controls=['MATURE63_H_K2_EQ_B0_R1_S1','BASE_H_K2_EQ_B0_R1_S1']
for fee in [10,30]:
    loaded={}
    for market in ['USA','EU']:
        with np.load(O/f'{market}_NAV_{fee}BP.npz',allow_pickle=False) as z:
            loaded[market]={k:z[k] for k in ['dates','configs','nav']}
    for candidate in ['MULTI_H_K2_EQ_B0_R1_S1','CONSENSUS_H_K2_EQ_B0_R1_S1']:
        for comparator in controls:
            month=pd.concat({m:monthly_returns(loaded[m],candidate)-monthly_returns(loaded[m],comparator) for m in loaded},axis=1).dropna().loc[:'2024-12']
            for block in [3,6]:
                x=block_contrasts(month,block);d=posterior_draws(x)
                rows.append({'candidate':candidate,'comparator':comparator,'fee_bps':fee,'block_months':block,'paired_blocks':len(x),'first_month':str(month.index[0]),'last_retained_month':str(month.index[len(x)*block-1]),'omitted_months':len(month)-len(x)*block,**probability_record(d),'status':'Explanatory post-replay contrast; model and prior unchanged; not new independent validation or decision retuning'})
pd.DataFrame(rows).to_csv(O/'MATCHED_TARGET_POSTERIOR_DIAGNOSTICS.csv',index=False)
print(pd.DataFrame(rows)[['candidate','comparator','fee_bps','block_months','p_US_mean_positive','p_EU_mean_positive','p_both_mean_positive','p_any_below_minus2pp']].to_string(index=False))
