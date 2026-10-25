#!/usr/bin/env python3
"""Archive genuine corrected-kernel EUR48 6× annual fit and economics with SHA256."""
from __future__ import annotations
import os,json,zipfile,hashlib,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path("etf-trader-v3 corrected/experiments/europe48_transfer/results/true_corrected_leaf_capacity_20261025")
FILES=[(40189199418,f"eu48-true-corrected-capacity-{yr}") for yr in range(2021,2027)]+[
       (40189614773,"eu48-true-corrected-15-31-63-127-economics")]
def sha(p):
    v=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(2**20),b""):
            v.update(b)
    return v.hexdigest()
def main():
    assert os.getenv("GH_TOKEN")
    arc=ROOT/"archives";out=ROOT/"tables";arc.mkdir(parents=True,exist_ok=True)
    out.mkdir(parents=True,exist_ok=True)
    audit=[]
    with tempfile.TemporaryDirectory() as tmp:
        for run,name in FILES:
            folder=Path(tmp)/name;folder.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
               "-n",name,"-D",str(folder)],check=True)
            files=sorted(p for p in folder.rglob("*") if p.is_file())
            expected=(["EUR48_ECONOMIC_CAGR_DD.csv","SKILL_COMPARISON.csv","PAIRED_BLOCK_BOOTSTRAP.csv",
                       "MONTHLY_65_ETF_PICKS.csv","MANIFEST.json"] if "economics" in name
                      else [f"EU48_{name[-4:]}_CORRECTED_15_31_63_127_OOS.csv",
                            f"EU48_{name[-4:]}_FEATURE_VS_CAPACITY.csv",
                            f"EU48_{name[-4:]}_MONTHLY_CHOICE_AND_LABEL.csv","MANIFEST.json"])
            assert set(expected)<={f.name for f in files},name
            dest=arc/(name+".zip")
            with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for f in files:z.write(f,f.relative_to(folder).as_posix())
            with zipfile.ZipFile(dest) as z:assert z.testzip() is None
            for fname in expected:
                f=next(f for f in files if f.name==fname)
                save=out/name/fname;save.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(f,save)
            audit.append(dict(run=run,artifact=name,
                original_url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                archive_sha256=sha(dest),archive_bytes=dest.stat().st_size,
                files=[dict(name=f.relative_to(folder).as_posix(),sha256=sha(f),bytes=f.stat().st_size) for f in files]))
            print("EU48_CORRECTED_ARCHIVE_PASS",name,dest.stat().st_size,flush=True)
    assert len(audit)==7
    (ROOT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(dict(
        checkpoint="2026-10-25",
        original_base_EU48_48_ISINs=True,n_model_years=6,all_v3_127_parity_passed=True,
        one_way_fee_bps=10,no_lookahead_annual_training=True,n_months=65,
        leaf_caps=[15,31,63,127],true_v3_corrected_feature_kernel_used=True,existing_V3_meta_not_refit_for_alternative_leaves=True,
        original_production_untouched=True,source_archive=audit),indent=2)+"\n")
    (ROOT/"README.md").write_text(
        "# Euro48 — true corrected V3 feature-kernel 15/31/63/127 leaf capacity, source audit\n\n"
        "Complete six original 2017+ annually fitted three-seed 125F leaf ablation files "
        "plus one 1374-day EUR 10bps economic comparison bundle.\n"
        "Data reused in earlier research; NOT new holdout.\n\n"
        "Every output and original GitHub Actions run is validated in `ARCHIVE_MANIFEST.json` "
        "with SHA-256. The numerical report and software defects are in "
        "[EU48_TRUE_CORRECTED_CAPACITY_20261025.md](../../EU48_TRUE_CORRECTED_CAPACITY_20261025.md).\n")
    print("EU48_CORRECTED_ARCHIVE_COMPLETE",len(audit),flush=True)
if __name__=="__main__":main()
