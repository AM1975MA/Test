"""Registered date-grouped objectives for 149-ETF 5-session ranking.
All operations are differentiated over the whole eligible cross-section for ONE signal date.
No test/future outcomes are inputs to prediction, and no group mixes timestamps.
"""
from __future__ import annotations
import torch
from torch.nn import functional as F

VARIANTS=("LISTNET_ALL","LISTMLE_TOP5","LISTNET_RETURN_HYBRID")

def listnet_distribution(y: torch.Tensor):
    """True Plackett-Luce top-one distribution from future cross-sectional ranks [-1,1]."""
    return F.softmax(3.5*y,dim=0)

def listnet_loss(s: torch.Tensor,y: torch.Tensor):
    if s.ndim!=1 or s.shape!=y.shape or s.numel()<10:raise ValueError("Bad query")
    return -(listnet_distribution(y)*F.log_softmax(s,dim=0)).sum()

def top5_listmle_loss(s: torch.Tensor,y: torch.Tensor):
    """Differentiable top-5 PL ranking likelihood over the COMPLETE 149-name query.
    True top-5 ordered by realized five-day cross-sectional rank; remaining alternatives
    continue competing in each denominator. Discount decreases at deeper positions.
    """
    if s.ndim!=1 or s.shape!=y.shape or s.numel()<10:raise ValueError("Bad query")
    order=torch.argsort(y,descending=True,stable=True)
    top=order[:5]
    loss=s.new_zeros(())
    discount=s.new_tensor([1.,.6309297536,.5,.4306765581,.3868528072])
    for k,idx in enumerate(top):
        loss=loss+discount[k]*(torch.logsumexp(s[order[k:]],dim=0)-s[idx])
    return loss/discount.sum()

def centered_relative_return(ret:torch.Tensor):
    """Training-only target, dimensionless spread-adjusted five-day relative gain.
    Ret used here must be matured. Never included in inference model inputs.
    """
    if ret.ndim!=1 or ret.numel()<10:raise ValueError("Bad return vector")
    med=ret.median()
    spread=torch.quantile(ret,.9)-torch.quantile(ret,.1)
    return torch.clamp((ret-med)/torch.clamp(spread,min=1e-5),-3.,3.)

def group_loss(s:torch.Tensor,y:torch.Tensor,ret:torch.Tensor,variant:str):
    if variant=="LISTNET_ALL":return listnet_loss(s,y)
    if variant=="LISTMLE_TOP5":return top5_listmle_loss(s,y)
    if variant=="LISTNET_RETURN_HYBRID":
        return listnet_loss(s,y)+.30*F.smooth_l1_loss(s,centered_relative_return(ret),beta=.3)
    raise ValueError(variant)
