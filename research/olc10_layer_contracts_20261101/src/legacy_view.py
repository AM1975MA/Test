"""Stable runtime matrix view, preserving the existing model's duplicated slots."""
from schema import canonical_matrix
import numpy as np

def legacy_view(frame,canonical,aliases,view):
    x=canonical_matrix(frame,list(canonical),dict(aliases))
    lookup={name:i for i,name in enumerate(canonical)}
    try:positions=[lookup[aliases.get(name,name)] for name in view]
    except KeyError as e:raise ValueError('Unknown legacy view feature') from e
    return np.ascontiguousarray(x[:,positions])
