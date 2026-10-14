import unittest
import numpy as np
import pandas as pd
from paper_ltr_v1 import learner as m

class ListNetTest(unittest.TestCase):
    def test_gradient_network_finite_difference(self):
        rng=np.random.default_rng(8); x=rng.normal(size=(7,4)); p=m.initialize(4,rng)
        labels=np.array([1,4,10,2,6,9,8]); groups=[np.arange(3),np.arange(3,7)]
        s,cache=m.forward(x,p); _,ds=m.listnet_loss_gradient(s,labels,groups); gradients=m.backward(p,cache,ds)
        for key in p:
            for flat_index in rng.choice(p[key].size,min(5,p[key].size),replace=False):
                idx=np.unravel_index(flat_index,p[key].shape); old=p[key][idx]; eps=1e-6
                p[key][idx]=old+eps; plus=m.listnet_loss_gradient(m.forward(x,p)[0],labels,groups)[0]
                p[key][idx]=old-eps; minus=m.listnet_loss_gradient(m.forward(x,p)[0],labels,groups)[0]
                p[key][idx]=old
                self.assertAlmostEqual((plus-minus)/(2*eps),gradients[key][idx],places=6)

    def test_query_shift_invariance(self):
        scores=np.array([-.4,.2,1.,3.,-1.]); labels=np.array([1,5,10,7,2]); groups=[np.arange(3),np.arange(3,5)]
        a,g=m.listnet_loss_gradient(scores,labels,groups)
        b,h=m.listnet_loss_gradient(scores+np.array([17.,17.,17.,-8.,-8.]),labels,groups)
        self.assertAlmostEqual(a,b,places=12); np.testing.assert_allclose(g,h,atol=1e-14)
        self.assertAlmostEqual(g[:3].sum(),0.,places=12)

    def frame(self):
        dates=pd.date_range('2013-01-01',periods=20,freq='MS')
        f=pd.DataFrame({'signal_date':dates,'ticker':'TEST','exit_date_21':dates+pd.Timedelta(days=28),'target_rank_21':.5})
        return f

    def test_maturity_and_purge(self):
        f=self.frame(); sub,val,start=m.split_training(f,2015)
        self.assertTrue((sub.exit_date_21<start).all()); self.assertTrue((val.signal_date>=start).all())
        f.loc[0,'exit_date_21']=pd.Timestamp('2015-01-01')
        with self.assertRaises(ValueError):m.split_training(f,2015)

    def test_transform_fitted_only_subtraining(self):
        f=self.frame(); sub,val,_=m.split_training(f,2015)
        x=np.arange(len(sub),dtype=float)[:,None]; x[0]=np.nan
        state=m.fit_transform_state(x); before={k:v.copy() for k,v in state.items()}
        m.transform(np.full((len(val),1),1e9),state)
        for k in state:np.testing.assert_array_equal(state[k],before[k])
        self.assertEqual(state['median'][0],np.median(np.arange(1,len(sub))))
        blank=m.fit_transform_state(np.full((5,2),np.nan))
        np.testing.assert_array_equal(m.transform(np.full((1,2),np.nan),blank),np.zeros((1,2)))

    def test_dropout_seeded_and_inference_deterministic(self):
        rng=np.random.default_rng(9); p=m.initialize(4,rng); x=rng.normal(size=(6,4))
        a=m.forward(x,p,np.random.default_rng(15))[0]; b=m.forward(x,p,np.random.default_rng(15))[0]
        np.testing.assert_array_equal(a,b); np.testing.assert_array_equal(m.forward(x,p)[0],m.forward(x,p)[0])

    def test_purge_whole_query_mixed_exit_dates(self):
        f=self.frame(); extra=f.iloc[[17]].copy(); extra['ticker']='SECOND'
        extra['exit_date_21']=f.signal_date.iloc[18]
        f=pd.concat([f,extra]).sort_values(m.KEYS).reset_index(drop=True)
        sub,val,start=m.split_training(f,2015)
        self.assertFalse((sub.signal_date==extra.signal_date.iloc[0]).any())
        self.assertEqual(start,f.signal_date.unique()[-2])

    def test_decile_boundaries(self):
        f=pd.DataFrame({'target_rank_21':[0,.001,.1,.10001,.9,.90001,1.]})
        np.testing.assert_array_equal(m.decile_labels(f),[1,1,1,2,9,10,10])

    def test_permutation_within_query(self):
        scores=np.array([-.4,.2,1.,3.,-1.]); labels=np.array([1,5,10,7,2]); groups=[np.arange(3),np.arange(3,5)]
        a,g=m.listnet_loss_gradient(scores,labels,groups); order=np.array([2,0,1,4,3])
        b,h=m.listnet_loss_gradient(scores[order],labels[order],groups)
        self.assertAlmostEqual(a,b,places=12); np.testing.assert_allclose(h,g[order],atol=1e-14)

    def test_optimizer_deterministic_and_learns_toy_ranking(self):
        old=m.RECIPE.copy()
        try:
            m.RECIPE.update(max_epochs=15,patience=15,learning_rate=.002)
            x=np.tile(np.linspace(-1,1,8)[:,None],(3,2)); labels=np.tile(np.arange(2,10),3)
            groups=[np.arange(j*8,(j+1)*8) for j in range(3)]
            a,au=m.train_network(x,labels,groups,x,labels,groups,101)
            b,bu=m.train_network(x,labels,groups,x,labels,groups,101)
            for key in a:np.testing.assert_array_equal(a[key],b[key])
            self.assertEqual(au,bu)
            self.assertLess(au['best_validation_loss'],.9*au['initial_validation_loss'])
        finally:m.RECIPE.clear(); m.RECIPE.update(old)

if __name__=='__main__':unittest.main()
