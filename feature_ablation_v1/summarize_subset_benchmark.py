#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

VARIANTS=("BASE125","K8","K12","K16","K24","K32","K40","FAMILY46")

def find_results(root:Path):
    out={}
    for p in root.rglob("*.json"):
        try: r=json.loads(p.read_text())
        except Exception: continue
        if r.get("status")=="COMPACT21_ORTHOGONAL_SUBSET_BENCHMARK_COMPLETE":
            out[r["variant"]]=r
    if set(out)!=set(VARIANTS):
        raise ValueError(f"Expected {VARIANTS}, found {sorted(out)}")
    return out

def metric(r,scope,key): return float(r["aggregate"][scope][key])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--inputs",required=True); ap.add_argument("--out",required=True); ap.add_argument("--md",required=True)
    a=ap.parse_args(); R=find_results(Path(a.inputs)); b=R["BASE125"]
    base={
      "rank_mad":metric(b,"common_inference","rank_mean_abs"),
      "stability_spearman":metric(b,"common_inference","mean_daily_spearman"),
      "top1_disagreement":metric(b,"common_inference","top1_disagreement_fraction"),
      "top5_jaccard":metric(b,"common_inference","top5_jaccard"),
      "ndcg5":metric(b,"quality","ndcg5"),
      "top5_realized_overlap":metric(b,"quality","top5_realized_overlap"),
      "target_spearman":metric(b,"quality","daily_spearman_vs_target")
    }
    rows=[]; advancing=[]
    for v in VARIANTS:
        r=R[v]
        m={
          "rank_mad":metric(r,"common_inference","rank_mean_abs"),
          "stability_spearman":metric(r,"common_inference","mean_daily_spearman"),
          "top1_disagreement":metric(r,"common_inference","top1_disagreement_fraction"),
          "top5_jaccard":metric(r,"common_inference","top5_jaccard"),
          "ndcg5":metric(r,"quality","ndcg5"),
          "top5_realized_overlap":metric(r,"quality","top5_realized_overlap"),
          "target_spearman":metric(r,"quality","daily_spearman_vs_target")
        }
        improve=0.0 if v=="BASE125" else 1.0-m["rank_mad"]/base["rank_mad"]
        ndcg_ratio=m["ndcg5"]/base["ndcg5"]
        top5_ratio=m["top5_realized_overlap"]/base["top5_realized_overlap"]
        pass_gate=(v!="BASE125" and improve>=0.25 and m["stability_spearman"]>=base["stability_spearman"] and m["top1_disagreement"]<=base["top1_disagreement"] and ndcg_ratio>=0.95 and top5_ratio>=0.95 and r["ALL_MATURITY_PASS"] and r["ALL_DETERMINISM_PASS"])
        pair_diag={}
        for pair in ("1-2","1-3","2-3"):
            cand=float(r["aggregate_by_pair"]["common_inference"][pair]["rank_mean_abs"])
            bb=float(b["aggregate_by_pair"]["common_inference"][pair]["rank_mean_abs"])
            pair_diag[pair]={"rank_mad":cand,"base":bb,"improvement":0.0 if v=="BASE125" else 1.0-cand/bb}
        row={"variant":v,"feature_count":r["feature_count"],**m,"rank_mad_improvement":improve,"ndcg5_ratio":ndcg_ratio,"top5_overlap_ratio":top5_ratio,"maturity_PASS":r["ALL_MATURITY_PASS"],"determinism_PASS":r["ALL_DETERMINISM_PASS"],"pair_diagnostics":pair_diag,"ADVANCE":pass_gate}
        rows.append(row)
        if pass_gate: advancing.append(v)
    qualified=[x for x in rows if x["variant"]!="BASE125" and x["ndcg5_ratio"]>=0.95 and x["top5_overlap_ratio"]>=0.95]
    best_quality_preserving=min(qualified,key=lambda x:(x["rank_mad"],x["top1_disagreement"],-x["ndcg5"]))["variant"] if qualified else None
    res={"status":"COMPACT21_ORTHOGONAL_SUBSET_BENCHMARK_SUMMARY_COMPLETE","acceptance_gate":{"rank_mad_improvement_min":0.25,"stability_spearman_no_worse":True,"top1_disagreement_no_worse":True,"ndcg5_ratio_min":0.95,"top5_realized_overlap_ratio_min":0.95,"maturity_required":True,"determinism_required":True},"baseline":base,"rows":rows,"advancing":advancing,"best_quality_preserving_diagnostic":best_quality_preserving}
    Path(a.out).write_text(json.dumps(res,indent=2,allow_nan=False)+"\n")
    lines=["# COMPACT21 ORTHOGONAL SUBSET BENCHMARK","",f"Advancing variants: {', '.join(advancing) if advancing else 'NONE'}","", "| Variant | N | Rank MAD | Δ Rank MAD | Top1 disag. | NDCG@5 | NDCG ratio | Top5 realized | Top5 ratio | Advance |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for x in rows:
        lines.append(f"| {x['variant']} | {x['feature_count']} | {x['rank_mad']:.6f} | {x['rank_mad_improvement']*100:.2f}% | {x['top1_disagreement']*100:.2f}% | {x['ndcg5']:.6f} | {x['ndcg5_ratio']*100:.2f}% | {x['top5_realized_overlap']*100:.2f}% | {x['top5_overlap_ratio']*100:.2f}% | {'YES' if x['ADVANCE'] else 'NO'} |")
    lines += ["",f"Best quality-preserving diagnostic candidate: {best_quality_preserving or 'NONE'}","", "No strategy CAGR/P&L is used by this benchmark or gate."]
    Path(a.md).write_text("\n".join(lines)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__": main()
