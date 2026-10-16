"""One preregistered PCA95 restriction of the verified annual LINEAR recipe."""
import copy
import os
from pathlib import Path
import numpy as np
from linear_pca_v1.basis import fit_basis,project
from paper_ltr_v1 import learner as v1
from paper_ltr_monthly_v1.core import fingerprints
from paper_ltr_v2.diagnostics_solver import relative_curvature as solver
from paper_ltr_v2.diagnostics_solver.verify_linear_stationarity import independent_gradient
from paper_ltr_v2.replay import sha

DISCARDED=os.environ.get('PCA_SUBSPACE','retained')=='discarded'
VARIANT='LINEAR_PCA_DISCARDED' if DISCARDED else 'LINEAR_PCA95'

def fit(train,tests,year,repeat,out,annual_root,annual):
    sub,val,_=v1.split_training(train,year)
    old=annual['per_year'][str(year)]['transforms'][str(repeat)]
    fp=fingerprints(train,sub,val)
    if any(old.get(k)!=v for k,v in fp.items()):raise ValueError('Training or split differs from annual control')
    state=v1.fit_transform_state(v1.raw_matrix(sub))
    if any(v1.array_hash(v)!=old['learned_state_hashes'][k] for k,v in state.items()):raise ValueError('Preprocessing changed')
    x=v1.transform(v1.raw_matrix(sub),state);vx=v1.transform(v1.raw_matrix(val),state)
    q,eigenvalues,cut=fit_basis(x);basis=q[:,cut:] if DISCARDED else q[:,:cut];k=basis.shape[1];z=project(x,basis)
    if k==0:raise ValueError('Empty selected PCA subspace')
    np.testing.assert_allclose(q.T@q,np.eye(125),rtol=0,atol=1e-12)
    covariance=x.T@x/(len(x)-1)
    np.testing.assert_allclose(q.T@covariance@q,np.diag(eigenvalues),rtol=0,atol=1e-10)
    original=Path(annual_root)/'models'/Path(old['saved_models'][0]).name
    if sha(original)!=annual['model_files_sha256'][original.relative_to(annual_root).as_posix()]:raise ValueError('Original coefficient file changed')
    with np.load(original,allow_pickle=False) as saved:w0=saved['w'].copy()
    original_scores=x@w0;rotated_scores=project(x,q)@(q.T@w0)
    rotation_error=float(np.max(np.abs(original_scores-rotated_scores)))
    if rotation_error>1e-10 or abs(w0@w0-(q.T@w0)@(q.T@w0))>1e-10:raise ValueError('Full rotation invariance failed')
    labels=v1.decile_labels(sub);groups=v1.query_indices(sub)
    beta,audit=solver.solve_linear(z,labels,groups)
    gradient=independent_gradient(z,beta,labels,groups)
    residual=float(np.max(np.abs(gradient)))
    if residual>1e-7:raise ValueError('Projected independent gradient failed')
    w=basis@beta
    np.testing.assert_allclose(x@w,z@beta,rtol=0,atol=1e-10)
    transformed=[v1.transform(v1.raw_matrix(t),state) for t in tests]
    predictions=[t@w for t in transformed]
    path=Path(out)/'models'/f'{year}_{repeat}_{VARIANT.lower()}.npz';path.parent.mkdir(parents=True,exist_ok=True)
    np.savez(path,w=w,w_pc=beta,pca_basis=basis,pca_eigenvalues=eigenvalues,pca_components=np.array(k),
             **state,feature_names=np.asarray(v1.FEATURES))
    audit.update(seed=0,parameter_sha256={'w':v1.array_hash(w),'w_pc':v1.array_hash(beta)},
                 prediction_sha256=[v1.array_hash(p) for p in predictions],new_fit_executed=True,
                 best_validation_loss=v1.listnet_loss_gradient(vx@w,v1.decile_labels(val),v1.query_indices(val))[0])
    meta=copy.deepcopy(old)
    meta.update(**fp,kind='PAPER_LISTNET_'+VARIANT,recipe=solver.RECIPE,saved_models=[str(path)],seeds=[audit],
                fit_matrix_sha256=v1.array_hash(x),validation_matrix_sha256=v1.array_hash(vx),
                learned_state_hashes={key:v1.array_hash(value) for key,value in state.items()},
                prediction_sha256=[v1.array_hash(p) for p in predictions],
                test_fit_matrix_sha256=[v1.array_hash(t) for t in transformed],new_seed_fits=1,reused_seeds=0,
                pca_fit_matrix_sha256=v1.array_hash(z),pca_basis_sha256=v1.array_hash(basis),
                pca_components=k,pca_subspace='discarded' if DISCARDED else 'retained',pca95_boundary= cut,pca_variance_retained=float((eigenvalues[cut:] if DISCARDED else eigenvalues[:cut]).sum()/eigenvalues.sum()),
                pca_boundary_eigengap=float(eigenvalues[cut-1]-eigenvalues[cut]) if cut<125 else None,
                full_rotation_score_max_error=rotation_error,full_rotation_invariance_PASS=True,
                projected_independent_gradient_inf=residual,solver_convergence_PASS=True,
                training_only_transform=True,full_training_refit=False)
    return predictions,meta
