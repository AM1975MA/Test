from pathlib import Path
import argparse


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--v6',type=Path,required=True); a=ap.parse_args()
    s=a.v6.read_text()
    old="    for h in [10,21,63,126]: D[f'vol_{h}']=base.snapshot(lr.rolling(h,min_periods=h).std()*np.sqrt(252),dates)\n"
    new=old+"    D['vol_ratio_10_63']=D['vol_10']/D['vol_63'].replace(0,np.nan)\n"
    if s.count(old)!=1: raise RuntimeError(f'expected one vol block, got {s.count(old)}')
    a.v6.write_text(s.replace(old,new,1)); print('added production vol_ratio_10_63')
if __name__=='__main__': main()
