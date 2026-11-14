"""Explicit issuer-verified missing split, in forward economic units.
No inference of split ratios from returns, no raw-file mutation, no price clipping.
Historical units before the ex-date are unchanged; from ex-date each economic
unit represents ratio actual shares. Not a whole-share brokerage simulation.
"""
import pandas as pd

def forward_units(frame,ex_date,ratio):
    if ratio<=0:raise ValueError('Invalid official split ratio')
    out=frame.copy();out['Volume']=out['Volume'].astype(float);mask=out.index>=pd.Timestamp(ex_date)
    for col in ['Open','High','Low','Close']:out.loc[mask,col]=out.loc[mask,col]*ratio
    out.loc[mask,'Volume']=out.loc[mask,'Volume']/ratio
    return out
