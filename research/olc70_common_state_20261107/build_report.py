#!/usr/bin/env python3
from pathlib import Path
import pandas as pd,numpy as np,json,zipfile,io
R=Path(__file__).resolve().parent
S=R/'results'
sc=pd.read_csv(S/'OLC70_COMPARISON.csv')
a=pd.read_csv(S/'OLC70_ANNUAL_COMPARISON.csv')
skill=pd.read_csv(S/'OLC70_FORECAST_SKILL_SUMMARY.csv')
shift=pd.read_csv(S/'OLC70_STATE_SHIFT_SUMMARY.csv')
act=pd.read_csv(S/'OLC70B_ACTION_COUNTS_ANNUAL.csv')
outcome=pd.read_csv(S/'OLC70B_ACTION_OUTCOMES_ANNUAL.csv')
qa=json.loads((S/'OLC70_INDEPENDENT_QA.json').read_text())

def score(m,p,period,fee=.001,col='cagr'):
  z=sc[(sc.market==m)&(sc.policy==p)&(sc.period==period)&(np.isclose(sc.fee,fee))]
  assert len(z)==1,(m,p,period,fee)
  return float(z.iloc[0][col])

def annual(m,year,p):
  d=a[(a.market==m)&(a.year==year)&(a.policy==p)&(np.isclose(a.fee,.001))]
  assert len(d)==1,(m,year,p)
  return float(d.iloc[0].year_return)

def aspercent(x):return f'{x*100:+.2f}%'

def pct(x):return f'{x*100:.2f}%'

header='''# OLC70 — Controfattuali allo stesso stato e apprendimento adattivo

**7 novembre 2026 · RESEARCH ONLY · Nessuna modifica a OLC19 o `main`.**

Questo è un esperimento eseguito nel motore OLC19, non un progetto teorico. Il periodo febbraio 2019–prima apertura luglio 2026 è già stato esplorato ripetutamente negli esperimenti OLC01–69. Nessuna finestra è un nuovo holdout indipendente. La conclusione è **NEGATIVA** per l'apprendimento adattivo; i protocolli sono fissati nei commit GitHub prima dei rispettivi esiti.

## 1. Risultati CAGR verificati

Tutte le varianti usano selezioni TOP2_CONTEXT_REVALUE, V6, FAST_LOCK3, stop-friction .001, e fee legacy .001. La nuova variante OLC70B parte in ciascun mese dal proprio stato contabile effettivo, genera 4 azioni controfattuali e aggiorna il learner solo su label precedenti e mature.

| Mercato e periodo | OLC19 (50/50 immediato) | OLC67 (MINVAR63 + DELAY3) | OLC70A (labels su stato OLC19) | OLC70B (labels on-policy) |
|---|---:|---:|---:|---:|
'''
for m,label in [('EU','Europa'),('USA','USA')]:
 for per,window in [('ACTIVE2021_2024','2021–2024'),('FULL','FULL 2019–lug2026*')]:
  header+=f'| {label} {window} | '+ ' | '.join(pct(score(m,p,per)) for p in ['OLC19','OLC67','OLC70A','OLC70B'])+' |\n'
header+='''
*Luglio 2026 contiene soltanto la prima apertura. Il CAGR segue la convenzione 252 valorizzazioni/anno dell'engine OLC19, non l'annualizzazione del solo 2026.*

### Max drawdown completo

| Mercato | OLC19 | OLC67 | OLC70A | OLC70B |
|---|---:|---:|---:|---:|
'''
for m,label in [('EU','Europa'),('USA','USA')]:
 header+=f'| {label} | '+' | '.join(pct(score(m,p,'FULL',col='maxdd')) for p in ['OLC19','OLC67','OLC70A','OLC70B'])+' |\n'
