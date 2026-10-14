"""Export annual net returns and observed min-max bands across frozen downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

def annual_returns(dates,equity):
    dates=pd.DatetimeIndex(dates)
    if dates.has_duplicates or not dates.is_monotonic_increasing or np.any(equity<=0):raise ValueError('Invalid equity path')
    logs=np.diff(np.r_[0.,np.log(equity)])
    f=pd.DataFrame(dict(year=dates.year,log_return=logs))
    annual=np.expm1(f.groupby('year').log_return.sum())
    if abs(np.log1p(annual).sum()-np.log(equity[-1]))>1e-12:raise ValueError('Year decomposition does not reconcile')
    return annual

def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter
    ap=argparse.ArgumentParser();ap.add_argument('--replays',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    specs=[('BASE','LINEAR_MONTHLY','baseline_control','#4669A2'),
           ('LINEAR annuale','LINEAR_NUMERICAL_REPAIR','candidate','#D78A38'),
           ('LINEAR mensile','LINEAR_MONTHLY','candidate','#2F8B76')]
    rows=[];paths={};hashes={};calendar=None
    for label,variant,folder,color in specs:
        for i in (1,2,3):
            p=Path(a.replays)/f'v2replay-{variant}-r{i}'/folder/'FULL_UNIVERSE_PATH.npz'
            with np.load(p,allow_pickle=False) as z:dates=z['dates'].copy();equity=z['equity'][0].copy()
            if calendar is None:calendar=dates
            elif not np.array_equal(calendar,dates):raise ValueError('Different calendars')
            for year,value in annual_returns(dates,equity).items():rows.append(dict(strategy=label,download=i,year=int(year),net_return=float(value)))
            paths[(label,i)]=equity;hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    df=pd.DataFrame(rows);df.to_csv(out/'ANNUAL_RETURNS_3_DOWNLOADS.csv',index=False)
    aggregate=df.groupby(['strategy','year']).net_return.agg(['mean','min','max','std']).reset_index()
    aggregate.to_csv(out/'ANNUAL_RETURNS_DISPERSION.csv',index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    years=sorted(df.year.unique());x=np.arange(len(years));fig,ax=plt.subplots(figsize=(17,7.5),layout='constrained')
    for j,(label,_,_,color) in enumerate(specs):
        g=aggregate[aggregate.strategy==label].set_index('year').loc[years];pos=x+(j-1)*.25
        ax.bar(pos,g['mean'],width=.22,color=color,label=label,alpha=.84)
        ax.errorbar(pos,g['mean'],yerr=np.vstack([g['mean']-g['min'],g['max']-g['mean']]),fmt='none',ecolor='#263344',capsize=4,lw=1.4)
        for i,dx in zip((1,2,3),(-.045,0,.045)):
            values=df[(df.strategy==label)&(df.download==i)].set_index('year').loc[years].net_return
            ax.scatter(pos+dx,values,s=16,color='#182331',alpha=.65,zorder=4)
    ax.axhline(0,color='#455363',lw=.8);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    ax.set_xticks(x,[str(y)+('*' if y in (2017,2026) else '') for y in years]);ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylabel('Rendimento netto del periodo');ax.set_title('ETF Trader V2 | Rendimenti per anno e dispersione dei tre download',loc='left',fontweight='bold',pad=20)
    ax.legend(frameon=False,ncol=3,loc='upper left')
    fig.text(.01,.005,'Barre: media dei 3 download. Baffi: minimo–massimo osservati; punti: singoli download (non intervalli di confidenza).\n* 2017 dal 1 febbraio; 2026 fino al 1 luglio: periodi parziali, rendimenti non annualizzati. Attribuzione per anno delle sedute del calendario canonico.',fontsize=9,color='#455363')
    fig.savefig(out/'ANNUAL_RETURNS.png',dpi=170,bbox_inches='tight');fig.savefig(out/'ANNUAL_RETURNS.pdf',bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(15,7),layout='constrained')
    for label,_,_,color in specs:
        values=np.stack([paths[(label,i)] for i in (1,2,3)])
        ax.fill_between(calendar,values.min(axis=0),values.max(axis=0),color=color,alpha=.15)
        ax.plot(calendar,values.mean(axis=0),color=color,label=label,lw=2)
    ax.set_yscale('log');ax.grid(alpha=.18);ax.legend(frameon=False);ax.set_ylabel('Capitale: investimento iniziale = 1 (scala logaritmica)')
    ax.set_title('ETF Trader V2 | Crescita del capitale e dispersione dei tre download',loc='left',fontweight='bold',pad=15)
    fig.text(.01,.005,'Linea: media dei patrimoni. Fascia: minimo–massimo osservati dei tre download congelati; non intervallo di confidenza.',fontsize=9,color='#455363')
    fig.savefig(out/'CAPITAL_GROWTH.png',dpi=170,bbox_inches='tight');fig.savefig(out/'CAPITAL_GROWTH.pdf',bbox_inches='tight');plt.close(fig)
    provenance=dict(sources_sha256=hashes,rows=len(df),strategies=3,downloads=3,years=years,
        metric='compounded net returns by canonical execution-session year; partial years not annualized',
        dispersion='observed minimum-maximum across three correlated frozen downloads, not a confidence interval',
        all_calendars_identical=True,annual_decomposition_reconciles=True)
    (out/'CHART_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print('ANNUAL_AND_CAPITAL_CHARTS_EXPORTED')

if __name__=='__main__':main()
