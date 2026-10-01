"""
ETF Trader — source-only A4 reconstruction: persistent clusters + destination PLS.

Clean-room extraction of the upstream cluster/destination semantics required by
the recovered A4 Persistence+Opportunity lane. Productive inputs are raw price
history, source-generated labels, source metadata and configuration only.

Recovered source:
Meteor_SuperGold_Diamond_v1_CORRECTED_COMPLETE_NATIVE_COLAB.ipynb
SHA-256: 1b1efa0e686baf8341be30ff43e127b59ce44e45c0dc9c1253725b23744aa2f9
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.covariance import LedoitWolf
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


RECOVERED_SOURCE_SHA256 = "1b1efa0e686baf8341be30ff43e127b59ce44e45c0dc9c1253725b23744aa2f9"

DEFENSIVE_CATEGORY = "C05_BONDS_CASH_CREDIT"
N_CLUSTERS = 8
N_DYNAMIC_CLUSTERS = 7
CLUSTER_LOOKBACK = 252
MIN_CLUSTER_OBS = 168
N_PCA_COMPONENTS = 5
MIN_CLUSTER_SIZE = 8
MAX_CLUSTER_SIZE = 30
DEST_HORIZONS = (42, 63)
DEST_PERSISTENCE_MONTHS = 2
MIN_PLS_TRAIN_DATES = 36
DEFAULT_SEED = 26072026  # source-exact seed from recovered notebook SHA256 1b1efa0e...

CLUSTER_FEATURE_COLS = [
    "cluster_size",
    "state_mom21", "state_mom63", "state_mom126",
    "state_vol21", "state_vol63",
    "state_breadth21", "state_breadth63", "state_drawdown63",
    "cov_mean_corr", "cov_corr_dispersion", "cov_pc1_share",
    "cov_cross_cluster_corr", "cluster_stability",
]

TICKER_COV_FEATURE_COLS = [
    "corr_cluster63", "beta_cluster63", "idio_vol63",
    "within_cluster_centrality", "cluster_mom_gap21", "cluster_mom_gap63",
]


@dataclass(frozen=True)
class ClusterBuildResult:
    clusters: pd.DataFrame
    ticker_cov: pd.DataFrame
    membership: pd.DataFrame
    source_audit: pd.DataFrame
    balance_audit: pd.DataFrame


@dataclass(frozen=True)
class DestinationBuildResult:
    destination: pd.DataFrame
    cutoff_audit: pd.DataFrame


def percentile_rank(values: pd.Series) -> pd.Series:
    return values.rank(pct=True, method="average")


def balanced_kmeans_assignment(
    z: np.ndarray,
    n_clusters: int = N_DYNAMIC_CLUSTERS,
    seed: int = DEFAULT_SEED,
    max_iter: int = 20,
    *,
    min_cluster_size: int = MIN_CLUSTER_SIZE,
    max_cluster_size: int = MAX_CLUSTER_SIZE,
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Recovered capacity-balanced KMeans + Hungarian assignment."""
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D matrix")
    n = z.shape[0]
    if n < n_clusters:
        raise ValueError("number of observations is smaller than n_clusters")

    base = n // n_clusters
    rem = n % n_clusters
    capacities = [base + (1 if i < rem else 0) for i in range(n_clusters)]
    if min(capacities) < min_cluster_size or max(capacities) > max_cluster_size:
        raise ValueError(f"cluster capacities outside frozen bounds: {capacities}")

    km = KMeans(n_clusters=n_clusters, n_init=20, random_state=int(seed))
    km.fit(z)
    centers = km.cluster_centers_.copy()
    labels_prev = None

    for _ in range(max_iter):
        distances = cdist(z, centers, metric="sqeuclidean")
        slots = np.repeat(np.arange(n_clusters, dtype=int), capacities)
        expanded = distances[:, slots]
        expanded = expanded + np.arange(expanded.shape[1], dtype=float)[None, :] * 1e-12
        row_ind, col_ind = linear_sum_assignment(expanded)
        order = np.argsort(row_ind)
        labels = slots[col_ind[order]]

        new_centers = np.vstack([z[labels == c].mean(axis=0) for c in range(n_clusters)])
        if labels_prev is not None and np.array_equal(labels, labels_prev):
            centers = new_centers
            break
        labels_prev = labels.copy()
        centers = new_centers

    return labels.astype(int), centers, capacities


