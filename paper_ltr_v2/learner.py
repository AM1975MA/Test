"""Due interventi registrati; la ricetta v1 è caricata senza modificarla."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path
import numpy as np
from paper_ltr_v1 import learner as V1

LINEAR_RECIPE=dict(l2=.001, max_iterations=2000, gradient_tolerance=1e-7,
                   memory=10, armijo=1e-4, max_line_search=50,
                   bias=False, solver='numpy_lbfgs', dtype='float64')
PARAMETERS=('W1','b1','W2','b2','W3','b3')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_checkpoint(path, expected_hash):
    if not expected_hash or sha(path)!=expected_hash:
        raise ValueError('Checkpoint originale modificato')
    with np.load(path,allow_pickle=False) as saved:
        return {k:saved[k].copy() for k in saved.files}

def check_prefix(extended, original):
    if any(extended[k]!=original[k] for k in ('initial_train_loss','initial_validation_loss')):
        raise ValueError('Loss iniziale diversa da v1')
    if extended['history'][:len(original['history'])]!=original['history']:
        raise ValueError('Prefisso delle epoche diverso da v1')
    return True

def reuse_integrity(seeds):
    return all(s.get('prefix100_PASS') and (s.get('new_fit_executed') or s.get('reuse_original_PASS')) for s in seeds)

def linear_objective(w,x,labels,groups):
    loss,ds=V1.listnet_loss_gradient(x@w,labels,groups)
    penalty=LINEAR_RECIPE['l2']
    return loss+.5*penalty*float(w@w),x.T@ds+penalty*w

def solve_linear(x,labels,groups):
    """L-BFGS con Armijo; il residuo certifica l'arresto, non il rendimento."""
    w=np.zeros(x.shape[1]); value,gradient=linear_objective(w,x,labels,groups)
    initial=value; pairs=[]; evaluations=1
    for iteration in range(LINEAR_RECIPE['max_iterations']+1):
        residual=float(np.max(np.abs(gradient)))
        if residual<=LINEAR_RECIPE['gradient_tolerance']:
            return w,dict(solver=LINEAR_RECIPE.copy(),iterations=iteration,
                          evaluations=evaluations,initial_objective=initial,
                          final_objective=value,gradient_inf_norm=residual,
                          stationary_PASS=True,stop_reason='gradient_tolerance')
        if iteration==LINEAR_RECIPE['max_iterations']:
            raise ValueError(f'Lineare non convergente: residuo {residual}')
        q=gradient.copy(); alphas=[]
        for s,y,rho in reversed(pairs):
            alpha=rho*float(s@q);alphas.append(alpha);q-=alpha*y
        scale=float(pairs[-1][0]@pairs[-1][1])/float(pairs[-1][1]@pairs[-1][1]) if pairs else 1.
        direction=q*scale
        for (s,y,rho),alpha in zip(pairs,reversed(alphas)):
            direction+=s*(alpha-rho*float(y@direction))
        direction=-direction; slope=float(gradient@direction)
        if slope>=0:
            direction=-gradient;slope=-float(gradient@gradient);pairs=[]
        step=1.
        for _ in range(LINEAR_RECIPE['max_line_search']):
            next_w=w+step*direction;next_value,next_gradient=linear_objective(next_w,x,labels,groups);evaluations+=1
            if np.isfinite(next_value) and next_value<=value+LINEAR_RECIPE['armijo']*step*slope:break
            step*=.5
        else:raise ValueError('Ricerca lineare Armijo fallita')
        s=next_w-w;y=next_gradient-gradient;sy=float(s@y)
        if sy>1e-12:
            pairs.append((s,y,1/sy));pairs=pairs[-LINEAR_RECIPE['memory']:]
        w,value,gradient=next_w,next_value,next_gradient

def _original(original):
    root=Path(original);result=json.loads((root/'RESULT.json').read_text())
    if result.get('status')!='PAPER_LTR_V1_COMPLETE' or result.get('ALL_MATURITY_PASS') is not True:
        raise ValueError('Originale ListNet incompleto')
    if result.get('sources',{}).get('paper_ltr_v1/learner.py')!=sha(V1.__file__):
        raise ValueError('Ricetta sorgente v1 diversa dal fit conservato')
    return root,result

def _identity(train,tests,year,old):
    sub,val,_=V1.split_training(train,year)
    state=V1.fit_transform_state(V1.raw_matrix(sub))
    expected=dict(train_keys_sha256=V1.keys_hash(train),
                  train_matrix_sha256=V1.array_hash(V1.raw_matrix(train)),
                  train_labels_sha256=V1.array_hash(V1.decile_labels(train)),
                  subtrain_keys_sha256=V1.keys_hash(sub),validation_keys_sha256=V1.keys_hash(val),
                  fit_matrix_sha256=V1.array_hash(V1.transform(V1.raw_matrix(sub),state)),
                  validation_matrix_sha256=V1.array_hash(V1.transform(V1.raw_matrix(val),state)),
                  test_fit_matrix_sha256=[V1.array_hash(V1.transform(V1.raw_matrix(t),state)) for t in tests])
    if any(old.get(k)!=v for k,v in expected.items()):raise ValueError('Input/split/target diversi dal fit originale')
    return sub,val,state