header+='''
### Rendimenti annuali 2024–2026 (2026 parziale, NON annualizzato)

| Mercato e anno | OLC19 | OLC67 | OLC70A | OLC70B |
|---|---:|---:|---:|---:|
'''
for m,label in [('EU','Europa'),('USA','USA')]:
 for y in [2024,2025,2026]:
  header+=f'| {label} {y}{"*" if y==2026 else ""} | '+' | '.join(pct(annual(m,y,p)) for p in ['OLC19','OLC67','OLC70A','OLC70B'])+' |\n'
header+='''
Nel 2024 OLC70B intercetta parte del vantaggio europeo rispetto alla vecchia strategia ma non preserva il rally USA. Nel 2025 è inferiore a entrambe le strategie USA; nel 2026 parziale non conserva il rendimento completo della vecchia strategia nei due mercati.

**Gate ex ante:** fallito. OLC70B presenta CAGR FULL e MAIN inferiori a OLC19 negli USA. Nessuna promozione; il ramo operativo resta quello originale.

## 2. Nuovo meccanismo: 4 azioni dalla stessa fotografia del conto

A ogni apertura mensile la simulazione originale OLC19 fornisce lo stato pre-trade: quantità ETF, strumenti difensivi, liquidità, cooldown, lock, stop, target e scheduler. Le quattro alternative sono A=50/50+IMMEDIATE, B=MINVAR63+IMMEDIATE, C=50/50+DELAY3, D=MINVAR63+DELAY3. I quattro rami partono dallo stesso capitale e stato e corrono fino all'apertura del mese successivo.

- **OLC70A:** addestra usando questi differenziali da snapshot della policy OLC19 sempre mantenuta.
- **OLC70B:** ad ogni mese sceglie e consolida **solo** il ramo realmente selezionato. Conserva lo stato risultante per il mese successivo; le etichette delle quattro azioni vengono aggiunte alla storia soltanto dopo il mese. Non si mescolano NAV di strategie indipendenti.
- Learner volutamente invariato da OLC69: 4 feature ex-ante, StandardScaler train-only, Ridge α25 per ciascuna delle alternative B/C/D, almeno 24 osservazioni e training fino a t−2; A se nessun vantaggio stimato superiore a 5 logbp.

I dati del 2019–2026 sono già stati utilizzati per costruire questa famiglia di esperimenti: i risultati di OLC70B NON rappresentano validazione indipendente.

## 3. Perché il risultato resta negativo: test sulla capacità di previsione

Ogni cella della tabella indica RMSE sul vantaggio mensile relativo all'azione A, in **log-basis-point**; più basso è migliore. Il riferimento è una previsione train-only della media degli outcome maturi, disponibile con le medesime informazioni. I periodi iniziali prima del minimo training sono esclusi.

| Mercato | Azione da prevedere | Media storica RMSE | OLC70B Ridge RMSE | Delta Ridge − media |
|---|---|---:|---:|---:|
'''
for m,label in [('EU','Europa'),('USA','USA')]:
 for arm in 'BCD':
  z=skill[(skill.policy=='OLC70B')&(skill.market==m)&(skill.action==arm)].iloc[0]
  header+=f'| {label} | {arm} | {z.historical_mean_rmse_logbp:.1f} | {z.ridge_rmse_logbp:.1f} | {z.delta_rmse_logbp:+.1f} |\n'
header+='''
**Cinque confronti su sei sono peggiori della media storica.** Correggere il target rende il confronto causale sullo stato, ma non aggiunge capacità di prevedere in anticipo la miglior azione.

## 4. Quanto importa davvero la differenza di stato?

La differenza fra etichette on-policy e quelle calcolate dagli stati della baseline non è nulla, soprattutto per le azioni con ritardo (C/D):

| Mercato | Azione | Eventi con differenza osservabile | 95° percentile dello scarto assoluto in logbp |
|---|---|---:|---:|
'''
for m,label in [('EU','Europa'),('USA','USA')]:
 for arm in 'BCD':
  z=shift[(shift.market==m)&(shift.action==arm)].iloc[0]
  header+=f'| {label} | {arm} | {z.nonzero_pct*100:.1f}% | {z.p95_abs_logbp:.1f} |\n'
