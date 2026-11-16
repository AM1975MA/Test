#!/usr/bin/env python3
"""Restore fetched immutable UTF-8 text only after Git blob SHA and byte-size checks."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/workspace/scratch/23237d81ce2c/olc110')
RECEIPT = Path('/workspace/scratch/23237d81ce2c/olc111/research/restore/OLC110_RESTORE_RECEIPT.json')
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
records = []
for entry in payload['files']:
    rel = Path(entry['path'])
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError(f'Unsafe relative path: {rel}')
    raw = entry['content'].encode('utf-8')
    blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if len(raw) != entry['size'] or blob != entry['sha']:
        raise ValueError(f'Remote integrity mismatch: {rel} expected {entry["size"]}/{entry["sha"]}, got {len(raw)}/{blob}')
    target = BASE / rel
    if target.exists() and target.read_bytes() != raw:
        raise ValueError(f'Refusing to overwrite different existing file: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    local = target.read_bytes()
    if local != raw:
        raise ValueError(f'Write verification failed: {target}')
    target.chmod(0o444)
    records.append({'path': str(rel), 'size': len(local), 'git_blob_sha1': blob, 'sha256': hashlib.sha256(local).hexdigest(), 'remote_sha_verified': True, 'remote_size_verified': True, 'read_only': True})
receipt = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {k: payload[k] for k in ['repository', 'commit', 'remote_prefix', 'subtree_sha']}
old = {r['path']: r for r in receipt.get('files', [])}
old.update({r['path']: r for r in records})
receipt.update({'restored_at_utc': datetime.now(timezone.utc).isoformat(), 'files': [old[k] for k in sorted(old)], 'total_files': len(old), 'total_bytes': sum(r['size'] for r in old.values()), 'all_files_sha_and_size_verified': True, 'scope': 'Selected code, protocol, metadata and aggregate tables only; archived ledgers and bulk audit tables excluded.'})
RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'batch_files_verified': len(records), 'total_files_verified': len(old), 'receipt': str(RECEIPT)}))
