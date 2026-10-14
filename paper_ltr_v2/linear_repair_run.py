"""Separate numerical repair run; the failed original LINEAR stays failed."""
import importlib.util
import json
from pathlib import Path
from paper_ltr_v2 import run as runner
from paper_ltr_v2.learner import sha
from paper_ltr_v2.diagnostics_solver import relative_curvature as repair

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/'paper_ltr_v2/diagnostics_solver/LINEAR_NUMERICAL_REPAIR_PROTOCOL.md'

def configured_repair(variant,original):
    if variant!='LINEAR':raise ValueError('Numerical repair only supports LINEAR')
    path=ROOT/'paper_ltr_v2/learner.py'
    spec=importlib.util.spec_from_file_location('isolated_original_linear',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.LINEAR_RECIPE['l2']==repair.RECIPE['l2']
    assert module.LINEAR_RECIPE['max_iterations']==repair.RECIPE['max_iterations']
    assert module.LINEAR_RECIPE['gradient_tolerance']==repair.RECIPE['gradient_tolerance']
    module.solve_linear=repair.solve_linear
    module.LINEAR_RECIPE=repair.RECIPE.copy()
    return lambda train,tests,year,tmp,tag:module.fit_linear(train,tests,year,tmp,tag,original)

def adapted_source(source):
    adapted=runner.adapter_source(source)
    variant_site='VARIANT = registered_variant'
    assert adapted.count(variant_site)==1
    adapted=adapted.replace(variant_site,'VARIANT = "LINEAR_NUMERICAL_REPAIR"')
    old='sha(ROOT / "paper_ltr_v2/PREREGISTRATION.md")'
    assert adapted.count(old)==1
    adapted=adapted.replace(old,'sha(ROOT / "paper_ltr_v2/diagnostics_solver/LINEAR_NUMERICAL_REPAIR_PROTOCOL.md")')
    injection='    result["original_reference"] = original_reference'
    assert adapted.count(injection)==1
    provenance=dict(execution='LINEAR_RELATIVE_CURVATURE_REPAIR',
        original_failed_run=38565352286,original_failed_job=115872018518,
        diagnostic_run=38578561014,original_failure_retained=True,
        separate_protocol_sha256=sha(PROTOCOL),
        repair_source_sha256=sha(repair.__file__),
        new_portfolio_rule=False,new_features=False)
    return adapted.replace(injection,injection+'\n    result["original_reference"]["variant"] = "LINEAR_NUMERICAL_REPAIR"\n    result["numerical_repair"] = '+repr(provenance))

def main():
    # Reuse the verified V1 runner and input contract in one fresh CLI process.
    # Source adaptation and configured_fit are explicit dependency injection.
    original_adapter=runner.adapter_source
    def adapter(source):
        runner.adapter_source=original_adapter
        try:return adapted_source(source)
        finally:runner.adapter_source=adapter
    runner.configured_fit=configured_repair
    runner.adapter_source=adapter
    runner.main()

if __name__=='__main__':main()
