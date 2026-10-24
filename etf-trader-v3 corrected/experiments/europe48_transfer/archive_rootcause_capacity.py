#!/usr/bin/env python3
"""Archive six annual EU48 capacity ablations plus validated original EUR NAV replay.

Preserve original Actions ZIP contents, SHA256 for each file, and directly
inspectable annual + combined summary CSVs under V3 only.
"""
from __future__ import annotations
import hashlib,json,os,subprocess,tempfile,zipfile,shutil
from pathlib import Path
import pandas as pd,numpy as np
ROOT=Path("etf-trader-v3 corrected/experiments/europe48_transfer/results/rootcause_capacity_20261024")
A=ROOT/"archives";T=ROOT/"tables"
SOURCES=[(40112204947,f"v3-europe48-capacity-diagnostic-{y}") for y in range(2021,2027)]
SOURCES.append((40112595040,"v3-europe48-capacity-exact-portfolio"))
def sh(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()
def main():
    assert os.getenv("GH_TOKEN")
    A.mkdir(parents=True,exist_ok=True);T.mkdir(parents=True,exist_ok=True)
    manifest=[];df=[]
    with tempfile.TemporaryDirectory() as tmp:
        for run,name in SOURCES:
            p=Path(tmp)/name;p.mkdir()
            subprocess.run(["gh","run","download",str(run),"-R","AM1975MA/Test",
                "-n",name,"-D",str(p)],check=True)
            files=sorted(f for f in p.rglob("*") if f.is_file())
            assert len(files)>=3,(run,name)
            values={f.name for f in files}
            wanted=({"EUR48_CAPACITY_MONTHLY.csv","EUR48_CAPACITY_SCORECARD.csv","MANIFEST.json"}
                if "diagnostic-" in name else
                {"CAPACITY_REAL_EUR_SCORECARD.csv","CAPACITY_REAL_EUR_DAILY_NAV.csv",
                 "CAPACITY_REAL_EUR_MONTHLY_LEDGER.csv","CAPACITY_REAL_EUR_CALENDAR_YEARLY.csv","MANIFEST.json"})
            assert wanted<=values,(name,wanted-values)
            if "diagnostic-" in name:
                df.append(pd.read_csv(next(f for f in files if f.name=="EUR48_CAPACITY_MONTHLY.csv")))
            for key in wanted:
                source=next(f for f in files if f.name==key)
                target=T/name/key;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
            archive=A/(name+".zip")
            with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zip:
                for f in files:zip.write(f,f.relative_to(p).as_posix())
            with zipfile.ZipFile(archive) as z:
                assert z.testzip() is None and len(z.namelist())==len(files)
            manifest.append(dict(run_id=run,source_url=f"https://github.com/AM1975MA/Test/actions/runs/{run}",
              artifact=name,zip_size=archive.stat().st_size,zip_sha256=sh(archive),
              source_files=[dict(path=f.relative_to(p).as_posix(),bytes=f.stat().st_size,
                 sha256=sh(f)) for f in files]))
            print("VERIFIED_YEAR_OR_ECON",name,len(files),archive.stat().st_size,flush=True)
    assert len(manifest)==7
    z=pd.concat(df,ignore_index=True)
    assert len(z)==260 and z.signal_date.nunique()==65
    assert z.groupby("leaf").size().eq(65).all()
    z.sort_values(["signal_date","leaf"]).to_csv(T/"CAPACITY_ALL_65_MONTHS.csv",index=False)
    summary=z.groupby("leaf").agg(n=("signal_date","size"),
        top1_excess_21=("selected_excess_vs_48mean","mean"),
        top1_hit=("top1_winner","mean"),top3_hit=("top3_winner","mean"),
        selected_delta_vs_v2=("delta_ret21_vs_v2","mean"),
        avg_rank_corr_to_v2=("rho_vs_old_v2","mean"))
    summary.to_csv(T/"CAPACITY_OVERALL_SKILL.csv")
    rng=np.random.default_rng(20261024)
    piv=z.pivot(index="signal_date",columns="leaf",values="selected_excess_vs_48mean").sort_index()
    n=len(piv);N=5000;bl=3
    ix=((rng.integers(0,n,size=(N,(n+bl-1)//bl))[:,:,None]
        +np.arange(bl))%n).reshape(N,-1)[:,:n]
    a=[]
    for leaf in (15,31,63):
        delta=(piv[leaf]-piv[127]).to_numpy(float)
        boot=delta[ix].mean(axis=1)
        a.append(dict(leaves=leaf,against_127_delta_21D=float(delta.mean()),
            ci_low=float(np.quantile(boot,.025)),ci_high=float(np.quantile(boot,.975)),
            calendar_months=n,boot_block=bl,n_boot=N))
    pd.DataFrame(a).to_csv(T/"CAPACITY_PAIRED_MONTHLY_CI.csv",index=False)
    (ROOT/"ARCHIVE_MANIFEST.json").write_text(json.dumps(dict(
      date="2026-10-24",archived_bundles=7,n_mature_months=65,etfs=48,
      original_127_fits_reproduced=True,original_v2_v3_tree_econ_parity=True,
      future_holdout=False,historical_already_analysed=True,
      production_unmodified=True,source_runs=manifest),indent=2)+"\n")
    (ROOT/"README.md").write_text(
      "# Europe48 V3 Root Cause — 127 versus 15/31/63 XGBoost leaf capacity\n\n"
      "All original 6 annual full EU48 numeric training artifacts plus exact "
      "real EURO self-financing 10bp economic result saved under V3.\n\n"
      "Read [technical root cause report](../../ROOT_CAUSE_V3_EU48_20261024.md).\n\n"
      "See tables/ for 65 monthly selected returns, complete turnover and NAV, "
      "paired 3-calendar-month exploratory bootstrap and per-year fit manifest.\n\n"
      "Crucial: prior 2021-2026 market history was used to design/test prior "
      "configurations. 15 and 31 leaves are not approved production candidates "
      "until genuinely new prospective evaluation.\n")
    print("EU48_ROOT_CAUSE_ARCHIVE_SUCCESS",len(manifest),flush=True)
    print(summary.to_string(),flush=True)
if __name__=="__main__":main()
