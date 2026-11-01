"""Generate the tested OLC06 engine from the exact verified OLC05 source."""
from pathlib import Path
import hashlib,shutil
ROOT=Path(__file__).resolve().parent
VENDOR=ROOT/'vendor/olc05_transitions_20261031'
source=VENDOR/'src/vector_engine.py'
if hashlib.sha256(source.read_bytes()).hexdigest()!='8d228b1dbaf6c667226ea1f3ce516f50375a79753fb10c1247e9a613625c9698':
    raise ValueError('Source engine is not the frozen OLC05 version')
s=source.read_text()
s=s.replace("['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE']","['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE','DELAY']")
anchor="        elif policy=='PHASE':\n"
if s.count(anchor)!=1:raise ValueError('Expected unique source anchor')
s=s.replace(anchor,"""        elif policy=='DELAY':
            # Only target scheduling changes; risk and observed-quote rules stay downstream.
            if fraction<1 or int(fraction)!=fraction:raise ValueError('Delay requires a positive integer session count')
            if economically_changed:remaining=int(fraction)
            if p.sum()==0:
                tar=p.copy();remaining=0
            elif np.sum(units*PC[k])<=1e-14:
                tar=p.copy();remaining=0
            elif remaining>1:
                remaining-=1  # Keep previous target, not a daily rebalance to drifted weights.
            else:
                tar=p.copy();remaining=0
"""+anchor)
if hashlib.sha256(s.encode()).hexdigest()!='a6dbe479353ba8edf7922f564a6e53827b5c74611371c84e803aaf0342703d2e':
    raise ValueError('Generated engine differs from tested engine')
(ROOT/'src').mkdir(exist_ok=True);(ROOT/'tests').mkdir(exist_ok=True)
(ROOT/'results/paths').mkdir(parents=True,exist_ok=True)
(ROOT/'results/daily').mkdir(parents=True,exist_ok=True)
(ROOT/'src/vector_engine.py').write_text(s)
shutil.copy2(VENDOR/'src/methods.py',ROOT/'src/methods.py')
for p in (VENDOR/'tests').glob('*.py'):shutil.copy2(p,ROOT/'tests'/p.name)
print('Generated engine SHA256 matches tested source')
