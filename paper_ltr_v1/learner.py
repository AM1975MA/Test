"""Adattamento preregistrato ListNet; nessuna ricerca sugli esiti fuori campione."""
from __future__ import annotations
import ast
import hashlib
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_tree = ast.parse((ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py').read_text())
FEATURES = next(ast.literal_eval(n.value) for n in _tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'F2D_FEATURES' for t in n.targets))
KEYS = ['signal_date', 'ticker']
RECIPE = dict(hidden=[64, 64], activation='relu', dropout=.2, learning_rate=1e-4,
              batch_queries=16, clip_norm=1., max_epochs=100, patience=25,
              validation_fraction=.1, seeds=[101, 202, 303], dtype='float64',
              adam_beta1=.9, adam_beta2=.999, adam_epsilon=1e-8,
              target='ceil(10*target_rank_21), clipped to 1..10',
              validation='last 10% chronological mature queries; purge exit >= first validation date',
              initialization='He normal hidden weights; Xavier normal output weights; zero biases')

def array_hash(value):
    a = np.ascontiguousarray(value)
    h = hashlib.sha256(); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()

def keys_hash(frame):
    return hashlib.sha256(frame[KEYS].sort_values(KEYS).to_csv(index=False, date_format='%Y-%m-%dT%H:%M:%S', lineterminator='\n').encode()).hexdigest()

def split_training(train, year):
    cutoff = pd.Timestamp(year, 1, 1)
    if train.empty or train[KEYS].isna().any().any() or train.duplicated(KEYS).any():
        raise ValueError('Chiavi di addestramento non valide')
    if not train[KEYS].reset_index(drop=True).equals(train.sort_values(KEYS)[KEYS].reset_index(drop=True)):
        raise ValueError('Query non ordinate')
    if train.exit_date_21.isna().any() or not ((train.signal_date < cutoff) & (train.exit_date_21 < cutoff)).all():
        raise ValueError('Etichette non mature')
    y = train.target_rank_21.to_numpy(float)
    if not np.isfinite(y).all() or ((y < 0) | (y > 1)).any():
        raise ValueError('Target percentile non valido')
    dates = np.sort(train.signal_date.unique())
    if len(dates) < 10:
        raise ValueError('Numero insufficiente di query temporali')
    start = pd.Timestamp(dates[-max(1, int(np.ceil(len(dates)*RECIPE['validation_fraction'])))])
    complete_dates = train.groupby('signal_date',sort=True).exit_date_21.max()
    safe_dates = complete_dates.index[(complete_dates.index < start) & (complete_dates < start)]
    sub = train[train.signal_date.isin(safe_dates)].reset_index(drop=True)
    val = train[train.signal_date >= start].reset_index(drop=True)
    if sub.empty or val.empty:
        raise ValueError('Partizione temporale vuota')
    return sub, val, start

def raw_matrix(frame):
    return frame[FEATURES].to_numpy(dtype=np.float64, copy=True)

def fit_transform_state(x):
    clean = np.where(np.isfinite(x), x, np.nan)
    # Colonne interamente mancanti: imputazione zero esplicita, nessuna feature eliminata.
    med = np.array([np.median(c[np.isfinite(c)]) if np.isfinite(c).any() else 0. for c in clean.T])
    z = np.where(np.isfinite(clean), clean, med)
    mean = z.mean(axis=0); scale = z.std(axis=0)
    scale[scale == 0] = 1.
    return dict(median=med, mean=mean, scale=scale)

def transform(x, state):
    z = np.where(np.isfinite(x), x, state['median'])
    out = (z-state['mean'])/state['scale']
    if not np.isfinite(out).all():
        raise ValueError('Matrice trasformata non finita')
    return out

def decile_labels(frame):
    return np.clip(np.ceil(10*frame.target_rank_21.to_numpy(float)), 1, 10).astype(np.int64)

def query_indices(frame):
    return [np.asarray(ix, dtype=int) for ix in frame.groupby('signal_date', sort=True).indices.values()]

def softmax(a):
    z = np.exp(a-np.max(a)); return z/z.sum()

def listnet_loss_gradient(scores, labels, groups):
    """Cross entropy Top-1, ogni query riceve lo stesso peso."""
    gradient = np.zeros_like(scores, dtype=float); loss = 0.
    for ix in groups:
        s = scores[ix]; q = softmax(labels[ix].astype(float)); p = softmax(s)
        logsum = np.log(np.exp(s-s.max()).sum())+s.max()
        loss += float(np.dot(q, logsum-s))
        gradient[ix] = (p-q)/len(groups)
    return loss/len(groups), gradient

def initialize(n_features, rng):
    return dict(W1=rng.normal(0, np.sqrt(2/n_features), (n_features, 64)), b1=np.zeros(64),
                W2=rng.normal(0, np.sqrt(2/64), (64, 64)), b2=np.zeros(64),
                W3=rng.normal(0, np.sqrt(1/64), (64, 1)), b3=np.zeros(1))

def forward(x, params, rng=None):
    z1=x@params['W1']+params['b1']; h1=np.maximum(z1, 0)
    m1 = (rng.random(h1.shape) >= RECIPE['dropout'])/(1-RECIPE['dropout']) if rng is not None else np.ones_like(h1)
    a1=h1*m1; z2=a1@params['W2']+params['b2']; h2=np.maximum(z2, 0)
    m2 = (rng.random(h2.shape) >= RECIPE['dropout'])/(1-RECIPE['dropout']) if rng is not None else np.ones_like(h2)
    a2=h2*m2; scores=(a2@params['W3']+params['b3']).ravel()
    return scores, (x, z1, a1, z2, a2, m1, m2)

def backward(params, cache, ds):
    x,z1,a1,z2,a2,m1,m2=cache; d=ds[:,None]
    out={'W3':a2.T@d, 'b3':d.sum(axis=0)}
    dz2=(d@params['W3'].T)*m2*(z2>0)
    out.update(W2=a1.T@dz2, b2=dz2.sum(axis=0))
    dz1=(dz2@params['W2'].T)*m1*(z1>0)
    out.update(W1=x.T@dz1, b1=dz1.sum(axis=0))
    return out

def train_network(x, labels, groups, vx, vlabels, vgroups, seed):
    rng=np.random.default_rng(seed); params=initialize(x.shape[1], rng)
    first={k:np.zeros_like(v) for k,v in params.items()}; second={k:np.zeros_like(v) for k,v in params.items()}
    initial_train=listnet_loss_gradient(forward(x,params)[0],labels,groups)[0]
    initial_val=listnet_loss_gradient(forward(vx,params)[0],vlabels,vgroups)[0]
    best=initial_val; best_epoch=0; best_params={k:v.copy() for k,v in params.items()}
    history=[]; step=0; clipped=0
    for epoch in range(1, RECIPE['max_epochs']+1):
        order=rng.permutation(len(groups))
        for pos in range(0, len(order), RECIPE['batch_queries']):
            selected=[groups[j] for j in order[pos:pos+RECIPE['batch_queries']]]
            ix=np.concatenate(selected); offsets=np.cumsum([0]+[len(g) for g in selected])
            bg=[np.arange(offsets[j],offsets[j+1]) for j in range(len(selected))]
            scores,cache=forward(x[ix],params,rng)
            _,ds=listnet_loss_gradient(scores,labels[ix],bg); grads=backward(params,cache,ds)
            norm=np.sqrt(sum(float(np.sum(g*g)) for g in grads.values()))
            if not np.isfinite(norm): raise ValueError('Gradiente non finito')
            factor=min(1.,RECIPE['clip_norm']/max(norm,1e-30)); clipped+=int(factor<1)
            step+=1
            for name in params:
                g=grads[name]*factor; first[name]=.9*first[name]+.1*g; second[name]=.999*second[name]+.001*g*g
                params[name]-=RECIPE['learning_rate']*(first[name]/(1-.9**step))/(np.sqrt(second[name]/(1-.999**step))+RECIPE['adam_epsilon'])
        train_loss=listnet_loss_gradient(forward(x,params)[0],labels,groups)[0]
        val_loss=listnet_loss_gradient(forward(vx,params)[0],vlabels,vgroups)[0]
        if not np.isfinite([train_loss,val_loss]).all(): raise ValueError('Loss non finita')
        history.append(dict(epoch=epoch,train_loss=train_loss,validation_loss=val_loss))
        if val_loss < best:
            best=val_loss; best_epoch=epoch; best_params={k:v.copy() for k,v in params.items()}
        if epoch-best_epoch >= RECIPE['patience']: break
    return best_params, dict(seed=seed, initial_train_loss=initial_train,initial_validation_loss=initial_val,
        best_validation_loss=best,best_epoch=best_epoch,epochs_executed=epoch,
        stop_reason='patience' if epoch-best_epoch>=RECIPE['patience'] else 'max_epochs',
        validation_improved=best<initial_val,optimizer_steps=step,clipped_steps=clipped,
        stationary_convergence_proven=False,history=history)

def fit(train, tests, year, tmp, tag):
    start=time.perf_counter(); sub,val,val_start=split_training(train,year)
    if not tests or any(t.empty or t[KEYS].isna().any().any() or t.duplicated(KEYS).any() for t in tests):
        raise ValueError('Inferenza vuota o chiavi non valide')
    state=fit_transform_state(raw_matrix(sub)); x=transform(raw_matrix(sub),state); vx=transform(raw_matrix(val),state)
    transformed=[transform(raw_matrix(t),state) for t in tests]
    labels=decile_labels(sub); vlabels=decile_labels(val); groups=query_indices(sub); vgroups=query_indices(val)
    tmp=Path(tmp); tmp.mkdir(parents=True,exist_ok=True); by_seed=[]; audits=[]; saved=[]
    for seed in RECIPE['seeds']:
        params,audit=train_network(x,labels,groups,vx,vlabels,vgroups,seed)
        pred=[forward(t,params)[0] for t in transformed]
        if any(not np.isfinite(p).all() for p in pred): raise ValueError('Previsioni non finite')
        audit['prediction_sha256']=[array_hash(p) for p in pred]
        audit['parameter_sha256']={n:array_hash(v) for n,v in params.items()}
        path=tmp/f'{tag}_listnet_{seed}.npz'
        np.savez(path,**params,**state,feature_names=np.asarray(FEATURES))
        saved.append(str(path)); by_seed.append(pred); audits.append(audit)
    predictions=[np.mean([p[j] for p in by_seed],axis=0) for j in range(len(tests))]
    meta=dict(kind='PAPER_LISTNET_MLP',recipe=RECIPE, feature_names=FEATURES,
        train_rows=len(train),subtrain_rows=len(sub),validation_rows=len(val),
        purged_rows=len(train)-len(sub)-len(val),subtrain_queries=len(groups),validation_queries=len(vgroups),
        cutoff=pd.Timestamp(year,1,1).isoformat(),validation_start=val_start.isoformat(),
        max_subtrain_signal_date=sub.signal_date.max().isoformat(),max_subtrain_exit_date_21=sub.exit_date_21.max().isoformat(),
        max_signal_date=train.signal_date.max().isoformat(),max_exit_date_21=train.exit_date_21.max().isoformat(),
        maturity_PASS=True,purge_PASS=bool((sub.exit_date_21<val_start).all()),
        train_keys_sha256=keys_hash(train),subtrain_keys_sha256=keys_hash(sub),validation_keys_sha256=keys_hash(val),
        train_matrix_sha256=array_hash(raw_matrix(train)),fit_matrix_sha256=array_hash(x),validation_matrix_sha256=array_hash(vx),
        train_labels_sha256=array_hash(decile_labels(train)),
        learned_state_hashes={n:array_hash(v) for n,v in state.items()},
        imputer_statistics=state['median'].tolist(),scaler_mean=state['mean'].tolist(),scaler_scale=state['scale'].tolist(),
        test_fit_matrix_sha256=[array_hash(t) for t in transformed],
        prediction_sha256=[array_hash(p) for p in predictions],seeds=audits,saved_models=saved,
        training_only_transform=True,full_training_refit=False)
    return predictions,meta,decile_labels(train),time.perf_counter()-start