def persistent_cluster_mapping(
    members_temp: Mapping[int, set[str]],
    previous_members: Mapping[int, set[str]],
    centers: np.ndarray,
    n_dynamic_clusters: int = N_DYNAMIC_CLUSTERS,
) -> dict[int, int]:
    """Match current clusters to persistent IDs using only prior-month membership."""
    temp_ids = sorted(members_temp)
    persistent_ids = list(range(1, int(n_dynamic_clusters) + 1))
    if len(temp_ids) != len(persistent_ids):
        raise ValueError("temporary cluster count does not match persistent-ID count")

    if not previous_members:
        order = sorted(temp_ids, key=lambda c: tuple(np.round(centers[c], 10)))
        return {temp: pid for temp, pid in zip(order, persistent_ids)}

    cost = np.ones((len(persistent_ids), len(temp_ids)), dtype=float)
    for i, pid in enumerate(persistent_ids):
        old = set(previous_members.get(pid, set()))
        for j, temp in enumerate(temp_ids):
            cur = set(members_temp[temp])
            union = len(old | cur)
            jac = len(old & cur) / union if union else 0.0
            cost[i, j] = 1.0 - jac

    rows, cols = linear_sum_assignment(cost)
    mapping = {temp_ids[j]: persistent_ids[i] for i, j in zip(rows, cols)}
    if len(mapping) != len(temp_ids):
        raise RuntimeError("incomplete persistent cluster matching")
    return mapping


def _validate_cluster_label_panel(panel: pd.DataFrame) -> pd.DataFrame:
    required = {"signal_date", "ticker"}
    for h in DEST_HORIZONS:
        required |= {f"fwd_ret_{h}", f"exit_date_{h}"}
    missing = required.difference(panel.columns)
    if missing:
        raise KeyError(f"missing cluster label columns: {sorted(missing)}")
    out = panel[list(required)].copy()
    out["signal_date"] = pd.to_datetime(out["signal_date"])
    for h in DEST_HORIZONS:
        out[f"exit_date_{h}"] = pd.to_datetime(out[f"exit_date_{h}"])
    if out.duplicated(["signal_date", "ticker"]).any():
        raise ValueError("duplicate signal_date/ticker rows in cluster label panel")
    return out


