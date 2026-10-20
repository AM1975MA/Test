"""Causal as-of risk estimates and matured future risk-relative label distributions.

As-of close t: vol63(t), beta_mkt63(t), mom21(t); never use future OHLCV
to estimate scale or beta. Target return from next Open(t+1) to Open(t+6).
Benchmark SPY held over the same NEXT-OPEN window. Future market/SPY is
used only to build matured TRAINING labels, never at inference.
"""
from __future__ import annotations
import hashlib
import numpy as np
from scipy.stats import rankdata
from tensor149_tcn5d.features import FIELDS

RISK_VARIANTS=("RAW_EXCESS_DIST","VOL_EXCESS_DIST","BETA_VOL_RESID_DIST")
CONTROL_VARIANTS=("MOM21","MOM21_RISK","BETA_MOM21_RISK","VOL63","INV_VOL63")
SIGMA_FLOOR=0.01
TARGET_TEMPERATURE=3.5

def asof_risk(x,available,spy_index):
    if x.ndim!=3 or x.shape[:2]!=available.shape:raise ValueError("Panel dimensions")
    raw_vol=x[:,:,FIELDS.index("vol63")].astype(np.float64)
    raw_beta=x[:,:,FIELDS.index("beta_mkt63")].astype(np.float64)
    mom21=x[:,:,FIELDS.index("mom21")].astype(np.float64)
    risk_vol=np.empty_like(raw_vol)
    risk_beta=np.empty_like(raw_beta)
    missing_vol=0;missing_beta=0
    for t in range(len(x)):
        # Cross-sectional fallback is based on today's already-computed features.
        good_vol=available[t] & np.isfinite(raw_vol[t]) & (raw_vol[t]>0)
        # Volatilities are annualized here; fallback only if single ETF unavailable.
        v=float(np.median(raw_vol[t,good_vol])) if good_vol.any() else .20
        missing_vol+=int(np.sum(available[t]&~good_vol))
        risk_vol[t]=np.where(np.isfinite(raw_vol[t]) & (raw_vol[t]>0),raw_vol[t],v)
        valid_beta=available[t]&np.isfinite(raw_beta[t])
        missing_beta+=int(np.sum(available[t]&~valid_beta))
        risk_beta[t]=np.clip(np.where(np.isfinite(raw_beta[t]),raw_beta[t],1.),-1.5,3.)
    # Annualized historical close-close sigma at t, projected on 5 trading sessions.
    sigma=np.maximum(risk_vol*np.sqrt(5/252),SIGMA_FLOOR)
    spy_mom=mom21[:,spy_index]
    hist_scale=np.maximum(risk_vol*np.sqrt(21/252),SIGMA_FLOOR)
    controls={
        "MOM21":mom21,
        "MOM21_RISK":(mom21-spy_mom[:,None])/hist_scale,
        "BETA_MOM21_RISK":(mom21-risk_beta*spy_mom[:,None])/hist_scale,
        "VOL63":risk_vol,
        "INV_VOL63":-risk_vol
    }
    for key in controls:
        v=np.asarray(controls[key],dtype=np.float64)
        controls[key]=np.nan_to_num(v,nan=-999.,posinf=-999.,neginf=-999.).astype(np.float32)
    audit=dict(annual_vol_missing_on_eligible=int(missing_vol),
               beta_missing_on_eligible=int(missing_beta),
               sigma_floor_weekly=SIGMA_FLOOR,
               vol_fallback="same-day cross-sectional median, or 20% annualized if no available ETF",
               beta_fallback="beta=1 when missing; otherwise clip [-1.5,3]",
               asof_only=True)
    return sigma.astype(np.float32),risk_beta.astype(np.float32),controls,audit

def maturity_targets(ret,available,sigma,beta,spy_index):
    """Produces three target matrices shaped [date, ETF]; each date softmax query
    is calculated over exactly the *eligible at that date* ETF observations
    with matured returns. All other entries are nan.
    """
    if ret.shape!=available.shape or ret.shape!=sigma.shape or ret.shape!=beta.shape:
        raise ValueError("Shapes differ")
    market=ret[:,spy_index]
    relative=ret-market[:,None]
    vol_adj=relative/sigma
    beta_adj=(ret-beta*market[:,None])/sigma
    raw_by_variant={"RAW_EXCESS_DIST":relative,"VOL_EXCESS_DIST":vol_adj,
                    "BETA_VOL_RESID_DIST":beta_adj}
    out={k:np.full(ret.shape,np.nan,dtype=np.float32) for k in RISK_VARIANTS}
    for t in range(len(ret)):
        mask=available[t] & np.isfinite(market[t])
        for key,mat in raw_by_variant.items():
            values=mat[t]
            valid=mask&np.isfinite(values)
            if np.sum(valid)<10:continue
            group=values[valid].astype(np.float64)
            med=np.median(group);spread=np.quantile(group,.9)-np.quantile(group,.1)
            # These med/quantiles are *labels*, not feature inputs. Used only after
            # future exits have matured within training/validation.
            z=np.clip((group-med)/max(float(spread),.01 if key=="RAW_EXCESS_DIST" else .1),-3,3)
            out[key][t,valid]=z.astype(np.float32)
    return out,raw_by_variant

def risk_distribution_loss(scores,targets):
    import torch
    from torch.nn import functional as F
    if scores.ndim!=1 or scores.shape!=targets.shape or scores.numel()<10:
        raise ValueError("Invalid cross-sectional group")
    if not torch.isfinite(targets).all():raise ValueError("Unmatured target")
    target_probs=F.softmax(TARGET_TEMPERATURE*targets,dim=0)
    return -(target_probs*F.log_softmax(scores,dim=0)).sum()

def oracle_risk_overlap(pred,ids,risk_target):
    pred_top=set(ids[np.argsort(-pred,kind="stable")[:5]])
    target_top=set(ids[np.argsort(-risk_target[ids],kind="stable")[:5]])
    return len(pred_top&target_top)/5.

def risk_excess_selected(ret,spy_index,chosen_ids,t,sigma,beta):
    obs=ret[t,chosen_ids]
    sp=ret[t,spy_index]
    return dict(benchmark_fwd_return=float(sp),
                avg_selected_benchmark_excess=float(np.mean(obs-sp)),
                avg_selected_beta_residual=float(np.mean(obs-beta[t,chosen_ids]*sp)),
                avg_selected_beta_sigma_residual=float(np.mean((obs-beta[t,chosen_ids]*sp)/sigma[t,chosen_ids])))
