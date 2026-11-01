"""Final diagnostic reconciliation, no fitted rule/parameter selection."""
from bootstrap import *
from evidence_math import daily_log,circular_weights
import pandas as pd,numpy as np,json

def run():
    out=ROOT/'results'
    main=pd.read_csv(out/'SCORECARD.csv');extra=pd.read_csv(out/'interaction/SCORECARD.csv');null=pd.read_csv(out/'NULL_SCORECARD.csv')
    main['experiment']='preregistered_main';extra['experiment']='postresult_2x2_cell';null['experiment']='postresult_null_information'
    allscores=pd.concat([main,extra,null],ignore_index=True)
    assert not allscores.duplicated(['config','period']).any()
    allscores.to_csv(out/'ALL_SCORECARD.csv',index=False)
    allscores.query("period=='ACTIVE2021_2024'").to_csv(out/'CONFRONTI_2021_2024.csv',index=False)
    meanrows=[]
    for market in ['EU','USA']:
      for fee in [.001,.003]:
        q=allscores[(allscores.market==market)&(allscores.fee==fee)&(allscores.period=='ACTIVE2021_2024')&(allscores.policy=='IMMEDIATE')]
        real=q[q.variant=='H_PATH'].iloc[0]
        n=q[q.variant.str.startswith('H_NULL')]
        assert len(n)==3
        meanrows.append({'market':market,'fee':fee,'true_cagr':real.cagr,'null_min_cagr':n.cagr.min(),'null_max_cagr':n.cagr.max(),'null_mean_cagr':n.cagr.mean(),'null_exceeding_true':int((n.cagr>real.cagr).sum()),'permutations':3,'warning':'descriptive small falsification; not a p-value, not a portfolio of null strategies'})
    pd.DataFrame(meanrows).to_csv(out/'NULL_VS_TRUE_SUMMARY.csv',index=False)
    contrasts=[]
    for market in ['EU','USA']:
      for fee in [.001,.003]:
       for policy in ['IMMEDIATE','DELAY3','PHASE5']:
        month={}
        for variant in ['REF_RSI','H_UNIQUE','H_PATH','H_PATH_KEEP']:
            folder=out/'interaction/paths' if variant=='H_PATH_KEEP' else out/'paths'
            z=np.load(folder/f'{market}_{variant}_{policy}_C{round(fee*10000)}.npz',allow_pickle=False)
            ds=pd.DatetimeIndex(z['dates'])[1:]
            month[variant]=pd.Series(daily_log(z['nav'])[:-1],index=ds).groupby(ds.to_period('M')).sum().loc['2021-01':'2024-12']
        x=pd.DataFrame(month);assert len(x)==48
        delta={'path_added_original42':x.H_PATH_KEEP-x.REF_RSI,'path_added_unique39':x.H_PATH-x.H_UNIQUE,'dedup_no_path':x.H_UNIQUE-x.REF_RSI,'dedup_with_path':x.H_PATH-x.H_PATH_KEEP,'interaction':x.H_PATH-x.H_UNIQUE-x.H_PATH_KEEP+x.REF_RSI}
        for name,d in delta.items():
            w=circular_weights(48,6,6000,20261101);draw=w@d.to_numpy()*1200
            contrasts.append({'market':market,'fee':fee,'policy':policy,'contrast':name,'annual_log_pp':d.mean()*1200,'ci95_low':np.quantile(draw,.025),'ci95_high':np.quantile(draw,.975),'status':'postresult interaction analysis; reused history'})
    pd.DataFrame(contrasts).to_csv(out/'HYBRID_2X2_CONTRASTS.csv',index=False)
    extra_audits=[]
    for family,pattern in [('null','null_models/*/*/*/audit.json'),('interaction','interaction_models/*/*/audit.json')]:
        for p in ROOT.glob(pattern):
            a=json.loads(p.read_text());m=json.loads(p.with_name('COMPLETE.json').read_text());assert valid_checkpoint(p.parent,m['key'])
            last=a.get('last_label_exit',a.get('last_exit'));assert pd.Timestamp(last)<pd.Timestamp(a['year'],1,1)
            ref=json.loads((ROOT/'models'/a['market']/'H_PATH'/str(a['year'])/'audit.json').read_text())
            assert a['train_keys']==ref['hybrid_train_keys'] and a['predict_keys']==ref['hybrid_predict_keys']
            assert a['matrices'][2]==ref['hybrid_input_hashes'][2]
            extra_audits.append({'family':family,'market':a['market'],'year':a['year'],'folder':str(p.parent.relative_to(ROOT)),'mature_matched_labels':True,'models':2})
    pd.DataFrame(extra_audits).to_csv(out/'AUXILIARY_FIT_CHECKS.csv',index=False)
    maincheck=json.loads((out/'VERIFIED_SUMMARY.json').read_text());nc=json.loads((out/'NULL_REPLAY_VERIFICATION.json').read_text());xc=json.loads((out/'interaction/REPLAY_SUMMARY.json').read_text())
    total={'main_models':480,'null_diagnostic_models':96,'interaction_models':32,'total_new_models':608,'main_paths':156,'null_paths':12,'interaction_paths':12,'total_paths':180,'unchanged_reference_paths':24,'independently_recomputed_metric_values':maincheck['checked_metric_values']+nc['metric_values']+xc['checked_metric_values'],'independently_reconstructed_intervals':maincheck['checked_intervals']+nc['intervals']+xc['checked_intervals'],'max_nav_error':max(maincheck['max_nav_error'],nc['max_nav_error'],xc['max_nav_error']),'max_metric_error':max(maincheck['max_metric_error'],nc['max_metric_error'],xc['max_metric_error']),'main_fit_inputs_audited':176,'auxiliary_fit_checkpoints_audited':len(extra_audits),'real_native_prefix_checks':8,'real_leadership_prefix_checks':4,'candidate_promotion':False,'review':'self-review, not independent reviewer','whole_repository_green':False,'representation':'39 stored canonical Hybrid inputs reconstruct42 learner inputs exactly; no performance claim from compression'}
    assert total['total_new_models']==480+sum(x['models'] for x in extra_audits)
    atomic_json(out/'FINAL_VERIFICATION.json',total);print(json.dumps(total,indent=2))
if __name__=='__main__':run()
