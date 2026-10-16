import unittest
import numpy as np
from raw_patterns_v1.model import learner,initialize

class ModelTest(unittest.TestCase):
    def test_gradient_and_dimensions(self):
        rng=np.random.default_rng(4);x=rng.normal(size=(8,5))
        p=initialize(5,rng);y=np.arange(1,9);groups=[np.arange(8)]
        scores,cache=learner.forward(x,p)
        _,ds=learner.listnet_loss_gradient(scores,y,groups)
        g=learner.backward(p,cache,ds)
        self.assertEqual(p['W1'].shape,(5,32));self.assertEqual(p['W2'].shape,(32,8))
        def loss():
            return learner.listnet_loss_gradient(learner.forward(x,p)[0],y,groups)[0]+.0005*sum(np.sum(p[k]**2) for k in ('W1','W2','W3'))
        for key,ix in [('W1',(0,0)),('W2',(0,0)),('W3',(0,0)),('b3',(0,))]:
            v=p[key][ix];h=1e-6;p[key][ix]=v+h;plus=loss();p[key][ix]=v-h;minus=loss();p[key][ix]=v
            self.assertAlmostEqual(g[key][ix],(plus-minus)/(2*h),places=6)
    def test_budget(self):
        self.assertEqual(learner.RECIPE['max_epochs'],20)
        self.assertEqual(learner.RECIPE['seeds'],[101,202,303])

if __name__=='__main__':unittest.main()