def build_persistent_clusters(
    close: pd.DataFrame,
    label_panel: pd.DataFrame,
    signal_dates: Sequence[pd.Timestamp],
    ticker_category: Mapping[str, str],
    *,
    seed: int = DEFAULT_SEED,
) -> ClusterBuildResult:
    """Rebuild the recovered S3B persistent cluster state from source-only inputs."""
    close = close.copy().sort_index()
    close.index = pd.to_datetime(close.index)
    close.columns = close.columns.astype(str)
    if close.index.has_duplicates:
        raise ValueError("close index contains duplicate dates")

    panel = _validate_cluster_label_panel(label_panel)
    panel_by_date = {
        pd.Timestamp(d): g.set_index("ticker")
        for d, g in panel.groupby("signal_date", sort=True)
    }

    tradable = sorted(set(close.columns).intersection(panel["ticker"].astype(str).unique()))
    defensive_universe = sorted(
        t for t in tradable if ticker_category.get(t) == DEFENSIVE_CATEGORY
    )
    dynamic_universe = sorted(t for t in tradable if t not in set(defensive_universe))
    if len(defensive_universe) < MIN_CLUSTER_SIZE:
        raise RuntimeError(
            f"insufficient defensive sleeve: {len(defensive_universe)} < {MIN_CLUSTER_SIZE}"
        )

    logret = np.log(close.where(close > 0)).diff()
    calendar = close.index
    cal_pos = {pd.Timestamp(d): i for i, d in enumerate(calendar)}

    cluster_rows = []
    ticker_cov_rows = []
    membership_rows = []
    source_audit = []
    balance_rows = []
    previous_dynamic_members = {}
    previous_defensive_members = set()

    for date_number, sd in enumerate(pd.Timestamp(d) for d in signal_dates):
        if sd not in panel_by_date or sd not in cal_pos:
            continue
        i = cal_pos[sd]
        if i + 1 < CLUSTER_LOOKBACK:
            continue

        # Exact recovered indexing: data never extend beyond signal_date.
        widx = calendar[max(1, i - CLUSTER_LOOKBACK + 1): i + 1]
        returns_window = logret.reindex(widx, columns=tradable)
        eligible_panel = set(panel_by_date[sd].index.astype(str))

        eligible_defensive = [
            t for t in defensive_universe
            if t in eligible_panel and returns_window[t].notna().sum() >= MIN_CLUSTER_OBS
        ]
        eligible_dynamic = [
            t for t in dynamic_universe
            if t in eligible_panel and returns_window[t].notna().sum() >= MIN_CLUSTER_OBS
        ]
        if len(eligible_defensive) < MIN_CLUSTER_SIZE:
            continue
        if len(eligible_dynamic) < N_DYNAMIC_CLUSTERS * MIN_CLUSTER_SIZE:
            continue

        dynamic_frame = returns_window[eligible_dynamic].copy()
        dynamic_frame = dynamic_frame.apply(lambda s: s.fillna(s.mean()), axis=0).fillna(0.0)
        dynamic_std = dynamic_frame.std(axis=0, ddof=0).replace(0.0, np.nan)
        dynamic_z = (
            dynamic_frame.sub(dynamic_frame.mean(axis=0), axis=1)
            .div(dynamic_std, axis=1)
            .fillna(0.0)
        )

        n_components = min(N_PCA_COMPONENTS, dynamic_z.shape[0] - 1, dynamic_z.shape[1])
        if n_components < 2:
            continue
        pca = PCA(n_components=n_components, svd_solver="full", random_state=seed)
        pca.fit(dynamic_z.to_numpy(dtype=float))
        loadings = pca.components_.T * np.sqrt(
            np.maximum(pca.explained_variance_, 1e-12)
        )[None, :]
        loadings = StandardScaler().fit_transform(loadings)

        temp_labels, temp_centers, capacities = balanced_kmeans_assignment(
            loadings, N_DYNAMIC_CLUSTERS, seed + date_number
        )
        names = np.asarray(eligible_dynamic)
        members_temp = {
            c: set(names[temp_labels == c]) for c in range(N_DYNAMIC_CLUSTERS)
        }
        mapping = persistent_cluster_mapping(
            members_temp, previous_dynamic_members, temp_centers
        )
        dynamic_members = {mapping[c]: members_temp[c] for c in members_temp}
        current_members = {0: set(eligible_defensive), **dynamic_members}
        if len(current_members) != N_CLUSTERS:
            raise AssertionError(
                f"expected {N_CLUSTERS} clusters, found {len(current_members)}"
            )

        stability = {}
        defensive_union = len(current_members[0] | previous_defensive_members)
        stability[0] = (
            len(current_members[0] & previous_defensive_members) / defensive_union
            if previous_defensive_members and defensive_union else np.nan
        )
        for cid in range(1, N_CLUSTERS):
            old = previous_dynamic_members.get(cid, set())
            cur = current_members[cid]
            union = len(old | cur)
            stability[cid] = len(old & cur) / union if old and union else np.nan

        previous_defensive_members = set(current_members[0])
        previous_dynamic_members = {
            cid: set(current_members[cid]) for cid in range(1, N_CLUSTERS)
        }

        eligible_all = sorted(set().union(*current_members.values()))
        all_frame = returns_window[eligible_all].copy()
        all_frame = all_frame.apply(lambda s: s.fillna(s.mean()), axis=0).fillna(0.0)
        all_matrix = all_frame.to_numpy(dtype=float)
        try:
            covariance = LedoitWolf().fit(all_matrix).covariance_
        except Exception:
            covariance = np.cov(all_matrix, rowvar=False)
        stdv = np.sqrt(np.maximum(np.diag(covariance), 1e-12))
        correlation = covariance / np.outer(stdv, stdv)
        correlation = np.clip(np.nan_to_num(correlation, nan=0.0), -1.0, 1.0)
        np.fill_diagonal(correlation, 1.0)
        ticker_position = {ticker: j for j, ticker in enumerate(eligible_all)}

        centroids = pd.DataFrame({
            cid: all_frame[sorted(members)].mean(axis=1)
            for cid, members in current_members.items()
        })
        centroid_corr = centroids.corr().fillna(0.0)

        cluster_sizes = [len(current_members[c]) for c in sorted(current_members)]
        shares = np.asarray(cluster_sizes, dtype=float) / max(
            1.0, float(sum(cluster_sizes))
        )
        balance_rows.append({
            "signal_date": sd,
            "n_clusters": len(cluster_sizes),
            "min_cluster_size": int(min(cluster_sizes)),
            "max_cluster_size": int(max(cluster_sizes)),
            "largest_cluster_share": float(max(shares)),
            "effective_clusters": float(1.0 / np.square(shares).sum()),
            "singleton_clusters": int(sum(size == 1 for size in cluster_sizes)),
            "dynamic_capacities": "|".join(map(str, capacities)),
            "pca_components": int(n_components),
            "pca_explained_variance": float(pca.explained_variance_ratio_.sum()),
        })

        pdate = panel_by_date[sd]
        for cid, members in sorted(current_members.items()):
            member_list = sorted(members)
            positions = [ticker_position[t] for t in member_list]
            subcorr = correlation[np.ix_(positions, positions)]
            off_diag = (
                subcorr[np.triu_indices_from(subcorr, k=1)]
                if len(positions) > 1 else np.asarray([0.0])
            )
            centroid_ret = centroids[cid]

            def trailing_sum(window):
                return float(centroid_ret.iloc[-window:].sum()) if len(centroid_ret) >= window else np.nan

            def trailing_vol(window):
                return (
                    float(centroid_ret.iloc[-window:].std(ddof=0) * math.sqrt(252.0))
                    if len(centroid_ret) >= window else np.nan
                )

            breadth21 = float((all_frame[member_list].iloc[-21:].sum(axis=0) > 0).mean())
            breadth63 = float((all_frame[member_list].iloc[-63:].sum(axis=0) > 0).mean())
            cumulative63 = np.exp(centroid_ret.iloc[-63:].cumsum())
            drawdown63 = float((cumulative63 / cumulative63.cummax() - 1.0).min())
            eigenvalues = np.linalg.eigvalsh(subcorr) if len(positions) > 1 else np.asarray([1.0])
            pc1_share = float(max(eigenvalues) / max(eigenvalues.sum(), 1e-12))
            cross_cluster_corr = float(centroid_corr.loc[cid].drop(index=cid).mean())

            rec = {
                "signal_date": sd,
                "cluster_id": int(cid),
                "cluster_size": int(len(member_list)),
                "state_mom21": trailing_sum(21),
                "state_mom63": trailing_sum(63),
                "state_mom126": trailing_sum(126),
                "state_vol21": trailing_vol(21),
                "state_vol63": trailing_vol(63),
                "state_breadth21": breadth21,
                "state_breadth63": breadth63,
                "state_drawdown63": drawdown63,
                "cov_mean_corr": float(np.nanmean(off_diag)),
                "cov_corr_dispersion": float(np.nanstd(off_diag)),
                "cov_pc1_share": pc1_share,
                "cov_cross_cluster_corr": cross_cluster_corr,
                "cluster_stability": stability[cid],
            }
            for horizon in DEST_HORIZONS:
                future_values = pdate.reindex(member_list)[f"fwd_ret_{horizon}"].dropna()
                rec[f"cluster_fwd_ret_{horizon}"] = (
                    float(future_values.mean()) if len(future_values) >= 3 else np.nan
                )
                exits = pdate.reindex(member_list)[f"exit_date_{horizon}"].dropna()
                rec[f"label_exit_date_{horizon}"] = exits.max() if len(exits) else pd.NaT
            cluster_rows.append(rec)

            centroid63 = centroid_ret.iloc[-63:]
            centroid_var = float(centroid63.var(ddof=0))
            for ticker in member_list:
                ticker63 = all_frame[ticker].iloc[-63:]
                cov_tc = (
                    float(np.cov(ticker63, centroid63, ddof=0)[0, 1])
                    if len(ticker63) >= 20 else np.nan
                )
                beta = cov_tc / centroid_var if centroid_var > 1e-12 else np.nan
                corr_centroid = (
                    float(ticker63.corr(centroid63)) if len(ticker63) >= 20 else np.nan
                )
                residual = ticker63 - beta * centroid63 if np.isfinite(beta) else pd.Series(dtype=float)
                idio_vol = (
                    float(residual.std(ddof=0) * math.sqrt(252.0))
                    if len(residual) else np.nan
                )
                pos = ticker_position[ticker]
                within_positions = [
                    ticker_position[t] for t in member_list if t != ticker
                ]
                centrality = (
                    float(np.nanmean(correlation[pos, within_positions]))
                    if within_positions else 0.0
                )
                ticker_cov_rows.append({
                    "signal_date": sd,
                    "ticker": ticker,
                    "cluster_id": int(cid),
                    "corr_cluster63": corr_centroid,
                    "beta_cluster63": beta,
                    "idio_vol63": idio_vol,
                    "within_cluster_centrality": centrality,
                    "cluster_mom_gap21": float(
                        all_frame[ticker].iloc[-21:].sum() - trailing_sum(21)
                    ),
                    "cluster_mom_gap63": float(
                        all_frame[ticker].iloc[-63:].sum() - trailing_sum(63)
                    ),
                })
                membership_rows.append({
                    "signal_date": sd,
                    "ticker": ticker,
                    "cluster_id": int(cid),
                })

        source_audit.append({
            "signal_date": sd,
            "window_start": widx.min(),
            "window_end": widx.max(),
            "max_source_date_le_signal": bool(widx.max() <= sd),
            "n_dynamic": len(eligible_dynamic),
            "n_defensive": len(eligible_defensive),
            "matching_used_only_previous_membership": True,
        })

    clusters = pd.DataFrame(cluster_rows)
    ticker_cov = pd.DataFrame(ticker_cov_rows)
    membership = pd.DataFrame(membership_rows)
    source = pd.DataFrame(source_audit)
    balance = pd.DataFrame(balance_rows)
    if clusters.empty or ticker_cov.empty:
        raise RuntimeError("persistent cluster reconstruction produced no rows")

    for horizon in DEST_HORIZONS:
        clusters[f"cluster_rank_pct_{horizon}"] = clusters.groupby(
            "signal_date"
        )[f"cluster_fwd_ret_{horizon}"].transform(percentile_rank)

    if len(source) and not source["max_source_date_le_signal"].astype(bool).all():
        raise AssertionError("cluster source-date audit failed")

    return ClusterBuildResult(
        clusters=clusters.sort_values(["signal_date", "cluster_id"]).reset_index(drop=True),
        ticker_cov=ticker_cov.sort_values(["signal_date", "ticker"]).reset_index(drop=True),
        membership=membership.sort_values(["signal_date", "ticker"]).reset_index(drop=True),
        source_audit=source.sort_values("signal_date").reset_index(drop=True),
        balance_audit=balance.sort_values("signal_date").reset_index(drop=True),
    )


