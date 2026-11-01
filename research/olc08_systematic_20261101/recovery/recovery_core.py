"""Explicit feature contracts and fail-closed, atomic research checkpoints."""
from __future__ import annotations
import hashlib,json,os,tempfile
from pathlib import Path
import numpy as np
import pandas as pd

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def rsi_domain(close:pd.DataFrame,h:int=14)->pd.DataFrame:
    """Preserve original EWM/finite arithmetic. Flat=50 is declared, not universal."""
    if h<1:raise ValueError('Positive lookback required')
    d=close.diff()
    up=d.clip(lower=0).ewm(alpha=1/h,adjust=False,min_periods=h).mean()
    down=(-d.clip(upper=0)).ewm(alpha=1/h,adjust=False,min_periods=h).mean()
    result=100-100/(1+up/down.replace(0,np.nan))
    result=result.mask((down==0)&(up>0),100.)
    result=result.mask((down==0)&(up==0),50.)
    return result

def lower_partial_rms(returns:pd.DataFrame,h:int)->pd.DataFrame:
    """Alternative downside size, not a correction of conditional dispersion."""
    if h<1:raise ValueError('Positive lookback required')
    return np.sqrt(returns.clip(upper=0).pow(2).rolling(h,min_periods=h).mean()*252)

def atomic_json(path:Path,obj:dict)->None:
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def inside(root:Path,name:str)->Path:
    root=root.resolve();path=(root/name).resolve()
    if not path.is_relative_to(root):raise ValueError('File escapes checkpoint directory')
    return path

def complete_checkpoint(root:Path,key:str,names:list[str],metadata:dict|None=None)->None:
    root=Path(root);files=[]
    for name in names:
        p=inside(root,name)
        if not p.is_file():raise FileNotFoundError(p)
        files.append({'path':name,'bytes':p.stat().st_size,'sha256':sha256(p)})
    atomic_json(root/'COMPLETE.json',{'key':key,'files':files,'metadata':metadata or {}})

def valid_checkpoint(root:Path,key:str)->bool:
    root=Path(root)
    try:
        obj=json.loads((root/'COMPLETE.json').read_text())
        if obj['key']!=key or not obj['files']:return False
        for item in obj['files']:
            p=inside(root,item['path'])
            if not p.is_file() or p.stat().st_size!=item['bytes'] or sha256(p)!=item['sha256']:return False
        return True
    except (OSError,ValueError,KeyError,TypeError):return False
