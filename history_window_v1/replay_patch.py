"""Explicit user-authorized research gate relaxation. No model tuning."""
import hashlib,json
from pathlib import Path

def patch_models(source):
    old='if n_train_dates<60:'
    old_required="'required':60"
    if source.count(old)!=1 or source.count(old_required)!=1:
        raise ValueError('Unexpected canonical models source; refusing patch')
    return source.replace(old,'if n_train_dates<58:').replace(old_required,"'required':58")

def patch_titanium(source):
    anchor='    pred=fit_predict(k,compact,tail,macro,mfeatures,extra,out/"annual_models")'
    if source.count(anchor)!=1:
        raise ValueError('Unexpected canonical Titanium source; refusing patch')
    floor=''.join(f"    {name}={name}[{name}.signal_date.ge('2012-01-01')].copy()\n" for name in ('compact','tail','macro','extra'))
    return source.replace(anchor,floor+anchor)

def apply(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for relative,fn in [('src/etf_trader/source_only/models.py',patch_models),('scripts/build_tit_r_source_only.py',patch_titanium)]:
        p=root/relative;before=p.read_text();after=fn(before)
        p.write_text(after)
        rows.append({'path':relative,'original_text_sha256':hashlib.sha256(before.encode()).hexdigest(),'patched_text_sha256':hashlib.sha256(after.encode()).hexdigest()})
    result={'training_signal_start':'2012-01-01','minimum_mature_compact21_months':58,'original_minimum':60,'maturity_filters_unchanged':True,'hyperparameters_features_costs_execution_unchanged':True,'patches':rows}
    (out/'RESEARCH_PATCH.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
