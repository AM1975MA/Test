"""Research history policy; model definitions are never changed."""
import pandas as pd

RAW_START = pd.Timestamp('2011-01-01')
TRAIN_START = pd.Timestamp('2012-01-01')

def trim(frame):
    return frame.loc[pd.to_datetime(frame.date).ge(RAW_START)].reset_index(drop=True)

def mature_rows(frame, exit_col, year):
    cutoff = pd.Timestamp(year,1,1)
    return frame.loc[frame.signal_date.ge(TRAIN_START) & frame.signal_date.lt(cutoff) & frame[exit_col].lt(cutoff)]

def selection_disagreement(frames):
    aligned=[x.set_index('date').sort_index()[['top1','top2']] for x in frames]
    assert len(aligned)==3
    assert all(x.index.equals(aligned[0].index) for x in aligned)
    assert all(x.index.is_unique and not x.isna().any().any() for x in aligned)
    n=len(aligned[0]); assert n
    sets=[x.apply(lambda r: tuple(sorted(r)),axis=1) for x in aligned]
    any1=(aligned[0].top1!=aligned[1].top1)|(aligned[0].top1!=aligned[2].top1)
    any2=(aligned[0]!=aligned[1]).any(axis=1)|(aligned[0]!=aligned[2]).any(axis=1)
    anys=(sets[0]!=sets[1])|(sets[0]!=sets[2])
    pairs=[]
    for a,b in [(0,1),(0,2),(1,2)]:
        pairs.append({'pair':[a+1,b+1], 'top1_fraction':float((aligned[a].top1!=aligned[b].top1).mean()),'top2_ordered_fraction':float((aligned[a]!=aligned[b]).any(axis=1).mean()),'top2_set_fraction':float((sets[a]!=sets[b]).mean())})
    return {'sessions':n,'top1_any_count':int(any1.sum()),'top1_any_fraction':float(any1.mean()),'top2_ordered_any_count':int(any2.sum()),'top2_ordered_any_fraction':float(any2.mean()),'top2_set_any_count':int(anys.sum()),'top2_set_any_fraction':float(anys.mean()),'pairwise':pairs}
