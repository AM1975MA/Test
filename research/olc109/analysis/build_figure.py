"""Publication-style static figure from the saved financial paths only."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,MultipleLocator
from matplotlib.colors import TwoSlopeNorm
from matplotlib.dates import YearLocator,DateFormatter

def build(root):
    root=Path(root).resolve();out=root/'figures';out.mkdir(exist_ok=True)
    score=pd.read_csv(root/'analysis/ALL_SCORECARD.csv');annual=pd.read_csv(root/'analysis/ALL_ANNUAL_RETURNS.csv')
    new='DEDUP_DUAL_TREND_OPP';old='DUAL21'
    green='#087f72';blue='#4776ad';gray='#777c84';ink='#1a2b3c';red='#b34545'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,'axes.titleweight':'bold',
                         'axes.labelcolor':ink,'text.color':ink,'axes.edgecolor':'#d0d8df','axes.spines.top':False,
                         'axes.spines.right':False,'grid.alpha':.28,'figure.facecolor':'#f8fafb','axes.facecolor':'white'})
    fig=plt.figure(figsize=(17,11.8));gs=fig.add_gridspec(2,2,height_ratios=[1.1,.9],hspace=.32,wspace=.24)
    ax=fig.add_subplot(gs[0,0])
    for arm,label,color in [(old,'Doppio selettore precedente',blue),('PASSIVE','S&P 500 in EUR (SXR8)',gray),(new,'Opportunità con trend positivo',green)]:
        row=score[(score.arm==arm)&(score.scenario=='BASE')].iloc[0]
        d=pd.read_csv(root/row.result_directory/row.path_id/'DAILY.csv.gz')
        ax.plot(pd.to_datetime(d.date),d.nav_close,color=color,lw=1.8 if arm!=new else 2.4,label=label)
    ax.set_title('Capitale nel tempo · partenza €10.000',loc='left',pad=15)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'€{x/1000:.0f}mila'))
    ax.xaxis.set_major_locator(YearLocator());ax.xaxis.set_major_formatter(DateFormatter('%Y'))
    ax.grid(axis='y');ax.legend(loc='upper left',frameon=False,fontsize=9.6)
    ax=fig.add_subplot(gs[0,1]);scenarios=['BASE','ZERO_COST','DOUBLE_COST','LAG1','LAG2'];xx=np.arange(5)
    for arm,off,col in [(old,-.19,blue),(new,.19,green)]:
        vals=score[(score.arm==arm)].set_index('scenario').loc[scenarios,'cagr'].to_numpy()*100
        bars=ax.bar(xx+off,vals,width=.36,color=col)
        for bar,value in zip(bars,vals):ax.text(bar.get_x()+bar.get_width()/2,value+.6,f'{value:.1f}'.replace('.',','),ha='center',fontsize=10,color=col,fontweight='bold')
    ax.axhline(30,color=red,ls=(0,(4,3)),lw=1.2)
    ax.text(4.48,30.7,'Obiettivo 30%',ha='right',color=red,fontsize=10)
    ax.set_ylim(0,34);ax.set_xticks(xx,['Base','Senza\ncosti','Costi\ndoppi','Ritardo\n+1 seduta','Ritardo\n+2 sedute'])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x:.0f}%'));ax.grid(axis='y');ax.set_axisbelow(True)
    ax.set_title('CAGR annuo · stessi cinque scenari',loc='left',pad=15)
    ax=fig.add_subplot(gs[1,0]);years=list(range(2020,2027))
    mat=np.array([annual[(annual.arm==arm)&(annual.scenario=='BASE')].set_index('year').loc[years,'annual_return'].to_numpy()*100 for arm in (old,new)])
    ax.imshow(mat,cmap='RdYlGn',norm=TwoSlopeNorm(vmin=-25,vcenter=0,vmax=120),aspect='auto')
    ax.set_yticks([0,1],['Precedente','Nuovo']);ax.set_xticks(range(7),['2020*','2021','2022','2023','2024','2025','2026*'])
    for i in range(2):
        for j in range(7):ax.text(j,i,f'{mat[i,j]:+.1f}%'.replace('.',','),ha='center',va='center',fontsize=12,fontweight='bold',color=ink)
    ax.set_title('Rendimenti annuali · il 2024 resta nel confronto',loc='left',pad=15)
    for spine in ax.spines.values():spine.set_visible(False)
    ax=fig.add_subplot(gs[1,1]);base=score[score.scenario=='BASE']
    ax.scatter(-base.maxdd_sampled*100,base.cagr*100,s=40,color='#bdc8d2',edgecolors='white',linewidth=.6,label='Altre configurazioni',zorder=2)
    for arm,col,mark,label in [(old,blue,'o','Precedente'),(new,green,'o','Nuovo candidato'),('PASSIVE',gray,'D','SXR8')]:
        r=base[base.arm==arm].iloc[0];x=-r.maxdd_sampled*100;y=r.cagr*100
        ax.scatter([x],[y],s=100,marker=mark,color=col,edgecolors='white',zorder=3)
        offset=(9,8) if arm!=old else (9,-14)
        ax.annotate(label,(x,y),xytext=offset,textcoords='offset points',fontsize=9.5,color=col,fontweight='bold')
    for arm,text in [('HORIZON63_TOP1','Top1 a 3 mesi'),('HORIZON126_TOP1','Top1 a 6 mesi')]:
        r=base[base.arm==arm].iloc[0];ax.annotate(text,(-r.maxdd_sampled*100,r.cagr*100),xytext=(-7,-12),textcoords='offset points',ha='right',fontsize=9,color=gray)
    ax.axhline(30,color=red,ls=(0,(4,3)),lw=1.2)
    ax.axhline(0,color='#b9c3cd',lw=.7)
    ax.set_xlim(10,95);ax.set_ylim(-19,33);ax.grid(alpha=.18);ax.set_axisbelow(True)
    ax.set_xlabel('Massimo drawdown campionato · perdita %')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'{x:.0f}%'))
    ax.set_title('40 configurazioni · rendimento e rischio osservati',loc='left',pad=15)
    fig.suptitle('OLC109  |  Migliora la selezione, il 30% resta da dimostrare',x=.06,y=.985,ha='left',fontsize=21,fontweight='bold')
    fig.text(.06,.948,'2.096 ETF EUR Xetra · 02/03/2020–30/10/2026 · 40 configurazioni × 5 scenari · nessuna leva di conto',fontsize=12,color=gray)
    fig.text(.06,.065,'* Rendimenti annuali parziali: 2020 da marzo; 2026 fino al 30 ottobre.',fontsize=10.5,color=gray)
    fig.text(.06,.024,'BASE: €1 per ordine + 0,15% per lato; imposte escluse, cash senza rendimento, unità economiche frazionarie.\nRicerca adattiva su un passato già osservato. Drawdown misurato a Open/Close, senza soglia di esclusione in questa fase.',fontsize=10.5,color=gray)
    fig.subplots_adjust(left=.075,right=.96,top=.895,bottom=.125)
    for extension in ('png','svg'):fig.savefig(out/f'OLC109_RISULTATI_PRINCIPALI.{extension}',dpi=180,facecolor=fig.get_facecolor())
    plt.close(fig)
    print(out/'OLC109_RISULTATI_PRINCIPALI.png')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();build(a.root)
