"""Frozen candidate scoring and current-context historical revaluation.
All forecast candidates remain present even when their future outcome is missing.
"""
import numpy as np
import pandas as pd
from paths import P16
from context_model import PRIOR,predict_weights
from parent_chrono import anchor_scale
from revalue_memory import revalue

def build_scores(groups,frames,controls,models,omit=None,lag=False):
    outputs={};traces=[]
    for market in ('EU','USA'):
        out=controls[market][['signal_date','ticker','RETURN']].copy()
        for s in ('CURRENT','SMOOTH','FUSION'):out[s]=np.nan
        gs=[g for g in groups if g['market']==market];betas=[]
        for g in gs:
            model=models.get(g['date'].year)
            x=g['xlag'].copy() if lag else g['x'].copy()
            if omit is not None:x[omit]=0.
            b=predict_weights(model,x) if model else PRIOR.copy();betas.append(b)
            current=anchor_scale(g['z']@b,g['anchor']) if model else g['anchor'].copy()
            out.loc[g['positions'],'CURRENT']=current
            traces.append(dict(market=market,date=g['date'],beta21=b[0],beta42=b[1],beta63=b[2],
              year=g['date'].year,adapted=model is not None,penalty=model.get('penalty') if model else None))
        sm=revalue(gs,betas)
        for g,s in zip(gs,sm):
            out.loc[g['positions'],'SMOOTH']=s
            out.loc[g['positions'],'FUSION']=.475*out.loc[g['positions'],'RETURN'].to_numpy()+.525*s
        outputs[market]=out
    return outputs,pd.DataFrame(traces)
