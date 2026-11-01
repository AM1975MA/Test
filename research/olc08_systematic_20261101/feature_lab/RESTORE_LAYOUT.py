"""Restore the single internal directory alias after extracting the complete checkpoint.
Run from an already extracted, hash-verified archive. Does not download prices or train.
"""
from pathlib import Path
import os,json,hashlib
root=Path(__file__).resolve().parent
alias=root/'parents/parents/olc07_calendar_20261101/phases/P0/legacy'
target=root/'parents/parents/eu_original_retest_20261031'
if not target.is_dir():raise FileNotFoundError('Complete checkpoint parent source not found')
if alias.is_symlink():
    if alias.resolve()!=target.resolve():alias.unlink()
elif alias.exists():raise RuntimeError('Refusing to replace an existing non-symlink legacy directory')
if not alias.exists():alias.symlink_to(os.path.relpath(target,alias.parent),target_is_directory=True)
print('Internal alias ready:',alias,'->',target)
manifest=root/'DELIVERY_MANIFEST.json'
if manifest.exists():
    obj=json.loads(manifest.read_text());verified=0
    for row in obj['files']:
        p=(root/row['path']).resolve()
        if not p.is_relative_to(root.resolve()):raise RuntimeError('Manifest path escapes root')
        if not p.is_file() or p.stat().st_size!=row['bytes']:raise RuntimeError('Missing/changed file: '+row['path'])
        h=hashlib.sha256()
        with p.open('rb') as f:
            for part in iter(lambda:f.read(4*1024*1024),b''):h.update(part)
        if h.hexdigest()!=row['sha256']:raise RuntimeError('Digest mismatch: '+row['path'])
        verified+=1
    print('Verified files:',verified)
print('Set OLC08F_ROOT to',root,'and run python -m pytest -q tests')
