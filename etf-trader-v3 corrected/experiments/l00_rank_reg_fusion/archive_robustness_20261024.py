#!/usr/bin/env python3
"""Reproducible immutable archive of all V3 meta-layer stress tests in V3 folder."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path("etf-trader-v3 corrected/experiments/l00_rank_reg_fusion/results/robustness_20261024")
ZIP=ROOT/"archives"
TABS=ROOT/"tables"
SOURCES=[
 (40035961810,"v3-meta-cost-0bps"),
 (40035961810,"v3-meta-cost-10bps"),
 (40035961810,"v3-meta-cost-25bps"),
 (40035961810,"v3-meta-cost-50bps"),
 (40035961810,"v3-meta-cost-100bps"),
 (40036167353,"v3-meta-trigger-second-10bps"),
 (40036167353,"v3-meta-trigger-second-50bps"),
 (40036464750,"v3-meta-risk-integration"),
 (40036590743,"v3-meta-structural-robustness"),
]
EXPORT={
 "v3-meta-cost-0bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-cost-10bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-cost-25bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-cost-50bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-cost-100bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-trigger-second-10bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-trigger-second-50bps":["ECONOMIC_SCORECARD.csv","PAIRED_21DAY_BLOCK.csv"],
 "v3-meta-risk-integration":["RISK_SCORECARD.csv","PAIRED_RISK_ALPHA.csv","YEARLY_RISK_ENSEMBLE.csv","RISK_MANIFEST.json"],
 "v3-meta-structural-robustness":["SUMMARY.json","YEARLY.csv","FIXED_BASKET_QUINTILES.csv","UNIQUE_TICKER_PAIR_EVENTS.csv","YEAR_EXCLUSION_STRESS.csv","ROBUSTNESS_BOOTSTRAP.csv"],
}
def digest(blob):return hashlib.sha256(blob).hexdigest()
def main():
    assert os.getenv("GH_TOKEN")
    ZIP.mkdir(parents=True,exist_ok=True)
    TABS.mkdir(parents=True,exist_ok=True)
    audit=[]
    with tempfile.TemporaryDirectory() as temp:
        for run,name in SOURCES:
            current=Path(temp)/name
            current.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                 "-n",name,"-D",str(current)],check=True)
            files=sorted(p for p in current.rglob("*") if p.is_file())
            assert files,(run,name)
            bundle=ZIP/(name+".zip")
            with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for file in files:z.write(file,file.relative_to(current).as_posix())
            with zipfile.ZipFile(bundle) as z:
                assert z.testzip() is None and len(z.namelist())==len(files)
            for selected in EXPORT[name]:
                matches=[p for p in files if p.name==selected]
                assert len(matches)==1,(name,selected)
                target=TABS/name/selected
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(matches[0],target)
            audit.append(dict(run_id=run,artifact_name=name,
                run_url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                bundle_path=str(bundle),bundle_bytes=bundle.stat().st_size,
                bundle_sha256=digest(bundle.read_bytes()),
                contents=[dict(path=p.relative_to(current).as_posix(),bytes=p.stat().st_size,
                  sha256=digest(p.read_bytes())) for p in files]))
            print("ARCHIVE_OK",run,name,bundle.stat().st_size,flush=True)
    assert len(audit)==9
    (ROOT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(dict(
        dated_checkpoint="2026-10-24",
        project="etf-trader-v3 corrected",
        production_files_modified=False,
        unchanged_corrected_first_stage_ranker_run=40016809498,
        frozen_causal_tree_run=40032282233,
        original_market_nextopen_replay=40032693599,
        fixed_etfs=149,canonical_baskets=500,months=101,
        experiment_count=len(audit),archives=audit),indent=2)+"\n")
    (ROOT/"README.md").write_text(
        "# V3 Corrected: verified tree robustness archive, 24 October 2026\n\n"
        "Nine complete artifacts reproduced locally in GitHub Actions and persisted as tracked V3 files.\n\n"
        "## Interpretation\n\n"
        "Research-only frozen-signal stress tests. No model/risk parameters tuned on CAGR.\n"
        "All historical 2018-2026 months were previously examined: NOT an independent holdout.\n"
        "Correlated baskets are not 50,500 independent data points.\n\n"
        "## Experiments\n\n"
        "- Fees: 0, 10, 25, 50, 100 bps on identical 500-basket next-open executed trades.\n"
        "- Tree correction gate, alternative held fixed as original ranker's runner-up (10/50bps).\n"
        "- Fixed original risk logic off/on for baseline vs tree (10bps), certified original no-risk equity parity within 1e-10.\n"
        "- OOS structural and regime stress: six-month paired bootstrap, exclusion of whole years, 786 unique ticker-pair-month events, clipped outliers and basket quintiles.\n\n"
        "## Files\n\n"
        "- `archives/*.zip`: all 9 complete original research outputs, including decisions and NAV paths.\n"
        "- `tables/<experiment>/*`: human-readable CSV summaries and audit tables.\n"
        "- `ARCHIVE_MANIFEST.json`: immutable GitHub Actions IDs and SHA-256 of every artifact and source file.\n"
        "- `../../ROBUSTNESS_COST_RISK_20261024.md`: methodology, numeric results, limitations and decisions.\n",
        encoding="utf8")
    print("FOLLOWUP_ARCHIVE_COMPLETE",len(audit),"bundles",flush=True)
if __name__=="__main__":main()
