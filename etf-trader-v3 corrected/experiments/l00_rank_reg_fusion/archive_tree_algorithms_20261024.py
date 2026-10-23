#!/usr/bin/env python3
"""Persist every completed V3 meta-tree algorithm comparison and OOS report in V3.

Run from a GitHub Actions archival workflow. All files are content-addressed
with SHA-256 and the original Actions artifact URL, after verifying contents.
"""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path("etf-trader-v3 corrected/experiments/l00_rank_reg_fusion/results/tree_algorithms_20261024")
ZIPS=ROOT/"archives"
TABLES=ROOT/"tables"
def gather():
    z=[]
    for f in ("DT","RF","ET","HGB","XGB","LGB","CAT","XGB_RET","LGB_RET"):
        z.append((40037256111,"v3-meta-tree-algorithm-"+f))
    z.append((40037463931,"v3-meta-boosted-algorithms-nested-selector"))
    for f in ("DT_PAYOFF","DT_LOSS","RF_PAYOFF","XGB_PAYOFF","CAT_PAYOFF","LGB_PAYOFF"):
        z.append((40037653615,"v3-meta-payoff-tree-"+f))
    z.append((40037957355,"v3-meta-all-family-nested-selector"))
    for f in ("DT_EVENT","RF_EVENT","XGB_EVENT","CAT_EVENT"):
        z.append((40037938627,"v3-meta-event-tree-"+f))
    for f in ("DT_CONTEXT","RF_CONTEXT","XGB_CONTEXT","CAT_CONTEXT"):
        z.append((40038182585,"v3-meta-context-tree-"+f))
    final=int(os.environ["FINAL_NESTED_RUN"])
    z.append((final,"v3-meta-definitive-23-family-nested"))
    assert len(z)==26
    assert len(set(x[1] for x in z))==len(z)
    return z
def sha(blob):return hashlib.sha256(blob).hexdigest()
def main():
    assert os.getenv("GH_TOKEN")
    ZIPS.mkdir(parents=True,exist_ok=True)
    TABLES.mkdir(parents=True,exist_ok=True)
    manifest=[]
    with tempfile.TemporaryDirectory() as temp:
        for run,name in gather():
            directory=Path(temp)/name
            directory.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                "-n",name,"-D",str(directory)],check=True)
            files=sorted(p for p in directory.rglob("*") if p.is_file())
            assert len(files)>=5,(run,name,files)
            names={p.name for p in files}
            expected=({"SELECTOR_SUMMARY.csv","SELECTOR_CHOICE_AUDIT.csv"} if "nested" in name
                 else {"SUMMARY.csv","PAIRED_MONTHLY.csv","PAIRED_BOOTSTRAP.csv","FITTING_AUDIT.csv"})
            assert expected <= names,(run,name,expected-names)
            arc=ZIPS/(name+".zip")
            with zipfile.ZipFile(arc,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for f in files:z.write(f,f.relative_to(directory).as_posix())
            with zipfile.ZipFile(arc) as z:
                assert z.testzip() is None and len(z.namelist())==len(files)
            exposed=({"SELECTOR_SUMMARY.csv","SELECTOR_PAIRED_BOOTSTRAP.csv","SELECTOR_YEARLY.csv","SELECTOR_CHOICE_AUDIT.csv"} if "nested" in name
                 else {"SUMMARY.csv","PAIRED_BOOTSTRAP.csv","YEARLY.csv","FITTING_AUDIT.csv","MANIFEST.json"})
            for fname in exposed:
                matches=[f for f in files if f.name==fname]
                assert len(matches)==1,(run,name,fname)
                out=TABLES/name/fname
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(matches[0],out)
            manifest.append(dict(workflow_run=run,artifact=name,
                url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                zip_path=str(arc),zip_size_bytes=arc.stat().st_size,
                zip_sha256=sha(arc.read_bytes()),contents=[
                    dict(file=p.relative_to(directory).as_posix(),size_bytes=p.stat().st_size,
                        sha256=sha(p.read_bytes())) for p in files]))
            print("RESEARCH_BUNDLE_VERIFIED",run,name,len(files),arc.stat().st_size,flush=True)
    assert len(manifest)==26
    summary=dict(checkpoint_date="2026-10-24",project="etf-trader-v3 corrected",
        compare_type="same frozen 149 ETFs,500 overlapping 24-member baskets",
        n_matured_test_months=101,first_stage_model_run=40016809498,
        first_stage_model_modified=False,incumbent_tree_run=40031144599,
        incumbent_nested_selection_run=40032282233,
        production_modules_unchanged=True,historical_reuse=True,
        proof_of_independent_holdout=False,archive_count=len(manifest),
        verified_archives=manifest)
    (ROOT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(summary,indent=2)+"\n")
    (ROOT/"README.md").write_text(
       "# ETF Trader V3 Corrected: tree model family and meta learning comparison\n\n"
       "All source code and protocols are in `../../`. These experiments are **historical exploratory**, not a new untouched holdout.\n\n"
       "## Comparisons\n"
       "- 9 ordinary tree families including XGBoost, LightGBM, CatBoost, forests, hist boosted trees, and payoff regressions.\n"
       "- 6 payoff-weighted binary classifiers, with loss magnitude and adverse error penalties.\n"
       "- 4 ETF-pair invariant 23-feature families (same event = exactly same features).\n"
       "- 4 14-feature basket-context-preserving families with inverse duplicate-pair weights.\n"
       "- 3 STRICTLY time-matured nested selection comparators (9 families, 15 families, 23 families), tested against prior frozen V3 meta policy.\n\n"
       "All training uses mature labels 60 days older than the first quarterly decision. 101 months; 149 ETF; canonical 500 baskets. Cross-sectional source OOS labels unchanged. Top3 membership invariant.\n\n"
       "`archives/` includes all 26 complete successful GitHub artifacts; `tables/` contains directly inspectable summaries, yearly scores, fitting histories, selection audits and paired uncertainty.\n"
       "`ARCHIVE_MANIFEST.json` stores original run IDs, source paths, byte counts and SHA-256 of every file.\n"
       "**Do not promote any candidate until truly unseen prospective evidence.**\n")
    print("ALGO_RESEARCH_ARCHIVE_PASSED",len(manifest),flush=True)
if __name__=="__main__":main()
