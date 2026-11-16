"""Run the fixed OLC111 causal forecast and complete-account research matrix."""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from advantage_model import AdvantageModel, fit_head
from replay_engine import simulate
from research_pipeline import (HEADS, build_research_bundle, execution_panel,
                               fresh_is_action, select_action, state_features)


ARMS = ("BASE", "STATIC_75", "MEAN", "PRICE", "VIX", "TERM")
LEARNED_ARMS = ARMS[2:]
SCENARIOS = {"NEXT_CLOSE": (1., .0015, "CLOSE"),
             "DOUBLE_COST": (2., .003, "CLOSE"),
             "NEXT_OPEN": (1., .0015, "OPEN")}
FIT_OPTIONS = dict(min_dates=504, min_blocks=24, n_boot=100, seed=111, penalty=1.)
INITIAL_CAPITAL = 10000.


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonable(value):
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def _json_bytes(value):
    return json.dumps(jsonable(value), sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _write_json(path, value):
    path = Path(path)
    raw = _json_bytes(value)
    if path.suffix == ".gz":
        path.write_bytes(gzip.compress(raw, mtime=0))
    else:
        path.write_text(json.dumps(jsonable(value), indent=2, allow_nan=False) + "\n")


def _read_json(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def _csv(frame, path):
    compression = {"method": "gzip", "mtime": 0} if str(path).endswith(".gz") else None
    frame.to_csv(path, index=False, compression=compression)


def verify_experiment_freeze(root):
    """Resolve all frozen relative paths against OLC111, including ../olc110."""
    root = Path(root).resolve()
    freeze_path = root / "docs/EXPERIMENT_FREEZE.json"
    freeze = _read_json(freeze_path)
    for section in ("code_hashes", "input_hashes"):
        for relative, expected in freeze[section].items():
            path = (root / relative).resolve()
            if not path.is_file() or sha(path) != expected:
                raise ValueError(f"FREEZE_HASH_MISMATCH {section} {relative}")
    if sha(root / "docs/DESIGN_AND_PROTOCOL.md") != freeze["protocol_sha256"]:
        raise ValueError("FREEZE_PROTOCOL_MISMATCH")
    if (freeze["arms"] != list(ARMS) or freeze["scenarios"] != list(SCENARIOS) or
            freeze["planned_paths"] != len(ARMS) * len(SCENARIOS) or
            freeze["planned_paths"] != 18):
        raise ValueError("FREEZE_MATRIX_MISMATCH")
    return freeze


class MonthlyFitCache:
    """One normal-cost fit per calendar cutoff/head, shared by every scenario."""

    def __init__(self, bank, dates, begin, *, folder=None, provenance=None, fit_options=None):
        self.bank = bank
        self.dates = pd.DatetimeIndex(dates)
        self.begin = int(begin)
        months = self.dates.to_period("M")
        first = np.r_[True, months[1:] != months[:-1]]
        self.cutoffs = np.maximum(np.maximum.accumulate(np.where(first, np.arange(len(dates)), 0)),
                                  self.begin - 1)
        self.folder = None if folder is None else Path(folder)
        if self.folder is not None:
            self.folder.mkdir(parents=True, exist_ok=True)
        self.provenance = provenance
        self.options = dict(FIT_OPTIONS, **({} if fit_options is None else fit_options))
        self.cache = {}

    def cutoff(self, k):
        return int(self.cutoffs[k])

    def get(self, k):
        cutoff = self.cutoff(k)
        if cutoff in self.cache:
            return self.cache[cutoff]
        path = None if self.folder is None else self.folder / f"FIT_{cutoff:06d}.json.gz"
        if path is not None and path.exists():
            stored = _read_json(path)
            if (stored["provenance"] != self.provenance or stored["cutoff"] != cutoff or
                    stored["fit_options"] != self.options):
                raise ValueError("FIT_CACHE_PROVENANCE_MISMATCH")
            fitted = {}
            for head in HEADS:
                record = stored["heads"][head]
                if record is None:
                    fitted[head] = None
                    continue
                models = {}
                for arm, values in record["models"].items():
                    models[arm] = AdvantageModel(values["model_name"], values["coefficients"],
                        values["bootstrap_coefficients"], values["transforms"],
                        values["feature_counts"], values["metadata"])
                    if hashlib.sha256(_json_bytes(models[arm].to_dict())).hexdigest() != record["hashes"][arm]:
                        raise ValueError("FIT_CACHE_MODEL_HASH_MISMATCH")
                fitted[head] = dict(models=models, meta=record["meta"], hashes=record["hashes"])
        else:
            fitted = {}
            exported = {}
            for head in HEADS:
                row = self.bank[head]
                result = fit_head(row["Xprice"], row["Xlegacy"], row["Xterm"], row["y"],
                                  row["signal_idx"], row["terminal_idx"], cutoff, **self.options)
                if result is None:
                    fitted[head] = None
                    exported[head] = None
                    continue
                models = {arm: model.to_dict() for arm, model in result["models"].items()}
                result["hashes"] = {arm: hashlib.sha256(_json_bytes(model)).hexdigest()
                                    for arm, model in models.items()}
                fitted[head] = result
                exported[head] = dict(models=models, meta=result["meta"], hashes=result["hashes"])
            if path is not None:
                _write_json(path, dict(cutoff=cutoff, date=str(self.dates[cutoff].date()),
                    provenance=self.provenance, fit_options=self.options, heads=exported,
                    source="primary_next_close_normal_cost_bank_only"))
        self.cache[cutoff] = fitted
        return fitted

    def prepare(self):
        first_by_head = {head: None for head in HEADS}
        all_ready = None
        for cutoff in np.unique(self.cutoffs[self.begin - 1:len(self.dates) - 1]):
            fitted = self.get(int(cutoff))
            for head in HEADS:
                if fitted[head] is not None and first_by_head[head] is None:
                    first_by_head[head] = dict(index=int(cutoff), date=str(self.dates[cutoff].date()))
            if all_ready is None and all(fitted[head] is not None for head in HEADS):
                all_ready = int(cutoff)
        post = None if all_ready is None else max(self.begin, all_ready + 1)
        if post is not None and post >= len(self.dates):
            post = None
        return dict(first_ready_by_head=first_by_head, all_heads_first_ready_idx=all_ready,
                    all_heads_first_ready_date=None if all_ready is None else str(self.dates[all_ready].date()),
                    postwarmup_start_idx=post,
                    postwarmup_start_date=None if post is None else str(self.dates[post].date()),
                    postwarmup_denominator="each_path_actual_close_nav_immediately_before_start",
                    monthly_cutoff="first_panel_date_of_month_clipped_to_begin_minus_one",
                    fit_options=self.options, fitted_calendar_cutoffs=sorted(self.cache))


class AccountPolicy:
    """Initial/warmup baseline, then daily native-net action comparisons."""

    def __init__(self, bundle, arm, fit_cache):
        if arm not in ARMS:
            raise ValueError("ARM")
        self.bundle, self.arm, self.fit_cache = bundle, arm, fit_cache
        self.dates = pd.DatetimeIndex(bundle["panel"]["dates"])
        self.trace = []

    def _record(self, k, current, context):
        units = np.asarray(context["units"])
        bought = np.asarray(context["last_buy_idx"])
        held = units > 1e-10
        known = held & (bought >= 0)
        ages = k - bought[known]
        age_weights = np.asarray(current)[known]
        row = dict(k=int(k), date=str(self.dates[k].date()), arm=self.arm,
                   initial=bool(context["initial"]), scheduled=bool(context["scheduled"]),
                   gross=float(np.sum(current)), cash=float(context["cash"]), nav=float(context["nav"]),
                   positions=int(held.sum()), unknown_age_positions=int((held & ~known).sum()),
                   mean_holding_age_sessions=(float(np.average(ages, weights=age_weights))
                       if len(ages) and age_weights.sum() > 0 else None),
                   max_holding_age_sessions=int(ages.max()) if len(ages) else None,
                   fit_cutoff_idx=self.fit_cache.cutoff(k),
                   fit_cutoff_date=str(self.dates[self.fit_cache.cutoff(k)].date()),
                   model_ready_all=False, source_available=bool(self.bundle["cboe"]["available"][k]),
                   fallback_price=False, action="HOLD", status="HOLD")
        for head in HEADS:
            for field in ("mean", "lower", "model_arm", "model_sha256", "max_abs_standardized_price"):
                row[f"{head.lower()}_{field}"] = None
        return row

    def __call__(self, k, current, context):
        row = self._record(k, current, context)
        fresh = np.asarray(self.bundle["targets"][k], float)
        scale = .75 if self.arm == "STATIC_75" else 1.
        def baseline(status):
            row.update(action="INITIAL" if context["initial"] else "SCHEDULED", status=status)
            self.trace.append(row)
            return dict(weights=fresh * scale, reason=row["action"], force=bool(context["initial"]),
                        meta=dict(arm=self.arm, status=status))
        if context["initial"]:
            return baseline("BASE_INITIAL")
        if self.arm in ("BASE", "STATIC_75"):
            if context["scheduled"]:
                return baseline("BASE_CONTROL")
            row["status"] = "BASE_HOLD"
            self.trace.append(row)
            return None
        fitted = self.fit_cache.get(k)
        row["model_ready_all"] = all(fitted[head] is not None for head in HEADS)
        if not row["model_ready_all"]:
            if context["scheduled"]:
                return baseline("WARMUP_MONTHLY")
            row["status"] = "WARMUP_HOLD"
            self.trace.append(row)
            return None
        if context["pending"] is not None or context["queued"]:
            row["status"] = "BUSY"
            self.trace.append(row)
            return None
        features = state_features(self.bundle["f"], k, current, fresh,
                                  self.bundle["breadth"][k], self.bundle["feature_monthly"])
        invested = float(np.sum(current)) > 1e-8
        possible = ("CASH", "FRESH") if invested else ("ENTRY",)
        predictions = {}
        legacy = self.bundle["cboe"]["legacy"][k]
        term = self.bundle["cboe"]["term"][k]
        source_ok = bool(row["source_available"] and np.isfinite(legacy).all() and np.isfinite(term).all())
        for head in possible:
            price = features[head]
            if price is None or not np.isfinite(price).all():
                continue
            if head in ("FRESH", "ENTRY") and not fresh_is_action(current, fresh):
                continue
            model_arm = "PRICE" if self.arm in ("VIX", "TERM") and not source_ok else self.arm
            row["fallback_price"] |= model_arm != self.arm
            model = fitted[head]["models"][model_arm]
            prediction = model.predict(price, legacy, term)
            predictions[head] = prediction
            scaler = model.transforms["price_scaler"]
            standardized = np.where(np.asarray(scaler["active"]),
                (np.asarray(price) - np.asarray(scaler["mean"])) / np.asarray(scaler["scale"]), 0.)
            prefix = head.lower()
            row.update({f"{prefix}_mean": prediction["mean"], f"{prefix}_lower": prediction["lower"],
                        f"{prefix}_model_arm": model_arm,
                        f"{prefix}_model_sha256": fitted[head]["hashes"][model_arm],
                        f"{prefix}_max_abs_standardized_price": float(np.max(np.abs(standardized)))})
        action = select_action(predictions)
        row.update(action=action, status="ACTION" if action != "HOLD" else
                   "HOLD_BUFFER" if predictions else "HOLD_UNSUPPORTED")
        self.trace.append(row)
        if action == "HOLD":
            return None
        target = np.zeros_like(fresh) if action == "CASH" else fresh.copy()
        return dict(weights=target, reason=action, force=True,
                    meta=dict(arm=self.arm, action=action, fit_cutoff_idx=row["fit_cutoff_idx"],
                              fallback_price=row["fallback_price"], predictions=predictions,
                              model_sha256=row[f"{action.lower()}_model_sha256"]))


def prequential_forecasts(bundle, cache):
    """Evaluate bank rows with their historical fit; right-edge labels are absent."""
    dates = pd.DatetimeIndex(bundle["panel"]["dates"])
    records = []
    for head in HEADS:
        bank = bundle["bank"][head]
        for i, (signal, terminal) in enumerate(zip(bank["signal_idx"], bank["terminal_idx"])):
            k, end = int(signal), int(terminal)
            if k < bundle["begin"] or end >= len(dates) or not np.isfinite(bank["y"][i]):
                continue
            fitted = cache.get(k)
            result = fitted[head]
            all_ready = all(fitted[h] is not None for h in HEADS)
            for arm in LEARNED_ARMS:
                row = dict(head=head, bank_row=int(i), arm=arm, signal_idx=k,
                           signal_date=str(dates[k].date()), terminal_idx=end,
                           terminal_date=str(dates[end].date()), outcome_available_idx=end,
                           reporting_cutoff_idx=len(dates), outcome=float(bank["y"][i]),
                           fit_cutoff_idx=cache.cutoff(k), fit_cutoff_date=str(dates[cache.cutoff(k)].date()),
                           head_ready=result is not None, all_heads_ready=all_ready,
                           prediction=None, lower=None, positive_buffer=False, model_sha256=None,
                           max_training_terminal_idx=None, n_training_dates=None, n_training_blocks=None)
                if result is not None:
                    if result["meta"]["max_terminal_idx"] >= cache.cutoff(k) or cache.cutoff(k) > k:
                        raise AssertionError("PREQUENTIAL_MATURITY")
                    prediction = result["models"][arm].predict(
                        bank["Xprice"][i], bank["Xlegacy"][i], bank["Xterm"][i])
                    row.update(prediction=prediction["mean"], lower=prediction["lower"],
                               positive_buffer=prediction["mean"] > 0 and prediction["lower"] > 0,
                               model_sha256=result["hashes"][arm],
                               max_training_terminal_idx=result["meta"]["max_terminal_idx"],
                               n_training_dates=result["meta"]["n_dates"],
                               n_training_blocks=result["meta"]["n_nonoverlap_blocks"])
                records.append(row)
    return pd.DataFrame(records, columns=(list(records[0]) if records else [
        "head", "arm", "signal_idx", "terminal_idx", "prediction", "lower", "outcome",
        "head_ready", "all_heads_ready", "positive_buffer"]))


def separated_episodes(signals, horizon=21):
    count, previous = 0, None
    for signal in sorted(set(int(k) for k in signals)):
        if previous is None or signal >= previous + horizon:
            count += 1
            previous = signal
    return count


def _date_weights(frame):
    counts = frame.groupby("signal_idx")["signal_idx"].transform("size").to_numpy(float)
    values = 1. / counts
    return values / values.sum()


def forecast_diagnostics(ledger):
    scores, bins = [], []
    for support in ("ALL_HEADS_READY", "HEAD_READY"):
        if ledger.empty:
            continue
        available = ledger["all_heads_ready"] if support == "ALL_HEADS_READY" else ledger["head_ready"]
        selected = ledger.loc[available & np.isfinite(ledger.prediction.to_numpy(float))]
        for (head, arm), frame in selected.groupby(["head", "arm"], sort=True):
            weights = _date_weights(frame)
            error = frame.prediction.to_numpy(float) - frame.outcome.to_numpy(float)
            positive = frame.loc[frame.positive_buffer]
            conditional = (float(_date_weights(positive) @ positive.outcome.to_numpy(float))
                           if len(positive) else None)
            row = dict(head=head, arm=arm, support=support, n_rows=len(frame),
                       n_dates=int(frame.signal_idx.nunique()),
                       n_nonoverlap_episodes=separated_episodes(frame.signal_idx),
                       mse=float(weights @ (error * error)), bias=float(weights @ error),
                       mean_prediction=float(weights @ frame.prediction.to_numpy(float)),
                       mean_outcome=float(weights @ frame.outcome.to_numpy(float)),
                       positive_buffer_rows=len(positive),
                       positive_buffer_dates=int(positive.signal_idx.nunique()),
                       positive_buffer_episodes=separated_episodes(positive.signal_idx),
                       positive_buffer_realized_mean=conditional,
                       conditional_realized_positive=conditional is not None and conditional > 0,
                       twelve_separated_positive_buffer_episodes=separated_episodes(positive.signal_idx) >= 12)
            scores.append(row)
            labels = pd.qcut(frame.prediction, 5, labels=False, duplicates="drop")
            if labels.isna().all():
                labels = pd.Series(0, index=frame.index)
            for label, group in frame.groupby(labels, observed=True):
                w = _date_weights(group)
                bins.append(dict(head=head, arm=arm, support=support, bin=int(label)+1,
                    n_rows=len(group), n_dates=int(group.signal_idx.nunique()),
                    prediction_min=float(group.prediction.min()), prediction_max=float(group.prediction.max()),
                    mean_prediction=float(w @ group.prediction.to_numpy(float)),
                    mean_outcome=float(w @ group.outcome.to_numpy(float))))
    references = {(row["head"], row["support"], row["arm"]): row["mse"] for row in scores}
    for row in scores:
        for reference in ("MEAN", "PRICE", "VIX"):
            value = references.get((row["head"], row["support"], reference))
            row[f"mse_delta_vs_{reference.lower()}"] = None if value is None else row["mse"] - value
            row[f"improves_mse_vs_{reference.lower()}"] = value is not None and row["mse"] < value
    return pd.DataFrame(scores), pd.DataFrame(bins)


def performance_window(core, daily, *, start_idx=None, initial=INITIAL_CAPITAL):
    rows = np.arange(len(daily)) if start_idx is None else np.flatnonzero(daily.k.to_numpy() >= start_idx)
    if not len(rows):
        return None
    preceding = float(initial) if rows[0] == 0 else float(daily.nav_close.iloc[rows[0]-1])
    selected = daily.iloc[rows]
    result = core.portfolio_metrics(selected.nav_close, selected.date, preceding, selected.nav_open)
    return dict(result, initial_nav=preceding, start_idx=int(selected.k.iloc[0]),
                end_idx=int(selected.k.iloc[-1]), start_date=str(selected.date.iloc[0]),
                end_date=str(selected.date.iloc[-1]), sessions=len(selected))


def summarize_path(bundle, arm, scenario, result, readiness):
    ticket, impact, fill = SCENARIOS[scenario]
    daily, orders = result["daily"], result["orders"]
    financial = performance_window(bundle["core"], daily)
    years = financial["days"] / 365.2425
    nav_by_date = daily.set_index("date").nav_open
    turnover = (float((orders.notional.to_numpy() / nav_by_date.loc[orders.date].to_numpy()).sum())
                if len(orders) else 0.)
    metrics = dict(path_id=f"{arm}__{scenario}", arm=arm, scenario=scenario, fill=fill,
                   currency="EUR", ticket=ticket, impact_bps=impact*10000, **financial,
                   orders=len(orders), trading_days=int(orders.date.nunique()),
                   costs=float(orders.cost.sum()), instructions=len(result["instructions"]),
                   trading_days_per_year=float(orders.date.nunique()/years),
                   two_sided_turnover_per_year=turnover/years,
                   mean_exposure=float(daily.gross.mean()), mean_cash_share=float((1-daily.gross).mean()),
                   mean_positions=float(daily.positions.mean()), full_cash_days=int((daily.gross<=1e-8).sum()),
                   deferred_sessions=result["deferred_sessions"],
                   max_self_financing_error=result["max_self_financing_error"],
                   cagr_target_pass=financial["cagr"] >= .30,
                   drawdown_sampling="OPEN_CLOSE" if fill=="OPEN" else "CLOSE_PRE_POST_FEES",
                   post_warmup_initial_nav=None, post_warmup_start_idx=readiness["postwarmup_start_idx"])
    if readiness["postwarmup_start_idx"] is not None:
        post = performance_window(bundle["core"], daily, start_idx=readiness["postwarmup_start_idx"])
        if post is not None:
            metrics.update({f"post_{key}": value for key, value in post.items()})
            metrics["post_warmup_initial_nav"] = post["initial_nav"]
    for action in HEADS:
        realized = orders.loc[orders.reason == action].drop_duplicates("instruction_id")
        metrics[f"{action.lower()}_realized_instructions"] = len(realized)
        metrics[f"{action.lower()}_separated_interventions"] = separated_episodes(realized.signal_idx)
        metrics[f"{action.lower()}_twelve_episode_diagnostic"] = separated_episodes(realized.signal_idx) >= 12
    return metrics


def save_path(folder, result, trace, metrics):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    _csv(result["daily"], folder / "DAILY.csv.gz")
    _csv(result["orders"], folder / "ORDERS.csv.gz")
    instructions = result["instructions"].copy()
    for column in ("target_weights", "raw_weights", "action_indices", "meta"):
        if column in instructions:
            instructions[column] = instructions[column].map(lambda value: _json_bytes(value).decode())
    _csv(instructions, folder / "INSTRUCTIONS.csv.gz")
    decisions = result["decisions"]
    arrays = {field: np.array([d[field] for d in decisions]) for field in
              ("units", "current_units", "current_weights", "raw_weights", "weights")}
    arrays.update(k=np.array([d["k"] for d in decisions], int),
                  cash=np.array([d["cash"] for d in decisions], float))
    np.savez_compressed(folder / "DECISIONS.npz", **arrays)
    _write_json(folder / "DECISIONS_META.json.gz", [
        {key:value for key,value in d.items() if not isinstance(value, np.ndarray)} for d in decisions])
    _csv(pd.DataFrame(trace), folder / "POLICY_TRACE.csv.gz")
    # Written last: this marks a fully saved path for resumable execution.
    _write_json(folder / "METRICS.json", metrics)


def annual_rows(bundle, daily, arm, scenario):
    years = pd.to_datetime(daily.date).dt.year.to_numpy()
    output = []
    for year in sorted(set(years)):
        indices = np.flatnonzero(years == year)
        initial = INITIAL_CAPITAL if indices[0] == 0 else float(daily.nav_close.iloc[indices[0]-1])
        frame = daily.iloc[indices].reset_index(drop=True)
        metrics = performance_window(bundle["core"], frame, initial=initial)
        output.append(dict(path_id=f"{arm}__{scenario}", arm=arm, scenario=scenario, year=int(year),
                           annual_return=metrics["cumulative"], maxdd_in_year=metrics["maxdd_sampled"],
                           initial_nav=initial, end_nav=float(frame.nav_close.iloc[-1]),
                           partial_year=int(year) in (int(years.min()), int(years.max()))))
    return output


def drawdown_rows(daily, arm, scenario):
    """Sampled peak/trough/recovery episodes, including pre-fee execution marks."""
    peak, peak_date, peak_k, peak_kind = INITIAL_CAPITAL, str(daily.date.iloc[0]), int(daily.k.iloc[0])-1, "INITIAL"
    active = None
    output = []
    for day in daily.itertuples():
        for kind, value in (("PRE_FEES", day.nav_open), ("CLOSE", day.nav_close)):
            value = float(value)
            if value >= peak:
                if active is not None:
                    active.update(recovery_date=str(day.date), recovery_idx=int(day.k), recovery_sample=kind,
                                  sessions_peak_to_recovery=int(day.k)-peak_k, recovered=True)
                    output.append(active)
                    active = None
                peak, peak_date, peak_k, peak_kind = value, str(day.date), int(day.k), kind
            else:
                depth = value/peak - 1.
                if active is None:
                    active = dict(path_id=f"{arm}__{scenario}", arm=arm, scenario=scenario,
                        peak_date=peak_date, peak_idx=peak_k, peak_sample=peak_kind, peak_nav=peak,
                        trough_date=str(day.date), trough_idx=int(day.k), trough_sample=kind,
                        trough_nav=value, depth=depth, recovery_date=None, recovery_idx=None,
                        recovery_sample=None, sessions_peak_to_recovery=None, recovered=False)
                elif depth < active["depth"]:
                    active.update(trough_date=str(day.date), trough_idx=int(day.k), trough_sample=kind,
                                  trough_nav=value, depth=depth)
    if active is not None:
        output.append(active)
    for episode in output:
        episode["sessions_peak_to_trough"] = episode["trough_idx"] - episode["peak_idx"]
    return output


def run(root, resume=False):
    root = Path(root).resolve()
    freeze = verify_experiment_freeze(root)
    freeze_sha = sha(root / "docs/EXPERIMENT_FREEZE.json")
    results = root / "results"
    results.mkdir(exist_ok=True)
    manifest_path = results / "RUN_MANIFEST.json"
    if manifest_path.exists():
        if not resume:
            raise FileExistsError("Existing research run; use --resume with the unchanged freeze")
        manifest = _read_json(manifest_path)
        if manifest["freeze_sha256"] != freeze_sha:
            raise ValueError("RUN_MANIFEST_FREEZE_MISMATCH")
    else:
        manifest = dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            freeze_sha256=freeze_sha, code_hashes=freeze["code_hashes"], input_hashes=freeze["input_hashes"],
            protocol_sha256=freeze["protocol_sha256"], arms=list(ARMS), scenarios=list(SCENARIOS),
            planned_paths=18, completed_paths=0, completed_path_ids=[], all_results_exploratory=True,
            pristine_holdout=False, previous_research_outcomes_seen=True, current_cagr_target=.30,
            fit_source="primary_next_close_normal_cost_bank", stress_model_refits=False,
            bootstrap_lower_is_calibrated_confidence=False, fit_options=FIT_OPTIONS,
            python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__)
        _write_json(manifest_path, manifest)
    with threadpool_limits(limits=1):
        # The independently frozen bank may already exist before this runner's first invocation.
        bundle = build_research_bundle(root, resume=True)
        cache = MonthlyFitCache(bundle["bank"], bundle["panel"]["dates"], bundle["begin"],
                                folder=results/"FITS", provenance=freeze_sha)
        print("Fitting fixed monthly expanding heads on mature normal-cost labels", flush=True)
        readiness = cache.prepare()
        _write_json(results / "FIT_READINESS.json", readiness)
        print("Writing causal prequential forecast ledger and diagnostics", flush=True)
        forecasts = prequential_forecasts(bundle, cache)
        _csv(forecasts, results / "PREQUENTIAL_FORECASTS.csv.gz")
        forecast_scores, forecast_bins = forecast_diagnostics(forecasts)
        _csv(forecast_scores, results / "FORECAST_SCORES.csv")
        _csv(forecast_bins, results / "FORECAST_BINS.csv")
        _write_json(results / "FORECAST_GATES.json", dict(
            diagnostics_only=True, changes_to_policy_or_search=False,
            primary_support="ALL_HEADS_READY", target="native_net_log_wealth_advantage",
            overlapping_labels_are_not_additive=True, pristine_holdout=False,
            lower_buffer_is_calibrated_confidence=False,
            diagnostics=forecast_scores.to_dict(orient="records")))
        scores, annual, common, drawdowns = [], [], [], []
        for arm in ARMS:
            for scenario, (ticket, impact, fill) in SCENARIOS.items():
                path_id = f"{arm}__{scenario}"
                folder = results / path_id
                if resume and (folder / "METRICS.json").exists():
                    required = ("DAILY.csv.gz", "ORDERS.csv.gz", "INSTRUCTIONS.csv.gz", "DECISIONS.npz",
                                "DECISIONS_META.json.gz", "POLICY_TRACE.csv.gz")
                    if not all((folder/name).exists() for name in required):
                        raise ValueError(f"INCOMPLETE_SAVED_PATH {path_id}")
                    metrics = _read_json(folder / "METRICS.json")
                    daily = pd.read_csv(folder / "DAILY.csv.gz", float_precision="round_trip")
                else:
                    callback = AccountPolicy(bundle, arm, cache)
                    panel = execution_panel(bundle["panel"], fill)
                    result = simulate(panel, bundle["f"], lambda k,w: bundle["targets"][k],
                        bundle["monthly"], legacy=bundle["core"], account_policy=callback,
                        allow_scheduled_hold=arm in LEARNED_ARMS, ticket=ticket, impact=impact,
                        start=str(pd.Timestamp(panel["dates"][bundle["begin"]]).date()),
                        end=str(pd.Timestamp(panel["dates"][-1]).date()), initial=INITIAL_CAPITAL)
                    metrics = summarize_path(bundle, arm, scenario, result, readiness)
                    daily = result["daily"]
                    save_path(folder, result, callback.trace, metrics)
                scores.append(metrics)
                annual.extend(annual_rows(bundle, daily, arm, scenario))
                drawdowns.extend(drawdown_rows(daily, arm, scenario))
                if readiness["postwarmup_start_idx"] is not None:
                    window = performance_window(bundle["core"], daily,
                                                start_idx=readiness["postwarmup_start_idx"])
                    if window is not None:
                        common.append(dict(path_id=path_id, arm=arm, scenario=scenario, **window))
                _csv(pd.DataFrame(scores), results / "SCORES.csv")
                manifest.update(completed_paths=len(scores), completed_path_ids=[r["path_id"] for r in scores],
                                all_heads_first_ready_idx=readiness["all_heads_first_ready_idx"],
                                postwarmup_start_idx=readiness["postwarmup_start_idx"])
                _write_json(manifest_path, manifest)
                print(f"{len(scores)}/18 {path_id}: CAGR {metrics['cagr']:.6f}, "
                      f"sampled DD {metrics['maxdd_sampled']:.6f}", flush=True)
        _csv(pd.DataFrame(annual), results / "ANNUAL_RETURNS.csv")
        _csv(pd.DataFrame(common), results / "COMMON_POST_WARMUP.csv")
        _csv(pd.DataFrame(drawdowns), results / "DRAWDOWN_EPISODES.csv")
    verify_experiment_freeze(root)
    manifest.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), completed_paths=18)
    _write_json(manifest_path, manifest)
    print("COMPLETE: 18 fixed paths; forecasts and diagnostic gates retained", flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    run(arguments.root, arguments.resume)
