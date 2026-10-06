"""One frozen nonlinear Ridge recipe; all learned transforms use mature train only."""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.kernel_approximation import RBFSampler
from sklearn.linear_model import Ridge
from compact21_predictive_v2.additive import validate
from compact21_learner_swap_v1.learners import array_hash
from etf_trader.source_only import kernel as k

PARAMS={"imputer_strategy":"median","input_scaler":"StandardScaler",
        "linear_skip_features":125,"rbf_gamma":1/125,"rbf_components":512,
        "rbf_scaler":"StandardScaler","alpha":30.,"fit_intercept":True,"solver":"svd",
        "seeds":[101,202,303],"aggregation":"mean three float64 raw seed score vectors"}


def fit(train,tests,year,tmp,tag):
    cutoff,x,tx,y=validate(train,tests,year)
    start=time.perf_counter()
    imputer=SimpleImputer(strategy="median",keep_empty_features=True)
    input_scale=StandardScaler()
    linear=input_scale.fit_transform(imputer.fit_transform(x))
    test_linear=[input_scale.transform(imputer.transform(t)) for t in tx]
    states={"imputer_statistics":imputer.statistics_,"input_scaler_mean":input_scale.mean_,
        "input_scaler_scale":input_scale.scale_,"input_scaler_variance":input_scale.var_,
        "input_scaler_n_samples_seen":np.asarray(input_scale.n_samples_seen_)}
    byseed=[];fit_hashes={};test_fit_hashes={};seed_hashes={}
    for seed in PARAMS["seeds"]:
        rbf=RBFSampler(gamma=PARAMS["rbf_gamma"],n_components=512,random_state=seed)
        rbf_scale=StandardScaler()
        nonlinear=rbf_scale.fit_transform(rbf.fit_transform(linear))
        test_nonlinear=[rbf_scale.transform(rbf.transform(t)) for t in test_linear]
        design=np.concatenate([linear,nonlinear],axis=1)
        test_design=[np.concatenate([l,r],axis=1) for l,r in zip(test_linear,test_nonlinear)]
        if design.shape!=(len(train),637) or not np.isfinite(design).all() or any(not np.isfinite(t).all() for t in test_design):
            raise ValueError("Invalid 637-column transformed design")
        ridge=Ridge(alpha=30.,fit_intercept=True,solver="svd")
        ridge.fit(design,y)
        predictions=[np.asarray(ridge.predict(t),dtype=np.float64) for t in test_design]
        if any(len(p)!=len(t) or not np.isfinite(p).all() for p,t in zip(predictions,tests)):
            raise ValueError("Invalid seed predictions")
        byseed.append(predictions)
        fit_hashes[str(seed)]=array_hash(design)
        test_fit_hashes[str(seed)]=[array_hash(t) for t in test_design]
        seed_hashes[str(seed)]=array_hash(np.concatenate(predictions))
        for name,value in {"rbf_random_weights":rbf.random_weights_,"rbf_random_offset":rbf.random_offset_,
            "rbf_scaler_mean":rbf_scale.mean_,"rbf_scaler_scale":rbf_scale.scale_,
            "rbf_scaler_variance":rbf_scale.var_,"rbf_scaler_n_samples_seen":np.asarray(rbf_scale.n_samples_seen_),
            "ridge_coef":ridge.coef_,"ridge_intercept":np.asarray(ridge.intercept_)}.items():
            states[f"seed_{seed}_{name}"]=np.asarray(value)
    predictions=[np.mean([p[j] for p in byseed],axis=0,dtype=np.float64) for j in range(len(tests))]
    meta={"kind":"RBF_RIDGE","feature_transform":"mature_median_standard_linear_skip_plus_scaled_RBF",
        "target":"continuous_percentile","model_params":dict(PARAMS),"feature_names":list(k.F2D_FEATURES),
        "input_features":125,"design_features":637,"train_rows":len(train),"test_rows":[len(t) for t in tests],
        "cutoff":cutoff.isoformat(),"max_signal_date":train.signal_date.max().isoformat(),
        "max_exit_date_21":train.exit_date_21.max().isoformat(),"maturity_PASS":True,
        "train_matrix_sha256":array_hash(x),"train_labels_sha256":array_hash(y),
        "train_groups_sha256":array_hash(train.groupby("signal_date",sort=True).size().to_numpy()),
        "test_matrix_sha256":[array_hash(t) for t in tx],"fit_matrix_sha256":fit_hashes,
        "test_fit_matrix_sha256":test_fit_hashes,"prediction_sha256":[array_hash(p) for p in predictions],
        "seed_prediction_sha256":seed_hashes,"learned_state_hashes":{n:array_hash(v) for n,v in states.items()},
        "imputer_statistics":imputer.statistics_.tolist(),"scaler_mean":input_scale.mean_.tolist(),
        "scaler_scale":input_scale.scale_.tolist()}
    destination=Path(tmp);destination.mkdir(parents=True,exist_ok=True)
    np.savez(destination/f"{tag}_STATES.npz",**states)
    np.save(destination/f"{tag}_SEED_PREDICTIONS.npy",np.stack([np.concatenate(p) for p in byseed]))
    return predictions,meta,y,time.perf_counter()-start
