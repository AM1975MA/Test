"""Restore OLC110 plus its frozen OLC109 and OLC108 dependencies.

Read a complete OLC110 repository snapshot, verify every original study file,
and restore two omitted input panels from the separately downloaded OLC109 ZIP.
Only a newly created destination is written. No simulation is executed.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import tempfile

from restore_olc109_bundle import verify_or_restore


REUSED_INPUTS = {
    "source/data/XETRA_EUR_ETF.npz": "14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96",
    "data/LIQUIDITY.npz": "b95fa3d67837fa06c5705aa4aea09807d396464ab44ec1671031d797b57f4485",
}


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def check_path(name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or "\\" in name:
        raise ValueError("Unsafe study path: " + name)


def check_file(path, metadata):
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.stat().st_size != metadata["bytes"] or digest(path) != metadata["sha256"]:
        raise ValueError("Frozen study file mismatch: " + str(path))


def restore(study, archive, destination):
    study = study.expanduser().resolve(strict=True)
    destination = destination.expanduser().resolve()
    if destination.exists():
        raise FileExistsError("Destination must be a new directory: " + str(destination))
    manifest_path = study / "provenance/OLC110_SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    missing = []
    for name, metadata in files.items():
        check_path(name)
        path = study / name
        if name in REUSED_INPUTS and not path.exists():
            missing.append(name)
            continue
        check_file(path, metadata)
    for name, expected in REUSED_INPUTS.items():
        if files[name]["sha256"] != expected:
            raise ValueError("The frozen reused-input contract changed: " + name)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".olc110-restore-", dir=destination.parent))
    try:
        restored = temporary / "restored"
        prior_verification = verify_or_restore(archive, restored)
        target = restored / "olc110"
        shutil.copytree(study, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name, expected in REUSED_INPUTS.items():
            frozen_input = restored / "olc109" / name
            if digest(frozen_input) != expected:
                raise ValueError("OLC109 input contract mismatch: " + name)
            output = target / name
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(frozen_input, output)
        for name, metadata in files.items():
            check_file(target / name, metadata)
        if destination.exists():
            raise FileExistsError(destination)
        restored.rename(destination)
    finally:
        shutil.rmtree(temporary)

    return {
        "status": "PASS_OLC110_AND_PRIOR_DEPENDENCIES_RESTORED",
        "destination": str(destination),
        "olc110_original_files_verified": len(files),
        "olc110_source_manifest_sha256": digest(manifest_path),
        "reused_inputs": REUSED_INPUTS,
        "inputs_absent_from_git_source": sorted(missing),
        "olc109_archive_sha256": prior_verification["archive_sha256"],
        "prior_archive_files_verified": prior_verification["files_checked"],
        "sibling_directories": ["olc108", "olc109", "olc110"],
        "simulations_executed": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--olc109-archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--study", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(restore(args.study, args.olc109_archive, args.destination), indent=2))
