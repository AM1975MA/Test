"""Exact original V2 economic replay with scoped, explicitly recorded interventions."""
from __future__ import annotations
import numpy as np

def run_replay(compare,state,selection_score,weight_score=None,
               force_equal_weight=False,ma3_agreement=True):
    """All cost/risk/V6/equity internals remain in original replay_full_universe."""
    if weight_score is None:weight_score=selection_score
    original_score=compare.stage19.score_matrix
    original_alloc=compare.producer.allocations_from_score
    original_weights=compare.stage19.confidence_weights
    try:
        def selected_score(_p,cal,tickers):
            if selection_score.shape!=(len(cal),len(tickers)):
                raise ValueError("Selection score not aligned")
            return selection_score
        def selected_alloc(_score,cal,dates,basket,basket_valid,*,continuous=True):
            choices=original_alloc(selection_score,cal,dates,basket,basket_valid,continuous=continuous)
            if force_equal_weight:
                weighting=compare.producer.AllocationResult(
                    d1=choices.d1,d2=choices.d2,
                    weight1=np.full_like(choices.weight1,.5),
                    margin=np.zeros_like(choices.margin))
            elif weight_score is selection_score:
                weighting=choices
            else:
                weighting=original_alloc(weight_score,cal,dates,basket,basket_valid,continuous=continuous)
            if choices.d1.shape!=weighting.weight1.shape or not np.isfinite(weighting.weight1).all():
                raise ValueError("Counterfactual daily allocations misaligned")
            return compare.producer.AllocationResult(
                d1=choices.d1.copy(),d2=choices.d2.copy(),
                weight1=weighting.weight1.copy(),margin=weighting.margin.copy())
        compare.stage19.score_matrix=selected_score
        compare.producer.allocations_from_score=selected_alloc
        if not ma3_agreement:
            def without_model_agreement(base,g,agree,agreeall,mode):
                return original_weights(base,g,np.zeros_like(agree,bool),agreeall,mode)
            compare.stage19.confidence_weights=without_model_agreement
        return compare.replay_full_universe(state)
    finally:
        compare.stage19.score_matrix=original_score
        compare.producer.allocations_from_score=original_alloc
        compare.stage19.confidence_weights=original_weights