header+='''
Gli scostamenti dimostrano che il problema di OLC69 (conti con stati diversi) era concreto. Ma passare da OLC70A a OLC70B produce solo un piccolo cambiamento nel CAGR; il limite dominante è la **debolezza dei segnali disponibili per prevedere il vantaggio relativo**, non un semplice bug di contabilità.

## 5. Audit delle azioni effettivamente scelte

OLC70B usa fallback A fino alla maturazione del training e in altri mesi non convenienti, ma sceglie frequentemente DELAY3 (C/D). I risultati ex-post della decisione rispetto all'alternativa A che parte dallo stesso stato sono registrati a parte. Segue il conteggio delle scelte per mercato su 82 eventi con input pre-signal:

| Mercato | A 50/50 immediato | B MINVAR immediato | C 50/50 DELAY3 | D MINVAR DELAY3 |
|---|---:|---:|---:|---:|
'''
rt=dat=lambda n:pd.read_csv(S/n)
for m,label in [('EU','Europa'),('USA','USA')]:
 r=rt('OLC70B_ROUTE.csv').query('market==@m');d=r.action.value_counts()
 header+=f'| {label} | '+' | '.join(str(int(d.get(k,0))) for k in 'ABCD')+' |\n'
header+='''
### Validazioni tecniche

- Hash SHA256 degli archivi originali OLC67 e OLC68 verificati.
- OLC70A: replay A e D bitwise sui sette array nativi OLC19 per entrambi i mercati; **356 rami** da uno snapshot OLC19 (89 mesi × 4) per ciascun mercato, con ogni ramo A coincidente con il segmento originale.
- OLC70B: **356 rami** on-policy per mercato (89 × 4); tutti gli eventi consolidati producono le **sette matrici del replay completo identiche bitwise** alla simulazione giornaliera non spezzata.
- 178 osservazioni mese×mercato per ciascuno dei due insiemi di label; 164 mesi×mercato con quattro feature disponibili; 342 previsioni per ciascuna variante; 40 coppie CAGR/MaxDD ricalcolate indipendentemente con errore numerico massimo <1e−10.
- Date as-of precedenti alle aperture; training t−2; conteggio training e azioni ricostruiti, nessuna label futura come input. L'OLC70B è osservazionale retrospettivo, non un out-of-sample incontaminato.
- Il costo .003 è applicato agli stessi piani decisionali, senza riottimizzarli. Lo storico delle quotazioni di stop è modellistico (OHLC), non broker grade.

## 6. Decisione e prossima ipotesi rigorosa

**OLC70A e OLC70B NON PROMOSSI.** Una simulazione controfattuale rigorosa evita di apprendere differenziali fra stati incompatibili, ma non crea automaticamente informazione sui movimenti futuri. Il risultato USA rimane inferiore alla baseline e nel 2024–2026 non recupera sufficientemente i rally; per migliorare occorre un predittore realmente incrementale del vantaggio dei due ETF, sviluppato e congelato su dati non minati o con una verifica prospettica.

Se in futuro si riapre la ricerca, usare i dati on-policy per valutare separatamente: (i) guadagno da concentrazione sul leader, (ii) costo di perdere le prime due sedute e (iii) probabilità di permanenza della leadership, accompagnati da controlli cronologici e un periodo prospettico. Non creare ora una nuova griglia per ottimizzare 2024/2025/2026.

**Riferimenti originali:** OLC19 FAST_LOCK3; OLC67 MINVAR63+DELAY3; OLC68 prezzi/indicatori pre-signal; OLC69 precedente selettore. Protocolli OLC70A e OLC70B congelati su GitHub (branch `research/olc70-common-state-counterfactual-20261107`).
'''
(R/'REPORT_OLC70_IT.md').write_text(header)
print('Report lines',len(header.splitlines()),'chars',len(header))