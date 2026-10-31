"""The old action logic consumes different information, not different proposals."""
import setup_paths
from setup_paths import ROOT,OLC2
import numpy as np,pandas as pd,joblib
from assets import PARENT
from state import action_features
from train_pairs import predict
from relative_information import Information
from selective_controller import CalibrationBank

def assemble(base,extra,feature_set):
 if feature_set=='OLD':return np.asarray(base,float).copy()
 if feature_set=='REL':return np.r_[base,extra[:12]]
 if feature_set=='PEER':return np.r_[base,extra]
 raise ValueError('Undeclared feature set')

class InformationBank:
 def __init__(self,a,feature_set,information=None):
  self.a=a;self.feature_set=feature_set;self.saved={}
  au=pd.read_csv(ROOT/f'results/{a.market}_FIT_AUDIT.csv')
  self.audit=au[au.feature_set==feature_set].copy()
  self.info=information or Information(pd.read_pickle(PARENT/f'inputs/{a.market}_Close.pkl').reindex(columns=a.score.columns))
 def model(self,family,year,h):
  key=(family,year,h)
  if key not in self.saved:
   path=OLC2/f'models/{self.a.market}_{family}_{year}_H{h}.joblib' if self.feature_set=='OLD' else ROOT/f'models/{self.a.market}_{self.feature_set}_{family}_{year}_H{h}.joblib'
   self.saved[key]=joblib.load(path)
  return self.saved[key]
 def values(self,family,s,actions,profile):
  xx=[]
  for pair in actions:
   b=action_features(self.a,s,pair)
   if b is None:raise ValueError('Missing existing expert inputs')
   nw=np.zeros(self.a.N);nw[list(pair)]=.5
   e=self.info.values(s['signal_date'],s['weights'],nw) if self.feature_set!='OLD' else np.zeros(30)
   xx.append(assemble(b,e,self.feature_set))
  heads=[21,42,63] if profile else [21]
  v=np.stack([predict(self.model(family,s['signal_date'].year,h),np.asarray(xx)) for h in heads],axis=1)
  return v.mean(axis=1),v

class InformationCalibration(CalibrationBank):
 def __init__(self,market,feature_set):
  p=pd.read_csv(ROOT/f'results/{market}_PREDICTIONS.csv.gz',parse_dates=['signal_date','exit21','exit42','exit63'],float_precision='round_trip')
  self.tables={f:p[(p.feature_set==feature_set)&(p.model==f)&p.is_full_proposal].copy() for f in ['RIDGE','HGB']}
  self.cache={};self.audit=[]
