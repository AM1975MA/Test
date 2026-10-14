"""Synthetic-only audit. No learner import, vendor access, or real-data fitting.

AST extraction executes the frozen mathematical functions verbatim. Diagnostic
instrumentation records iterations but does not change the production solver.
Run from any directory with Python + NumPy; output stays beside this script.
"""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

def selected(path, names):
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    return '\n\n'.join(ast.get_source_segment(source, n) for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name in names)

v1 = {'np': np}
exec(selected(ROOT/'paper_ltr_v1/learner.py', {'softmax', 'listnet_loss_gradient'}), v1)
source = (ROOT/'paper_ltr_v2/learner.py').read_text(encoding='utf-8')
tree = ast.parse(source)
recipe = next(ast.get_source_segment(source, n) for n in tree.body
    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='LINEAR_RECIPE' for t in n.targets))
base = {'np': np, 'V1': SimpleNamespace(**{k:v for k,v in v1.items() if not k.startswith('__')})}
exec(recipe+'\n'+selected(ROOT/'paper_ltr_v2/learner.py', {'linear_objective'}), base)
solver = selected(ROOT/'paper_ltr_v2/learner.py', {'solve_linear'})

def run(x, labels, groups, retain_terminal=False):
    trace=[]; terminal={}
    def record(iteration,w,value,gradient,pairs,**kw):
        trace.append(dict(iteration=int(iteration), objective=float(value),
            residual=float(np.max(np.abs(gradient))), pairs=len(pairs), **kw))
        terminal.update(w=w.copy(),pairs=list(pairs))
    code=solver.replace('        residual=float', '        record(iteration,w,value,gradient,pairs)\n        residual=float')
    code=code.replace('        if sy>1e-12:', "        trace[-1].update(sy=sy, step=step, slope=slope, line_search_evaluations=_+1, objective_change=next_value-value, step_inf=float(np.max(np.abs(s))), gradient_change_inf=float(np.max(np.abs(y))))\n        if sy>1e-12:")
    ns={**base, 'record':record, 'trace':trace}
    exec(code,ns)
    try:
        w,audit=ns['solve_linear'](x,labels,groups)
        result=dict(success=True, audit=audit)
    except ValueError as exc:
        result=dict(success=False,error=str(exc))
    pairs=terminal['pairs']; dim=x.shape[1]
    def precondition(g):
        q=g.copy(); alphas=[]
        for s,y,rho in reversed(pairs):
            alpha=rho*float(s@q); alphas.append(alpha); q-=alpha*y
        d=q*float(pairs[-1][0]@pairs[-1][1])/float(pairs[-1][1]@pairs[-1][1])
        for (s,y,rho),alpha in zip(pairs,reversed(alphas)):
            d+=s*(alpha-rho*float(y@d))
        return d
    inverse=np.column_stack([precondition(e) for e in np.eye(dim)])
    hess=.001*np.eye(dim)
    for ix in groups:
        p=v1['softmax'](x[ix]@terminal['w']); hess+=x[ix].T@(np.diag(p)-np.outer(p,p))@x[ix]/len(groups)
    contraction=np.linalg.eigvals(np.eye(dim)-inverse@hess)
    value,g=base['linear_objective'](terminal['w'],x,labels,groups)
    delta=np.linalg.solve(hess,-g)
    newton_value,newton_gradient=base['linear_objective'](terminal['w']+delta,x,labels,groups)
    result.update(first=trace[:3],last=trace[-5:],
        terminal_hessian_min_eigenvalue=float(np.linalg.eigvalsh(hess).min()),
        strong_convexity_suboptimality_upper_bound=float(g@g/(2*.001)),
        diagnostic_only_newton_gradient_inf=float(np.max(np.abs(newton_gradient))),
        diagnostic_only_newton_objective_change=newton_value-value,
        last_accepted_pair_iteration=max(t['iteration'] for t in trace if t.get('sy',0)>1e-12),
        terminal_fixed_metric_local_contraction_radius=float(np.max(np.abs(contraction))),
        tail_residual_ratio=trace[-1]['residual']/trace[-2]['residual'],
        accepted_pairs=sum(t.get('sy',0)>1e-12 for t in trace),
        skipped_pairs=sum('sy' in t and t['sy']<=1e-12 for t in trace),
        zero_steps=sum(t.get('step_inf',1)==0 for t in trace),
        minimum_residual=min(t['residual'] for t in trace))
    if retain_terminal:
        result.update(terminal_w=terminal['w'].tolist(),trace=trace,
            terminal_pairs=[dict(s=s.tolist(),y=y.tolist(),rho=rho) for s,y,rho in pairs])
    return result