def _destination_horizon(
    cluster_table: pd.DataFrame,
    horizon: int,
    *,
    min_train_dates: int = MIN_PLS_TRAIN_DATES,
):
    predictions = []
    audits = []
    rank_col = f"cluster_rank_pct_{horizon}"
    exit_col = f"label_exit_date_{horizon}"
    required = {"signal_date", "cluster_id", rank_col, exit_col, *CLUSTER_FEATURE_COLS}
    missing = required.difference(cluster_table.columns)
    if missing:
        raise KeyError(f"missing destination columns: {sorted(missing)}")

    frame = cluster_table.copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    frame[exit_col] = pd.to_datetime(frame[exit_col])

    for d in sorted(frame["signal_date"].dropna().unique()):
        d = pd.Timestamp(d)
        train = frame[
            (frame["signal_date"] < d)
            & (frame[exit_col] < d)
            & frame[rank_col].notna()
        ].copy()
        test = frame[frame["signal_date"].eq(d)].copy()
        if train["signal_date"].nunique() < min_train_dates or len(test) != N_CLUSTERS:
            continue

        imputer = SimpleImputer(strategy="median", keep_empty_features=True)
        scaler = StandardScaler()
        x_train = scaler.fit_transform(imputer.fit_transform(train[CLUSTER_FEATURE_COLS]))
        x_test = scaler.transform(imputer.transform(test[CLUSTER_FEATURE_COLS]))
        y_train = train[rank_col].to_numpy(dtype=float)
        n_components = min(2, x_train.shape[1], max(1, x_train.shape[0] - 1))
        pls = PLSRegression(n_components=n_components, scale=False, max_iter=500)
        pls.fit(x_train, y_train.reshape(-1, 1))

        prediction = pls.predict(x_test).reshape(-1)
        scores = pls.transform(x_test)
        if scores.shape[1] == 1:
            scores = np.column_stack([scores[:, 0], np.zeros(len(scores))])

        current = test[["signal_date", "cluster_id"]].copy()
        current[f"dest_pred_{horizon}"] = prediction
        current[f"dest_rank_{horizon}"] = percentile_rank(
            pd.Series(prediction, index=current.index)
        ).to_numpy()
        current[f"pls1_{horizon}"] = scores[:, 0]
        current[f"pls2_{horizon}"] = scores[:, 1]
        predictions.append(current)

        latest_exit = train[exit_col].max()
        audits.append({
            "stage": "DESTINATION_PLS",
            "horizon": horizon,
            "signal_date": d,
            "latest_train_exit": latest_exit,
            "n_train_rows": len(train),
            "n_train_dates": train["signal_date"].nunique(),
            "cutoff_pass": bool(latest_exit < d),
        })

    if not predictions:
        raise RuntimeError(f"no destination predictions generated for horizon {horizon}")
    audit = pd.DataFrame(audits)
    if audit.empty or not audit["cutoff_pass"].astype(bool).all():
        raise AssertionError(f"destination maturity audit failed for horizon {horizon}")
    return pd.concat(predictions, ignore_index=True), audit


