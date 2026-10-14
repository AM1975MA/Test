"""Synthetic regressions only; no imports from vendor or production learner."""
import importlib
import unittest
import numpy as np
from paper_ltr_v2.diagnostics_solver import synthetic_audit as original


class RepairTests(unittest.TestCase):
    def test_original_fails_and_relative_filter_converges_same_problem(self):
        repair=importlib.import_module('paper_ltr_v2.diagnostics_solver.relative_curvature')
        rng=np.random.default_rng(0); z=rng.normal(size=(100,10))
        x=np.concatenate([z,z[:,:8]+.003*rng.normal(size=(100,8))],axis=1)
        x=(x-x.mean(axis=0))/x.std(axis=0)
        y=rng.integers(1,11,size=100); groups=[np.arange(i,i+10) for i in range(0,100,10)]
        frozen={**original.base}; exec(original.solver,frozen)
        with self.assertRaisesRegex(ValueError,'Lineare non convergente'):
            frozen['solve_linear'](x,y,groups)
        w,audit=repair.solve_linear(x,y,groups)
        residual=np.max(np.abs(original.base['linear_objective'](w,x,y,groups)[1]))
        self.assertLessEqual(residual,1e-7)
        self.assertEqual(audit['solver']['gradient_tolerance'],1e-7)
        self.assertEqual(audit['solver']['max_iterations'],2000)
        for key,value in original.base['LINEAR_RECIPE'].items():
            if key!='solver': self.assertEqual(repair.RECIPE[key],value)
        self.assertEqual(repair._patched_solver.replace(repair.NEW_FILTER,repair.OLD_FILTER),original.solver)
        self.assertTrue(audit['stationary_PASS'])
        self.assertEqual(audit['variant'],'LINEAR_NUMERICAL_REPAIR')
        print('SYNTHETIC_REPAIR',audit['iterations'],residual,flush=True)

    def test_zero_initialization_toy_and_source_immutability(self):
        repair=importlib.import_module('paper_ltr_v2.diagnostics_solver.relative_curvature')
        before={p:p.read_bytes() for p in [original.ROOT/'paper_ltr_v1/learner.py',original.ROOT/'paper_ltr_v2/learner.py']}
        x=np.tile(np.arange(8)[:,None]/7,(3,2)); y=np.tile(np.arange(2,10),3)
        groups=[np.arange(i*8,(i+1)*8) for i in range(3)]
        _,audit=repair.solve_linear(x,y,groups)
        self.assertEqual(audit['initial_objective'],original.base['linear_objective'](np.zeros(2),x,y,groups)[0])
        for p,b in before.items(): self.assertEqual(p.read_bytes(),b)
        self.assertLessEqual(audit['gradient_inf_norm'],1e-7)
        self.assertEqual(audit['numerical_repair']['replacement_count'],1)
        self.assertEqual(len(audit['numerical_repair']['original_solver_sha256']),64)
        print('TOY_REPAIR',audit['iterations'],audit['gradient_inf_norm'],flush=True)

if __name__=='__main__': unittest.main()
