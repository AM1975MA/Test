#!/usr/bin/env python3
"""Render OLC73 report solely from verified CSVs; no optimization or refitting."""
from pathlib import Path
import pandas as pd,json,hashlib
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
sc=pd.read_csv(R/'OLC73_SCORECARD.csv')
a=pd.read_csv(R/'OLC73_ANNUAL.csv')
b=pd.read_csv(R/'OLC73_PAIRED_BLOCK6.csv')
qa=json.loads((R/'OLC73_INDEPENDENT_QA.json').read_text())
fmt=lambda n:f'{n*100:,.2f}%'.replace(',','.')
pp=lambda n:f'{n*100:+.2f} pp'

def get(m,pol,t,period,metric='cagr',fee=.001):
 x=sc[(sc.market==m)&(sc.policy==pol)&(sc.timing==t)&(sc.period==period)&(sc.fee==fee)]
 assert len(x)==1
 return float(x.iloc[0][metric])

def yearly(m,pol,t,yr,fee=.001):
 x=a[(a.market==m)&(a.policy==pol)&(a.timing==t)&(a.year==yr)&(a.fee==fee)]
 assert len(x)==1
 return float(x.iloc[0]['return'])

def table(rows,headers):
 return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])
parts=["# OLC73 — Allocazione fra i Top2: 64 replay nativi controllati", "",
"**8 novembre 2026 · Ricerca retrospettiva, non segnale di trading · Nessuna modifica a OLC19, OLC67 o `main`.**",
"",
"## Esito principale", "",
"Non emerge **un'unica allocazione** capace di migliorare contemporaneamente Europa e USA rispetto a 50/50 nello stesso regime di timing, sul periodo principale 2021–2024 e sull'intera serie. Il risultato più informativo è una **asimmetria del valore economico del primo/secondo ETF della coppia contestuale**, che cambia nel tempo.", "",
"- Nel periodo 2021–2024, in EU il 25/75 a favore del secondo ETF tende a battere il 75/25 a favore del primo; in USA domina il 75/25 a favore del primo.",
"- USA 2024: 75% sul primo avrebbe reso 115,91% nell'anno contro 78,61% del 50/50. USA 2025: lo stesso 75/25 sul primo rende appena 1,92% contro 13,57% del 50/50; il 75% sul secondo rende 26,62%. Le differenze non sono CAGR ma rendimenti annuali nativi.",
"- Gli USA del 2025–2026 e l'Europa del 2026 mostrano un'inversione dell'efficacia della preferenza per l'ordine dei Top2. **Non sappiamo ancora anticipare questa inversione** con segnali osservabili al momento della decisione.", "",
"Tutti i confronti modificano **soltanto** il peso tra i due ETF già selezionati da `TOP2_CONTEXT_REVALUE`. FUSION Return/ET/XGB, V6, FAST_LOCK3, prezzi, calendari e stop restano congelati.","",
"## Otto politiche preregistrate, ingresso immediato", ""]
labels={'HALF':'50/50 (OLC19)','TOP1_65':'65/35 sul primo','TOP1_75':'75/25 sul primo','TOP2_65':'35/65 sul secondo','TOP2_75':'25/75 sul secondo','INVOL63_CAP25':'Inverso volatilità 63 (25–75)','MOM63_LEADER65':'65% al maggiore momentum 63','MINVAR63_CAP25':'MinVar63 (25–75, OLC56)'}
rows=[]
for pol in labels:
 rows.append([labels[pol],fmt(get('EU',pol,'IMMEDIATE','ACTIVE2021_2024')),fmt(get('USA',pol,'IMMEDIATE','ACTIVE2021_2024')),
             fmt(get('EU',pol,'IMMEDIATE','FULL')),fmt(get('USA',pol,'IMMEDIATE','FULL'))])
parts.append(table(rows,['Pesi','EU CAGR 2021–24','USA CAGR 2021–24','EU CAGR FULL','USA CAGR FULL']))
parts+=['','FULL = febbraio 2019 → prima apertura luglio 2026; 2026 parziale; CAGR su 252 sedute contabili/anno. Commissioni legacy=0,001, stop friction=0,001. Non sono quotazioni broker.','',
"## Stesse politiche con DELAY3",'']
rows=[]
for pol in labels:
 rows.append([labels[pol],fmt(get('EU',pol,'DELAY3','ACTIVE2021_2024')),fmt(get('USA',pol,'DELAY3','ACTIVE2021_2024')),
             fmt(get('EU',pol,'DELAY3','FULL')),fmt(get('USA',pol,'DELAY3','FULL'))])
parts.append(table(rows,['Pesi','EU CAGR 2021–24','USA CAGR 2021–24','EU CAGR FULL','USA CAGR FULL']))
parts+=['',"La precedente OLC67 coincide esattamente con MINVAR63+DELAY3+FAST_LOCK3: **EU 34,43% / USA 51,27% CAGR 2021–24**, **EU 22,61% / USA 42,10% FULL**. Non è una nuova scoperta OLC73.",'',
"## Il cambio di leadership nel 2024–2026",'']
rows=[]
for m in ['EU','USA']:
 for yr in [2024,2025,2026]:
  rows.append([m,str(yr)+('*' if yr==2026 else ''),fmt(yearly(m,'HALF','IMMEDIATE',yr)),fmt(yearly(m,'TOP1_75','IMMEDIATE',yr)),fmt(yearly(m,'TOP2_75','IMMEDIATE',yr)),fmt(yearly(m,'MOM63_LEADER65','IMMEDIATE',yr))])
