"""Isolated, immutable checkpoint *contract* for ETF Trader V2 research.

This module is NOT wired to the trading engine and never fits a learner.
Copies a caller-produced XGBoost UBJ plus exact inputs and validates them.
The manifest proves byte identity, not financial correctness or authenticity.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Mapping


class CheckpointError(ValueError):
    """A model checkpoint does not meet the frozen training contract."""


REQUIRED_META = frozenset({
    "cutoff", "training_exit_before_cutoff", "feature_names", "seed",
    "model_parameters", "runtime_versions", "source_commit", "cohort_key_hash",
})


def _canonical(data: object) -> bytes:
    try:
        return json.dumps(data, sort_keys=True, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as err:
        raise CheckpointError("non-JSON checkpoint metadata") from err


def _sha_file(path: Path) -> dict:
    digest = hashlib.sha256()
    n = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            n += len(block)
    return {"sha256": digest.hexdigest(), "size": n}


def _validate_metadata(metadata: Mapping) -> None:
    missing = REQUIRED_META - metadata.keys()
    if missing:
        raise CheckpointError("missing metadata: " + ", ".join(sorted(missing)))
    try:
        date.fromisoformat(metadata["cutoff"])
    except (ValueError, TypeError) as err:
        raise CheckpointError("invalid annual cutoff") from err
    if metadata["training_exit_before_cutoff"] is not True:
        raise CheckpointError("training maturity attestation is not true")
    fs = metadata["feature_names"]
    if not isinstance(fs, list) or not fs or any(not isinstance(f, str) or not f for f in fs) or len(set(fs)) != len(fs):
        raise CheckpointError("invalid feature schema")
    if not isinstance(metadata["model_parameters"], dict) or not isinstance(metadata["runtime_versions"], dict):
        raise CheckpointError("missing parameter/runtime dictionaries")
    _canonical(metadata)


def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not name or name in (".", "..") or "/" in name or "\\" in name or name.startswith("."):
        raise CheckpointError("unsafe asset name")


def create_checkpoint(destination: Path, model_path: Path, sources: Mapping[str, Path],
                      metadata: Mapping) -> dict:
    """Build a frozen directory, never overwrite an existing checkpoint.

    Inputs are copied verbatim; no model training or price transformation occurs.
    The caller must verify cutoff/labels with its own training-maturity audit;
    metadata's maturity flag alone is *not* a data-proven causality check.
    """
    dest, model = Path(destination), Path(model_path)
    if dest.exists() or dest.is_symlink():
        raise CheckpointError(f"checkpoint exists: {dest}")
    _validate_metadata(metadata)
    if not sources:
        raise CheckpointError("no input sources were supplied")
    for name in sources:
        _validate_name(name)
    if not model.is_file() or model.is_symlink():
        raise CheckpointError("model path is missing or symlinked")
    for path in sources.values():
        src = Path(path)
        if not src.is_file() or src.is_symlink():
            raise CheckpointError("source path is missing or symlinked")

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{dest.name}.stage.", dir=dest.parent))
    try:
        (tmp / "models").mkdir()
        (tmp / "sources").mkdir()
        paths = {"models/model.ubj": model}
        for name, path in sources.items():
            paths[f"sources/{name}"] = Path(path)
        records = {}
        for logical, source in sorted(paths.items()):
            staged = tmp / logical
            shutil.copyfile(source, staged)
            copied = _sha_file(staged)
            if copied != _sha_file(source):
                raise CheckpointError("source changed during copying")
            records[logical] = copied
        manifest = {"schema": "etf-v2-checkpoint-v1", "metadata": dict(metadata), "files": records}
        payload = _canonical(manifest)
        (tmp / "manifest.json").write_bytes(payload + b"\n")
        (tmp / "manifest.sha256").write_text(hashlib.sha256(payload + b"\n").hexdigest() + "\n")
        if dest.exists() or dest.is_symlink():
            raise CheckpointError(f"checkpoint exists: {dest}")
        os.rename(tmp, dest)
        return manifest
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def verify_checkpoint(destination: Path, *, expected_sources: Mapping[str, Path] | None = None,
                      expected_metadata: Mapping | None = None) -> dict:
    """Fail closed on any changed model, saved input, manifest or current input."""
    dest = Path(destination)
    try:
        raw = (dest / "manifest.json").read_bytes()
        expected_manifest_hash = (dest / "manifest.sha256").read_text().strip()
    except (OSError, UnicodeError) as err:
        raise CheckpointError("checkpoint manifest missing") from err
    if hashlib.sha256(raw).hexdigest() != expected_manifest_hash:
        raise CheckpointError("manifest checksum mismatch")
    try:
        manifest = json.loads(raw)
    except (ValueError, UnicodeError) as err:
        raise CheckpointError("invalid manifest") from err
    if manifest.get("schema") != "etf-v2-checkpoint-v1":
        raise CheckpointError("unsupported checkpoint schema")
    _validate_metadata(manifest["metadata"])
    if expected_metadata is not None and _canonical(expected_metadata) != _canonical(manifest["metadata"]):
        raise CheckpointError("metadata mismatch")
    files = manifest["files"]
    if "models/model.ubj" not in files:
        raise CheckpointError("model missing from manifest")
    for logical, expected in files.items():
        group, separator, filename = logical.partition("/")
        if separator != "/" or group not in ("sources", "models"):
            raise CheckpointError("invalid manifest file path")
        _validate_name(filename)
        file_path = dest / logical
        if file_path.is_symlink() or not file_path.is_file() or _sha_file(file_path) != expected:
            raise CheckpointError(f"digest mismatch: {logical}")
    if expected_sources is not None:
        if set(expected_sources) != {name.split("/", 1)[1] for name in files if name.startswith("sources/")}:
            raise CheckpointError("source mismatch: unexpected source names")
        for name, path in expected_sources.items():
            _validate_name(name)
            path = Path(path)
            if not path.is_file() or path.is_symlink() or _sha_file(path) != files[f"sources/{name}"]:
                raise CheckpointError(f"source mismatch: {name}")
    return manifest
