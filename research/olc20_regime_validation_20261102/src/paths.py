"""Resolve authenticated local parents without modifying their modules."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
P19=ROOT/'parent/olc19_combined_risk_20261102'
P18=P19/'restore/olc18_execution_20261102'
P17=P18/'parent_archive'
P16=P17/'parent/olc16_contextual_rank_20261102'
for p in (P16/'src',P17/'src',P18/'src',P19/'src'):
    if str(p) not in sys.path: sys.path.append(str(p))
