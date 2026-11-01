from pathlib import Path
import sys,os
ROOT=Path(os.environ.get('OLC08_ROOT',Path(__file__).resolve().parents[1]))
P0=ROOT/'parents/olc07_calendar_20261101/phases/P0'
SOURCE=ROOT/'parents/eu_original_retest_20261031/source/research/tail-only-and-allocation-ablation-20261017'
sys.path[:0]=[str(P0/'src'),str(SOURCE),str(SOURCE/'vendor/etf_trader_v2/src')]
from etf_trader.source_only import kernel
from etf_trader.ma3.hybrid_producer import FEATURES_42,ET_MODEL_KW,XGB_MODEL_KW,corrected_target
from compact21_return_v1.core import recipe,prepare_targets,native_x
CAL=P0/'results/calendar'
