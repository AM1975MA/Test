from calendar_rebuild import *
checks=[]
for market in ['USA','EU']:
 cp=pd.read_pickle(OUT/f'{market}_COMPACT.pkl');hp=pd.read_pickle(OUT/f'{market}_HYBRID.pkl')
 for name,f in [('COMPACT',cp),('HYBRID',hp)]:
  good=f.source_date.notna();age=(f.loc[good,'signal_date']-f.loc[good,'source_date']).dt.days
  assert (age>=0).all() and (age<=5).all()
  assert not f.duplicated(['signal_date','ticker']).any()
  checks.append({'market':market,'check':name+'_ASOF','rows':int(good.sum()),'max_age':int(age.max()),'pass':True})
 audits=json.loads((OUT/f'{market}_FIT_AUDIT.json').read_text())
 for a in audits:assert pd.Timestamp(a['max_exit'])<pd.Timestamp(a['cutoff']) and pd.Timestamp(a['max_signal'])<pd.Timestamp(a['cutoff'])
 checks.append({'market':market,'check':'FIT_MATURITY','records':len(audits),'pass':True})
 frames,u=raw_frames(market);C=pd.DataFrame({t:f.Close for t,f in frames.items()}).sort_index()
 bench=C.SPY.dropna() if market=='USA' else (1+C.ffill(limit=3).pct_change(fill_method=None).median(axis=1).fillna(0.)).cumprod()
 fn,fh,_,_=source_functions(bench)
 perturbed=bench.copy();perturbed.loc[perturbed.index>='2023-01-01']*=1.8
 fn2,fh2,_,_=source_functions(perturbed)
 # Representative real ticker prefixes plus exact helper source invariants.
 sample=list(frames)[::max(1,len(frames)//8)][:8]
 for ticker in sample:
  f=frames[ticker];fm={field:f[[field]].rename(columns={field:ticker}) for field in FIELDS};other={field:v.copy() for field,v in fm.items()}
  for field in FIELDS:other[field].loc[other[field].index>='2023-01-01']*=1.7
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');a=fn(fm);b=fn2(other);aa=fh(fm);bb=fh2(other)
  for family,left,right in [('COMPACT',a,b),('HYBRID_RAW',aa,bb)]:
   for key in left:
    before=left[key].loc[:'2022-12-31'];after=right[key].reindex(before.index)
    np.testing.assert_allclose(before,after,rtol=0,atol=1e-12,equal_nan=True)
  checks.append({'market':market,'check':'RAW_FEATURE_PREFIX','ticker':ticker,'pass':True})
 # Source membership labels deliberately contain no realized future outcomes.
 cutoff=pd.Timestamp('2020-12-31');eligible=cp[(cp.eligible)&(cp.signal_date<=cutoff)][['signal_date','ticker']].copy()
 for h in [42,63]:eligible[f'fwd_ret_{h}']=np.nan;eligible[f'exit_date_{h}']=pd.NaT
 cats=dict(zip(u.ticker,u.macro_category));cats={t:('C05_BONDS_CASH_CREDIT' if ('BOND' in str(c) or str(c)=='SOVEREIGN_EUR') else c) for t,c in cats.items()}
 dates=pd.DatetimeIndex(sorted(cp[cp.signal_date<=cutoff].signal_date.unique()))
 with warnings.catch_warnings():
  warnings.simplefilter('ignore');got=build_persistent_membership(C.loc[:cutoff].ffill(limit=3),eligible,dates,cats,seed=DEFAULT_SEED).membership
 expected=pd.read_csv(OUT/f'{market}_CLUSTERS.csv',parse_dates=['signal_date']);expected=expected[expected.signal_date<=cutoff]
 key=['signal_date','ticker'];got=got.sort_values(key).reset_index(drop=True);expected=expected.sort_values(key).reset_index(drop=True)
 pd.testing.assert_frame_equal(got,expected)
 checks.append({'market':market,'check':'CLUSTER_PREFIX_FULL_TO_2020','rows':len(got),'pass':True})
(OUT/'CAUSAL_CHECKS.json').write_text(json.dumps(checks,indent=2));print('CALENDAR_CHECKS',len(checks),'PASS')
