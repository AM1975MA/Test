#!/usr/bin/env python3
"""Immutable on-repository archives of validated V3 research Actions outputs.

Run ONLY from the archive CI workflow with GH_TOKEN. The frozen OHLCV snapshot is
referenced by its immutable original workflow ID, not copied or silently replaced.
"""
from __future__ import annotations
import csv, hashlib, io, json, os, pathlib, shutil, subprocess, tempfile, zipfile

ROOT=pathlib.Path("etf-trader-v3 corrected/experiments/l00_rank_reg_fusion")
OUT=ROOT/"results"
ARCH=OUT/"archives"
EXTRACT=OUT/"tables"
SOURCES=[
  (40016809498,"rrf-feature-s1",("OOS_SCORES.csv","FIT_AUDIT.json")),
  (40016809498,"rrf-feature-s2",("OOS_SCORES.csv","FIT_AUDIT.json")),
  (40016809498,"rrf-feature-s3",("OOS_SCORES.csv","FIT_AUDIT.json")),
  (40016809498,"rrf-regression-s1",("OOS_SCORES.csv","FIT_AUDIT.json")),
  (40016809498,"rrf-regression-s2",("OOS_SCORES.csv","FIT_AUDIT.json")),
  (40016809498,"rrf-regression-s3",("OOS_SCORES.csv","FIT_AUDIT.json")),
  (40016809498,"v3-l00-rank-reg-fusion-results",("SUMMARY.csv","PAIRED_MONTHLY.csv")),
  (40030122839,"v3-weighted-ranker-regressor-results",("SUMMARY.csv","PAIRED_BOOTSTRAP.csv")),
  (40031144599,"v3-meta-exponential-results",("SUMMARY.csv","PAIRED_BOOTSTRAP.csv")),
  (40031144599,"v3-meta-tree-results",("SUMMARY.csv","PAIRED_BOOTSTRAP.csv")),
  (40032282233,"v3-nested-meta-tree-validation",("NESTED_SUMMARY.csv","NESTED_SELECTION_AUDIT.csv")),
  (40032693599,"v3-nested-meta-tree-nextopen-economics",("ECONOMIC_SCORECARD.csv","ACTUAL_DECISION_LOG.csv")),
]
EXPOSE={
  "v3-l00-rank-reg-fusion-results":["SUMMARY.csv","PAIRED_BOOTSTRAP.csv","YEARLY.csv"],
  "v3-weighted-ranker-regressor-results":["SUMMARY.csv","PAIRED_BOOTSTRAP.csv","YEARLY.csv"],
  "v3-meta-exponential-results":["SUMMARY.csv","PAIRED_BOOTSTRAP.csv","YEARLY.csv"],
  "v3-meta-tree-results":["SUMMARY.csv","PAIRED_BOOTSTRAP.csv","YEARLY.csv","AUDIT.json"],
  "v3-nested-meta-tree-validation":["NESTED_SUMMARY.csv","NESTED_BOOTSTRAP.csv","NESTED_SELECTION_AUDIT.csv"],
  "v3-nested-meta-tree-nextopen-economics":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv","YEARLY_ENSEMBLE.csv","DECISION_VALIDATION.csv","ECONOMIC_MANIFEST.json"],
}
def sha(x:bytes):return hashlib.sha256(x).hexdigest()
def main():
    assert os.getenv("GH_TOKEN"),"GitHub workflow token required"
    OUT.mkdir(parents=True,exist_ok=True)
    ARCH.mkdir(parents=True,exist_ok=True)
    EXTRACT.mkdir(parents=True,exist_ok=True)
    rec=[]
    with tempfile.TemporaryDirectory() as tmp:
        for run,name,mandatory in SOURCES:
            folder=pathlib.Path(tmp)/name
            folder.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                            "-n",name,"-D",str(folder)],check=True)
            files=sorted(x for x in folder.rglob("*") if x.is_file())
            assert files,(run,name)
            available={x.name for x in files}
            assert set(mandatory)<=available,(run,name,mandatory,available)
            target=ARCH/(name+".zip")
            with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for path in files:
                    z.write(path,path.relative_to(folder).as_posix())
            with zipfile.ZipFile(target) as z:
                assert z.testzip() is None
                assert sorted(z.namelist())==sorted([p.relative_to(folder).as_posix() for p in files])
            for original in EXPOSE.get(name,[]):
                matches=[p for p in files if p.name==original]
                assert len(matches)==1,(name,original)
                dest=EXTRACT/name/original
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(matches[0],dest)
            records=[dict(filename=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,
                          sha256=sha(p.read_bytes())) for p in files]
            rec.append(dict(workflow_run=run,artifact_name=name,
                            artifact_url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                            bundle_repo_path=str(target),
                            bundle_sha256=sha(target.read_bytes()),bundle_size_bytes=target.stat().st_size,
                            files=records))
            print("ARCHIVED",run,name,len(files),target.stat().st_size,flush=True)
    assert len(rec)==len(SOURCES)==12
    manifest={
        "archive_date":"2026-10-24",
        "project_path":"etf-trader-v3 corrected/",
        "frozen_raw_github_actions_run":39482809691,
        "frozen_baseline_github_actions_run":39515716383,
        "canonical_universe_etfs":149,
        "canonical_baskets":500,
        "membership_sha256":"36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e",
        "fully_matured_months":101,
        "best_chronological_candidate":"NESTED_24_TOP1_GUARD",
        "candidate_not_production_approved":True,
        "research_only_no_operational_module_changed":True,
        "archived_artifacts":rec,
    }
    (OUT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    (OUT/"README.md").write_text(
       "# V3 Corrected — reproducible L00 ranking/regression decision-tree research\n\n"
       "Saved in the real existing V3 project folder. Original V2/V3 execution modules are unchanged.\n\n"
       "## Status\n\n"
       "- Causal candidate: **NESTED_24_TOP1_GUARD**, exploratory only.\n"
       "- First-stage: original CORRECTED125 out-of-year ranker.\n"
       "- Meta: quarterly matured decision tree, monthly 24-month chronological parameter rule, 60-day outcome lag.\n"
       "- Original 149 ETFs / 500 fixed baskets / 101 matured months.\n"
       "- No retrospective CAGR selection of meta parameters.\n"
       "- Functional validation: Actions 40032282233.\n"
       "- Market-next-open 10bps next-open economic replay: Actions 40032693599.\n\n"
       "## Verified matched 2022-02 through 2026-06 aggregate CAGR (baseline -> meta)\n\n"
       "| Fixed allocation | Ranker only | Ranker + nested tree |\n"
       "|---|---:|---:|\n"
       "| TOP1 100% | 21.21% | 24.62% |\n"
       "| TOP2 75/25 or 100/0 | 19.82% | 21.45% |\n"
       "| TOP3 50/30/20 | 17.96% | 18.54% |\n\n"
       "**Not independently validated future alpha.** All paired economic alpha confidence intervals contain zero, and the 2018–2026 calendar was already used to develop many settings. The basket aggregate is mean portfolio equity of dependent baskets, not a single investable pooled ETF fund.\n\n"
       "## Source and results\n\n"
       "- All scripts and protocols reside in the parent directory.\n"
       "- `tables/`: human-readable summaries, yearly results, confidence intervals, model audit and dated model decisions.\n"
       "- `archives/`: all **twelve** complete verified experiment artifact bundles; includes original per-ETF OOS signals, 50,500 decisions and daily portfolio NAV series.\n"
       "- `ARCHIVE_MANIFEST.json`: archive, source run, original filenames, byte counts and individual SHA256 hashes.\n"
       "- The **frozen original raw OHLCV** remains in Actions run 39482809691 rather than duplicating historical market data.\n"
       "- Nothing is merged into the original production trading model by this archival task.\n",
       encoding="utf8")
    print("VERIFIED_ARCHIVE_PASS",len(rec),"bundles",
          sum(a["bundle_size_bytes"] for a in rec),"compressed_bytes",flush=True)

if __name__=="__main__":
    main()
