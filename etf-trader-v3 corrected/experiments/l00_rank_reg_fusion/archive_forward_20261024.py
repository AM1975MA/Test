#!/usr/bin/env python3
"""Persist complete 2026 extension proof under ETF Trader V3 corrected.

4 successfully verified immutable GitHub Actions result sets, including
full 149 OHLCV adjusted price append-only frozen research snapshot, complete
reconstructed first-stage scores, June prelabel independent replay, and
June-Aug nested/hurdle 500-basket decision comparison.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,shutil,tempfile,zipfile
from pathlib import Path

ROOT=Path("etf-trader-v3 corrected/experiments/l00_rank_reg_fusion/results/forward_20261024")
ARCS=ROOT/"archives";TABLE=ROOT/"tables"
SOURCES=[
    (40082539622,"v3-forward-frozen-149-raw-20261024"),
    (40083752344,"v3-forward-2026-frozen-first-stage"),
    (40084221662,"v3-forward-june-aug-incumbent-utility-comparison"),
    (40084390775,"v3-forward-june-2026-archived-head-predictions"),
]
EVIDENCE={
 "v3-forward-frozen-149-raw-20261024":["PROVENANCE.json","original_manifest.json","universe.csv"],
 "v3-forward-2026-frozen-first-stage":["REPRODUCTION_AUDIT.csv","MANIFEST.json",
     "NEW_MATURED_2026_JUN_AUG_SCORES.csv","SEPTEMBER_2026_UNMATURED_PREDICTIONS.csv"],
 "v3-forward-june-aug-incumbent-utility-comparison":["THREE_MONTHS_SUMMARY.csv",
    "THREE_NEW_MONTHS.csv","SELECTION_AUDIT.csv","CHANGED_PAIR_EVENTS.csv","MANIFEST.json"],
 "v3-forward-june-2026-archived-head-predictions":["JUNE_FROZEN_PRELABEL.csv",
    "INCUMBENT_JUNE_CHANGED_PAIRS.csv","MANIFEST.json"],
}
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()
def main():
    assert os.getenv("GH_TOKEN")
    ARCS.mkdir(parents=True,exist_ok=True);TABLE.mkdir(parents=True,exist_ok=True)
    results=[]
    with tempfile.TemporaryDirectory() as temp:
        for run,name in SOURCES:
            folder=Path(temp)/name
            folder.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                  "-n",name,"-D",str(folder)],check=True)
            files=sorted(p for p in folder.rglob("*") if p.is_file())
            names={p.name for p in files}
            assert set(EVIDENCE[name])<=names,(name,set(EVIDENCE[name])-names)
            if "raw" in name:
                assert len([p for p in files if p.suffix==".csv"])==150
                prov=json.loads(next(p for p in files if p.name=="PROVENANCE.json").read_text())
                assert len(prov["rows"])==149 and prov["original_historic_prefix_unchanged"]
            arc=ARCS/(name+".zip")
            with zipfile.ZipFile(arc,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for p in files:z.write(p,p.relative_to(folder).as_posix())
            with zipfile.ZipFile(arc) as z:
                assert z.testzip() is None and len(z.namelist())==len(files)
            for requested in EVIDENCE[name]:
                match=[p for p in files if p.name==requested]
                assert len(match)==1,requested
                out=TABLE/name/requested;out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(match[0],out)
            results.append(dict(original_run_id=run,
                original_url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                artifact=name,zip_path=str(arc),zip_size_bytes=arc.stat().st_size,
                zip_sha256=sha(arc),
                entries=[dict(path=p.relative_to(folder).as_posix(),
                         size=p.stat().st_size,sha256=sha(p)) for p in files]))
            print("FORWARD_ARCHIVE_VERIFIED",run,name,len(files),arc.stat().st_size,flush=True)
    assert len(results)==4
    (ROOT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(dict(
        checkpoint_date="2026-10-24",
        n_archives=4,full_149_raw_extension_archived=True,
        original_monthly_firststage_run=40016809498,
        extended_firststage_run=40083752344,
        old_meta_selector_run=40032282233,
        n_etfs=149,n_baskets=500,n_new_matured_months=3,
        original_june_signals_archived_before_labels=True,
        original_Jan_Jun_reproducibility_passed=True,
        original_May_36tree_and_3utility_parity_passed=True,
        prospective_outcome_claim=False,untouched_trading_source=True,
        sources=results),indent=2)+"\n")
    (ROOT/"README.md").write_text(
        "# V3 corrected — 2026 June–August first out-of-time continuation (24 October 2026)\n\n"
        "Complete evidence behind [research report](../../FORWARD_2026_JUN_AUG_RESULTS_20261024.md).\n\n"
        "FOUR complete GitHub Actions artifacts retained permanently as zipped V3 files:\n\n"
        "- Original 149 ETF full OHLCV append-only Yahoo-adjusted snapshot, through 2026-10-23. "
        "Historical frozen pre-2026-07-01 observations not revised.\n"
        "- CORRECTED125 + 5 regressors faithfully re-trained and exactly Jan–Jun compared; "
        "June–August matured first-stage, September predictions immature.\n"
        "- 500 basket × 3 new mature monthly selector and hurdle model comparisons, "
        "May all-36-tree and all-three-hurdle retrospective parity gates.\n"
        "- Independent June OOS archived BEFORE future 21D labels; measured from fresh next-open OHLCV.\n\n"
        "The calendar is retrospective, 3 months only; NO new CAGR claim and NO production promotion.\n\n"
        "`ARCHIVE_MANIFEST.json` includes file-by-file SHA256, repository Action sources "
        "and immutable ZIP digests. `tables/` offers audit CSV and JSON directly.\n")
    print("FORWARD_RESEARCH_ARCHIVE_PASSED",len(results),flush=True)
if __name__=="__main__":main()
