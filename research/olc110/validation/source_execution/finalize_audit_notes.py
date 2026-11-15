#!/usr/bin/env python3
"""Finalize OLC110 source findings without changing prices, rules, or accounts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"validation/source_execution"
OLD=ROOT.parent/"olc109/validation/source_execution"
RAW=ROOT.parent/"olc108"


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()


def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,(np.integer,np.bool_)):return x.item()
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x


def write_json(name,data):
    (OUT/name).write_text(json.dumps(clean(data),indent=2,allow_nan=False)+"\n")


def read(name):return pd.read_csv(OUT/name,float_precision="round_trip")


def main():
    s=json.loads((OUT/"SOURCE_EXECUTION_AUDIT.json").read_text())
    assert s["paths_checked"]==78
    events=read("SOURCE_EVENT_CATALOGUE.csv");uses=read("ACTUAL_SOURCE_EVENT_USE.csv")
    history=read("SELECTED_FEATURE_HISTORY_MATERIAL_FLAGS.csv");orders=read("EXECUTION_PARTICIPATION.csv.gz")
    paths=read("PATH_SOURCE_EXECUTION_SUMMARY.csv");priority=read("PRIORITY_OPEN_EVENT_CHECKS.csv")
    original=json.loads((OLD/"EVENT_ADJUDICATION.json").read_text())
    point_path=RAW/"superseded_v2/results/POINT_EVENT_SOURCE_REVIEW.validation.json"
    point=json.loads(point_path.read_text())
    archive_checks=[]
    for src in point["sources"]:
        if src.get("key") not in ("LBRA_NAV_20261023","LBRA_NAV_20261026"):continue
        archive=RAW/"superseded_v2/results/source_event_archives"/Path(src["archive_path"]).name
        actual=sha(archive)
        assert actual==src["sha256"], "INHERITED_PRIMARY_ARCHIVE_HASH_MISMATCH"
        archive_checks.append(dict(source_key=src["key"],path=str(archive),sha256=actual,archived_primary_evidence_unchanged=True,
            url=src["url"],facts=src["facts"]))
    assert len(archive_checks)==2
    context_source=RAW/"data/ADJUSTMENT_ANOMALIES_REVIEW.csv"
    adjustments=pd.read_csv(context_source,float_precision="round_trip")
    contexts=uses[(~uses.used_in_olc109)&(~uses.material)][["isin","symbol","date"]].drop_duplicates()
    context_checks=[]
    for r in contexts.itertuples():
        old=adjustments[(adjustments["isin"]==r.isin)&(adjustments.date==r.date)]
        assert len(old)==1,("UNEXPECTED_CONTEXT",r.isin,r.date)
        old=old.iloc[0]; actual=float(old.adjustment_multiplier)
        expected=1/(1-float(old.dividend)/float(old.previous_raw_close))
        residual=float(np.log(actual/expected))
        uu=uses[(uses["isin"]==r.isin)&(uses.date==r.date)]
        good=abs(residual)<1e-6 and old.review_status=="DESCRIPTIVE_CONTEXT_ONLY"
        context_checks.append(dict(isin=r.isin,symbol=r.symbol,date=r.date,
            frozen_review_status=old.review_status,provider_dividend=float(old.dividend),
            previous_raw_close=float(old.previous_raw_close),actual_factor_multiplier=actual,
            expected_dividend_factor_multiplier=expected,log_residual=residual,
            arithmetic_reconciles=good,account_use_paths=len(uu),open_fills=int(uu.open_fill_count.sum()),
            close_fills=int(uu.close_fill_count.sum()),primary_ex_date_independently_rechecked=False,
            disposition="RETAIN_EXISTING_DIVIDEND_CONTEXT_WITH_DATE_VINTAGE_LIMIT" if good else "REVIEW_REQUIRED"))
    pd.DataFrame(context_checks).to_csv(OUT/"NEW_CONTEXT_EVENT_RECONCILIATION.csv",index=False)
    material=[]
    material_keys=set(zip(uses.loc[uses.material,"isin"],uses.loc[uses.material,"date"]))
    material_keys |= set(zip(history["isin"],history.date))
    for isin,date in sorted(material_keys):
        event=events[(events["isin"]==isin)&(events.date==date)].iloc[0]
        uu=uses[(uses["isin"]==isin)&(uses.date==date)]
        hh=history[(history["isin"]==isin)&(history.date==date)]
        if isin=="LU0832435464" and date=="2020-03-12":
            disposition="RETAIN_KNOWN_V3_AND_OLC109_VOLATILITY_EVENT"
            rationale=("Same accepted source event used by V3 and OLC109. Accepted Close rose 29.2082%, adjustment factor unchanged, "
                "positive volume. OLC110 adds no event-day fill; all 78 accounts hold the event. Close-based trend/monitoring "
                "lineage includes it. No new quote corruption evidence; exact venue quote and depth are not independently certified.")
            evidence=str(OLD/"EVENT_ADJUDICATION.json")
        elif isin=="LU1900066207" and date=="2026-10-26":
            disposition="RETAIN_KNOWN_ISSUER_NAV_CORROBORATED_LOSS_AND_OPEN_EXECUTION_LIMIT"
            rationale=("New direct use versus OLC109, but the unchanged source event was already independently reviewed in OLC108/V3. "
                "Archived issuer NAV fell from EUR30.5324 to EUR24.8836 (-18.5010%); source Close fell 19.6950%, "
                "Open 25.0902%, factor unchanged and volume 169561. The broad economic loss is corroborated. "
                "The exact EUR22.84 Open and executable spread/depth remain uncertified; issuer NAV is not a substitute quote. "
                "Retain both losses on FRESH holdings and REFRESH_WEEKLY gains from buying at that Open. "
                "NEXT_CLOSE never uses the Open as a fill/mark and is separately recorded at EUR24.48500061035156. "
                "No deletion, replacement with NAV, or financial rerun.")
            evidence=str(point_path)
        else:
            prior=[r for r in original.get("material_selected_history_events",[]) if r["isin"]==isin and r["date"]==date]
            if prior:
                disposition="RETAIN_PRIOR_BOUNDED_SOURCE_EVENT_JUDGMENT_WITH_CURRENT_USE_COUNTS"
                rationale="Prior OLC109 assessment retained; its historical use counts are not asserted for OLC110. Prior rationale: "+prior[0]["rationale"]
                evidence=str(OLD/"EVENT_ADJUDICATION.json")
            else:
                disposition="REVIEW_REQUIRED"
                rationale="New material source/history use has not been independently adjudicated. No source change is authorized by this audit."
                evidence=""
        material.append(dict(isin=isin,symbol=event.symbol,date=date,old_review_status=event.old_review_status,
            frozen_flags=event.frozen_flags,new_direct_use_vs_olc109=not bool(event.used_in_olc109),
            current_direct_use_paths=len(uu),current_open_use_paths=int(uu.source_open_used.sum()),
            current_close_use_paths=int(uu.source_close_used.sum()),open_fills=int(uu.open_fill_count.sum()),
            close_fills=int(uu.close_fill_count.sum()),selected_or_monitored_history_rows=len(hh),
            selected_history_paths=hh.path_id.nunique(),first_history_signal=hh.signal_date.min() if len(hh) else None,
            last_history_signal=hh.signal_date.max() if len(hh) else None,
            endpoint_history_rows=int(hh.accepted_close_feature_endpoint_horizons.notna().sum()),
            min_asset_day_pnl_eur=float(uu.asset_day_pnl_before_costs_eur.min()) if len(uu) else None,
            max_asset_day_pnl_eur=float(uu.asset_day_pnl_before_costs_eur.max()) if len(uu) else None,
            max_abs_pnl_prior_nav_share=float(uu.asset_day_pnl_prior_nav_share.abs().max()) if len(uu) else None,
            accepted_close_return=event.accepted_close_return,accepted_open_jump=event.accepted_open_jump,
            factor_change=event.factor_change,raw_volume=event.volume,disposition=disposition,rationale=rationale,
            inherited_evidence_path=evidence,inherited_evidence_sha256=sha(evidence) if evidence else None))
    pd.DataFrame(material).to_csv(OUT/"MATERIAL_EVENT_ADJUDICATION.csv",index=False)
    pd.DataFrame(material).to_csv(OUT/"MATERIAL_SELECTED_HISTORY_REVIEW.csv",index=False)
    material_uses=uses[uses.material].copy()
    material_uses["abs_pnl_prior_nav_share"]=material_uses.asset_day_pnl_prior_nav_share.abs()
    material_uses.sort_values("abs_pnl_prior_nav_share",ascending=False).to_csv(OUT/"MATERIAL_EVENT_ACCOUNT_IMPACT.csv",index=False)
    controls={"BASE","STATIC_HALF","STATIC_75","REFRESH_WEEKLY"}
    paths["family"]=np.where(paths.arm.isin(controls),"CONTROL","DYNAMIC_CASH")
    base=paths[paths.scenario=="BASE"].sort_values("cagr",ascending=False)
    dynamic_base=base[~base.arm.isin(controls)]
    best=str(base.iloc[0].arm);best_dynamic=str(dynamic_base.iloc[0].arm)
    path_columns=["path_id","arm","scenario","execution_quote","family","cagr","orders",
        "orders_participation_ge10pct","orders_participation_ge100pct","maximum_participation_ratio",
        "maximum_held_close_age_days","maximum_execution_fallback_close_age_days"]
    paths[path_columns].to_csv(OUT/"ALL_78_PATH_CAPACITY_SUMMARY.csv",index=False)
    arm_totals=paths.groupby(["arm","family"],sort=True).agg(paths=("path_id","size"),orders=("orders","sum"),
        orders_ge10pct=("orders_participation_ge10pct","sum"),orders_ge100pct=("orders_participation_ge100pct","sum"),
        maximum_participation=("maximum_participation_ratio","max")).reset_index()
    arm_totals.to_csv(OUT/"ALL_ARMS_PARTICIPATION_SUMMARY.csv",index=False)
    selected_arms=list(dict.fromkeys(["BASE",s["primary_arm"],best,best_dynamic,"EXIT21_STAGED_FRESHD"]))
    focus=paths[paths.arm.isin(selected_arms)].copy()
    focus[path_columns].to_csv(OUT/"PRIMARY_AND_OBSERVED_BEST_CAPACITY.csv",index=False)
    scenario=paths.groupby(["scenario","execution_quote"]).agg(paths=("path_id","size"),orders=("orders","sum"),
        ge10=("orders_participation_ge10pct","sum"),ge100=("orders_participation_ge100pct","sum"),
        maximum=("maximum_participation_ratio","max")).reset_index()
    scenario.to_csv(OUT/"SCENARIO_PARTICIPATION_SUMMARY.csv",index=False)
    allowed=(not s["status"].startswith("FAIL") and all(r["arithmetic_reconciles"] for r in context_checks)
        and all(r["disposition"]!="REVIEW_REQUIRED" for r in material))
    adjudication=dict(status="PASS_BOUNDED_KNOWN_EVENT_AND_EXECUTION_LIMITS_RETAINED" if allowed else "REVIEW_REQUIRED",
        source_checks_status=s.get("initial_source_checks_status",s["status"]),paths=78,material_events=material,new_context_events=context_checks,
        inherited_primary_archive_checks=archive_checks,priority_open_checks=priority.to_dict("records"),
        observed_best_BASE_arm=best,observed_best_dynamic_BASE_arm=best_dynamic,
        no_inputs_or_financial_results_modified=True,no_source_or_loss_deleted=True,
        limits=["Provider dividend arithmetic does not certify issuer ex-date or historical factor vintage.",
            "Known source-event economic corroboration does not certify exact Open/Close attainability or auction depth.",
            "New uses include both adverse and favorable recorded outcomes; neither is excluded.",
            "Review thresholds and selected/monitored lineage are bounded checks, not exhaustive proof that every source quote is correct."])
    write_json("EVENT_ADJUDICATION.json",adjudication)
    s["initial_source_checks_status"]=s.get("initial_source_checks_status",s["status"])
    s["status"]=adjudication["status"]
    s["event_adjudication_status"]=adjudication["status"]
    s["adjudication_evidence_sha256"]={str(point_path):sha(point_path),str(context_source):sha(context_source),
        str(OLD/"EVENT_ADJUDICATION.json"):sha(OLD/"EVENT_ADJUDICATION.json"),
        **{r["path"]:r["sha256"] for r in archive_checks}}
    write_json("SOURCE_EXECUTION_AUDIT.json",s)
    worst=orders.loc[orders.participation_ratio.idxmax()]
    lines=["# OLC110 — Independent source and execution audit","",
        f"**Result: {adjudication['status']}.** All **78 frozen paths**, **{s['orders_checked']:,} recorded orders**, and "
        f"**{s['actual_traded_isins']} traded ISINs** were examined. There are **{len(s['new_traded_isins_vs_olc109'])} newly traded ISINs** "
        "versus the complete OLC109 set. No wrong accepted-quote fill, accepted-panel/raw-price mismatch, liquidity-source mismatch, or new obvious quote corruption was found in this bounded review. "
        "The 2026 Brazil-fund event is newly used relative to OLC109, but its earlier primary-source adjudication is retained. Execution capacity remains materially uncertain.","",
        "## Frozen scope and independent reconstruction","",
        f"The protocol SHA256 is `{s['protocol_sha256']}`. The audit requires the completed 13 × 6 matrix and checks its input/code hashes against the pre-result freeze. "
        "It imports neither strategy nor engine, creates no strategy account, and changes no prices, quarantine, protocol, order, decision, or financial result. "
        "Quantities and cash are accumulated solely from recorded orders using round-trip CSV parsing. This source-usage reconstruction supplements the separate full financial/state audit.","",
        f"Maximum unit discrepancy is **{s['max_units_reconstruction_error']:.3g}**, cash discrepancy **EUR{s['max_cash_reconstruction_error']:.3g}**, "
        f"pretrade-mark NAV discrepancy **EUR{s['max_pretrade_mark_nav_error']:.3g}**, and Close NAV discrepancy **EUR{s['max_close_nav_reconstruction_error']:.3g}**. "
        f"Numeric dust never exceeds EUR{s['max_numeric_dust_value']:.3g}. There are {len(s['invalid_fill_source_events'])} invalid-fill findings, "
        f"{len(s['accepted_panel_raw_mismatches'])} accepted-price/source discrepancies, and {len(s['liquidity_mismatches'])} turnover discrepancies. "
        "Both quarantine files are byte-identical to OLC109; all five quarantined series remain absent.","",
        f"Economic holding Close age and execution-fallback Close age both peak at **{s['maximum_held_close_age_days']} calendar days**. "
        f"There are **{s['stale_asset_path_sessions_gt5']} held asset/path sessions** and **{s['execution_fallback_asset_sessions_gt5']} fallback asset/path sessions** older than five days. "
        "The 1e-10 quantity threshold is used only to describe economic holdings/staleness; all signed numerical residuals remain in reconstruction.","",
        "## NEXT_CLOSE is a separate execution convention","",
        "The 65 original-scenario paths execute against accepted Open and the independent Open mask. The 13 NEXT_CLOSE paths execute against accepted Close and the Close-observation mask. "
        "For NEXT_CLOSE, the field named `nav_open` is the Close valuation before fees, not an opening quote. Its reported drawdown samples Close pre/post fees and does not measure intraday loss. "
        "The audit records `execution_quote`, Open fills, Close fills, Open-source use, Close-source use, and fallback marks separately. NEXT_CLOSE trades are never labelled as Open executions. "
        "Full-day turnover is only a descriptive denominator in both modes; neither opening nor closing auction capacity is observed.","",
        "## Participation and capacity","",
        "Participation = recorded EUR notional / (raw EUR Close × the venue's reported full-day volume). "
        "There are no missing/nonpositive denominators and no invalid-geometry raw Close denominators among recorded orders. "
        "This ratio does not observe spread, order-book depth, auction volume, market-maker inventory, creations/redemptions, or trading on other venues. "
        "The six scenarios repeat related opportunities; pooled counts are not independent observations.","",
        "| Scenario | Quote | Paths | Orders | ≥10% of daily turnover | ≥100% | Maximum ratio |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for r in scenario.itertuples():lines.append(f"| {r.scenario} | {r.execution_quote} | {r.paths} | {r.orders:,} | {r.ge10:,} | {r.ge100:,} | {r.maximum:.4f}× |")
    lines += ["",f"Across the matrix, **{s['orders_participation_ge10pct']:,} orders are ≥10%** and **{s['orders_participation_ge100pct']} are ≥100%** of full-day venue turnover. "
        f"The largest is **{worst.participation_ratio:.4f}×**: `{worst.path_id}`, {worst.side} {worst.symbol} on {worst.date}, "
        f"notional **EUR{worst.notional_eur:,.2f}**, volume **{worst.raw_volume:.0f}**, full-day turnover **EUR{worst.raw_day_turnover_eur:,.2f}**.","",
        "All thirteen BASE accounts:","",
        "| Arm | Orders | ≥10% | ≥100% | Maximum ratio |","|---|---:|---:|---:|---:|"]
    for r in base.itertuples():lines.append(f"| {r.arm} | {r.orders} | {r.orders_participation_ge10pct} | {r.orders_participation_ge100pct} | {r.maximum_participation_ratio:.4f}× |")
    lines += ["",f"The predeclared primary is **{s['primary_arm']}**; the observed highest BASE CAGR is **{best}**, and the highest dynamic-protection BASE CAGR is **{best_dynamic}**. "
        "This is a description after the fixed matrix, not an added strategy-selection test. Their full six-scenario capacity records, including FRESHD, are in `PRIMARY_AND_OBSERVED_BEST_CAPACITY.csv`. "
        "All arm/scenario counts are in `ALL_78_PATH_CAPACITY_SUMMARY.csv` and six-scenario totals for every cash/control model in `ALL_ARMS_PARTICIPATION_SUMMARY.csv`.","",
        "The primary FRESHW BASE has one order at 3.3002× full-day turnover. FRESHD BASE has five orders above 100%, with maximum 4.2839×. "
        "EXIT63_STAGED BASE has no order above 100% but a maximum of 93.04%; its LAG1 maximum reaches 3.1345×. "
        "The existing EUR100,000 median-turnover eligibility condition does not guarantee sufficient volume on a later exit or delayed fill day. "
        "Fixed transaction costs cannot establish that the reported price was attainable for these quantities.","",
        "## Actual use of reviewed source events","",
        f"The bounded scan covers **{s['scanned_instruments']} histories**, comprising recorded traded/selected/monitored identities and three priority Open cases. "
        f"The catalogue retains **{s['source_event_catalogue_rows']} event rows**, including **{s['material_source_event_rows']} material review-trigger rows**. "
        f"There are **{s['source_event_path_uses']} source-event/path uses across {s['unique_source_events_used']} distinct source dates**. "
        "A discarded raw row is not counted as used just because its instrument was held that day: the audit traces accepted quote provenance, including carried Close and fallback marks.","",
        "### Known VIX futures event: 12 March 2020","",
        "VOOL is held by all 78 accounts on this date, with zero event-day fills. Its accepted Close rises 29.2082% with unchanged factor and positive volume. "
        "The event was already used in V3 and OLC109. Its source history enters the current strategy/monitoring lineage, but the audit identifies no new corruption finding or independently certified exchange execution price.","",
        "### Newly used Brazil event: 26 October 2026","",
        "LBRA is newly used relative to OLC109 in 12 paths: nine Open-scenario paths and three NEXT_CLOSE paths. "
        "Six Open-scenario FRESH accounts retain the adverse held-fund move; the two NEXT_CLOSE FRESH accounts also retain their loss. "
        "Three REFRESH_WEEKLY Open accounts buy at EUR22.84 and receive the recorded intraday rebound; the NEXT_CLOSE weekly account buys at EUR24.48500061035156 and receives no same-day price PnL. "
        "These are four buys in total, comprising three Open and one Close fills.","",
        "The archived issuer NAV moves from EUR30.5324 to EUR24.8836, a loss of 18.5010%, corroborating a large economic decline. "
        "The source Close falls 19.6950%, the Open 25.0902%, with unchanged adjustment factor and reported volume 169,561. "
        "Both primary NAV archive hashes match the previous independent review. Exact Open EUR22.84, spread, and auction depth remain uncertified; issuer NAV is not substituted for a venue quote. "
        "The BASE primary FRESHW loses EUR1,709.67 before costs on this source date; FRESHD BASE loses EUR2,049.21. REFRESH_WEEKLY BASE records EUR566.41 of intraday gain before costs. "
        "All of these outcomes remain unchanged. See `MATERIAL_EVENT_ACCOUNT_IMPACT.csv` and `MATERIAL_EVENT_ADJUDICATION.csv`.","",
        "### New ordinary dividend context","",
        f"Five dates are newly used descriptive factor/dividend context. All reconcile with the provider dividend arithmetic; the maximum absolute log residual is "
        f"**{max(abs(r['log_residual']) for r in context_checks):.3g}**. This checks arithmetic consistency, not issuer ex-dates, currency treatment, or historical adjustment-factor availability.","",
        "| Symbol | Date | Paths | Open fills | Close fills | Factor multiplier |","|---|---|---:|---:|---:|---:|"]
    for r in context_checks:lines.append(f"| {r['symbol']} | {r['date']} | {r['account_use_paths']} | {r['open_fills']} | {r['close_fills']} | {r['actual_factor_multiplier']:.8f} |")
    lines += ["","The earlier source review's distinction between arithmetic consistency and correct ex-date remains essential; no new primary dividend-date certification is claimed. "
        "See `NEW_CONTEXT_EVENT_RECONCILIATION.csv`.","",
        "## Selected and daily-monitored source history","",
        f"There are **{s['selected_material_history_rows']:,} potential material Close-source lineage rows**: 7,812 for VOOL and eight for LBRA. "
        "The audit includes raw targets, selected monthly identities, slot asset/base identities, and daily monitoring even when no order is emitted. "
        "This broader coverage is not directly comparable to OLC109's monthly selected-history count. "
        "Lineage includes carried source observations at the oldest endpoint and reports endpoints at 0/1/5/10/21/63/126/252 sessions, SMA windows, volatility21, and correlation126 price windows. "
        "Membership in a window is potential influence, not proof that a particular ranking or exit changed because of that observation.","",
        "The three priority suspicious Open cases (F703 2020-03-18, IQSE 2021-02-15, UEQU 2022-03-08) remain absent from all actual trades and selected/monitored history. "
        "They have zero event-day accounting use and zero fills in either mode. Close-based feature lineage does not use an unusual Open merely because the date shares an instrument identity.","",
        "## Remaining limits","",
        "The current catalogue does not reconstruct all closed or delisted funds. Historical source-adjustment vintages are uncertified. "
        "Original accepted Opens depend on the completed day's positive volume, which is not information available at the Open. NEXT_CLOSE changes price timing but does not repair survivorship or adjustment vintage. "
        "Fractional economic units, zero cash interest, omitted taxes, and source Open/Close proxies remain research conventions. "
        "Review thresholds do not rule out smaller source errors. The audit does not replay every rejected competitor or establish source correctness across the entire historical universe. "
        "A source-accounting pass is not certification that the portfolio could trade at the quoted auction prices. "
        "The negative protection results are preserved and no additional threshold or financial arm was tested.","",
        "## Reproduction and files","","```bash",
        "python validation/source_execution/audit_source_execution.py",
        "python validation/source_execution/finalize_audit_notes.py","```","",
        "`SOURCE_EXECUTION_AUDIT.json` records all financial-result and input hashes, including the frozen panel/turnover and source CSVs. "
        "`EVENT_ADJUDICATION.json` retains inherited judgments and primary archive checks. `FINAL_VERIFICATION.json` records the final unchanged-input checks. "
        "`ARTIFACT_MANIFEST.json` hashes the audit package, excluding active log files. No real order, automation, external message, source download, or remote mutation was performed.",""]
    (OUT/"AUDIT_NOTES.md").write_text("\n".join(lines))
    unchanged=[path for path,digest in s["input_and_result_sha256"].items() if sha(path)!=digest]
    assert not unchanged,("INPUT_OR_RESULT_MUTATED",unchanged)
    assert sha(OUT/"audit_source_execution.py")==s["audit_script_sha256"]
    verification=dict(status="PASS" if allowed else "REVIEW_REQUIRED",paths=78,orders=s["orders_checked"],
        input_result_hashes_checked=len(s["input_and_result_sha256"]),changed_inputs_or_results=unchanged,
        core_audit_script_hash_matches=True,primary_archives_verified=len(archive_checks),
        original_source_prices_and_financial_results_unchanged=True,
        finalizer_sha256=sha(__file__),adjudication_status=adjudication["status"])
    write_json("FINAL_VERIFICATION.json",verification)
    artifacts={path.name:sha(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name!="ARTIFACT_MANIFEST.json" and path.suffix!=".log"}
    write_json("ARTIFACT_MANIFEST.json",artifacts)
    print(json.dumps(clean(verification),indent=2))


if __name__=="__main__":main()
