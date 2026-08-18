#!/usr/bin/env python3
"""Build a deterministic SHA-256 manifest for the parity package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    excluded = {"manifest/PACKAGE_MANIFEST.json", "manifest/SHA256SUMS.txt"}
    files = [path for path in root.rglob("*") if path.is_file() and path.relative_to(root).as_posix() not in excluded]
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in sorted(files)
    ]
    payload = {
        "package": root.name,
        "purpose": "Titanium V2 historical/live-as-of parity correction",
        "official_final_date": "2026-07-01",
        "files": records,
    }
    manifest_dir = root / "manifest"
    manifest_dir.mkdir(exist_ok=True)
    (manifest_dir / "PACKAGE_MANIFEST.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [f"{row['sha256']}  {row['path']}" for row in records]
    (manifest_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
