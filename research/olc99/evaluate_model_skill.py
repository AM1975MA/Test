#!/usr/bin/env python3
"""Independent hold-out-in-time descriptive ranking diagnostics; no refit."""
from pathlib import Path
import pandas as pd,numpy as np,json
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score
R=Path(__file__).resolve().parent;O=R/'results'
panel=pd.read_csv(O/'OLC99_TOP10_ECONOMIC_PANEL.csv.gz')
sel=pd.read_csv(O/'OLC99_SELECTIONS.csv')
score=pd.read_csv(O/'OLC99_STATIC_TOP2_OUTCOMES.csv')
rows=[]
for (m,j),g in panel.groupby(['market','event_j']):
 if j<24 or j==89 or not g.future_logr.notna().all():continue
 vals=g.future_logr.to_numpy(float)
 context=g.TOP2_CONTEXT_REVALUE_FUSION.to_numpy(float)
 pred=g.economic_pred.to_numpy(float)
 if not np.isfinite(pred).all():continue
 top=g.nlargest(2,'future_logr').ticker.tolist()
 # The TOP2 contextual score is the actual native baseline score on this shortlist.
 r={"market":m,'event_j':j,'signal_date':g.signal_date.iloc[0],
    'n_candidates':len(g),'spearman_ctx':float(spearmanr(context,vals).statistic),
    'spearman_econ':float(spearmanr(pred,vals).statistic),
    'ndcg2_ctx':float(ndcg_score([g.future_logr.rank(pct=True).to_numpy()],[context],k=2)),
    'ndcg2_econ':float(ndcg_score([g.future_logr.rank(pct=True).to_numpy()],[pred],k=2)),
    'oracle_top2_logr':float(g.nlargest(2,'future_logr').future_logr.mean())}
 for a in ['E0_CONTEXT','E1_ANCHORED_20','E2_ANCHORED_35']:
  pair=sel[(sel.market==m)&(sel.event_j==j)&(sel.arm==a)].iloc[0]
  got=g[g.ticker.isin([pair.ticker1,pair.ticker2])]
  r[a+'_payoff_logr']=float(got.future_logr.mean())
  r[a+'_oracle_gap_logpp']=100*(r['oracle_top2_logr']-r[a+'_payoff_logr'])
  r[a+'_oracle_hit']=int(pair.ticker1 in top)+int(pair.ticker2 in top)
 rows.append(r)
d=pd.DataFrame(rows);d.to_csv(O/'OLC99_ECONOMIC_SKILL.csv',index=False)
qa=[]
for m,g in d.groupby('market'):
 qa.append({'market':m,'n_evaluable':len(g),
 'ctx_spearman':float(g.spearman_ctx.mean()),'econ_spearman':float(g.spearman_econ.mean()),
 'ctx_ndcg2':float(g.ndcg2_ctx.mean()),'econ_ndcg2':float(g.ndcg2_econ.mean()),
 'ctx_oracle_gap_logpp':float(g.E0_CONTEXT_oracle_gap_logpp.mean()),
 'E1_oracle_gap_logpp':float(g.E1_ANCHORED_20_oracle_gap_logpp.mean()),
 'E2_oracle_gap_logpp':float(g.E2_ANCHORED_35_oracle_gap_logpp.mean()),
 'ctx_top2_oracle_hit_pct':float(g.E0_CONTEXT_oracle_hit.sum()/(2*len(g))),
 'E1_top2_oracle_hit_pct':float(g.E1_ANCHORED_20_oracle_hit.sum()/(2*len(g)))})
pd.DataFrame(qa).to_csv(O/'OLC99_ECONOMIC_SKILL_SUMMARY.csv',index=False)
print(pd.DataFrame(qa).to_string(index=False))