parts.append(table(rows,['Mercato','Anno','50/50','75% primo','75% secondo','65% momentum leader']))
parts+=['','*2026 cumulato sino alla prima apertura di luglio; non annualizzato. Nel ramo contabile nativo `d1` è il primo ETF ordinato dal ranking contestuale discendente, non necessariamente il più redditizio in futuro.','',
"## Rischio e costi",'']
rows=[]
for m in ['EU','USA']:
 for p in ['HALF','TOP1_75','TOP2_75','MINVAR63_CAP25','MOM63_LEADER65']:
  rows.append([m,labels[p],fmt(get(m,p,'IMMEDIATE','FULL','maxdd')),fmt(get(m,p,'DELAY3','FULL','maxdd')),
               fmt(get(m,p,'IMMEDIATE','FULL','cagr',fee=.003)),fmt(get(m,p,'DELAY3','FULL','cagr',fee=.003))])
parts.append(table(rows,['Mercato','Peso','DD FULL immediato','DD FULL DELAY3','CAGR FULL immediato costi 0,003','CAGR FULL DELAY3 costi 0,003']))
parts+=['',"Aumento dei costi da coefficiente 0,001 a 0,003: le differenze di direzione sul peso del primo/secondo ETF rimangono visibili, ma i CAGR sono più bassi. Il rischio USA di TOP1_75 con DELAY3 arriva a circa −30,65% FULL, contro −26,12% della baseline OLC19 immediata. Evitare di confondere questo confronto fra timing diversi con la sola variazione dei pesi.",'',
"## Incertezza e verifica di robustezza",'']
rows=[]
for m,p,t in [('EU','TOP2_75','IMMEDIATE'),('USA','TOP1_75','IMMEDIATE'),('EU','TOP2_75','DELAY3'),('USA','TOP1_75','DELAY3')]:
 for period in ['MAIN2021_2024','FULL']:
  x=b[(b.market==m)&(b.timing==t)&(b.policy==p)&(b.fee==.001)&(b.period==period)].iloc[0]
  rows.append([m,labels[p],t,period,pp(x.diff_annual_log),f'[{pp(x.ci_low)}; {pp(x.ci_high)}]'])
parts.append(table(rows,['Mercato','Peso','Timing','Periodo','Δ log rendimento annualizzato vs 50/50','IC95% block6 descrittivo']))
parts+=['',
"I bootstrap sono appaiati su blocchi circolari di 6 mesi (4.000 repliche); non correggono la ricerca su decine di test OLC01–72. **Tutti gli intervalli FULL riportati qui includono zero.** La performance del 2024/2025 e la selezione dell'allocazione vincente sono dati già esplorati: non c'è un holdout indipendente.",
"La verifica preregistrata richiedeva per una sola regola comune: miglioramento del FULL CAGR in *entrambi* EU/USA, MAIN non inferiore in entrambi e FULL MaxDD non deteriorato di oltre 3pp rispetto al 50/50 con lo stesso timing. **Nessuna delle sette politiche alternative supera tutti questi gate**. Non viene promossa alcuna strategia.","",
"## QA e limiti delle fonti",'']
parts += [f"- **64 replay nativi** = 8 pesi × 2 timing × 2 mercati × 2 coefficienti di costo; **{qa['verified_scorecard_period_rows']} periodi/metriche** ricalcolati autonomamente da rendimenti giornalieri.",
"- Parità **esatta dei 7 array** nativi di OLC19 sulla baseline 50/50/IMMEDIATE per entrambi i mercati; **16 serie log-rendimento** precedentemente eseguite in OLC67 coincidono (HALF e MINVAR, immediato/delay3, fee 0,001/0,003). 90 eventi mensili per mercato, le identità delle due posizioni sono fisse.",
"- Per MOM63 e INVOL63, i prezzi sono SOLO gli ultimi 64 Close completati prima dell'ingresso. In EU la disponibilità dei flag `observed` obbliga a fallback 50/50 in **34 su 90** eventi per ciascuna policy; in USA 4/90. I dati USA originali non includono i flag osservati, quindi il codice segue la convenzione storica OLC56 `observed = finite(C)&(C>0)`: **non certifica la reale osservabilità dei prezzi USA**.",
"- Come già noto, restano non certificati universo point-in-time, maschera quote USA, adjusted/total-return/dividendi omogenei, prezzi di esecuzione degli stop/bid-ask, costi broker effettivi e impatto della liquidità. Sono limiti rilevanti per ogni CAGR, non soltanto per OLC73.","",
"## Prossimo problema da studiare (nessun nuovo backtest in questo report)","",
"La prima posizione della coppia contestuale ha un vantaggio economico **che cambia segno nel tempo**. Piuttosto che una media di portafogli o un semplice selettore di policy (OLC69/70), il passo metodologicamente utile sarebbe un *modello pairwise* sulle stesse due opportunità, con target cronologicamente maturo `log((1+r_1)/(1+r_2))` a 21 e 42 sedute, e input ex ante originari Return/ET/XGB, margine contestuale, momentum e volatilità della coppia. Un test isolerebbe la capacità di prevedere quale ETF meriti più capitale, senza cambiare Top2 né timing. Fissare a priori la calibrazione/regularizzazione e valutare il 2024/2025 come date già esplorate, mai come nuovo OOS. È un progetto, NON un miglioramento dimostrato.","",
"**Decisione:** conservare OLC19 come baseline e OLC67 come candidato paper; registrare OLC73 come evidenza che la costruzione dei pesi Top2 è una leva importante, non ancora sfruttabile con una regola universale affidabile."]
path=ROOT/'REPORT_OLC73_IT.md';path.write_text('\n'.join(parts)+'\n',encoding='utf-8')
print(f'Wrote {path} ({path.stat().st_size} bytes)')