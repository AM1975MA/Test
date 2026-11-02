"""Minimal, hash-checked timing patch to the unchanged OLC16 accounting engine.
NOW/NOW equals legacy; PREVIOUS/PREVIOUS equals legacy LAG1. Mixed modes
and OFF are diagnostic probes, not new strategy recommendations.
"""
from pathlib import Path
import hashlib
_p=Path(__file__).resolve().parents[1]/'parent/olc16_contextual_rank_20261102/src/vector_engine.py'
if not _p.exists():_p=Path(__file__).resolve().parents[2]/'olc16_contextual_rank_20261102/src/vector_engine.py'
_b=_p.read_bytes()
assert hashlib.sha1(b'blob '+str(len(_b)).encode()+b'\0'+_b).hexdigest()=='9aa1afec426cc042ebe51048e451d5b16a93ed3b'
_s=_b.decode()
def _replace(old,new):
 global _s
 assert _s.count(old)==1,old
 _s=_s.replace(old,new)
_replace('top4=None, risk_on=True, lag_systemic=False):','top4=None, risk_on=True, lag_systemic=False, exposure_timing="NOW", stop_timing="NOW"):')
_replace('    if policy not in','''    if exposure_timing not in ('NOW','PREVIOUS','OFF') or stop_timing not in ('NOW','PREVIOUS','OFF'):
        raise ValueError('Unknown information timing')
    if lag_systemic:
        if (exposure_timing,stop_timing)!=('NOW','NOW'):
            raise ValueError('Do not combine lag_systemic with explicit modes')
        exposure_timing=stop_timing='PREVIOUS'
    if policy not in''')
_replace("    if lag_systemic:\n        gap=np.concatenate([gap[:1]*0,gap[:-1]]);ud1=np.r_[0.,ud1[:-1]];uneg=np.r_[0.,uneg[:-1]]",'''    pgap=np.concatenate([gap[:1]*0,gap[:-1]])
    pud1=np.r_[0.,ud1[:-1]]; puneg=np.r_[0.,uneg[:-1]]
    egap,eud,euneg=(pgap,pud1,puneg) if exposure_timing=='PREVIOUS' else (gap,ud1,uneg)
    sgap,sud,suneg=(pgap,pud1,puneg) if stop_timing=='PREVIOUS' else (gap,ud1,uneg)''')
_replace("        pg=float(np.dot(tar,gap[k]));sysm=bool(risk_on and active and ((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75)))",'''        pg=float(np.dot(tar,egap[k]));sysm=bool(risk_on and active and exposure_timing!='OFF' and ((pg<=-.032 and eud[k]>=.70) or (pg<=-.044 and euneg[k]>=.75)))
        stop_pg=float(np.dot(tar,sgap[k]))
        stop_systemic=bool(risk_on and active and ((stop_pg<=-.032 and sud[k]>=.70) or (stop_pg<=-.044 and suneg[k]>=.75)))
        stop_armed=stop_timing!='OFF' and (stop_systemic or sud[k]>=.55)''')
_replace('and (sysm or ud1[k]>=.55):','and stop_armed:')
exec(compile(_s,'<OLC17_hash_checked_engine>','exec'),globals())
