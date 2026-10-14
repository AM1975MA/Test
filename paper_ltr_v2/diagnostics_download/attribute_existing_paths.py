"""Read-only attribution of archived wealth paths; no fits or backtest execution.

Run with the bundled Python; all outputs stay beside this script.
Positive gap means left portfolio outperformed right portfolio.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
ROOT = OUT.parents[1]
INPUT = ROOT / '_evidence/listnet-v2-BUDGET300/_replays'
spec = importlib.util.spec_from_file_location('existing_summary', ROOT/'paper_ltr_v2/summarize_replay.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


def records(frame):
    return json.loads(frame.to_json(orient='records', date_format='iso', double_precision=15))


def read(repeat, kind):
    folder = INPUT / f'v2replay-BUDGET300-r{repeat}' / kind
    path = folder/'FULL_UNIVERSE_PATH.npz'
    metrics, dates = summary.metrics(path)
    archived = json.loads((folder/'RESULT.json').read_text())['v2_full_universe']
    for key, value in metrics.items():
        assert abs(value-archived[key]) < 1e-12, (folder,key)
    leaders = summary.checked_leaders(folder/'DAILY_LEADERS.csv', dates).set_index('date')
    with np.load(path, allow_pickle=False) as z:
        equity = z['equity'][0]
        frame = leaders.assign(log_return=np.diff(np.r_[0., np.log(equity)]),
                               weight1=z['weight1'][0], turnover=z['turnover'][0],
                               alt_idx=z['alt_idx'][0], d1=z['d1'][0], d2=z['d2'][0])
        for col, tickercol in [('d1','top1'),('d2','top2')]:
            valid=frame[frame[col]>=0]
            assert valid.groupby(col)[tickercol].nunique().max()==1
        assert frame.log_return.iloc[-1]==0, 'Terminal mark must not add a return'
        schema = {k: {'shape':list(z[k].shape),'dtype':str(z[k].dtype)} for k in z.files}
    hashes = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (path,folder/'DAILY_LEADERS.csv')}
    return frame, metrics, schema, hashes


def attribute(left, right, name):
    common = left.index.intersection(right.index).sort_values()
    a, b = left.loc[common], right.loc[common]
    gap = a.log_return-b.log_return
    f = pd.DataFrame({'date':common, 'log_gap':gap.to_numpy(),
                      'left_top1':a.top1.to_numpy(), 'left_top2':a.top2.to_numpy(),
                      'right_top1':b.top1.to_numpy(), 'right_top2':b.top2.to_numpy(),
                      'left_weight1':a.weight1.to_numpy(), 'right_weight1':b.weight1.to_numpy(),
                      'left_turnover':a.turnover.to_numpy(), 'right_turnover':b.turnover.to_numpy()})
    f['month']=f.date.dt.strftime('%Y-%m')
    f['same_top1']=f.left_top1.eq(f.right_top1)
    f['same_ordered_pair']=f.same_top1 & f.left_top2.eq(f.right_top2)
    f['same_unordered_pair']=[set(x)==set(y) for x,y in zip(zip(f.left_top1,f.left_top2),zip(f.right_top1,f.right_top2))]
    f['same_weight1']=np.isclose(a.weight1.to_numpy(),b.weight1.to_numpy(),rtol=0,atol=1e-12)
    f['same_alt_idx']=a.alt_idx.to_numpy()==b.alt_idx.to_numpy()
    f['same_pair_weight_alt']=f.same_ordered_pair & f.same_weight1 & f.same_alt_idx
    f['left_rebalance_log_cost']=np.log1p(-.001*f.left_turnover)
    f['right_rebalance_log_cost']=np.log1p(-.001*f.right_turnover)
    f['rebalance_log_cost_gap']=f.left_rebalance_log_cost-f.right_rebalance_log_cost
    monthly=f.groupby('month',as_index=False).agg(log_gap=('log_gap','sum'),sessions=('date','size'),
                                                  different_top1=('same_top1',lambda s:int((~s).sum())))
    # Partition by complete observed selection tuple: exact additive grouping,
    # not constituent P&L, which is unavailable from these path artifacts.
    pair=f.groupby(['left_top1','left_top2','right_top1','right_top2'],as_index=False).agg(
        log_gap=('log_gap','sum'),sessions=('date','size'),months=('month','nunique'))
    groups=f.groupby('same_ordered_pair',as_index=False).agg(log_gap=('log_gap','sum'),sessions=('date','size'))
    richer_groups=f.groupby(['same_ordered_pair','same_weight1','same_alt_idx'],as_index=False).agg(
        log_gap=('log_gap','sum'),sessions=('date','size'))
    total=float(gap.sum()); positive=float(gap.clip(lower=0).sum()); negative=float(gap.clip(upper=0).sum())
    concentration={}
    for label, values in [('days',f.log_gap),('months',monthly.log_gap)]:
        positive_values=values[values>0].sort_values(ascending=False)
        concentration[label]={str(n):{'signed_gap':float(positive_values.head(n).sum()),
             'fraction_net_gap':float(positive_values.head(n).sum()/total) if total else None,
             'fraction_positive_gap':float(positive_values.head(n).sum()/positive_values.sum()) if positive_values.sum() else None}
             for n in (1,5,10,20)}
    f.to_csv(OUT/f'{name}_daily.csv',index=False,float_format='%.17g')
    monthly.to_csv(OUT/f'{name}_monthly.csv',index=False,float_format='%.17g')
    pair.to_csv(OUT/f'{name}_selection_groups.csv',index=False,float_format='%.17g')
    assert abs(float(monthly.log_gap.sum())-total)<1e-12
    assert abs(float(pair.log_gap.sum())-total)<1e-12
    terminal_identity_error = abs(total - float(np.log(np.exp(left.log_return.sum())/np.exp(right.log_return.sum())))) if len(common)==len(left)==len(right) else None
    if terminal_identity_error is not None: assert terminal_identity_error < 1e-12
    return {'common_sessions':len(common),'left_only':len(left)-len(common),'right_only':len(right)-len(common),
        'monthly_and_selection_partition_residual_below':1e-12,'terminal_log_ratio_residual':terminal_identity_error,
        'start':str(common[0].date()),'end':str(common[-1].date()),'total_logwealth_gap':total,
        'wealth_ratio_on_common_returns':float(np.exp(total)), 'positive_daily_gap_sum':positive,
        'negative_daily_gap_sum':negative,'disagreement':{c: {'sessions':int((~f[c]).sum()),'fraction':float((~f[c]).mean())}
        for c in ('same_top1','same_ordered_pair','same_unordered_pair')},'same_pair_partition':records(groups),
        'same_pair_weight_alt_partition':records(richer_groups),
        'rebalance_cost_component':{'cost_rate':.001,'log_gap':float(f.rebalance_log_cost_gap.sum()),
            'remaining_log_gap':total-float(f.rebalance_log_cost_gap.sum()),
            'interpretation':'Only explicit rebalance multiplier 1-cost*T; remaining gap includes market P&L, stops, state, other fees and interactions, not pure gross return.'},
        'top_positive_months':records(monthly.nlargest(10,'log_gap')),'top_negative_months':records(monthly.nsmallest(10,'log_gap')),
        'top_positive_dates':records(f.nlargest(10,'log_gap')),'top_negative_dates':records(f.nsmallest(10,'log_gap')),
        'top_positive_selection_groups':records(pair.nlargest(10,'log_gap')),
        'top_negative_selection_groups':records(pair.nsmallest(10,'log_gap')),'concentration':concentration}


def main():
    frames={}; metrics={}; hashes={}; schemas={}
    for kind in ('baseline_control','candidate'):
        for r in (1,2,3):
            key=f'{kind}_r{r}'
            frames[key],metrics[key],schemas[key],h=read(r,kind);hashes.update(h)
    ids={}
    for f in frames.values():
        for col,tickercol in [('d1','top1'),('d2','top2')]:
            for ident,ticker in zip(f[col],f[tickercol]):
                if ident<0:continue
                if ident in ids:assert ids[ident]==ticker
                ids[ident]=ticker
    for relative in ('paper_ltr_v2/summarize_replay.py','vendor/p45/v2_stage19_kernel.py',
                     'holdout70/v2_canonical_same_source_compare.py',
                     'forensics_v1/results/EXECUTION_ABLATION.json'):
        hashes[relative]=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    common=frames[next(iter(frames))].index
    for f in frames.values():common=common.intersection(f.index)
    comparisons={}
    for r in (1,2,3):
        name=f'baseline_minus_budget300_r{r}'
        comparisons[name]=attribute(frames[f'baseline_control_r{r}'],frames[f'candidate_r{r}'],name)
    across={}
    for kind in ('baseline_control','candidate'):
        across[kind]=summary.selections([frames[f'{kind}_r{r}'].reset_index()[['date','top1','top2']] for r in (1,2,3)])
        for a,b in ((2,1),(3,1),(3,2)):
            name=f'{kind}_r{a}_minus_r{b}'
            comparisons[name]=attribute(frames[f'{kind}_r{a}'],frames[f'{kind}_r{b}'],name)
    result={'method':'sum of observed daily log-return differences, derived from stored equity (initial wealth 1)',
        'common_sessions_all_six':len(common),'all_six_identical_calendars':all(f.index.equals(common) for f in frames.values()),
        'metrics':metrics,'selection_disagreement_across_downloads':across,'comparisons':comparisons,
        'schema':schemas,'input_sha256':hashes,
        'timing_audit':{'source':'vendor/p45/v2_stage19_kernel.py:160-215; holdout70/v2_canonical_same_source_compare.py:246-251',
            'equity_at_index_k':'marked at next open k+1 after executing targets at open k and stops during k',
            'leaders_at_index_k':'target allocation consumed at k; no additional execution lag',
            'interval_label':'date is execution/interval-start date, not ending valuation date',
            'last_row':'terminal open mark repeated, zero return, d1/d2=-1 may produce spurious CSV last ticker; no economic gap'},
        'limitations':[
          'Selection-tuple grouping is an exact partition of portfolio log gaps, not causal ticker P&L attribution.',
          'Same leaders can have different weight, return inputs, costs or market state; these causes are not identified here.',
          'No constituent daily returns or parquet features were read; no price/feature/solver causal decomposition.',
          'Correlated sessions repeat monthly decisions; no independent-sample inference or promotion test.',
          'No fits, market downloads, or backtests run. Existing equity paths alone provide return evidence.']}
    (OUT/'ATTRIBUTION.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    concise={k:v for k,v in result.items() if k not in ('comparisons','schema')}
    keep=('total_logwealth_gap','disagreement','same_pair_partition',
          'same_pair_weight_alt_partition','rebalance_cost_component')
    concise['comparisons']={name:{k:value[k] for k in keep} for name,value in comparisons.items()}
    (OUT/'ATTRIBUTION_SUMMARY.json').write_text(json.dumps(concise,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'metrics':metrics,'across':across,'comparisons':{k:{x:v[x] for x in ('total_logwealth_gap','disagreement','top_positive_months','concentration')} for k,v in comparisons.items()}},indent=2))


if __name__=='__main__':main()
