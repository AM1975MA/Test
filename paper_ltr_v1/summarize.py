"""Confronto appaiato della fattibilità ListNet; nessun nuovo fit BASE."""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from compact21_predictive_v2.metrics import evaluate, paired_compare
KEYS=['vintage','signal_date','ticker']

def ordered(frame):
    f=frame.copy(); f['vintage']=f.vintage.astype(str)
    f['signal_date']=pd.to_datetime(f.signal_date)
    if f.duplicated(KEYS).any(): raise ValueError('Chiavi duplicate')
    return f.sort_values(KEYS).reset_index(drop=True)

def common_truth(frame,truth):
    f=ordered(frame); truth=ordered(truth)
    outcomes=truth[truth.vintage=='2'].drop(columns=['vintage','pred'])
    z=f[KEYS+['pred']].merge(outcomes,on=['signal_date','ticker'],how='left',validate='many_to_one',indicator=True)
    if not z['_merge'].eq('both').all(): raise ValueError('Esiti comuni mancanti')
    return z.drop(columns='_merge')

def stability(frame):
    f=ordered(frame); rows=[]
    for date,g in f.groupby('signal_date',sort=True):
        pieces={i:g[g.vintage==str(i)].sort_values('ticker').reset_index(drop=True) for i in (1,2,3)}
        if any(not pieces[1].ticker.equals(pieces[i].ticker) for i in (2,3)):
            raise ValueError('Supporto nativo non identico: nessuna intersezione silenziosa')
        ranks={i:pieces[i].pred.rank(method='average',pct=True).to_numpy() for i in pieces}
        leaders={i:pieces[i].sort_values(['pred','ticker'],ascending=[False,True],kind='stable').ticker.tolist()[:2] for i in pieces}
        for i,j in ((1,2),(1,3),(2,3)):
            rows.append(dict(signal_date=str(date.date()),pair=f'{i}-{j}',rank_mad=float(np.abs(ranks[i]-ranks[j]).mean()),
                top1_disagreement=float(leaders[i][0]!=leaders[j][0]),ordered_top2_disagreement=float(leaders[i]!=leaders[j]),
                unordered_top2_disagreement=float(set(leaders[i])!=set(leaders[j]))))
    r=pd.DataFrame(rows); fields=['rank_mad','top1_disagreement','ordered_top2_disagreement','unordered_top2_disagreement']
    return dict(queries=int(r.signal_date.nunique()),estimand='Media delle tre coppie, date equiponderate; non disaccordo any fra tre',
        aggregate={m:float(r[m].mean()) for m in fields},by_pair={pair:{m:float(g[m].mean()) for m in fields} for pair,g in r.groupby('pair')},per_date=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--baseline',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    c=Path(a.candidate);b=Path(a.baseline)
    cr=json.loads((c/'RESULT.json').read_text());br=json.loads((b/'RESULT.json').read_text())
    if cr.get('status')!='PAPER_LTR_V1_COMPLETE' or cr.get('ALL_MATURITY_PASS') is not True:raise ValueError('Candidato non completo o maturazione fallita')
    for directory,result in ((c,cr),(b,br)):
        for name in ('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet'):
            if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=result['files_sha256'][name]:raise ValueError('Hash predizioni non corrispondente')
    if cr['input_sha256']!=br['input_sha256']:raise ValueError('Identità input diversa')
    cn=pd.read_parquet(c/'NATIVE_PREDICTIONS.parquet');bn=pd.read_parquet(b/'NATIVE_PREDICTIONS.parquet')
    cc=pd.read_parquet(c/'COMMON_PREDICTIONS.parquet');bc=pd.read_parquet(b/'COMMON_PREDICTIONS.parquet')
    for x,y in ((cn,bn),(cc,bc)):
        if not ordered(x)[KEYS].equals(ordered(y)[KEYS]):raise ValueError('Copertura diversa dalla baseline')
    qualities={};stabs={}
    for label,native,common in (('LISTNET',cn,cc),('BASE',bn,bc)):
        qualities[label]=evaluate(common_truth(native,bn),quality_exit_cutoff='2026-07-01')
        stabs[label]={'native':stability(native),'common':stability(common)}
    cq=qualities['LISTNET']['aggregate_by_date'];bq=qualities['BASE']['aggregate_by_date']
    cs=stabs['LISTNET'];bs=stabs['BASE']
    reductions={scope:{metric:float(1-cs[scope]['aggregate'][metric]/bs[scope]['aggregate'][metric]) if bs[scope]['aggregate'][metric] else None for metric in ('rank_mad','top1_disagreement')} for scope in ('common','native')}
    checks={
        'rank_mad_common_reduction_ge25pct':reductions['common']['rank_mad']>=.25,
        'native_top1_reduction_ge25pct':reductions['native']['top1_disagreement']>=.25,
        'native_ordered_top2_not_worse':cs['native']['aggregate']['ordered_top2_disagreement']<=bs['native']['aggregate']['ordered_top2_disagreement'],
        'top1_quality_ge95pct':cq['top1_realized_percentile']>=.95*bq['top1_realized_percentile'],
        'ndcg5_ge95pct':cq['ndcg5']>=.95*bq['ndcg5'],
        'precision5_ge95pct':cq['top5_overlap']>=.95*bq['top5_overlap'],
        'independent_refit_2017_repeat2_exact':bool(cr.get('DETERMINISM_2017_REPEAT2_PASS',False)),
    }
    paired=paired_compare(qualities['LISTNET'],qualities['BASE'],n_bootstrap=20000,seed=20261012,block_lengths=(3,1,6))
    paired['lower98_75_interpretation']='Limite descrittivo aggiuntivo; non correzione per la storia complessiva dei test. Un solo nuovo candidato preregistrato.'
    result=dict(status='PAPER_LTR_FEASIBILITY_COMPLETE',candidate='LISTNET_DECILE_64',checks=checks,
        ADVANCE_FULL_REPLAY=all(checks.values()),input_sha256=cr['input_sha256'],quality_common_outcomes=qualities,stability=stabs,
        reductions=reductions,paired_quality=paired,baseline_fit_repeated=False,portfolio_metrics_evaluated=False,
        interpretation='Fattibilità del trasferimento ListNet a Compact21; nessuna replica CRSP né prova di robustezza universale. Gate congiunto, nessuna promozione automatica.',
        evidence_sha256={f'{label}/{name}':hashlib.sha256((path/name).read_bytes()).hexdigest() for label,path in (('candidate',c),('baseline',b)) for name in ('RESULT.json','NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet')})
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(checks=checks,quality_BASE=bq,quality_LISTNET=cq,reductions=reductions,ADVANCE_FULL_REPLAY=result['ADVANCE_FULL_REPLAY']),indent=2))

if __name__=='__main__':main()
