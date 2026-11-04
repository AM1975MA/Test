#!/usr/bin/env python3
"""OLC44-N3: authenticated offline restore of the user's existing OLC14 assets.

Inputs are the ORIGINAL two Library ZIPs (not repackaged or substituted).
No remote uploads, no model loads during verify stage, no overwrite of source
files. This script does not run a background job or claim a new native CAGR.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile
from datetime import datetime, timezone

EXPECTED={
    "OLC14_Heads_Checkpoint_20261101.zip":{
        "size":364165692,
        "sha256":"a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458"},
    "OLC14_Fitting_Risultati_20261101.zip":{
        "size":40006829,
        "sha256":"4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1"}
}
VERIFY_MEMBERS=("HEADS_MANIFEST.json","RESULTS_MANIFEST.json")

def sha256(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        while b:=f.read(2<<20):
            h.update(b)
    return h.hexdigest()

def validate_zip_members(zf:zipfile.ZipFile):
    seen=set()
    for m in zf.infolist():
        p=PurePosixPath(m.filename.replace("\\","/"))
        if p.is_absolute() or any(v in ("..",".") for v in p.parts):
            raise ValueError("Unsafe archive path: "+m.filename)
        if m.filename in seen:
            raise ValueError("Duplicate ZIP member name: "+m.filename)
        seen.add(m.filename)
        if stat.S_ISLNK(m.external_attr >> 16):
            raise ValueError("ZIP symbolic link not accepted: "+m.filename)

def validate_original_zip(path:Path):
    if path.name not in EXPECTED:raise ValueError("Not an original OLC14 archive basename")
    m=EXPECTED[path.name]
    if not path.is_file():raise FileNotFoundError(path)
    if path.stat().st_size!=m["size"]:raise ValueError(f"ZIP size mismatch for {path.name}")
    digest=sha256(path)
    if digest!=m["sha256"]:raise ValueError(f"ZIP SHA256 mismatch for {path.name}")
    with zipfile.ZipFile(path) as z:
        validate_zip_members(z)
        count=len(z.infolist())
        if z.testzip() is not None:
            raise ValueError("ZIP CRC check failed")
    return {"file":str(path),"sha256":digest,"members":count}

def read_manifests(root:Path):
    found={}
    for name in VERIFY_MEMBERS:
        located=list(root.rglob(name))
        if len(located)!=1:
            raise FileNotFoundError(f"Expected exactly one {name}, found {len(located)}")
        p=located[0]
        doc=json.loads(p.read_text(encoding="utf-8"))
        if "files" not in doc or not isinstance(doc["files"],list):
            raise ValueError("Malformed manifest "+str(p))
        base=p.parent
        checks=0
        for member in doc["files"]:
            rel=PurePosixPath(member["path"])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("Unsafe manifest path")
            f=base / Path(*rel.parts)
            if not f.is_file() or f.stat().st_size!=int(member["bytes"]):
                raise ValueError("Missing/size mismatch: "+str(f))
            if sha256(f)!=member["sha256"]:
                raise ValueError("Manifest file hash mismatch: "+str(f))
            checks+=1
        found[name]={"path":str(p),"entries_verified":checks}
    if found["HEADS_MANIFEST.json"]["entries_verified"]!=848:
        raise ValueError("Head archive manifest not the original 848-entry set")
    if found["RESULTS_MANIFEST.json"]["entries_verified"]!=220:
        raise ValueError("Result archive manifest not the original 220-entry set")
    return found

def restore(heads:Path,results:Path,dest:Path):
    for p in (heads,results):
        validate_original_zip(p)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError("Restore destination must be empty to avoid overwriting data")
    dest.mkdir(parents=True,exist_ok=True)
    for p in (heads,results):
        with zipfile.ZipFile(p) as z:
            # Only after ZIP digest validation and path-safety checks.
            validate_zip_members(z)
            z.extractall(dest)
    verified=read_manifests(dest)
    audit={"restored_at_utc":datetime.now(timezone.utc).isoformat(),
           "source":"original user Library OLC14 two archives",
           "verified_zip_names":list(EXPECTED),
           "manifest_checks":verified,
           "trusted_restored":True,
           "native_refit_run":False,
           "raw_ETF_feature_source_reconstructed":False,
           "warning":"Prepared OLC11/OLC14 inputs do NOT contain valid 42-feature rows for new ETF by construction; source OHLC feature generation and train group reranking still required"}
    (dest/"OLC44N_OFFLINE_RESTORE_AUDIT.json").write_text(json.dumps(audit,indent=2)+"\n")
    return audit

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--heads",required=True,type=Path)
    ap.add_argument("--results",required=True,type=Path)
    ap.add_argument("--destination",required=True,type=Path)
    a=ap.parse_args()
    print(json.dumps(restore(a.heads,a.results,a.destination),indent=2))

if __name__=="__main__":
    main()
