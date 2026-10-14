"""Separate LINEAR numerical repair; original learners remain untouched.

Only algorithmic replacement: finite sy > eps64*||s||2*||y||2 and sy > 0.
This relative test avoids an absolute curvature floor as steps approach zero.
All line search, initialization, memory, budget and convergence logic is the
original AST-extracted function. No real input or vendor file is read here.
"""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
VARIANT='LINEAR_NUMERICAL_REPAIR'
OLD_FILTER='if sy>1e-12:'
NEW_FILTER=('if np.isfinite(sy) and sy>0 and '
    'np.isfinite(np.linalg.norm(s)) and np.isfinite(np.linalg.norm(y)) and '
    'sy>np.finfo(np.float64).eps*np.linalg.norm(s)*np.linalg.norm(y):')

def _sha(value): return hashlib.sha256(value).hexdigest()

def _function(source,name):
    matches=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(matches)!=1: raise ValueError(f'Expected unique original function: {name}')
    return ast.get_source_segment(source,matches[0])

_v1_path=ROOT/'paper_ltr_v1/learner.py'
_v2_path=ROOT/'paper_ltr_v2/learner.py'
_v1_source=_v1_path.read_text(encoding='utf-8')
_v2_source=_v2_path.read_text(encoding='utf-8')
_original_solver=_function(_v2_source,'solve_linear')
if _original_solver.count(OLD_FILTER)!=1:
    raise ValueError('Original curvature filter must occur exactly once')
_patched_solver=_original_solver.replace(OLD_FILTER,NEW_FILTER,1)
_recipe_nodes=[n for n in ast.parse(_v2_source).body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='LINEAR_RECIPE' for t in n.targets)]
if len(_recipe_nodes)!=1: raise ValueError('Expected unique original recipe')
_recipe_source=ast.get_source_segment(_v2_source,_recipe_nodes[0])
_v1={'np':np}
exec(_function(_v1_source,'softmax')+'\n'+_function(_v1_source,'listnet_loss_gradient'),_v1)
_namespace={'np':np,'V1':SimpleNamespace(softmax=_v1['softmax'],listnet_loss_gradient=_v1['listnet_loss_gradient'])}
exec(_recipe_source+'\n'+_function(_v2_source,'linear_objective')+'\n'+_patched_solver,_namespace)
LINEAR_RECIPE=_namespace['LINEAR_RECIPE'].copy()
REPAIR_METADATA=dict(variant=VARIANT,replacement_count=1,curvature_filter=NEW_FILTER,
    epsilon_float64=float(np.finfo(np.float64).eps),
    original_solver_sha256=_sha(_original_solver.encode('utf-8')),
    patched_solver_sha256=_sha(_patched_solver.encode('utf-8')),
    source_sha256={'paper_ltr_v1/learner.py':_sha(_v1_path.read_bytes()),
        'paper_ltr_v2/learner.py':_sha(_v2_path.read_bytes()),
        'relative_curvature.py':_sha(Path(__file__).read_bytes())})
RECIPE={**LINEAR_RECIPE,'solver':'numpy_lbfgs_relative_curvature',
    'curvature_filter':NEW_FILTER,'variant':VARIANT,
    'numerical_repair':REPAIR_METADATA}

def solve_linear(x,labels,groups):
    """Run the separately identified repair with unchanged original stopping."""
    w,audit=_namespace['solve_linear'](x,labels,groups)
    audit['variant']=VARIANT
    audit['solver']={**RECIPE,'numerical_repair':dict(REPAIR_METADATA)}
    audit['numerical_repair']={**REPAIR_METADATA,'source_sha256':REPAIR_METADATA['source_sha256'].copy()}
    return w,audit
