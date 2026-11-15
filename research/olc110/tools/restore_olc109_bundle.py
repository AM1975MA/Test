"""Verify and restore the immutable OLC109 study and OLC108 audit dependencies.

This archival helper does not execute or modify financial research code.
The archive is downloaded separately by the reader using the Library link.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile


ARCHIVE_SHA256 = "fc89eadb3ee94f6ade1dceafbd43707f5bac518bb889e4dc350f55de32e2281e"
MANIFEST_SHA256 = "4ff730283d1ee2870291a05c5fbea9b62df7da10e27c5107203f8fc0b7340af7"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_or_restore(archive_path, destination=None):
    archive_path = archive_path.expanduser().resolve(strict=True)
    if digest(archive_path) != ARCHIVE_SHA256:
        raise ValueError("Archive SHA-256 does not match the frozen OLC109 bundle")
    if destination is not None:
        destination = destination.expanduser().resolve()
        if destination.exists():
            raise FileExistsError("Destination must be a new directory: " + str(destination))
        destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path) as archive:
        payload = archive.read("BUNDLE_MANIFEST.json")
        if hashlib.sha256(payload).hexdigest() != MANIFEST_SHA256:
            raise ValueError("Bundle manifest SHA-256 mismatch")
        manifest = json.loads(payload)
        files = manifest["files"]
        members = archive.namelist()
        if len(members) != len(set(members)):
            raise ValueError("Duplicate archive member")
        if set(members) != set(files) | {"BUNDLE_MANIFEST.json"}:
            raise ValueError("Archive members do not exactly match the frozen manifest")
        for name in members:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("Unsafe archive path: " + name)

        temporary = None
        try:
            if destination is not None:
                temporary = Path(tempfile.mkdtemp(prefix=".olc109-restore-", dir=destination.parent))
            total = 0
            for name, metadata in sorted(files.items()):
                hasher = hashlib.sha256()
                count = 0
                output = None
                if temporary is not None:
                    target = temporary / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    output = target.open("xb")
                try:
                    with archive.open(name) as handle:
                        for block in iter(lambda: handle.read(1 << 20), b""):
                            hasher.update(block)
                            count += len(block)
                            if output is not None:
                                output.write(block)
                finally:
                    if output is not None:
                        output.close()
                if count != metadata["bytes"] or hasher.hexdigest() != metadata["sha256"]:
                    raise ValueError("Frozen member mismatch: " + name)
                total += count
            if temporary is not None:
                (temporary / "BUNDLE_MANIFEST.json").write_bytes(payload)
                if destination.exists():
                    raise FileExistsError(destination)
                temporary.rename(destination)
                temporary = None
        finally:
            if temporary is not None:
                shutil.rmtree(temporary)

    return {
        "status": "PASS_EVERY_FROZEN_MEMBER_VERIFIED",
        "archive_sha256": ARCHIVE_SHA256,
        "bundle_manifest_sha256": MANIFEST_SHA256,
        "files_checked": len(files),
        "uncompressed_member_bytes": total,
        "destination": str(destination) if destination is not None else None,
        "financial_paths": manifest["financial_paths"],
        "prior_baseline_paths": manifest["prior_baseline_paths"],
        "prior_source_price_csvs": manifest["prior_source_price_csvs"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--destination", type=Path)
    mode.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_or_restore(args.archive, args.destination), indent=2))
