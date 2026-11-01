"""Explicit feature identity and reproducible sampling contracts.
No automatic economic equivalences, feature selection or future-label use.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def canonical_matrix(frame:pd.DataFrame, canonical:list[str], aliases:dict[str,str]|None=None)->np.ndarray:
    aliases=dict(aliases or {})
    if frame.columns.duplicated().any() or len(canonical)!=len(set(canonical)):
        raise ValueError('Duplicate column names')
    if any(a in canonical or b not in canonical or b in aliases for a,b in aliases.items()):
        raise ValueError('Invalid alias mapping')
    missing=set(canonical)-set(frame)
    if missing:raise ValueError('Missing canonical columns: '+str(sorted(missing)))
    unknown=set(frame)-set(canonical)-set(aliases)
    if unknown:raise ValueError('Unknown columns: '+str(sorted(unknown)))
    for alias,original in aliases.items():
        if alias in frame and not frame[alias].equals(frame[original]):
            raise ValueError('Inconsistent alias: '+alias)
    x=frame.loc[:,canonical].to_numpy(dtype=float,copy=True)
    if np.isinf(x).any():raise ValueError('Infinite input is not a valid feature')
    return np.ascontiguousarray(x)

def column_parameters(width:int,mode:str)->tuple[int|float,float]:
    if not isinstance(width,int) or width<1:raise ValueError('Invalid input width')
    if mode=='LEGACY':return .4,.9
    if mode=='ALL':return 1.0,1.0
    if mode!='FIXED' or width<38:raise ValueError('Invalid mode or insufficient feature width')
    fraction=37.25/width
    if not 0<fraction<=1 or int(np.floor(np.float32(fraction)*width))!=37:
        raise ValueError('Cannot encode nominal37-column budget')
    return 16,fraction
