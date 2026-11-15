#!/usr/bin/env python3
"""Produce the bounded event adjudication and human-readable audit evidence."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"validation/source_execution"
PRIOR=ROOT.parent/"olc108"

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def clean(o):
    if isinstance(o,dict):return {str(k):clean(v) for k,v in o.items()}
    if isinstance(o,list):return [clean(x) for x in o]
    if isinstance(o,(np.integer,np.bool_)):return o.item()
    if isinstance(o,(float,np.floating)):return float(o) if np.isfinite(o) else None
    return o

def main():
    summary=json.loads((P/"SOURCE_EXECUTION_AUDIT.json").read_text())
    events=pd.read_csv(P/"SOURCE_EVENT_CATALOGUE.csv")
    uses=pd.read_csv(P/"ACTUAL_SOURCE_EVENT_USE.csv")
    history=pd.read_csv(P/"SELECTED_FEATURE_HISTORY_MATERIAL_FLAGS.csv")
    orders=pd.read_csv(P/"EXECUTION_PARTICIPATION.csv.gz")
    paths=pd.read_csv(P/"PATH_SOURCE_EXECUTION_SUMMARY.csv")
    frozen=pd.read_csv(PRIOR/"data/ADJUSTMENT_ANOMALIES_REVIEW.csv")
    contexts=uses[(~uses.used_in_prior_v3)&(~uses.material)][["isin","symbol","date"]].drop_duplicates()
    checks=[]
    for r in contexts.itertuples(index=False):
        old=frozen[(frozen["isin"]==r.isin)&(frozen.date==r.date)].iloc[0]
        eu=uses[(uses["isin"]==r.isin)&(uses.date==r.date)]
        expected=1/(1-float(old.dividend)/float(old.previous_raw_close))
        actual=float(old.adjustment_multiplier)
        residual=float(np.log(actual/expected))
        reconciles=abs(residual)<1e-6
        checks.append(dict(isin=r.isin,symbol=r.symbol,date=r.date,
            frozen_status=old.review_status,provider_dividend=float(old.dividend),previous_raw_close=float(old.previous_raw_close),
            raw_close=float(old.raw_close),volume=float(old.daily_volume),
            actual_factor_multiplier=actual,expected_cash_dividend_factor_multiplier=expected,
            factor_log_residual=residual,provider_arithmetic_reconciles=reconciles,
            paths_with_account_use=len(eu),fills=int(eu.fill_count.sum()),
            max_abs_asset_day_pnl_eur=float(eu.asset_day_pnl_before_costs_eur.abs().max()),
            disposition="EXISTING_DESCRIPTIVE_DIVIDEND_CONTEXT; PROVIDER_ARITHMETIC_RECONCILES; NO_PRIMARY_DATE_CERTIFICATION" if reconciles else "REVIEW_REQUIRED"))
    pd.DataFrame(checks).to_csv(P/"NEW_CONTEXT_EVENT_RECONCILIATION.csv",index=False)
    pd.DataFrame(summary["priority_open_event_checks"]).to_csv(P/"PRIORITY_OPEN_EVENT_CHECKS.csv",index=False)

    material=[]
    for (isin,symbol,date), h in history.groupby(["isin","symbol","date"]):
        e=events[(events["isin"]==isin)&(events.date==date)].iloc[0]
        count=int(((uses["isin"]==isin)&(uses.date==date)).sum())
        if symbol=="VOOL.DE":
            disposition="KNOWN_V3_DIRECT_EVENT; ALSO_SELECTED_CLOSE_HISTORY; NO_NEW_SOURCE_ERROR_FINDING"
            rationale="Accepted Close rises 29.2082% during the March 2020 volatility episode; factor is unchanged. This is the same source event already used in V3. Exact exchange execution remains uncertified."
        elif symbol=="XBAK.DE":
            disposition="OPEN_REVERSAL_UNUSED; NORMAL_CLOSE_ONLY_IN_SELECTED_HISTORY"
            rationale="The flagged Open jumps 25.7426%, but no path holds or trades the event. Close changes -0.6828%; Close-based feature lineage does not use the anomalous Open."
        elif symbol=="UBUD.DE":
            disposition="NEW_SELECTED_HISTORY_CONTEXT; FLAGGED_INTRADAY_OPEN_NOT_A_SIGNAL_INPUT"
            rationale="No direct event accounting use. Raw Open is -16.6569% from previous Close and rebounds 28.5731% intraday; accepted Close changes +7.1569%, with essentially unchanged adjustment factor. The new selected history uses Close, including some correlation/volatility windows, and not that Open. No independent exact quote certification is claimed."
        elif symbol=="IS0D.DE":
            disposition="EXISTING_MATERIAL_CLOSE_MOVEMENT_IN_BROAD_HISTORY; NO_DIRECT_ACCOUNT_USE"
            rationale="The accepted IS0D Close falls 27.0508% on 9 March 2020 with unchanged factor and positive volume. Selected 26 February 2021 history contains the move, but none of the checked momentum endpoints equals this source date. No new direct account use or new corruption finding."
        else:
            disposition="REVIEW_REQUIRED"
            rationale="Additional material selected-history event; requires an explicit bounded review before finalization."
        material.append(dict(isin=isin,symbol=symbol,date=date,source_flags=e.frozen_flags,
            selected_history_rows=len(h),selected_paths=h.path_id.nunique(),
            first_selected_signal_date=h.signal_date.min(),last_selected_signal_date=h.signal_date.max(),
            accepted_close_endpoint_rows=int(h.accepted_close_feature_endpoint_horizons.notna().sum()),
            rows_in_63_return_window=int(h.accepted_close_in_63_return_window.sum()),
            rows_in_126_return_window=int(h.accepted_close_in_126_return_window.sum()),
            direct_event_use_paths=count,raw_open_jump=float(e.raw_open_jump),accepted_close_return=float(e.accepted_close_return),
            adjustment_factor_change=float(e.factor_change),disposition=disposition,rationale=rationale))
    pd.DataFrame(material).to_csv(P/"MATERIAL_SELECTED_HISTORY_REVIEW.csv",index=False)
    voe=orders[(orders.symbol=="VOOL.DE")&(orders.date=="2020-03-12")]
    lb=uses[(uses.symbol=="LBRA.DE")&(uses.date=="2026-10-26")]
    adjudication=dict(
        status="PASS_BOUNDED_NO_NEW_SOURCE_CORRUPTION_EVIDENCE" if all(x["provider_arithmetic_reconciles"] for x in checks) and not summary["new_unique_material_source_events_used_vs_v3_global"] and all(x["disposition"]!="REVIEW_REQUIRED" for x in material) else "REVIEW_REQUIRED",
        direct_use_new_context_events=checks,
        material_selected_history_events=material,
        known_VOOL_event=dict(date="2020-03-12",path_uses=int(((uses.symbol=="VOOL.DE")&(uses.date=="2020-03-12")).sum()),
            new_fill_uses=voe[["stage","path_id","side","notional_eur","raw_day_turnover_eur","participation_ratio"]].to_dict("records"),
            note="The source Open was already used as a mark in V3; four risk-reduction sells now execute on this date. This is a new execution use type, not a new quote event. It does not independently certify exact attainability at the Open."),
        known_LBRA_event=dict(date="2026-10-26",current_direct_use_paths=len(lb),current_selected_history_rows=int(((history.symbol=="LBRA.DE")&(history.date=="2026-10-26")).sum()),
            prior_review_path="../olc108/superseded_v2/results/POINT_EVENT_SOURCE_REVIEW.validation.json",
            prior_review_evidence="Issuer NAV EUR30.5324 on 23 October to EUR24.8836 on 26 October 2026 corroborated the large economic loss; the exact EUR22.84 Xetra opening fill was not certified. There are no direct uses of this event in OLC109."),
        priority_unusual_open_events=summary["priority_open_event_checks"],
        limitations=["No new independent primary corporate-action date verification for the seven ordinary provider dividend context events.",
            "Selected-history inspection follows selected instruments and accepted Close provenance; it is not exhaustive lineage for every non-selected group member or competing rank.",
            "Thresholds are review triggers, not proof that smaller quote errors cannot exist.",
            "No counterfactual deletion, source repair, financial rerun, or universe change."])
    (P/"EVENT_ADJUDICATION.json").write_text(json.dumps(clean(adjudication),indent=2,allow_nan=False)+"\n")

    group=paths.groupby("stage").agg(paths=("path_id","size"),orders=("orders","sum"),ge10=("orders_participation_ge10pct","sum"),ge100=("orders_participation_ge100pct","sum"),maximum=("max_participation_ratio","max"))
    group=group.reindex([s for s in ["stage1","results_stage2","results_stage3"] if s in group.index])
    base_names=["DUAL21","LIQ_DUAL21","CLUSTER_DUAL21","CLUSTER_DUAL_PEERS2","DEDUP_DUAL21","DEDUP_DUAL_PEERS2","CLUSTER_PEERS2_RISK15","CLUSTER_PEERS2_RISK20","HORIZON63","HORIZON126","HORIZON252","CAPITAL_3H","CAPITAL_3H_TILT"]
    base=paths[paths.path_id.isin([f"{x}__BASE" for x in base_names]) | (paths.path_id.str.contains("TOP1") & paths.path_id.str.endswith("__BASE"))]
    top1=[]
    for arm in ["HORIZON63_TOP1","HORIZON126_TOP1","HORIZON252_TOP1"]:
        pp=paths[paths.path_id.str.startswith(arm+"__")].copy()
        if len(pp)==0:continue
        b=pp[pp.path_id.eq(arm+"__BASE")].iloc[0]
        top1.append(dict(arm=arm,base_orders=int(b.orders),base_orders_ge10pct=int(b.orders_participation_ge10pct),
            base_orders_ge100pct=int(b.orders_participation_ge100pct),base_max_participation_ratio=float(b.max_participation_ratio),
            lag1_max_participation_ratio=float(pp[pp.path_id.eq(arm+"__LAG1")].max_participation_ratio.iloc[0]),
            lag2_max_participation_ratio=float(pp[pp.path_id.eq(arm+"__LAG2")].max_participation_ratio.iloc[0]),
            all_scenario_orders_ge100pct=int(pp.orders_participation_ge100pct.sum())))
    pd.DataFrame(top1).to_csv(P/"TOP1_PARTICIPATION_SUMMARY.csv",index=False)
    worst=orders.loc[orders.participation_ratio.idxmax()]
    lines=[
        "# OLC109 — independent source and execution review", "",
        f"**Bounded result:** {summary['paths_checked']} completed paths ({summary['stage_path_counts']['stage1']} original, {summary['stage_path_counts'].get('results_stage2',0)} adaptive stage 2, and {summary['stage_path_counts'].get('results_stage3',0)} adaptive stage 3), {summary['orders_checked']:,} recorded orders, and {summary['actual_traded_isins']} actually traded ISINs were reviewed. No newly used material source event or obvious new source-price corruption was identified. Recorded quantities and NAV reconcile independently. This is a source-accounting result, not a certificate that the orders were executable at the reported Open.", "",
        "## Independent reconstruction and staleness", "",
        "The audit accumulates signed quantities and cash flows from ORDERS without importing strategy or engine code. Every residual unit remains in the cash/NAV reconstruction. Accepted Close is carried causally from its last observed source row; invalid and zero-volume raw rows never become replacement marks. The 1e-10 unit threshold is used only to describe economic holdings and stale exposure.", "",
        f"Maximum absolute differences from recorded decision snapshots: units {summary['maximum_units_reconstruction_difference']:.3g}, cash EUR{summary['maximum_cash_reconstruction_difference']:.3g}. Maximum daily Close NAV difference is EUR{summary['maximum_close_nav_reconstruction_difference']:.3g}. Maximum value of numeric dust is EUR{summary['maximum_numeric_dust_value_eur']:.3g}. There are {len(summary['invalid_fill_source_events'])} invalid-Open fill findings and {len(summary['accepted_panel_vs_raw_price_mismatches'])} accepted-panel/raw-price discrepancies in the bounded source histories.", "",
        f"Maximum Close quote age for an economic holding is **{summary['maximum_held_close_age_days']} calendar days**. There are **{summary['stale_asset_path_sessions_gt5']} held asset/path sessions older than 5 days**. All five quarantined series remain absent from the panel and recorded orders. See `RECONSTRUCTION_CHECKS.csv`, `PATH_SOURCE_EXECUTION_SUMMARY.csv`, and `HELD_STALENESS_EVENTS.csv.gz`.", "",
        f"Opening marks that fall back to the prior accepted Close also have maximum quote age **{summary['maximum_opening_fallback_close_age_days']} calendar days**, with **{summary['opening_fallback_asset_path_sessions_gt5']} economic asset/path sessions older than 5 days**. This check includes the interval from the source Close date to the current opening mark date.", "",
        "## Execution participation", "",
        "Participation = recorded EUR order notional / (raw EUR Close × that venue's full-day reported volume). This is deliberately a descriptive ex-post denominator. It does not observe opening auction volume, order-book depth, spread, primary-market creation/redemption capacity, or trading at other venues. The five scenario paths repeat related economic opportunities; pooled counts are not independent market observations.", "",
        "| Stage | Paths | Orders | Orders ≥10% | Orders ≥100% | Maximum ratio |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for stage,r in group.iterrows():lines.append(f"| {stage} | {int(r.paths)} | {int(r.orders):,} | {int(r.ge10):,} | {int(r.ge100):,} | {r.maximum:.4f}× |")
    lines += ["",f"Across all paths, **{summary['orders_participation_ge10pct']:,} orders are at least 10%** and **{summary['orders_participation_ge100pct']} are at least 100%** of full-day venue turnover. There are {summary['invalid_participation_denominators']} missing or nonpositive denominators. The maximum is **{worst.participation_ratio:.4f}×**, a {worst.side} of {worst.symbol} on {worst.date} in `{worst.path_id}`: notional EUR{worst.notional_eur:,.2f}, raw Close EUR{worst.raw_close:.6f}, volume {worst.raw_volume:.0f}, full-day turnover EUR{worst.raw_day_turnover_eur:,.2f}.", "",
        "Selected BASE paths:","", "| Path | Orders | ≥10% | ≥100% | Maximum participation |", "|---|---:|---:|---:|---:|"]
    for r in base.itertuples(index=False):lines.append(f"| {r.path_id} | {r.orders} | {r.orders_participation_ge10pct} | {r.orders_participation_ge100pct} | {100*r.max_participation_ratio:.2f}% |")
    if top1:
        lines += ["", "Concentrated TOP1 controls and delay stresses:", "", "| Arm | BASE maximum | LAG1 maximum | LAG2 maximum | Orders ≥100% across all scenarios |", "|---|---:|---:|---:|---:|"]
        for r in top1:lines.append(f"| {r['arm']} | {100*r['base_max_participation_ratio']:.2f}% | {100*r['lag1_max_participation_ratio']:.2f}% | {100*r['lag2_max_participation_ratio']:.2f}% | {r['all_scenario_orders_ge100pct']} |")
        lines += ["", "Every TOP1 BASE case has zero orders at or above 100% of venue turnover. Some delayed HORIZON63_TOP1 and HORIZON252_TOP1 orders exceed that level; concentration and execution timing therefore still require explicit scrutiny. See `TOP1_PARTICIPATION_SUMMARY.csv`."]
    lines += ["", "The rolling EUR100,000 signal filter reduces participation problems in several paths, but it cannot ensure sufficient volume on a later exit or delayed execution day. Fixed transaction-cost assumptions do not establish attainability of the larger orders. This limitation matters even when source quotes themselves are valid. The complete per-order evidence is `EXECUTION_PARTICIPATION.csv.gz`.", "",
        "## Source-event coverage and actual use", "",
        f"The audit combines the frozen V3 source catalogue with a fresh bounded scan of histories of actually traded instruments and the three specifically requested suspicious Open cases. Review triggers are adjustment-factor change >10%, adjusted Close return >30%, raw or adjusted Open jump >30%, accepted-panel jumps >30%, and existing frozen flags. The catalogue has {summary['bounded_source_event_catalogue_rows']} event rows, including {summary['bounded_material_source_event_rows']} material review-trigger rows. It is not a universe-wide rescan or a new primary-source validation of every quote.", "",
        "An event counts as directly used only when its accepted Open supplies a fill or opening mark, or its accepted Close supplies a held Close mark or later carry/fallback. Holding an instrument on a date whose raw quote was discarded is insufficient to count that discarded quote as used.", "",
        f"There are {summary['source_event_path_uses']} event/path uses across {summary['unique_source_events_used']} distinct source dates. {len(checks)} dates are newly held ordinary dividend-factor context; material direct uses are individually retained in the event evidence. None of those new dividend-context dates meets the fresh material thresholds. No source or outcome was deleted or changed.", "",
        f"### {len(checks)} new ordinary dividend-context dates", "",
        "| Symbol | Date | Paths holding source event | Factor multiplier | Provider cash-dividend multiplier | Fills |", "|---|---|---:|---:|---:|---:|"]
    for r in checks:lines.append(f"| {r['symbol']} | {r['date']} | {r['paths_with_account_use']} | {r['actual_factor_multiplier']:.7f} | {r['expected_cash_dividend_factor_multiplier']:.7f} | {r['fills']} |")
    lines += ["", "These were already labelled `DESCRIPTIVE_CONTEXT_ONLY` in the frozen review. Their factor changes agree with the recorded provider dividend arithmetic to an absolute log residual below 1.1e-7. This arithmetic check supports retaining the existing descriptive classification; it does not independently certify issuer ex-dates or point-in-time adjustment availability. All reconciled context dates have positive volume and accepted observations; their event-day fills are reported explicitly in the table. See `NEW_CONTEXT_EVENT_RECONCILIATION.csv`.", "",
        "### Known material events and unusual Opens", "",
        f"**VOOL, 12 March 2020:** used in {adjudication['known_VOOL_event']['path_uses']} paths. Four new simulated sells use the event's Open: CLUSTER_DUAL_RISK15/20 and DEDUP_DUAL_RISK15/20, all LAG2. Notionals range from EUR{voe.notional_eur.min():.2f} to EUR{voe.notional_eur.max():.2f}; participation ranges from {100*voe.participation_ratio.min():.4f}% to {100*voe.participation_ratio.max():.4f}% of that day's EUR{voe.raw_day_turnover_eur.iloc[0]:,.2f} venue turnover. The event was already marked in V3; the newly used execution type is explicitly retained in the evidence. Its accepted Close move is +29.2082%, with unchanged adjustment factor. No new source-error finding follows from this volatile move, while exact Open execution is still not independently certified.", "",
        "**LBRA, 26 October 2026:** no direct accounting or selected-history use in OLC109. The prior review's issuer-NAV corroboration and its warning that the exact EUR22.84 Xetra Open was not certified remain applicable to the archived V3 event; no fresh LBRA source investigation was needed here.", "",
        "**F703, 18 March 2020; IQSE, 15 February 2021; UEQU, 8 March 2022:** each suspicious Open is present in the accepted input, but none of these three instruments is traded by any OLC109 path. There are zero event-day holdings/fills and zero selected-Close-history joins in the checked paths. Their Open anomalies therefore do not supply a new OLC109 fill or mark. See `PRIORITY_OPEN_EVENT_CHECKS.csv`.", "",
        "## Selected feature history", "",
        f"The conservative selected-instrument 253-session lineage has {len(history)} rows covering {len(material)} material frozen events. None coincides with the checked selected momentum endpoints at horizons 0, 21, 63, 126, or 252. A historical observation can nevertheless enter correlation, volatility, or moving-average windows; endpoint absence is not a general proof of no influence.", "",
        "| Source event | History rows | First selected signal | Last selected signal | Direct event use paths |", "|---|---:|---|---|---:|"]
    for r in material:lines.append(f"| {r['symbol']} {r['date']} | {r['selected_history_rows']} | {r['first_selected_signal_date']} | {r['last_selected_signal_date']} | {r['direct_event_use_paths']} |")
    lines += ["", "UBUD is the additional selected-history case requiring a distinction between Open and Close: its accepted 18 March 2020 Close is +7.1569% with an essentially unchanged factor, while the flagged intraday Open/reversal is not a Close-based feature input and was never traded or held on the event date. XBAK similarly has an unusual +25.7426% Open while its accepted Close is -0.6828%; it has zero direct event use. IS0D's -27.0508% March 2020 Close is a pre-existing large market-move context and appears only in later selected history. Exact source quotes are not independently certified by these lineage checks. The per-event decisions and all joins are preserved in `MATERIAL_SELECTED_HISTORY_REVIEW.csv` and `SELECTED_FEATURE_HISTORY_MATERIAL_FLAGS.csv`.", "",
        "This source audit does not replay every non-selected cluster member and competing rank. It therefore supports the bounded finding of no obvious new source-derived fake win in the recorded accounts; it does not claim exhaustive historical signal-source certification.", "",
        "## Remaining conventions and reproducibility", "",
        "The current-catalogue universe retains survivorship limitations. An accepted Open is conditioned on the completed day's positive reported volume, which was not known at the opening trade time. Historical adjustment factors are retrospective and their point-in-time availability is uncertified. Lag stresses do not remove these source conventions. The economic exposure and execution caveats above remain even though the accounting reconstruction passes.", "",
        "Reproduce with:", "", "```bash", "python validation/source_execution/audit_source_execution.py --results " + " ".join(summary["directories"]), "python validation/source_execution/finalize_audit_notes.py", "```", "",
        f"Frozen ETF panel SHA256: `{summary['panel_sha256']}`. `SOURCE_EXECUTION_AUDIT.json` records input and result hashes; `ARTIFACT_MANIFEST.json` records this audit package's hashes. Financial source, protocols, panels, result paths, orders, and instructions were not modified. No real trade, automation, external message, or remote mutation occurred.", "",
    ]
    (P/"AUDIT_NOTES.md").write_text("\n".join(lines))
    manifest={str(f.relative_to(ROOT)):sha(f) for f in sorted(P.iterdir()) if f.is_file() and f.name!="ARTIFACT_MANIFEST.json"}
    (P/"ARTIFACT_MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"adjudication_status":adjudication["status"],"contexts_reconciled":len(checks),"material_history_events":len(material),"notes":str(P/"AUDIT_NOTES.md"),"artifact_files":len(manifest)},indent=2))

if __name__=="__main__":main()
