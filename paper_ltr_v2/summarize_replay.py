"""Confronto economico indipendente: BASE, ListNet100 e due ricette registrate."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd


def checked_calendar(values):
    dates=pd.DatetimeIndex(pd.to_datetime(values,errors='raise'))
    if len(dates)<2 or dates.isna().any() or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('Calendario vuoto, nullo, duplicato o non ordinato')
    if not dates.equals(dates.normalize()):raise ValueError('Calendario giornaliero con orari inattesi')
    return dates


def metrics(path):
    with np.load(path,allow_pickle=False) as z:
        dates=checked_calendar(z['dates']);equity=np.asarray(z['equity'],float)
    if equity.shape!=(1,len(dates)) or not np.isfinite(equity).all() or not (equity>0).all():
        raise ValueError('Percorso equity non valido')
    lr=np.diff(np.log(np.column_stack([np.ones(1),equity])),axis=1);returns=np.expm1(lr)
    curve=np.exp(np.cumsum(lr,axis=1));peak=np.maximum.accumulate(np.column_stack([np.ones(1),curve]),axis=1)[:,1:]
    sd=float(returns.std(ddof=1))
    if sd==0 and float(returns.mean())!=0:raise ValueError('Sharpe indefinito: rendimenti costanti non nulli')
    return dict(cagr=float(np.expm1(lr.sum()*252/len(dates))),maxdd=float((curve/peak-1).min()),
                sharpe=0. if sd==0 else float(returns.mean()*np.sqrt(252)/sd),
                terminal_equity=float(equity[0,-1])),dates


def checked_leaders(path,dates):
    frame=pd.read_csv(path)
    if not set(('date','top1','top2')).issubset(frame):raise ValueError('Colonne leader mancanti')
    calendar=checked_calendar(frame['date'])
    if not calendar.equals(dates):raise ValueError('Leader CSV non allineati alle date NPZ')
    if frame[['top1','top2']].isna().any().any():raise ValueError('Leader mancanti')
    for col in ('top1','top2'):
        if frame[col].astype(str).str.strip().eq('').any():raise ValueError('Ticker vuoto')
    frame['date']=calendar
    return frame


def selections(frames):
    if len(frames)!=3 or any(not frames[0].date.equals(f.date) for f in frames[1:]):
        raise ValueError('Tre acquisizioni con calendari identici richieste')
    a=np.column_stack([f.top1.to_numpy(str) for f in frames]);b=np.column_stack([f.top2.to_numpy(str) for f in frames])
    top1=(a!=a[:,[0]]).any(axis=1);ordered=top1|(b!=b[:,[0]]).any(axis=1)
    unordered=np.array([len({tuple(sorted((x,y))) for x,y in zip(aa,bb)})>1 for aa,bb in zip(a,b)])
    pairs={}
    for i,j in ((0,1),(0,2),(1,2)):
        t1=a[:,i]!=a[:,j];t2=b[:,i]!=b[:,j]
        pairs[f'{i+1}-{j+1}']=dict(top1_fraction=float(t1.mean()),top2_ordered_fraction=float((t1|t2).mean()))
    return dict(sessions=len(a),top1_any_count=int(top1.sum()),top1_any_fraction=float(top1.mean()),
                top2_ordered_any_count=int(ordered.sum()),top2_ordered_any_fraction=float(ordered.mean()),
                top2_unordered_any_count=int(unordered.sum()),top2_unordered_any_fraction=float(unordered.mean()),
                pairwise=pairs,interpretation='Sedute correlate con decisioni mensili ripetute; tre revisioni dello stesso mercato.')


def dispersion(rows):
    c=np.array([r['cagr'] for r in rows])
    return dict(mean_cagr=float(c.mean()),cagr_span_pp=float(np.ptp(c)*100),cagr_population_std_pp=float(c.std()*100),
                mean_maxdd=float(np.mean([r['maxdd'] for r in rows])),mean_sharpe=float(np.mean([r['sharpe'] for r in rows])))


def gates(rows,base,disp,base_disp,selection,base_selection):
    checks=dict(mean_cagr_ge95pct=disp['mean_cagr']>=.95*base_disp['mean_cagr'],
        each_cagr_ge95pct=all(r['cagr']>=.95*b['cagr'] for r,b in zip(rows,base)),
        mean_sharpe_ge95pct=disp['mean_sharpe']>=.95*base_disp['mean_sharpe'],
        mean_maxdd_within2pp=disp['mean_maxdd']>=base_disp['mean_maxdd']-.02,
        each_maxdd_within2pp=all(r['maxdd']>=b['maxdd']-.02 for r,b in zip(rows,base)),
        cagr_span_reduced25pct=disp['cagr_span_pp']<=.75*base_disp['cagr_span_pp'],
        top1_disagreement_reduced25pct=selection['top1_any_fraction']<=.75*base_selection['top1_any_fraction'],
        top2_ordered_not_worse=selection['top2_ordered_any_fraction']<=base_selection['top2_ordered_any_fraction'])
    pareto=all(r['cagr']>=b['cagr'] and r['maxdd']>=b['maxdd'] and r['sharpe']>=b['sharpe'] for r,b in zip(rows,base))
    return dict(checks=checks,economic_screen_PASS=all(checks.values()),each_source_cagr_dd_sharpe_nondominated=pareto,
                statistical_noninferiority_proven=False,production_adoption=False)


def summarize(inputs,v1_inputs,variants=('BUDGET300','LINEAR')):
    rows={s:[] for s in ('BASE','LISTNET100',*variants)};leaders={s:[] for s in rows}
    support=None;verification=[];hashes={};baseline_frames={};baseline_paths={};repair_provenance={}
    def read(root,result,scope,folder,label,repeat):
        nonlocal support
        expected=result[scope]
        if expected['candidate_count']!=149 or expected['sessions']!=2366:raise ValueError('Universo/calendario canonicale diverso')
        path=root/folder/'FULL_UNIVERSE_PATH.npz';actual,dates=metrics(path)
        if support is None:support=dates
        if not support.equals(dates):raise ValueError('Calendari replay non identici')
        if str(dates[0].date())!=expected['start'] or str(dates[-1].date())!=expected['end']:raise ValueError('Estremi calendario non coerenti')
        differences={m:abs(actual[m]-expected['v2_full_universe'][m]) for m in actual}
        if max(differences.values())>1e-12:raise ValueError('Metriche non riproducibili dal percorso')
        frame=checked_leaders(root/folder/'DAILY_LEADERS.csv',dates)
        verification.append(dict(repeat=repeat,variant=label,absolute_metric_differences=differences,leader_npz_dates_exact=True))
        hashes[f'{label}/{repeat}/NPZ']=hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[f'{label}/{repeat}/leaders']=hashlib.sha256((root/folder/'DAILY_LEADERS.csv').read_bytes()).hexdigest()
        return dict(repeat=repeat,**expected['v2_full_universe']),frame,path
    for i in (1,2,3):
        root=Path(v1_inputs)/f'paper-ltr-replay-r{i}';result=json.loads((root/'RESULT.json').read_text())
        if result.get('status')!='PAPER_LTR_CACHE_REPLAY_COMPLETE' or result['repeat']!=i or result['audit']['baseline_replay']['PASS'] is not True:
            raise ValueError('Replay storico ListNet non verificato')
        for label,scope,folder in [('BASE','baseline','baseline_control'),('LISTNET100','candidate','candidate')]:
            row,frame,path=read(root,result,scope,folder,label,i);rows[label].append(row);leaders[label].append(frame)
            if label=='BASE':baseline_frames[i]=frame;baseline_paths[i]=path
    for variant in variants:
        for i in (1,2,3):
            root=Path(inputs)/f'v2replay-{variant}-r{i}';result=json.loads((root/'RESULT.json').read_text())
            if variant=='LINEAR_NUMERICAL_REPAIR':
                proof=result.get('numerical_repair')
                if not proof or not proof.get('separate_protocol_sha256') or not proof.get('repair_source_sha256'):
                    raise ValueError('Provenienza riparazione numerica mancante')
                if variant in repair_provenance and repair_provenance[variant]!=proof:
                    raise ValueError('Protocolli riparazione diversi tra acquisizioni')
                repair_provenance[variant]=proof
            if (result.get('status')!='PAPER_LTR_V2_CACHE_REPLAY_COMPLETE' or result.get('variant')!=variant
                or result.get('repeat')!=i or result['audit']['baseline_replay']['PASS'] is not True
                or result['audit']['input_linkage']['PASS'] is not True):raise ValueError('Replay/chiusura input V2 non verificato')
            _,frame,path=read(root,result,'baseline','baseline_control',variant+'_BASE_CONTROL',i)
            pd.testing.assert_frame_equal(frame,baseline_frames[i],check_exact=True)
            with np.load(path,allow_pickle=False) as actual,np.load(baseline_paths[i],allow_pickle=False) as expected:
                if set(actual.files)!=set(expected.files):raise ValueError('Schema percorso controllo diverso')
                for key in expected.files:
                    aa,bb=actual[key],expected[key]
                    if aa.shape!=bb.shape or aa.dtype!=bb.dtype:raise ValueError('Schema array controllo diverso')
                    if np.issubdtype(aa.dtype,np.floating):
                        if not np.allclose(aa,bb,rtol=0,atol=1e-12,equal_nan=True):raise ValueError('Percorso controllo diverso')
                    elif not np.array_equal(aa,bb):raise ValueError('Decisioni controllo diverse')
            row,frame,_=read(root,result,'candidate','candidate',variant,i);rows[variant].append(row);leaders[variant].append(frame)
    disp={s:dispersion(rr) for s,rr in rows.items()};select={s:selections(ff) for s,ff in leaders.items()}
    screens={s:gates(rows[s],rows['BASE'],disp[s],disp['BASE'],select[s],select['BASE']) for s in rows if s!='BASE'}
    return dict(status='PAPER_LTR_V2_ECONOMIC_COMPARISON_COMPLETE',variants_evaluated=list(variants),
        both_new_variants_completed=set(variants)=={'BUDGET300','LINEAR'},numerical_repair=repair_provenance,metrics=rows,dispersion=disp,
        selection_disagreement=select,economic_screens=screens,independent_path_metric_verification=verification,
        evidence_sha256=hashes,all_calendars_identical=True,source_fit_repeated=False,production_adoption=False,
        interpretation='Sviluppo retrospettivo: nessuna selezione di ricetta mediante CAGR outer; esiti negativi conservati.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--v1-inputs');ap.add_argument('--out',required=True)
    ap.add_argument('--v1-only',action='store_true');ap.add_argument('--variants',nargs='+',choices=['BUDGET300','LINEAR','LINEAR_NUMERICAL_REPAIR','LINEAR_MONTHLY'])
    args=ap.parse_args()
    if args.v1_only:variants=();v1_inputs=args.inputs
    else:
        if not args.v1_inputs:ap.error('--v1-inputs richiesto per il confronto nuovo')
        v1_inputs=args.v1_inputs
        variants=tuple(args.variants or [v for v in ('BUDGET300','LINEAR') if any(Path(args.inputs).glob(f'v2replay-{v}-r*'))])
        if not variants:raise ValueError('Nessun replay candidato disponibile')
    result=summarize(args.inputs,v1_inputs,variants)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
