"""Metriche economiche ricalcolate dai percorsi, tre acquisizioni complete."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd

def metrics(path):
    with np.load(path) as f: e=np.asarray(f['equity'],float);dates=f['dates']
    if e.shape!=(1,len(dates)) or not np.isfinite(e).all() or not (e>0).all():raise ValueError('Percorso non valido')
    lr=np.diff(np.log(np.column_stack([np.ones(1),e])),axis=1);r=np.expm1(lr)
    eq=np.exp(np.cumsum(lr,axis=1));peak=np.maximum.accumulate(np.column_stack([np.ones(1),eq]),axis=1)[:,1:]
    return dict(cagr=float(np.expm1(lr.sum()*252/len(dates))),maxdd=float((eq/peak-1).min()),sharpe=float(r.mean()*np.sqrt(252)/r.std(ddof=1))),dates

def selections(frames):
    if any(not frames[0]['date'].equals(f['date']) for f in frames[1:]):raise ValueError('Date selezioni diverse')
    n=len(frames[0]);a=np.column_stack([f.top1 for f in frames]);b=np.column_stack([f.top2 for f in frames])
    top1=(a!=a[:,[0]]).any(axis=1)
    ordered=top1|(b!=b[:,[0]]).any(axis=1)
    unordered=np.array([len({tuple(sorted((x,y))) for x,y in zip(a[j],b[j])})>1 for j in range(n)])
    return dict(sessions=n,top1_any_count=int(top1.sum()),top1_any_fraction=float(top1.mean()),
        top2_ordered_any_count=int(ordered.sum()),top2_ordered_any_fraction=float(ordered.mean()),
        top2_unordered_any_count=int(unordered.sum()),top2_unordered_any_fraction=float(unordered.mean()),
        interpretation='Almeno una delle tre acquisizioni differisce; frequenza giornaliera di decisioni mensili ripetute, non campioni indipendenti')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    rows={s:[] for s in ('baseline','candidate')};leaders={s:[] for s in rows};support=None;verification=[];hashes={}
    for i in (1,2,3):
        root=Path(a.inputs)/f'paper-ltr-replay-r{i}'
        result=json.loads((root/'RESULT.json').read_text())
        if result['status']!='PAPER_LTR_CACHE_REPLAY_COMPLETE' or result['repeat']!=i or result['audit']['baseline_replay']['PASS'] is not True:raise ValueError('Replay non verificato')
        for scope,subdir in (('baseline','baseline_control'),('candidate','candidate')):
            path=root/subdir/'FULL_UNIVERSE_PATH.npz';actual,dates=metrics(path)
            if support is None:support=dates
            if not np.array_equal(support,dates):raise ValueError('Calendari non identici')
            expected=result[scope]['v2_full_universe'];differences={m:abs(actual[m]-expected[m]) for m in actual}
            if max(differences.values())>1e-12:raise ValueError('Metriche non riproducibili dal percorso')
            verification.append(dict(repeat=i,scope=scope,absolute_metric_differences=differences))
            rows[scope].append(dict(repeat=i,**expected));leaders[scope].append(pd.read_csv(root/subdir/'DAILY_LEADERS.csv'))
            hashes[f'{i}/{scope}/NPZ']=hashlib.sha256(path.read_bytes()).hexdigest()
    dispersion={scope:dict(mean_cagr=float(np.mean([r['cagr'] for r in rr])),cagr_span_pp=float(np.ptp([r['cagr'] for r in rr])*100),
        cagr_population_std_pp=float(np.std([r['cagr'] for r in rr])*100),mean_maxdd=float(np.mean([r['maxdd'] for r in rr])),
        mean_sharpe=float(np.mean([r['sharpe'] for r in rr]))) for scope,rr in rows.items()}
    select={scope:selections(frames) for scope,frames in leaders.items()}
    result=dict(status='PAPER_LTR_THREE_SOURCE_ECONOMIC_COMPARISON_COMPLETE',**rows,dispersion=dispersion,selection_disagreement=select,
        independent_path_metric_verification=verification,equity_path_sha256=hashes,source_fit_repeated=False,
        production_adoption=False,interpretation='Confronto di ricerca sullo stesso mercato, tre revisioni correlate; nessuna garanzia sul massimo CAGR futuro.')
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