def traced_solver(x, labels, groups):
    """Frozen solver plus observational trace; no threshold/budget changes."""
    return run(x, labels, groups, retain_terminal=True)

def main():
    rng=np.random.default_rng(748)
    x=rng.normal(size=(35,7)); labels=rng.integers(1,11,size=35)
    groups=[np.arange(0,3),np.arange(3,10),np.arange(10,35)]
    w=rng.normal(size=7)*.2
    objective=base['linear_objective']; loss,g=objective(w,x,labels,groups)
    eps=1e-5
    numeric=np.array([(objective(w+np.eye(7)[j]*eps,x,labels,groups)[0]-objective(w-np.eye(7)[j]*eps,x,labels,groups)[0])/(2*eps) for j in range(7)])
    scores=x@w; _,ds=v1['listnet_loss_gradient'](scores,labels,groups)
    numeric_scores=np.array([(v1['listnet_loss_gradient'](scores+np.eye(35)[j]*eps,labels,groups)[0]-v1['listnet_loss_gradient'](scores-np.eye(35)[j]*eps,labels,groups)[0])/(2*eps) for j in range(35)])
    hess=.001*np.eye(7)
    for ix in groups:
        p=v1['softmax'](scores[ix]); hess+=x[ix].T@(np.diag(p)-np.outer(p,p))@x[ix]/len(groups)
    report=dict(scope='Synthetic only; frozen production thresholds and solver; no real fit',
        numpy_version=np.__version__,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'paper_ltr_v1/learner.py',ROOT/'paper_ltr_v2/learner.py']},
        gradient_checks=dict(linear_max_abs_error=float(np.max(np.abs(numeric-g))),score_max_abs_error=float(np.max(np.abs(numeric_scores-ds))),minimum_hessian_eigenvalue=float(np.linalg.eigvalsh(hess).min())),cases=[])
    # Correlated but column-standardized synthetic features stress small-curvature
    # modes without using any frozen ETF inputs or labels.
    for seed in [0]:
        rng=np.random.default_rng(seed)
        z=rng.normal(size=(100,10))
        x=np.concatenate([z, z[:,:8]+.003*rng.normal(size=(100,8))],axis=1)
        x=(x-x.mean(axis=0))/x.std(axis=0)
        labels=rng.integers(1,11,size=100); groups=[np.arange(i,i+10) for i in range(0,100,10)]
        result=run(x,labels,groups); report['cases'].append(dict(seed=seed,**result))
        frozen={**base}; exec(solver,frozen)
        try:
            _,original_audit=frozen['solve_linear'](x,labels,groups)
            result['uninstrumented_parity']=result['success'] and original_audit==result['audit']
        except ValueError as exc:
            result['uninstrumented_parity']=not result['success'] and str(exc)==result['error']
        report['cases'][-1].update(uninstrumented_parity=result['uninstrumented_parity'])
        print(seed,result['success'],result['last'][-1]['residual'],result['skipped_pairs'],flush=True)
        if not result['success']: break
    toy_x=np.tile(np.arange(8)[:,None]/7,(3,2)); toy_y=np.tile(np.arange(2,10),3)
    toy_groups=[np.arange(i*8,(i+1)*8) for i in range(3)]
    _,toy_audit=frozen['solve_linear'](toy_x,toy_y,toy_groups)
    report['existing_toy_test_frozen_solver']=toy_audit
    (Path(__file__).parent/'synthetic_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['gradient_checks'],indent=2))

if __name__=='__main__': main()
