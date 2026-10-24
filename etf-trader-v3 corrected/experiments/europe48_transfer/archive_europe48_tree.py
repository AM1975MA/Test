#!/usr/bin/env python3
"""Permanently preserve validated V3 EUR48 original 6 annual OOS datasets + economics."""
import hashlib,json,os,subprocess,tempfile,zipfile,shutil
from pathlib import Path
ROOT=Path("etf-trader-v3 corrected/experiments/europe48_transfer/results")
ARCH=ROOT/"archives"
DIR=ROOT/"tables"
SOURCES=[(40086216896,"v3-europe48-127leaf-heads-"+str(y)) for y in range(2021,2027)]
SOURCES.append((40087054494,"v3-europe48-127leaf-tree-economic-benchmark"))
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()
def main():
    assert os.getenv("GH_TOKEN")
    ARCH.mkdir(parents=True,exist_ok=True);DIR.mkdir(parents=True,exist_ok=True)
    audit=[]
    with tempfile.TemporaryDirectory() as tmp:
        for run,name in SOURCES:
            input=Path(tmp)/name;input.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                           "-n",name,"-D",str(input)],check=True)
            files=sorted(x for x in input.rglob("*") if x.is_file())
            need={"EU48_V3_FIRSTSTAGE_SCORES.csv","FIT_AUDIT.json","MANIFEST.json"} if name.startswith("v3-europe48-127leaf-heads-") else {
                "EU48_COSTED_ECONOMIC_SCORECARD.csv","EU48_PAIRED_500_BASKET_MONTHLY.csv",
                "EU48_NESTED_TREE_SELECTION_AUDIT.csv","EU48_UNRESTRICTED_48_PREDICTIVE_SKILL_MONTHLY.csv",
                "EU48_PAIRED_SKILL_BOOTSTRAP.csv","MANIFEST.json"}
            assert need <= {x.name for x in files},(name,files)
            if not name.startswith("v3-europe48-127leaf-heads-"):
                m=json.loads(next(x for x in files if x.name=="MANIFEST.json").read_text())
                assert m["money_simulation_original125_exact_parity"] and m["months"]==65
            arc=ARCH/(name+".zip")
            with zipfile.ZipFile(arc,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for file in files:z.write(file,file.relative_to(input).as_posix())
            with zipfile.ZipFile(arc) as z:assert z.testzip() is None and len(z.namelist())==len(files)
            for file in files:
                if file.name in need or (file.name.endswith(".csv") and not file.name.startswith("NAV_")):
                    out=DIR/name/file.name;out.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(file,out)
            audit.append(dict(run=run,artifact=name,archive=str(arc),
                url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                zipped_size=arc.stat().st_size,zipped_SHA256=sha(arc),
                files=[dict(path=str(f.relative_to(input)),bytes=f.stat().st_size,sha256=sha(f)) for f in files]))
            print("EU48_ARCHIVE_PASS",run,name,len(files),arc.stat().st_size,flush=True)
    assert len(audit)==7
    (ROOT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(dict(
      version="2026-10-24",source_branch="research/v3-europe48-tree-transfer-20261024",
      universe="48 EUR-listed strict Europe exposure distinct legal ISIN",
      original_EUR48_source_comparability_true=True,full_stage19_previous_europe_CAGR=-.001548735494856131,
      certified_old_EUR48_compact125_standalone_top1_CAGR=.04727914934059951,
      original_ranker_149_pretrained_reused=False,
      n_months=65,source_only_training=True,source_only_economic_replay=True,
      fees_per_side=.001,years=list(range(2021,2027)),
      no_production_changes=True,archives=audit),indent=2))
    (ROOT/"README.md").write_text(
      "# V3 Europe48 127-leaf + nested tree EU-only reproducibility archive\n\n"
      "Seven complete verified source-only GitHub artifacts with per-file SHA256.\n"
      "48 actual European exposure, EUR-listed ETF quotes, 65 months January 2021–May 2026.\n"
      "First stage 2021–26 yearly mature-only original 125F, 127 leaf 3 seed, 5 regression models.\n"
      "Meta 36 original tree families, exact 24 mature month Top1 guard and 60-day embargo, "
      "500 balanced 24-ETF source canonical baskets.\n"
      "Economic comparator is a SINGLE REAL EUR48 portfolio with 0.1% per-side genuine next-open fees "
      "and exact certified old EUR48 125F source economic reproduction. "
      "V2 full Stage19 risk results are a separate architecture and not directly isolated meta-layer delta.\n\n"
      "For analysis see ../EUROPE48_V3_TREE_RESULTS_20261024.md. No changes to V2 / operational V3.\n")
    print("EU48_V3_RESEARCH_ARCHIVE_COMPLETE",len(audit),flush=True)
if __name__=="__main__":main()
