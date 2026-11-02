"""Registered post-observation score-only extension; no additional fitting."""
import json,numpy as np,pandas as pd
from experiment import ROOT,MARKETS,LEARNED,NULLS,load_groups,readcsv,dump
from context_model import PRIOR,predict_weights
from revalue_memory import revalue

def main():
    groups,frames,controls=load_groups();models={int(k):v for k,v in json.loads((ROOT/'results/ANNUAL_MODELS.json').read_text()).items()}
    checks=[]
    for market in MARKETS:
        out=readcsv(ROOT/f'results/{market}_SCORES.csv.gz');gs=[g for g in groups if g['market']==market]
        for v in LEARNED+NULLS:
            name=v+'_REVALUE';betas=[]
            for g in gs:
                p=models.get(g['date'].year,{}).get(v)
                betas.append(predict_weights(p,g['x']) if p else PRIOR.copy())
            sm=revalue(gs,betas)
            out[name+'_CURRENT']=out[v+'_CURRENT'];out[name+'_SMOOTH']=np.nan;out[name+'_FUSION']=np.nan
            for g,a in zip(gs,sm):
                out.loc[g['positions'],name+'_SMOOTH']=a
                out.loc[g['positions'],name+'_FUSION']=.475*out.loc[g['positions'],'RETURN'].to_numpy()+.525*a
            np.testing.assert_array_equal(out[name+'_CURRENT'],out[v+'_CURRENT'])
            checks.append(dict(market=market,variant=name,current_unchanged=True,signals=len(gs)))
        out.to_csv(ROOT/f'results/{market}_SCORES.csv.gz',index=False,compression='gzip')
    dump(ROOT/'results/REVALUE_COMPLETE.json',dict(new_models=0,checks=checks))
if __name__=='__main__':main()
