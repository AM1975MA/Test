"""OASIS: research-only impulse/switch decision contract. NO price forecasts."""
from dataclasses import dataclass
from statistics import NormalDist
from math import isfinite

@dataclass(frozen=True)
class Candidate:
    ticker: str
    mean_relative_log_gain: float
    epistemic_se_of_mean: float
    total_switch_cost: float
    expected_shortfall_loss: float
    probability_edge_survives_horizon: float

@dataclass(frozen=True)
class MarketState:
    incumbent: str
    incumbent_expected_shortfall_loss: float
    posterior_systemic_stress: float
    maximum_allowed_expected_shortfall_loss: float
    verified_defensive_available: bool

@dataclass(frozen=True)
class Decision:
    action: str
    ticker: str
    lower_bound_net_log_gain: float | None
    reason: str

def decide(state: MarketState, candidates: list[Candidate],
           *, simultaneous_candidates: int, family_error_rate: float = 0.05
           ) -> Decision:
    """No-trade region: posterior MEAN uncertainty (not aleatoric volatility).

    Bonferroni for all candidates *actually tested*, requires calibration
    and validation for non-Gaussian posterior mean uncertainty. Research only.
    """
    if simultaneous_candidates < len(candidates) or simultaneous_candidates < 1:
        raise ValueError("Candidate count must include all concurrent comparisons")
    if not 0 < family_error_rate < 1: raise ValueError("invalid error rate")
    if not 0 <= state.posterior_systemic_stress <= 1:
        raise ValueError("invalid systemic probability")
    if state.maximum_allowed_expected_shortfall_loss <= 0:
        raise ValueError("invalid tail loss budget")
    if (state.posterior_systemic_stress >= .75
        and state.incumbent_expected_shortfall_loss >
                state.maximum_allowed_expected_shortfall_loss):
        if state.verified_defensive_available:
            return Decision("DEFEND",state.incumbent,None,"Systemic tail-risk override")
        return Decision("RISK_ALERT",state.incumbent,None,
                        "No verified defensive instrument, cannot assume safe cash")
    z=NormalDist().inv_cdf(1.-family_error_rate/simultaneous_candidates)
    valid=[]
    for c in candidates:
        vals=(c.mean_relative_log_gain,c.epistemic_se_of_mean,
              c.total_switch_cost,c.expected_shortfall_loss,
              c.probability_edge_survives_horizon)
        if not all(isfinite(v) for v in vals): continue
        if (c.epistemic_se_of_mean<0 or c.total_switch_cost<0
            or not 0<=c.probability_edge_survives_horizon<=1
            or c.expected_shortfall_loss<0
            or c.ticker==state.incumbent): continue
        if c.expected_shortfall_loss>state.maximum_allowed_expected_shortfall_loss:
            continue
        if c.probability_edge_survives_horizon<.6: continue
        low=c.mean_relative_log_gain-c.total_switch_cost-z*c.epistemic_se_of_mean
        if low>0:valid.append((low,c))
    if not valid:
        return Decision("HOLD",state.incumbent,None,
                        "No relative opportunity clears cost and epistemic uncertainty")
    lo,best=max(valid,key=lambda v:(v[0],v[1].ticker))
    return Decision("ROTATE",best.ticker,lo,
                    "Positive conservative net opportunity after multiple comparisons")
