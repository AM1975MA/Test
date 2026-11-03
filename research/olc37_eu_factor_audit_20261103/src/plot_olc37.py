#!/usr/bin/env python3
from pathlib import Path
import numpy as np,pandas as pd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1];r=P/'results';f=P/'figures';f.mkdir(exist_ok=True)
d=pd.read_csv(r/'EU_FACTOR_CLONE_DAILY.csv',parse_dates=['date'])
fig,ax=plt.subplots(figsize=(12,6.4))
for col,label,style in [
 ('strategy_OLC19_index','OLC19 EU (NAV archivio, netto)','-'),
 ('style_clone_fee_index','Clone stile a 5 proxy (costo ipotetico)','-'),
 ('EU_broad_EXSA_index','Europa 600 — EXSA (prezzo)','--'),
 ('US_broad_SXR8_index','USA S&P 500 — SXR8 (prezzo)','--'),
 ('US_IT_QDVE_index','Tecnologia USA — QDVE (prezzo)','--')]:
 ax.plot(d.date,d[col],style,label=label,linewidth=2 if col.startswith('strategy') else 1.5)
ax.set_title('OLC37: confronto descrittivo, stessi Open EUR osservati (2021–2024)')
ax.set_xlabel('Data');ax.set_ylabel('Indice da 100 (non total-return certificato)')
ax.grid(alpha=.25);ax.legend(loc='upper left',fontsize=9)
fig.tight_layout();fig.savefig(f/'EU_FACTOR_CLONE_VS_PORTFOLIO.png',dpi=145);plt.close(fig)

w=pd.read_csv(r/'EU_STYLE_TRAIN_BY_YEAR.csv')
labels=['EXSA.DE','SXR8.DE','SXRV.DE','QDVE.DE','EXX1.DE','cash_weight'];print_cols=labels
fig,ax=plt.subplots(figsize=(11,5.4))
bottom=np.zeros(len(w));years=w.year.astype(str)
for c in print_cols:
 val=w[c].to_numpy(float)*100
 ax.bar(years,val,bottom=bottom,label=c)
 bottom+=val
ax.set_ylim(0,105);ax.set_ylabel('Peso stimato dal solo passato (%)')
ax.set_title('Clone OLC37: proxy e cassa per anno (stile dei rendimenti precedenti)')
ax.legend(loc='center left',bbox_to_anchor=(1.0,.5),fontsize=9);ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(f/'EU_STYLE_WEIGHTS_BY_YEAR.png',dpi=145,bbox_inches='tight');plt.close(fig)

p=pd.read_csv(r/'EU_SEMICONDUCTOR_TECH_EXPOSURE_DIAGNOSTIC.csv')
fig,ax=plt.subplots(figsize=(10.5,5.2));years=p.year.astype(str)
first=p.mean_VVSM_semiconductor_portfolio_weight_pct.to_numpy()
second=p.mean_QDVE_US_IT_portfolio_weight_pct.to_numpy()
ax.bar(years,first,label='VVSM.DE — semiconduttori',width=.65)
ax.bar(years,second,bottom=first,label='QDVE.DE — IT USA',width=.65)
ax.set_ylabel('Peso medio sul NAV del portafoglio (%)')
ax.set_title('EU OLC19: peso effettivo medio nei due ETF tecnologici (nessun look-through)')
ax.set_ylim(0,65);ax.legend();ax.grid(axis='y',alpha=.2)
for i,v in enumerate(first+second): ax.text(i,v+.8,f'{v:.1f}%',ha='center',fontsize=10)
fig.tight_layout();fig.savefig(f/'EU_TECH_SEMIS_ACTUAL_HOLDINGS.png',dpi=145);plt.close(fig)

l=pd.read_csv(r/'EU_FACTOR_LEADERSHIP_DIAGNOSTIC.csv',parse_dates=['signal_date'])
y=l.groupby(l.signal_date.dt.year).agg(same=('same_leader','sum'),n=('same_leader','size'),mean_diff=('past_leader_minus_ew_pp','mean'))
fig,ax=plt.subplots(figsize=(9,5.2));ax.bar(y.index.astype(str),y.same/y.n*100)
ax.axhline(20,linestyle='--',linewidth=1,label='Riferimento ingenuo 1/5 (non test statistico)')
ax.set_ylim(0,60);ax.set_ylabel('Leader passato = leader dei 126 giorni successivi (%)')
ax.set_title('Persistenza della leadership in cinque proxy, 2021–2024')
ax.grid(axis='y',alpha=.2);ax.legend()
fig.tight_layout();fig.savefig(f/'EU_FACTOR_LEADERSHIP_HIT_BY_YEAR.png',dpi=145);plt.close(fig)
print('WROTE',[(x.name,x.stat().st_size)for x in f.glob('*.png')])
