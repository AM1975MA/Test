"""Reproduce the descriptive historical bridge chart from verified CSVs."""
from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(os.environ.get('RECONCILIATION_REPORT_ROOT',str(Path(__file__).resolve().parent)))
o=root/'results'
d=pd.read_csv(o/'EXACT_FINAL_BRIDGE.csv')
y=d.annual_log_pp.to_numpy();cum=np.r_[0.,np.cumsum(y)]
labels=['Selezione\na politica neutra','Concentrazione','DD-first /\nHighCAGR','V6','Protezione\nsistemica','Stop','Differenza\ncosti','Divario\ntotale']
fig,ax=plt.subplots(figsize=(12.5,6.3))
for i,v in enumerate(y):
    ax.bar(i,abs(v),bottom=min(cum[i],cum[i+1]),width=.66,hatch='//' if v<0 else None)
    ax.text(i,max(cum[i],cum[i+1])+.12,f'{v:+.3f}'.replace('.',','),ha='center',va='bottom',fontsize=11)
    if i<len(y)-1:ax.plot([i+.33,i+.67],[cum[i+1]]*2,linewidth=.8,alpha=.55)
ax.bar(len(y),cum[-1],width=.66)
ax.text(len(y),cum[-1]+.12,f'{cum[-1]:+.3f}'.replace('.',','),ha='center',va='bottom',fontsize=12,fontweight='bold')
ax.set_xticks(np.arange(8),labels,fontsize=10)
ax.set_ylabel('Punti di rendimento logaritmico annualizzato',fontsize=11)
ax.set_ylim(0,max(cum)+1.0)
ax.set_title('Dal BASE a Return-Rank + Hybrid: riconciliazione del divario storico',loc='left',fontsize=15,pad=22)
ax.spines[['top','right']].set_visible(False)
ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
fig.text(.07,.055,'Original149 | 01/02/2017–01/07/2026 | Media di 3 revisioni correlate dei prezzi',fontsize=10)
fig.text(.07,.025,'Il totale non è alpha dimostrato: IC esplorativo 95% [−4,116; +15,135] punti logaritmici annui.',fontsize=10)
fig.subplots_adjust(left=.075,right=.985,top=.87,bottom=.19)
fig.savefig(o/'CONTRIBUTION_BRIDGE.png',dpi=180)
fig.savefig(o/'CONTRIBUTION_BRIDGE.svg')
plt.close(fig)
print(o/'CONTRIBUTION_BRIDGE.png')
