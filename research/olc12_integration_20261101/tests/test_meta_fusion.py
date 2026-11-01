import numpy as np,pandas as pd
from meta_fusion import fit_meta,predict_meta,mature_groups

def test_fit_nonnegative_and_informative():
    x=np.linspace(-2,2,200)[:,None];y=(x[:,0]>1).astype(float);dates=np.repeat(np.arange(20),10)
    m=fit_meta(x,y,dates);p=predict_meta(m,x)
    assert np.all(np.array(m['coef'])>=0) and p[-1]>p[0] and np.isfinite(p).all()

def test_constant_features_finite():
    x=np.ones((100,2));y=np.r_[np.ones(20),np.zeros(80)];m=fit_meta(x,y,np.repeat(np.arange(10),10));p=predict_meta(m,x)
    np.testing.assert_allclose(p,.2,atol=1e-6)

def test_month_equal_weight_replicating_rows():
    x=np.array([[-1.],[1.],[-2.],[2.]]);y=np.array([0.,1.,0.,1.]);d=np.array([1,1,2,2])
    a=fit_meta(x,y,d);b=fit_meta(np.r_[x,x[:2],x[:2]],np.r_[y,y[:2],y[:2]],np.r_[d,d[:2],d[:2]])
    np.testing.assert_allclose(a['mean'],b['mean'],atol=1e-12);np.testing.assert_allclose(a['coef'],b['coef'],atol=1e-7)

def test_full_group_maturity():
    f=pd.DataFrame({'signal_date':pd.to_datetime(['2020-08-31','2020-08-31','2020-09-30','2020-09-30']), 'exit_date_63':pd.to_datetime(['2020-12-01','2020-12-02','2020-12-31','2021-01-04']),'TARGET':[.2,.8,.3,.7]})
    out=mature_groups(f,2021);assert len(out)==2 and (out.signal_date==pd.Timestamp('2020-08-31')).all()

def test_future_labels_do_not_enter_maturity_selection():
    f=pd.DataFrame({'signal_date':pd.to_datetime(['2020-01-31','2020-01-31','2021-01-31','2021-01-31']), 'exit_date_63':pd.to_datetime(['2020-05-01','2020-05-01','2021-05-01','2021-05-01']),'TARGET':[.2,.8,.3,.7]})
    a=mature_groups(f,2021);f.loc[2:,'TARGET']=[1,0];b=mature_groups(f,2021);pd.testing.assert_frame_equal(a,b)
