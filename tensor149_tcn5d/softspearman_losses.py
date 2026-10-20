"""Genuine torchsort differentiable Spearman losses for one dated ETF cross section.

torchsort.soft_rank implements Blondel et al. regularized differentiable sorting
on the permutahedron, not a pairwise sigmoid-rank or fake straight-through rank.
Input signals only; matured future labels passed solely to train/validation.
"""
from __future__ import annotations
import torch
import torchsort
from torch.nn import functional as F

VARIANTS=("SOFTSPEARMAN","SOFTSPEARMAN_RETURN","SOFTSPEARMAN_TOP5")
RANK_REGULARIZATION=1.0
TOP5_TRUTH_WEIGHT=5.0
HYBRID_RETURN_WEIGHT=0.30

def _hard_target_ranks(y):
    if y.ndim!=1 or not torch.isfinite(y).all():raise ValueError("Bad matured label")
    return torch.argsort(torch.argsort(y,dim=0,stable=True),dim=0,stable=True).to(y.dtype)+1.

def _weighted_pearson(a,b,w):
    w=w/w.sum()
    ac=a-(w*a).sum()
    bc=b-(w*b).sum()
    cross=(w*ac*bc).sum()
    denom=torch.sqrt((w*ac.square()).sum().clamp_min(1e-10)
                     *(w*bc.square()).sum().clamp_min(1e-10))
    return cross/denom

def centered_relative_return(ret):
    if ret.ndim!=1 or not torch.isfinite(ret).all():raise ValueError("Unmatured returns")
    med=ret.median()
    spread=torch.quantile(ret,.9)-torch.quantile(ret,.1)
    return torch.clamp((ret-med)/torch.clamp(spread,min=1e-5),-3.,3.)

def softspearman_loss(score,y,ret,variant):
    if variant not in VARIANTS:raise ValueError(variant)
    if score.ndim!=1 or score.shape!=y.shape or y.numel()<10:
        raise ValueError("Invalid dated eligible cross-section")
    if not torch.isfinite(score).all():raise ValueError("Nonfinite model scores")
    if variant=="SOFTSPEARMAN_RETURN" and (ret.shape!=y.shape or not torch.isfinite(ret).all()):
        raise ValueError("Unmatured relative return")

    # Standardize PREDICTED group logits only. This is an inference-accessible
    # group statistic (never target-dependent), making strength comparable across folds.
    centered=score-score.mean()
    scaled=centered/score.std(unbiased=False).clamp_min(1e-3)
    sr=torchsort.soft_rank(scaled[None,:],regularization="l2",
                           regularization_strength=RANK_REGULARIZATION)[0]
    yr=_hard_target_ranks(y)
    w=torch.ones_like(sr)
    if variant=="SOFTSPEARMAN_TOP5":
        top=torch.argsort(y,descending=True,stable=True)[:5]
        w[top]=TOP5_TRUTH_WEIGHT
    correlation=_weighted_pearson(sr,yr,w)
    loss=1.-correlation
    if variant=="SOFTSPEARMAN_RETURN":
        # Coefficient fixed ex ante; label from matured next-open 5-session return.
        loss=loss+HYBRID_RETURN_WEIGHT*F.smooth_l1_loss(score,centered_relative_return(ret),beta=.3)
    if not torch.isfinite(loss):raise ValueError("Degenerate Spearman gradient/loss")
    return loss
