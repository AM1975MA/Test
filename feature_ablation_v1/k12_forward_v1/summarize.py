#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def find_results(root):
    out={}
    for p in Path(root).rglob("*.json"):
        try:r=json.loads(p.read_text())
        except:continue
        if r.get("status")=="COMPACT21_K12_FORWARD_BENCHMARK_COMPLETE":
            out[r["variant"]]=r
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inputs",required=True); ap.add_argument("--variants",required=True)
    ap.add_argument("--out",required=True); ap.add_argument("--md",required=True)
    a=ap.parse_args()
    spec=json.loads(Path(a.variants).read_text()); R=find_results(a.inputs)
    expected=set(spec["variants"])
    if set(R)!=expected: raise ValueError(f"Expected {sorted(expected)}, found {sorted(R)}")
    b=spec["base_reference"]; gate=spec["gate"]; rows=[]; advancing=[]
    for v in spec["variants"]:
        r=R[v]; ci=r["aggregate"]["common_inference"]; q=r["aggregate"]["quality"]
        m={"rank_mad":float(ci["rank_mean_abs"]),"stability_spearman":float(ci["mean_daily_spearman"]),"top1_disagreement":float(ci["top1_disagreement_fraction"]),"ndcg5":float(q["ndcg5"]),"top5_realized_overlap":float(q["top5_realized_overlap"])}
        improve=1-m["rank_mad"]/b["rank_mad"]; nr=m["ndcg5"]/b["ndcg5"]; tr=m["top5_realized_overlap"]/b["top5_realized_overlap"]
        adv=(improve>=gate["rank_mad_improvement_min"] and m["stability_spearman"]>=b["stability_spearman"] and m["top1_disagreement"]<=b["top1_disagreement"] and nr>=gate["ndcg5_ratio_min"] and tr>=gate["top5_realized_overlap_ratio_min"] and r["ALL_MATURITY_PASS"] and r["ALL_DETERMINISM_PASS"])
        row={"variant":v,"feature_count":r["feature_count"],**m,"rank_mad_improvement":improve,"ndcg5_ratio":nr,"top5_ratio":tr,"ADVANCE":adv}
        rows.append(row)
        if adv: advancing.append(v)
    eligible=[x for x in rows if x["ADVANCE"]]
    winner=min(eligible,key=lambda x:(x["feature_count"],x["rank_mad"],-x["top5_ratio"],-x["ndcg5_ratio"]))["variant"] if eligible else None
    res={"status":"COMPACT21_K12_FORWARD_SUMMARY_COMPLETE","base_reference":b,"gate":gate,"rows":rows,"advancing":advancing,"winner":winner}
    Path(a.out).write_text(json.dumps(res,indent=2)+"\n")
    lines=["# K12 -> K16 conditional forward ablation V1","",f"Winner: {winner or 'NONE'}",f"Advancing: {', '.join(advancing) if advancing else 'NONE'}","",
    "| Variant | N | Rank MAD | Δ Rank MAD | Top1 disag. | NDCG@5 | NDCG ratio | Top5 | Top5 ratio | Advance |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for x in rows:
        lines.append(f"| {x['variant']} | {x['feature_count']} | {x['rank_mad']:.6f} | {x['rank_mad_improvement']*100:.2f}% | {x['top1_disagreement']*100:.2f}% | {x['ndcg5']:.6f} | {x['ndcg5_ratio']*100:.2f}% | {x['top5_realized_overlap']*100:.2f}% | {x['top5_ratio']*100:.2f}% | {'YES' if x['ADVANCE'] else 'NO'} |")
    Path(a.md).write_text("\n".join(lines)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__": main()
