"""Deterministic null-information and lossless feature-schema helpers."""
import hashlib
import numpy as np
import pandas as pd

def permute_block(frame, columns, seed, market):
    if not set(columns)<=set(frame):raise ValueError('Missing block columns')
    if frame.duplicated(['signal_date','ticker']).any():raise ValueError('Duplicate date/ticker')
    out=frame.copy()
    for date,g in frame.groupby('signal_date',sort=True):
        order=g.sort_values('ticker').index
        token=f'{seed}|{market}|{pd.Timestamp(date).isoformat()}'
        rng=np.random.default_rng(int.from_bytes(hashlib.sha256(token.encode()).digest()[:8],'little'))
        permutation=rng.permutation(len(order))
        out.loc[order,columns]=frame.loc[order,columns].to_numpy()[permutation]
    return out

def canonicalize(frame, aliases):
    for duplicate,original in aliases.items():
        if duplicate not in frame or original not in frame or original in aliases or not frame[duplicate].equals(frame[original]):
            raise ValueError(f'Not an exact independent alias: {duplicate} -> {original}')
    canonical=frame.drop(columns=list(aliases)).copy()
    return canonical,{'original_columns':list(frame.columns),'aliases':dict(aliases),'canonical_columns':list(canonical.columns)}

def restore_columns(frame, metadata):
    if list(frame.columns)!=metadata['canonical_columns']:raise ValueError('Canonical schema differs')
    out=frame.copy()
    for duplicate,original in metadata['aliases'].items():out[duplicate]=out[original]
    return out.loc[:,metadata['original_columns']]