def build_destination_pls(
    cluster_table: pd.DataFrame,
    *,
    min_train_dates: int = MIN_PLS_TRAIN_DATES,
) -> DestinationBuildResult:
    """Recovered causal 42/63-session PLS destination layer."""
    tables = []
    audits = []
    for horizon in DEST_HORIZONS:
        table, audit = _destination_horizon(
            cluster_table, horizon, min_train_dates=min_train_dates
        )
        tables.append(table)
        audits.append(audit)

    destination = tables[0]
    for table in tables[1:]:
        destination = destination.merge(
            table,
            on=["signal_date", "cluster_id"],
            how="inner",
            validate="one_to_one",
        )
    cutoff_audit = pd.concat(audits, ignore_index=True)
    rank_cols = [f"dest_rank_{h}" for h in DEST_HORIZONS]
    destination["destination_score_raw"] = destination[rank_cols].mean(axis=1)
    destination = destination.sort_values(["cluster_id", "signal_date"])
    destination["destination_score_persistent"] = destination.groupby("cluster_id")[
        "destination_score_raw"
    ].transform(
        lambda s: s.rolling(DEST_PERSISTENCE_MONTHS, min_periods=1).mean()
    )
    destination["destination_rank_final"] = destination.groupby("signal_date")[
        "destination_score_persistent"
    ].transform(percentile_rank)
    destination = destination.sort_values(
        ["signal_date", "cluster_id"]
    ).reset_index(drop=True)

    counts = destination.groupby("signal_date")["cluster_id"].nunique()
    if len(counts) and not (counts == N_CLUSTERS).all():
        raise AssertionError("destination output lost one or more cluster IDs")
    return DestinationBuildResult(
        destination=destination,
        cutoff_audit=cutoff_audit.sort_values(
            ["signal_date", "horizon"]
        ).reset_index(drop=True),
    )


