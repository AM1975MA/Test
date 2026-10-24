#!/usr/bin/env python3
"""Reproducible source-of-truth archival of all completed V3 utility tests."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path

BASE=Path("etf-trader-v3 corrected/experiments/l00_rank_reg_fusion/results/utility_regret_20261024")
OUT=BASE/"archives";TABLE=BASE/"tables"
ARTIFACTS=[
 (40079852872,"v3-meta-hurdle-DT14"),
 (40079852872,"v3-meta-hurdle-DT_REGIME"),
 (40079852872,"v3-meta-hurdle-HGB_REGIME"),
 (40079852872,"v3-meta-hurdle-RF_REGIME"),
 (40080236687,"v3-meta-hurdle-aggregate-comparison"),
 (40080407962,"v3-meta-utility-econ-DT14_L15"),
 (40080407962,"v3-meta-utility-econ-HGB_REGIME_L15"),
 (40080407962,"v3-meta-utility-econ-RF_REGIME_L10"),
 (40080774850,"v3-meta-utility-calendar-exclusion"),
]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.getenv("GH_TOKEN"),"Only on verified GitHub Actions"
    OUT.mkdir(parents=True,exist_ok=True);TABLE.mkdir(parents=True,exist_ok=True)
    audit=[]
    with tempfile.TemporaryDirectory() as temp:
        for run,name in ARTIFACTS:
            inp=Path(temp)/name;inp.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                  "-n",name,"-D",str(inp)],check=True)
            files=sorted(p for p in inp.rglob("*") if p.is_file())
            assert files,(run,name)
            expected=(
                {"ECONOMIC_SCORECARD.csv","ACTUAL_DECISION_LOG.csv",
                 "PAIRED_21DAY_BLOCK.csv","ECONOMIC_MANIFEST.json"}
                if "-econ-" in name else
                {"AGGREGATE_SCORECARD.csv","FULL_COMPARISON_BOOTSTRAP.csv"}
                if "aggregate" in name else
                {"THROUGH_2025_VS_FULL2026.csv","YEAR_BY_YEAR_PATHS.csv"}
                if "calendar-exclusion" in name else
                {"SUMMARY.csv","CHANGED_DECISIONS.csv","FIT_AUDIT.csv",
                 "PAIRED_MONTHLY.csv","PAIRED_BOOTSTRAP.csv"}
            )
            names={p.name for p in files}
            assert expected<=names,(name,expected-names)
            archive=OUT/(name+".zip")
            with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for f in files:z.write(f,f.relative_to(inp).as_posix())
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None and len(z.namelist())==len(files)
            include=(expected|{"MANIFEST.json","YEARLY.csv","YEARLY_ENSEMBLE.csv",
                              "PAIRED_YEARLY_VS_INCUMBENT.csv","PAIRED_RISK_ALPHA.csv"})
            for f in files:
                if f.name in include:
                    path=TABLE/name/f.name;path.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(f,path)
            audit.append(dict(run_id=run,artifact=name,url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
                archive=str(archive),archive_size=archive.stat().st_size,
                sha256_archive=sha(archive),
                files=[dict(path=f.relative_to(inp).as_posix(),bytes=f.stat().st_size,
                    sha256=sha(f)) for f in files]))
            print("UTILITY_ARCHIVE_OK",run,name,len(files),archive.stat().st_size,flush=True)
    assert len(audit)==9
    (BASE/"ARCHIVE_MANIFEST.json").write_text(json.dumps(dict(
        checkpoint_date="2026-10-24",
        prior_source_first_stage_run=40016809498,
        prior_incumbent_nested_selector_run=40032282233,
        prior_economic_replay_run=40032693599,
        raw_prices_snapshot_run=39482809691,
        OOS_months=101,etfs=149,canonical_baskets=500,
        immutable_production_model=True,virgin_holdout=False,
        n_verified_archives=len(audit),artifacts=audit),indent=2)+"\n")
    (BASE/"README.md").write_text(
       "# V3 2026-10-24 — expected-regret hurdle model\n\n"
       "Nine verified immutable experiment archives, including all original changed "
       "ETF decisions and monthly OOS outcomes; SHA256 in ARCHIVE_MANIFEST.json.\n\n"
       "## Method\n\n"
       "4 families (Decision Tree original features, Decision Tree as-of-price-regime, "
       "HistGradientBoosting regime, Random Forest regime), 2 fixed downside aversion "
       "coefficients (1.0 and 1.5), fixed 20-bp proxy switch cost, quarterly mature-label "
       "meta refits with 60-calendar-day lag, 101 verified 500-basket months.\n\n"
       "Regime features use last known <= signal-date closes, 21/63-trading-day momentum, "
       "volatility, drawdown, breadth and SPY. No future price row admitted to features.\n\n"
       "## Files\n\n"
       "- archives/: all full original GitHub Actions results, zipped and checksum verified\n"
       "- tables/: direct CSV economic and forecast competence statistics\n"
       "- ARCHIVE_MANIFEST.json: source run IDs and immutable checksums\n"
       "- ../../EXPECTED_REGRET_RESULTS_20261024.md: interpretation and decision\n\n"
       "IMPORTANT: Previously researched historical 2018–2026 calendar is NOT an "
       "independent holdout; no variants have been promoted to production.\n")
    print("UTILITY_ARCHIVE_ALL_PASSED",len(audit),flush=True)
if __name__=="__main__":main()
