"""Hardware-only evidence; never fit a model or examine new predictive quality."""
import argparse,json
from pathlib import Path
from compact21_predictive_v2.run import numerical_gate
from compact21_predictive_v2.summarize import normalized_numeric
from numpy.lib.introspect import opt_func_info
from numpy._core._multiarray_umath import __cpu_baseline__,__cpu_dispatch__

ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
contract=numerical_gate();normalized=normalized_numeric(contract)
targets=opt_func_info()
if any('AVX512' in state['current'] for fn in targets.values() for state in fn.values()):
    raise ValueError('Unexpected active AVX512 optimized function')
p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(dict(numeric_contract=contract,normalized=normalized,cpu_baseline=__cpu_baseline__,cpu_dispatch=__cpu_dispatch__,optimized_functions=targets,hardware_only=True),indent=2)+'\n')
print('Hardware-only runtime evidence PASS')