def fit_budget(train,tests,year,tmp,tag,original):
    root,result=_original(original);repeat=tag.split('_')[1]
    old=result['per_year'][str(year)]['transforms'][repeat]
    _identity(train,tests,year,old)
    spec=importlib.util.spec_from_file_location('paper_ltr_v2_isolated_v1',V1.__file__)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.RECIPE={**module.RECIPE,'max_epochs':300}
    original_network=module.train_network
    lookup={s['seed']:s for s in old['seeds']};reused={};verified={}
    def network(x,labels,groups,vx,vlabels,vgroups,seed):
        previous=lookup[seed];relative=f'models/{year}_{repeat}_listnet_{seed}.npz'
        path=root/relative;digest=result['model_files_sha256'].get(relative)
        saved=load_checkpoint(path,digest)
        for name in PARAMETERS:
            if V1.array_hash(saved[name])!=previous['parameter_sha256'][name]:raise ValueError('Parametri originali diversi dall’audit')
        if previous['stop_reason']=='patience':
            parameters={n:saved[n] for n in PARAMETERS};audit=copy.deepcopy(previous)
            reused[seed]=(path,digest)
            audit.update(reuse_original_PASS=True,prefix100_PASS=True,new_fit_executed=False,
                         original_checkpoint_sha256=digest,prefix_scope='intera traiettoria v1 riusata')
            return parameters,audit
        if previous['stop_reason']!='max_epochs' or previous['epochs_executed']!=100:
            raise ValueError('Arresto originale non previsto')
        parameters,audit=original_network(x,labels,groups,vx,vlabels,vgroups,seed)
        check_prefix(audit,previous);verified[seed]=True
        audit.update(reuse_original_PASS=False,prefix100_PASS=True,new_fit_executed=True,
                     original_checkpoint_sha256=digest,prefix_scope='100 epoche esatte')
        return parameters,audit
    module.train_network=network
    predictions,meta,labels,seconds=module.fit(train,tests,year,tmp,tag)
    for audit in meta['seeds']:
        if audit['seed'] in reused:
            previous=lookup[audit['seed']]
            if audit['prediction_sha256']!=previous['prediction_sha256']:
                raise ValueError('Inferenza del checkpoint riusato diversa dall’originale')
            source,digest=reused[audit['seed']]
            destination=Path(tmp)/f'{tag}_listnet_{audit["seed"]}.npz'
            shutil.copyfile(source,destination)
            if sha(destination)!=digest:raise ValueError('Copia checkpoint non identica')
    meta.update(kind='PAPER_LISTNET_BUDGET300',prefix100_PASS=True,
                reuse_original_PASS=reuse_integrity(meta['seeds']),
                reused_seeds=len(reused),new_seed_fits=len(verified),
                original_result_sha256=sha(root/'RESULT.json'),original_recipe=old['recipe'])
    return predictions,meta,labels,seconds

def fit_linear(train,tests,year,tmp,tag,original):
    started=time.perf_counter();root,result=_original(original);repeat=tag.split('_')[1]
    old=result['per_year'][str(year)]['transforms'][repeat]
    sub,val,state=_identity(train,tests,year,old)
    x=V1.transform(V1.raw_matrix(sub),state);vx=V1.transform(V1.raw_matrix(val),state)
    w,audit=solve_linear(x,V1.decile_labels(sub),V1.query_indices(sub))
    transformed=[V1.transform(V1.raw_matrix(t),state) for t in tests]
    predictions=[t@w for t in transformed]
    if any(not np.isfinite(p).all() for p in predictions):raise ValueError('Predizioni lineari non finite')
    tmp=Path(tmp);tmp.mkdir(parents=True,exist_ok=True);path=tmp/f'{tag}_linear.npz'
    np.savez(path,w=w,**state,feature_names=np.asarray(V1.FEATURES))
    audit.update(seed=0,parameter_sha256={'w':V1.array_hash(w)},
                 prediction_sha256=[V1.array_hash(p) for p in predictions],new_fit_executed=True,
                 best_validation_loss=V1.listnet_loss_gradient(vx@w,V1.decile_labels(val),V1.query_indices(val))[0])
    meta={k:copy.deepcopy(v) for k,v in old.items() if k not in ('seeds','saved_models','prediction_sha256','kind','recipe')}
    meta.update(kind='PAPER_LISTNET_LINEAR',recipe=LINEAR_RECIPE.copy(),seeds=[audit],
                saved_models=[str(path)],prediction_sha256=[V1.array_hash(p) for p in predictions],
                full_training_refit=False,original_result_sha256=sha(root/'RESULT.json'),
                no_seed_ensemble=True,new_seed_fits=1,reused_seeds=0,
                solver_convergence_PASS=audit['stationary_PASS'])
    return predictions,meta,V1.decile_labels(train),time.perf_counter()-started

def configured_fit(variant,original):
    if variant not in ('BUDGET300','LINEAR'):raise ValueError('Variante non registrata')
    selected=fit_budget if variant=='BUDGET300' else fit_linear
    return lambda train,tests,year,tmp,tag:selected(train,tests,year,tmp,tag,original)