@dataclass(frozen=True)
class ClusterMembershipBuildResult:
    membership: pd.DataFrame
    source_audit: pd.DataFrame
    balance_audit: pd.DataFrame


def build_persistent_membership(
    close: pd.DataFrame,
    label_panel: pd.DataFrame,
    signal_dates: Sequence[pd.Timestamp],
    ticker_category: Mapping[str, str],
    *,
    seed: int = DEFAULT_SEED,
) -> ClusterMembershipBuildResult:
    """Build only the persistent cluster membership required by MA3.

    This is mathematically identical to the membership stage of
    `build_persistent_clusters`, but intentionally skips covariance,
    cluster-state and per-ticker covariance calculations that the MA3
    feature-panel builder does not consume.
    """
    close = close.copy().sort_index()
    close.index = pd.to_datetime(close.index)
    close.columns = close.columns.astype(str)
    if close.index.has_duplicates:
        raise ValueError("close index contains duplicate dates")

    panel = _validate_cluster_label_panel(label_panel)
    panel_by_date = {
        pd.Timestamp(d): g.set_index("ticker")
        for d, g in panel.groupby("signal_date", sort=True)
    }

    tradable = sorted(
        set(close.columns).intersection(panel["ticker"].astype(str).unique())
    )
    defensive_universe = sorted(
        t for t in tradable if ticker_category.get(t) == DEFENSIVE_CATEGORY
    )
    dynamic_universe = sorted(
        t for t in tradable if t not in set(defensive_universe)
    )
    if len(defensive_universe) < MIN_CLUSTER_SIZE:
        raise RuntimeError(
            f"insufficient defensive sleeve: "
            f"{len(defensive_universe)} < {MIN_CLUSTER_SIZE}"
        )

    logret = np.log(close.where(close > 0)).diff()
    calendar = close.index
    cal_pos = {pd.Timestamp(d): i for i, d in enumerate(calendar)}

    membership_rows = []
    source_audit = []
    balance_rows = []
    previous_dynamic_members = {}
    previous_defensive_members = set()

    for date_number, sd in enumerate(pd.Timestamp(d) for d in signal_dates):
        if sd not in panel_by_date or sd not in cal_pos:
            continue
        i = cal_pos[sd]
        if i + 1 < CLUSTER_LOOKBACK:
            continue

        widx = calendar[max(1, i - CLUSTER_LOOKBACK + 1): i + 1]
        returns_window = logret.reindex(widx, columns=tradable)
        eligible_panel = set(panel_by_date[sd].index.astype(str))

        eligible_defensive = [
            t for t in defensive_universe
            if t in eligible_panel
            and returns_window[t].notna().sum() >= MIN_CLUSTER_OBS
        ]
        eligible_dynamic = [
            t for t in dynamic_universe
            if t in eligible_panel
            and returns_window[t].notna().sum() >= MIN_CLUSTER_OBS
        ]
        if len(eligible_defensive) < MIN_CLUSTER_SIZE:
            continue
        if len(eligible_dynamic) < N_DYNAMIC_CLUSTERS * MIN_CLUSTER_SIZE:
            continue

        dynamic_frame = returns_window[eligible_dynamic].copy()
        dynamic_frame = dynamic_frame.fillna(
            dynamic_frame.mean(axis=0)
        ).fillna(0.0)
        dynamic_std = dynamic_frame.std(axis=0, ddof=0).replace(
            0.0, np.nan
        )
        dynamic_z = (
            dynamic_frame.sub(dynamic_frame.mean(axis=0), axis=1)
            .div(dynamic_std, axis=1)
            .fillna(0.0)
        )

        n_components = min(
            N_PCA_COMPONENTS,
            dynamic_z.shape[0] - 1,
            dynamic_z.shape[1],
        )
        if n_components < 2:
            continue
        pca = PCA(
            n_components=n_components,
            svd_solver="full",
            random_state=seed,
        )
        pca.fit(dynamic_z.to_numpy(dtype=float))
        loadings = pca.components_.T * np.sqrt(
            np.maximum(pca.explained_variance_, 1e-12)
        )[None, :]
        loadings = StandardScaler().fit_transform(loadings)

        temp_labels, temp_centers, capacities = balanced_kmeans_assignment(
            loadings,
            N_DYNAMIC_CLUSTERS,
            seed + date_number,
        )
        names = np.asarray(eligible_dynamic)
        members_temp = {
            cid: set(names[temp_labels == cid])
            for cid in range(N_DYNAMIC_CLUSTERS)
        }
        mapping = persistent_cluster_mapping(
            members_temp,
            previous_dynamic_members,
            temp_centers,
        )
        dynamic_members = {
            mapping[cid]: members_temp[cid]
            for cid in members_temp
        }
        current_members = {
            0: set(eligible_defensive),
            **dynamic_members,
        }
        if len(current_members) != N_CLUSTERS:
            raise AssertionError(
                f"expected {N_CLUSTERS} clusters, "
                f"found {len(current_members)}"
            )

        previous_defensive_members = set(current_members[0])
        previous_dynamic_members = {
            cid: set(current_members[cid])
            for cid in range(1, N_CLUSTERS)
        }

        cluster_sizes = [
            len(current_members[cid])
            for cid in sorted(current_members)
        ]
        shares = np.asarray(cluster_sizes, dtype=float) / max(
            1.0,
            float(sum(cluster_sizes)),
        )
        balance_rows.append({
            "signal_date": sd,
            "n_clusters": len(cluster_sizes),
            "min_cluster_size": int(min(cluster_sizes)),
            "max_cluster_size": int(max(cluster_sizes)),
            "largest_cluster_share": float(max(shares)),
            "effective_clusters": float(
                1.0 / np.square(shares).sum()
            ),
            "singleton_clusters": int(
                sum(size == 1 for size in cluster_sizes)
            ),
            "dynamic_capacities": "|".join(map(str, capacities)),
            "pca_components": int(n_components),
            "pca_explained_variance": float(
                pca.explained_variance_ratio_.sum()
            ),
        })

        for cid, members in sorted(current_members.items()):
            for ticker in sorted(members):
                membership_rows.append({
                    "signal_date": sd,
                    "ticker": ticker,
                    "cluster_id": int(cid),
                })

        source_audit.append({
            "signal_date": sd,
            "window_start": widx.min(),
            "window_end": widx.max(),
            "max_source_date_le_signal": bool(widx.max() <= sd),
            "n_dynamic": len(eligible_dynamic),
            "n_defensive": len(eligible_defensive),
            "matching_used_only_previous_membership": True,
        })

    membership = pd.DataFrame(membership_rows)
    source = pd.DataFrame(source_audit)
    balance = pd.DataFrame(balance_rows)
    if membership.empty:
        raise RuntimeError(
            "persistent cluster membership reconstruction produced no rows"
        )
    if (
        len(source)
        and not source["max_source_date_le_signal"].astype(bool).all()
    ):
        raise AssertionError("cluster source-date audit failed")

    return ClusterMembershipBuildResult(
        membership=membership.sort_values(
            ["signal_date", "ticker"]
        ).reset_index(drop=True),
        source_audit=source.sort_values(
            "signal_date"
        ).reset_index(drop=True),
        balance_audit=balance.sort_values(
            "signal_date"
        ).reset_index(drop=True),
    )
