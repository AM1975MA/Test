"""Read-only forensic decomposition of final OLC108 V3. No strategy simulation.

Reconstructs existing holdings from archived executed orders; explains existing
NAV by instrument and calendar period; enriches existing selections using only
data known by their signal close. Writes exclusively beside this script.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2] / "olc108"
EXPECTED = "14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96"


def native(x):
    if isinstance(x, dict): return {str(k): native(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [native(v) for v in x]
    if isinstance(x, np.ndarray): return native(x.tolist())
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating, float)): return float(x) if np.isfinite(x) else None
    if isinstance(x, np.bool_): return bool(x)
    if isinstance(x, pd.Timestamp): return x.strftime("%Y-%m-%d")
    return x


def theme(name):
    s = str(name).lower()
    for label, tokens in [
        ("VIX futures", ["vix futures"]),
        ("Blockchain/crypto equities", ["blockchain", "crypto"]),
        ("Korea equities", ["korea"]),
        ("Gold-mining equities", ["gold miner", "gold mining", "gold producers", "pure gold", "gold bugs"]),
        ("Silver-mining equities", ["silver miner"]),
        ("Hydrogen equities", ["hydrogen"]),
        ("Clean-energy equities", ["clean energy", "clean edge", "solar"]),
        ("Oil/gas equities", ["oil & gas", "energy sector", "energy select sector", "world energy", "usa energy", "europe energy", "energy infrastructure", "oil services"]),
        ("Semiconductors", ["semiconductor"]),
        ("China technology/internet", ["china internet", "china technology", "hang seng tech"]),
        ("China equities", ["china"]),
        ("Brazil equities", ["brazil"]),
        ("Pakistan equities", ["pakistan"]),
        ("Poland equities", ["poland"]),
        ("Greece equities", ["greece"]),
        ("Turkey equities", ["turkey"]),
        ("Indonesia equities", ["indonesia"]),
        ("Thailand equities", ["thailand"]),
        ("Mexico equities", ["mexico"]),
        ("GCC equities", ["gcc select"]),
        ("Battery/lithium equities", ["battery", "lithium"]),
        ("Automotive equities", ["automobiles"]),
        ("Private-equity listed equities", ["private equity"]),
        ("AI/robotics equities", ["artificial intelligence"]),
        ("Gaming equities", ["gaming"]),
        ("Telecom equities", ["telecommunications"]),
        ("Travel/leisure equities", ["travel & leisure"]),
        ("Long-duration government bonds", ["treasury bond 20+", "government bond 25+"]),
        ("Broad commodity futures", ["commodity index", "bloomberg commodity", "commodity ex-agriculture"]),
        ("Real-estate equities", ["real estate", "epra", "property yield"]),
        ("Utilities equities", ["utilities"]),
        ("Bank equities", ["banks"]),
        ("Uranium equities", ["uranium"]),
        ("Genomics/biotechnology", ["genomic", "biotech"]),
        ("Space equities", ["space innovator"]),
        ("Cybersecurity equities", ["cybersecurity"]),
        ("Cloud-computing equities", ["cloud computing"]),
        ("Rare-earth/mining equities", ["rare earth", "strategic metals"]),
    ]:
        if any(t in s for t in tokens): return label
    return "Other / not classified"


def main():
    manifest = json.loads((ROOT / "results/RUN_MANIFEST.json").read_text())
    assert manifest["data_revision"] == 3
    panel_path = ROOT / "source/data/XETRA_EUR_ETF.npz"
    digest = hashlib.sha256(panel_path.read_bytes()).hexdigest()
    assert digest == EXPECTED == manifest["source_hashes"]["XETRA_EUR_ETF"]
    with np.load(panel_path, allow_pickle=False) as z:
        p = {k: z[k] for k in z.files}
    dates = pd.DatetimeIndex(p["dates"])
    names = p["names"]
    obs = p["observed"]
    C = pd.DataFrame(np.where(obs & np.isfinite(p["C"]) & (p["C"] > 0), p["C"], np.nan)).ffill().to_numpy()
    coverage = pd.read_csv(ROOT / "data/UNIVERSE_COVERAGE.csv").set_index("isin")
    catalogue = pd.read_csv(ROOT / "data/XETRA_EUR_CATALOGUE.csv").set_index("ISIN")
    scores = pd.read_csv(ROOT / "results/SCORECARD.csv")
    annual_source = pd.read_csv(ROOT / "results/ANNUAL_RETURNS.csv")
    published_pnl = pd.read_csv(ROOT / "results/HOLDINGS_PNL_ATTRIBUTION.csv")
    corrs = pd.read_csv(ROOT / "results/TARGET_PAIR_CORRELATIONS.csv.gz")
    observed_counts = obs.cumsum(axis=0)
    price_cache = {}

    def identity(j):
        isin = str(names[j]); row = coverage.loc[isin]
        provider_name = str(row.provider_name)
        if provider_name == "nan": provider_name = str(row.catalogue_name)
        return {"isin": isin, "symbol": str(row.symbol), "name": provider_name,
                "theme_proxy": theme(provider_name)}

    def selected_features(j, k):
        ident = identity(j); c = C[:, j]
        valid = np.flatnonzero(obs[:k + 1, j])
        first = int(valid[0]); row = coverage.loc[str(names[j])]
        listing = pd.to_datetime(row.listing_first_date)
        f = dict(**ident, signal_date=str(dates[k].date()), observed_history=int(observed_counts[k, j]),
                 observed_in_last253=int(obs[max(0, k-252):k+1, j].sum()),
                 observed_history_age_days=int((dates[k] - dates[first]).days),
                 listing_age_days=int((dates[k] - listing).days),
                 first_valid_date=str(dates[first].date()), listing_date=str(listing.date()))
        for h in (21, 63, 126, 252): f[f"return_{h}"] = c[k] / c[k-h] - 1
        for h in (63, 126, 200):
            mean = np.mean(c[k-h+1:k+1]); f[f"above_sma{h}_ratio"] = c[k] / mean - 1
        f["absolute_trend_200_and_252"] = bool(f["above_sma200_ratio"] > 0 and f["return_252"] > 0)
        symbol = ident["symbol"]
        if symbol not in price_cache:
            raw = pd.read_csv(ROOT / "data/prices" / (symbol + ".csv.gz"), parse_dates=["date"]).set_index("date")
            raw = raw[~raw.index.duplicated(keep="last")].reindex(dates)
            turnover = raw.volume * raw.close
            ok = obs[:, j] & np.isfinite(turnover) & (turnover > 0)
            price_cache[symbol] = np.where(ok, turnover, np.nan)
        tv = price_cache[symbol]
        for h in (63, 252):
            v = tv[max(0, k-h+1):k+1]
            f[f"prior{h}_positive_turnover_sessions"] = int(np.isfinite(v).sum())
            f[f"prior{h}_median_positive_turnover_eur"] = float(np.nanmedian(v))
            f[f"prior{h}_mean_turnover_zero_missing_eur"] = float(np.nansum(v) / len(v))
        return f

    def ranked_pnl(v, ids, denominator):
        records = []
        for idx in np.argsort(v):
            if abs(v[idx]) < 1e-7: continue
            j = ids[idx]
            records.append(dict(**identity(j), net_pnl_eur=float(v[idx]), contribution_pp=float(100*v[idx]/denominator)))
        return records

    paths = scores[(scores.universe == "XETRA_EUR_ETF") & (scores.scenario == "BASE")]
    paths = paths[~((paths.arm == "PASSIVE") & (paths.cadence == "WEEKLY"))]
    output = dict(scope="Final OLC108 V3 only; descriptive, no new strategy runs or optimization",
                  source_sha256=digest, window="2020-03-02 through 2026-10-30",
                  limitations=["2020 and 2026 are partial calendar years.",
                    "Current Xetra catalogue plus available provider histories is not a survivorship-free historical universe.",
                    "Theme labels are name-based proxies, not verified holdings overlap or a full derivative-exposure audit.",
                    "Turnover is archived Xetra raw daily volume times raw close, filtered by final V3 observed mask; it is not market-wide ETF liquidity or executable bid/ask capacity.",
                    "V3 source eligibility uses complete daily volume retrospectively; original results are already research on a seen sample.",
                    "Contributions explain existing accounts arithmetically; they do not identify predictive or causal relations.",
                    "Sampled drawdown uses archived open-before-fees and close NAV, not intraday lows."])
    results = {}
    all_selections = []
    for score in paths.to_dict("records"):
        path = score["path_id"]; d = ROOT / "results" / path
        daily = pd.read_csv(d / "DAILY.csv.gz")
        orders = pd.read_csv(d / "ORDERS.csv.gz")
        decisions = pd.read_csv(d / "DECISIONS.csv")
        ids = np.array(sorted(orders.j.unique()), dtype=int)
        local = {int(j): z for z, j in enumerate(ids)}
        ix = daily.k.to_numpy(dtype=int); T = len(ix); n = len(ids)
        delta = np.zeros((T, n)); fee = np.zeros((T, n))
        for o in orders.itertuples(index=False):
            t = int(o.execution_idx) - int(ix[0]); j = local[o.j]
            delta[t, j] += o.quantity * (1 if o.side == "BUY" else -1)
            fee[t, j] += o.cost
        units = delta.cumsum(axis=0); old = np.vstack([np.zeros((1, n)), units[:-1]])
        opening = np.where(p["open_observed"][ix][:, ids] & np.isfinite(p["O"][ix][:, ids]) & (p["O"][ix][:, ids] > 0), p["O"][ix][:, ids], C[ix-1][:, ids])
        overnight = np.nan_to_num(old * (opening - C[ix-1][:, ids]), nan=0.)
        intraday = np.nan_to_num(units * (C[ix][:, ids] - opening), nan=0.) - fee
        pnls = overnight + intraday
        nav = daily.nav_close.to_numpy(); opening_nav = daily.nav_open.to_numpy()
        max_daily_error = float(np.max(np.abs(pnls.sum(axis=1) - np.diff(np.r_[10000, nav]))))
        assert max_daily_error < 1e-6, (path, max_daily_error)
        published = published_pnl[published_pnl.path_id == path].set_index("ticker")
        max_lifetime_error = max(abs(pnls[:, z].sum() - published.loc[str(names[j]), "net_pnl"]) for z, j in enumerate(ids))
        assert max_lifetime_error < 1e-6
        segments = np.stack([overnight, intraday], axis=1).reshape(2*T, n)
        chain = np.r_[10000, np.column_stack([opening_nav, nav]).ravel()]
        assert np.max(np.abs(segments.sum(axis=1) - np.diff(chain))) < 1e-6

        def chain_label(pos):
            if pos == 0: return "INITIAL:2020-03-02"
            return daily.date.iloc[(pos-1)//2] + (":OPEN" if (pos-1) % 2 == 0 else ":CLOSE")

        def dd_between(start, finish):
            sub = chain[start:finish+1]
            dd = sub / np.maximum.accumulate(sub) - 1
            trough = start + int(dd.argmin())
            peak = start + int(np.argmax(chain[start:trough+1]))
            pnl = segments[peak:trough].sum(axis=0)
            assert abs(pnl.sum() - (chain[trough] - chain[peak])) < 1e-6
            recoveries = np.flatnonzero(chain[trough+1:] >= chain[peak])
            recovery = chain_label(trough+1+int(recoveries[0])) if len(recoveries) else None
            ranking = ranked_pnl(pnl, ids, chain[peak])
            return {"peak": chain_label(peak), "trough": chain_label(trough), "recovery": recovery,
                    "drawdown": float(dd.min()), "peak_nav": float(chain[peak]), "trough_nav": float(chain[trough]),
                    "loss_eur": float(chain[trough]-chain[peak]), "contributors": ranking}

        worst = dd_between(0, len(chain)-1)
        assert abs(worst["drawdown"] - score["maxdd_sampled"]) < 1e-12
        annual = []
        years = pd.to_datetime(daily.date).dt.year.to_numpy()
        exposure = np.nan_to_num(units*C[ix][:,ids], nan=0.) / nav[:, None]
        themes = np.array([identity(j)["theme_proxy"] for j in ids])
        for year in sorted(set(years)):
            ts = np.flatnonzero(years == year); first, last = int(ts[0]), int(ts[-1])
            base = 10000 if first == 0 else nav[first-1]
            pnl = pnls[ts].sum(axis=0)
            annual_return = nav[last]/base - 1
            published_ann = annual_source[(annual_source.path_id == path) & (annual_source.year == year)]["return"].iloc[0]
            assert abs(annual_return - published_ann) < 1e-12
            theme_rows = []
            for th in sorted(set(themes)):
                m = themes == th
                theme_rows.append({"theme_proxy": th, "contribution_pp": float(100*pnl[m].sum()/base),
                                   "mean_close_exposure": float(exposure[ts][:, m].sum(axis=1).mean())})
            annual.append(dict(year=int(year), annual_return=float(annual_return), start_nav=float(base),
                               costs_eur=float(fee[ts].sum()), costs_pp=float(100*fee[ts].sum()/base),
                               contributors=ranked_pnl(pnl, ids, base),
                               themes=sorted(theme_rows, key=lambda r:r["contribution_pp"]),
                               worst_drawdown=dd_between(2*first, 2*(last+1))))
        selection_rows = []
        for q, dec in decisions.iterrows():
            meta = json.loads(dec.meta_json); k = int(dec.signal_idx)
            next_k = int(decisions.signal_idx.iloc[q+1]) if q+1 < len(decisions) else int(ix[-1])
            for slot, j in enumerate(meta.get("selected_indices", []), 1):
                f = selected_features(j, k)
                localj = local[int(j)]
                interval = (ix > k) & (ix <= next_k)
                before = 10000 if k < ix[0] else nav[int(k-ix[0])]
                f.update(path_id=path, arm=score["arm"], cadence=score["cadence"], risk=score["risk"],
                         slot=slot, role=("annual_leader" if j in meta.get("leader_indices", []) else "challenger"),
                         opportunity_used=bool(meta.get("opportunity_used", False)),
                         interval_end=str(dates[next_k].date()), next_interval_sessions=int(interval.sum()),
                         next_interval_net_pnl_eur=float(pnls[interval, localj].sum()),
                         next_interval_account_contribution_pp=float(100*pnls[interval, localj].sum()/before))
                selected_first_open = C[k, j]
                if k+1 < len(dates) and p["open_observed"][k+1, j]: selected_first_open = p["O"][k+1,j]
                f["next_interval_open_to_close_price_return"] = float(C[next_k, j]/selected_first_open - 1)
                f["next_open_half_nav_vs_prior63_mean_turnover"] = float(.5*before/f["prior63_mean_turnover_zero_missing_eur"]) if f["prior63_mean_turnover_zero_missing_eur"] > 0 else None
                selection_rows.append(f)
                all_selections.append(f)
        selected_df = pd.DataFrame(selection_rows)
        cp = corrs[corrs.path_id == path]
        pairs = []
        for q, dec in decisions.iterrows():
            meta = json.loads(dec.meta_json); s = meta.get("selected_indices", [])
            if len(s) != 2: continue
            a, b = [identity(j) for j in s]
            c = cp[cp.signal_date == dec.signal_date]
            pair = {"signal_date": dec.signal_date, "symbol1": a["symbol"], "symbol2": b["symbol"],
                    "name1": a["name"], "name2": b["name"], "theme1": a["theme_proxy"], "theme2": b["theme_proxy"],
                    "same_classified_theme": a["theme_proxy"] == b["theme_proxy"] != "Other / not classified",
                    "trailing126_corr": float(c.trailing126_corr.iloc[0]) if len(c) else None}
            pairs.append(pair)
        first_selected = selected_df.sort_values("signal_date").groupby("isin", sort=False).first().reset_index().to_dict("records")
        pairs_df = pd.DataFrame(pairs)
        concentration = {"pair_decisions": len(pairs),
                         "same_classified_theme_count": int(pairs_df.same_classified_theme.sum()) if len(pairs) else 0,
                         "corr_above090_count": int((pairs_df.trailing126_corr > .90).sum()) if len(pairs) else 0,
                         "corr_median": float(pairs_df.trailing126_corr.median()) if len(pairs) else None,
                         "same_theme_pairs": [x for x in pairs if x["same_classified_theme"]],
                         "pairs": pairs}
        results[path] = dict(scorecard=score, max_daily_pnl_reconciliation_error=max_daily_error,
                             max_lifetime_asset_reconciliation_error=float(max_lifetime_error),
                             global_drawdown=worst, annual=annual, concentration=concentration,
                             lifetime_contributors=ranked_pnl(pnls.sum(axis=0), ids, 10000),
                             first_selections=first_selected, selections=selection_rows)
        print(path, "annual DD reconstructed", "maxerr", max_daily_error, flush=True)

    output["paths"] = results
    selected_df = pd.DataFrame(all_selections)
    diagnostic_groups = []
    for keys, g in selected_df.groupby(["arm", "cadence", "risk"]):
        if keys[0] == "PASSIVE": continue
        for feature, mask in [("absolute_trend_pass", g.absolute_trend_200_and_252),
                              ("absolute_trend_fail", ~g.absolute_trend_200_and_252),
                              ("positive_21_session_momentum", g.return_21 > 0),
                              ("nonpositive_21_session_momentum", g.return_21 <= 0),
                              ("observations_under_504", g.observed_history < 504),
                              ("observations_atleast_504", g.observed_history >= 504)]:
            z = g[mask]
            diagnostic_groups.append(dict(arm=keys[0], cadence=keys[1], risk=keys[2], condition=feature,
                                           selected_asset_intervals=len(z),
                                           mean_next_interval_return=float(z.next_interval_open_to_close_price_return.mean()),
                                           median_next_interval_return=float(z.next_interval_open_to_close_price_return.median()),
                                           negative_next_interval_share=float((z.next_interval_open_to_close_price_return < 0).mean()),
                                           sum_account_contribution_pp=float(z.next_interval_account_contribution_pp.sum())))
    output["diagnostic_groups"] = diagnostic_groups
    output["diagnostic_group_caveat"] = "Overlapping and dependent selected-asset intervals; groups were inspected retrospectively, price returns omit trading costs and are not strategy performance. Sum of interval contributions is not a compounded full-period return. No causal or predictive inference is asserted."
    output["same_state_annual"] = pd.read_csv(ROOT / "results/SAME_STATE_ANNUAL.csv").query("universe == 'XETRA_EUR_ETF' and control == 'leaders'").to_dict("records")
    output["same_state_summary"] = pd.read_csv(ROOT / "results/SAME_STATE_SUMMARY.csv").query("universe == 'XETRA_EUR_ETF' and control == 'leaders'").to_dict("records")
    critical = []
    event_days = ["2023-11-30", "2023-12-28", "2023-12-29", "2024-01-02", "2024-01-05", "2024-01-12", "2024-01-19", "2024-01-31"]
    for isin in ["IE00BMDKNW35", "IE000XAGSCY5"]:
        j = int(np.flatnonzero(names == isin)[0])
        for day in event_days:
            k = int(dates.get_loc(pd.Timestamp(day)))
            critical.append(selected_features(j, k))
    output["critical_2024_blockchain_event_features"] = critical
    (OUT / "diagnosis_v3.json").write_text(json.dumps(native(output), indent=2, allow_nan=False) + "\n")
    summary = dict(source_sha256=digest, scope=output["scope"], limitations=output["limitations"], paths={})
    focus_symbols = {"VOOL.DE", "IQQH.DE", "ETLX.DE", "QCLN.DE", "DAVV.DE", "HYCN.DE", "BLCH.DE", "JEDI.DE", "FLXK.DE", "KWBE.DE", "LKOR.DE"}
    for key, r in results.items():
        summary["paths"][key] = dict(
            scorecard=r["scorecard"], global_drawdown=r["global_drawdown"],
            concentration={k:v for k,v in r["concentration"].items() if k not in ("pairs", "same_theme_pairs")},
            annual=[dict(year=a["year"], annual_return=a["annual_return"], costs_pp=a["costs_pp"],
                         biggest_losses=[x for x in a["contributors"] if x["net_pnl_eur"] < 0][:6],
                         biggest_gains=list(reversed([x for x in a["contributors"] if x["net_pnl_eur"] > 0][-5:])),
                         worst_drawdown=a["worst_drawdown"]) for a in r["annual"]],
            first_selection_examples=[q for q in r["first_selections"] if q["symbol"] in focus_symbols],
            max_daily_pnl_reconciliation_error=r["max_daily_pnl_reconciliation_error"],
            max_lifetime_asset_reconciliation_error=r["max_lifetime_asset_reconciliation_error"])
    summary["critical_2024_blockchain_event_features"] = critical
    summary["same_state_summary"] = output["same_state_summary"]
    summary["same_state_annual"] = output["same_state_annual"]
    (OUT / "diagnosis_summary_v3.json").write_text(json.dumps(native(summary), indent=2, allow_nan=False) + "\n")
    print("WROTE", OUT / "diagnosis_v3.json")


if __name__ == "__main__": main()
