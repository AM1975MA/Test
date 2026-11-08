#!/usr/bin/env python3
"""Source-backed Italian OLC74 decision report; outputs computed from frozen CSV results."""
from pathlib import Path
import json,hashlib,zipfile
import numpy as np,pandas as pd
root=Path(__file__).resolve().parent;R=root/'results'
score=pd.concat([pd.read_csv(R/n) for n in ['OLC74_SCORECARD.csv','OLC74B_SCORECARD.csv','OLC74C_SCORECARD.csv']],ignore_index=True)
ann=pd.concat([pd.read_csv(R/n) for n in ['OLC74_ANNUAL.csv','OLC74B_ANNUAL.csv','OLC74C_ANNUAL.csv']],ignore_index=True)
pair=pd.read_csv(R/'OLC74_PAIR_PANEL.csv');pair.event_date=pd.to_datetime(pair.event_date)
forecast=pd.read_csv(R/'OLC74_FORECAST_SKILL.csv'); top10=pd.read_csv(R/'OLC74B_FORECAST_SKILL.csv'); onpol=pd.read_csv(R/'OLC74C_FORECAST_SKILL_SUMMARY.csv'); assoc=pd.read_csv(R/'OLC74_ASSOCIATIONS.csv');
ci=pd.read_csv(R/'OLC74_PAIRED_BLOCK6.csv'); cqa=json.loads((R/'OLC74C_QA.json').read_text());aQA=json.loads((R/'OLC74_QA.json').read_text()); ia=json.loads((R/'OLC74_INDEPENDENT_QA.json').read_text());ic=json.loads((R/'OLC74C_INDEPENDENT_QA.json').read_text());gate=pd.read_csv(R/'OLC74_POLICY_GATES.csv')

def pct(v):return f'{v*100:+.2f}%'.replace('.',',')
def dd(v):return f'{v*100:.2f}%'.replace('.',',')
def get(m,p,t,period,col='cagr'):
 d=score[(score.market==m)&(score.policy==p)&(score.timing==t)&(score.fee==.001)&(score.period==period)]
 assert len(d)==1,(m,p,t,period)
 return float(d.iloc[0][col])
def annual(m,p,t,y):
 d=ann[(ann.market==m)&(ann.policy==p)&(ann.timing==t)&(ann.fee==.001)&(ann.year==y)]
 assert len(d)==1
 return float(d.iloc[0]['return'])
rows=[]
policies=['HALF','MINVAR63','FUSION_CONF','RETURN_CONF','PAIR_RIDGE','PAIR_LOGIT','RISK_PLUS_RIDGE','TOP10_RIDGE','TOP10_LOGIT','OLC74C_ONPOLICY']
for p in policies:
 if p=='OLC74C_ONPOLICY':t='IMMEDIATE'
 else:t='IMMEDIATE'
 rows.append(f"| {p} | {pct(get('EU',p,t,'ACTIVE2021_2024'))} | {pct(get('USA',p,t,'ACTIVE2021_2024'))} | {pct(get('EU',p,t,'FULL'))} | {pct(get('USA',p,t,'FULL'))} | {dd(get('EU',p,t,'FULL','maxdd'))} | {dd(get('USA',p,t,'FULL','maxdd'))} |")
annual_table=[]
for m in ('EU','USA'):
 for y in (2024,2025,2026):
  annual_table.append(f"| {m} | {y}{'*' if y==2026 else ''} | {pct(annual(m,'HALF','IMMEDIATE',y))} | {pct(annual(m,'MINVAR63','IMMEDIATE',y))} | {pct(annual(m,'FUSION_CONF','IMMEDIATE',y))} | {pct(annual(m,'OLC74C_ONPOLICY','IMMEDIATE',y))} |")
quality=[]
for m in ('EU','USA'):
 a=forecast[(forecast.market==m)&(forecast.period=='MAIN')].iloc[0]
 b=top10[(top10.market==m)&(top10.period=='MAIN')].iloc[0]
 c=onpol[(onpol.market==m)&(onpol.period=='MAIN')].iloc[0]
 quality.append(f"| {m} | {a.ridge_mse:.5f} / {a.mean_only_mse:.5f} | {a.logit_brier:.3f} / {a.train_frequency_brier:.3f} | {b.mse:.5f} / {b.null_mse:.5f} | {c.ridge_MSE_bp2:,.0f} / {c.mean_only_MSE_bp2:,.0f} |".replace(',000',' 000'))
corr=[]
for x in ['d_return','d_hybrid_smooth','d_fusion','d_mom21','d_mom63','d_log_vol63','corr63']:
 vals=[]
 for m in ('EU','USA'):
  d=assoc[(assoc.market==m)&(assoc.period=='MAIN')&(assoc.feature==x)].iloc[0]
  vals.append(f'{d.spearman:+.3f} (n={d.n})')
 corr.append(f"| {x} | {vals[0]} | {vals[1]} |")
full_ci=[]
for m in ('EU','USA'):
 for period in ('MAIN','FULL'):
  q=ci[(ci.market==m)&(ci.timing=='IMMEDIATE')&(ci.policy=='FUSION_CONF')&(ci.period==period)].iloc[0]
  full_ci.append(f"| {m} | {period} | {q.delta_log_ann_pp:+.2f} pp | [{q.ci95_lo:+.2f}; {q.ci95_hi:+.2f}] pp | {q.positive_months}/{q.months} |")
cf=pd.read_csv(R/'OLC74C_ON_POLICY_COUNTERFACTUAL_LABELS.csv');links=[]
for m in ('EU','USA'):
 d=cf[cf.market==m];rho=d.marginal_y_logbp.corr(d.price_monthly_spread_logbp)
 links.append(f"| {m} | {rho:.3f} | {int((d.w25_stops!=d.w75_stops).sum())}/{len(d)} | {d.marginal_y_logbp.mean():+.1f} bp |")
win=[]
for m in ('EU','USA'):
 for y in (2024,2025,2026):
  d=pair[(pair.market==m)&(pair.event_date.dt.year==y)&pair.diff_month_log.notna()]
  win.append(f'| {m} | {y} | {int((d.diff_month_log>0).sum())}/{len(d)} | {d.diff_month_log.mean()*100:+.2f}% |')
report=f'''# OLC74 — Gestione causale delle esposizioni tra i due ETF: audit e replay nativi

**8 novembre 2026 · Ricerca retrospettiva, nessuna promozione in produzione.** Il periodo febbraio 2019–prima apertura luglio 2026 e' gia' stato esplorato in OLC01–73; OLC74 NON costituisce una nuova validazione indipendente dell'alpha.

## Decisione in sintesi

**Fra le policy testate, nessuna allocazione dinamica supera i controlli prestabiliti in Europa e negli USA.** La differenza di score `ORIGINAL_FUSION` e' l'indicatore semplice piu' interessante negli USA, ma penalizza l'Europa e il suo beneficio americano sull'intera finestra non e' robusto al ricampionamento a blocchi. I tre modelli di previsione diretta (OLC74A, OLC74B, OLC74C) NON superano i rispettivi predittori banali nel 2021–24. Anche 45 coppie Top10/mese aggiungono informazione sui ticker, ma non decine di regimi indipendenti per mese.

**Causalita' verificata e suo limite:** il vantaggio della concentrazione in un ETF si puo' calcolare con interventi diversi **da identico stato contabile** nel motore OLC19 (stesse posizioni, free cash, V6, stop/lock, OHLC esogeni). L'effetto `do(w1=.75)` meno `do(w1=.25)` e' causalmente identificato *nel simulatore a prezzi fissi*. La correlazione di questo effetto con score/indicatori storici non e' causalita' economica ne' dimostra profittabilita' futura.

## 1. Contratto e disegno preregistrato

GitHub research branch: `research/olc74-top2-exante-allocation-20261108`. I tre protocolli sono stati congelati **prima dei rispettivi risultati**: OLC74A originale, OLC74B dopo la prima diagnostica negativa, OLC74C dopo A/B. Per B/C non viene falsamente dichiarata un'indipendenza della scelta dell'esperimento. Nessun post-outcome tuning.

- **Scelta ETF invariata:** originali FUSION → TOP2_CONTEXT_REVALUE, 90 segnali mensili EU e USA, V6, FAST_LOCK3, stop friction 0,001.
- **Informazione utilizzata:** punteggi RETURN, ORIGINAL_SMOOTH, ORIGINAL_FUSION, momentum 21 e 63 sedute, volatilita' relativa 63 e correlazione fra i due ETF, calcolati usando esclusivamente Close precedenti all'apertura dell'evento. Due mesi di maturazione minima delle label prima dell'addestramento.
- **A:** Ridge e LogisticRegression con sei caratteristiche; i target prevedono rendimenti OPEN-next-month relativi. Politiche di controllo: 50/50, MINVAR63, tilt su differenza FUSION, tilt su differenza RETURN, Ridge, Logit e MINVAR più Ridge.
- **B:** tutte le 45 coppie possibili del Top10 originale al mese, training simmetrico (`ETF1↔ETF2` → segno predizione invertito), pesi per gruppo mensile; Ridge e Logit, nessuna identita' ticker.
- **C:** tre interventi `.25/.50/.75` sul primo ETF da stesso stato completo on-policy; 89 episodi maturi per mercato, tre rami controfattuali ognuno, training Ridge sulle loro differenze effettive nel mese t solo da t−2. Unico portafoglio reale simulato con stato persistente.
- **Replay:** 56 A +16 B +4 C = **76 percorsi completi**, con commissioni simulate coefficienti legacy .001 e .003; prequential e regole di stop originali. Le commissioni non equivalgono a prezzi bid/ask verificati.

## 2. Evidenza: correlazioni ex ante con il vincitore della coppia

La grandezza obiettivo e' `log(Open1_next/Open1_now) - log(Open2_next/Open2_now)`, dopo la scelta della coppia originale. Coefficiente Spearman su **2021–2024**:

| Feature ante-segnale | EU | USA |
|---|---:|---:|
{chr(10).join(corr)}

**Interpretazione:** il differenziale FUSION ha associazione debole con la vittoria relativa, e negli USA e' quasi nullo sulla semplice differenza di rendimento mensile. La volatilita' relativa e' piu' associata in Europa, ma con soli 38 mesi maturi e NON si replica negli USA. Queste sono associazioni condizionate alla selezione delle coppie Top2, non evidenze causali indipendenti; i sette confronti e decine di ricerche precedenti impongono cautela statistica.

### Chi vince: primo o secondo ETF?

| Mercato | Anno | Mesi vinti dal primo ETF | Spread medio mensile primo−secondo |
|---|---|---:|---:|
{chr(10).join(win)}

Il regime di efficacia relativa cambia: nel 2024 il primo ETF vince spesso negli USA, nel 2025/2026 il vantaggio si ribalta. Un classificatore di regime deve anticipare tali inversioni, non scegliere retrospettivamente i pesi vincenti.

## 3. Skill prequential: modelli complessi contro semplici controlli

| Mercato | OLC74A Ridge MSE vs mean-only | OLC74A Logit Brier vs frequenza storica | OLC74B Top10 Ridge MSE vs predizione nulla | OLC74C eff. causale Ridge vs mean-only, bp² |
|---|---:|---:|---:|---:|
{chr(10).join(quality)}

I benchmark B sono volutamente semplici (previsione zero/0,5) mentre A/C usano la rispettiva media delle etichette storiche; i valori MSE per prezzi sono in **log-return²** e quelli C in **bp²**, non vanno confrontati direttamente. **Tutti i nostri nuovi learner incrementali hanno errore maggiore dei controlli MAIN nei due mercati**, anche con training sulle altre coppie del Top10. Il target C e' stato misurato sotto il percorso proprio effettivo, non sullo stato diverso di un'altra strategia.

## 4. Performance del motore OLC19 su periodi perfettamente comparabili

Tutte le righe sono con **IMMEDIATE, FAST_LOCK3 e fee 0,001**; differenti soltanto nei pesi fra gli stessi due ETF (nessuna modifica FUSION o stop). Il periodo principale MAIN e' 2021–2024; FULL febbraio 2019–luglio 2026 parziale. **CAGR e MaxDD**:

| Policy peso primo ETF | EU MAIN | USA MAIN | EU FULL | USA FULL | EU FULL MaxDD | USA FULL MaxDD |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

Le varianti A/B sono state testate anche con DELAY3 e fee 0,003. Il punto di partenza OLC67 (MINVAR63+DELAY3) mantiene EU MAIN 34,43%, USA MAIN 51,27%, EU FULL 22,61%, USA FULL 42,10%. Anche qui la relazione fra segnale e premio relativo non migliora automaticamente spostando la data di esecuzione.

### FOCUS 2024–2026, CAGR non applicabile ai singoli anni parziali

| Mercato | Anno | HALF | MINVAR63 | FUSION_CONF | OLC74C on-policy |
|---|---:|---:|---:|---:|---:|
{chr(10).join(annual_table)}

*2026 include soltanto il periodo disponibile sino all'apertura di luglio; ritorno cumulato NON annualizzato.*

Negli USA la policy FUSION_CONF ha un MaxDD completo marginalmente inferiore alla baseline (−25,96% contro −26,12%), ma il beneficio di rendimento del 2024 viene ridotto dal 2025–2026. Confronti diretti con OLC73 TOP1_75 evidenziano un CAGR USA MAIN 65,46% e FULL 44,43%, ma con MaxDD FULL −27,66% e un 2025 gravemente sfavorevole: **non e' una validazione di un peso fisso 75/25**.

## 5. Incertezza e stabilita' temporale della FUSION_CONF USA

Intervalli bootstrap descrittivi a blocchi *circolari di sei mesi*, 4.000 ricampionamenti, di **delta log rendimento annualizzato** versus HALF; NON differenze aritmetiche di CAGR e NON corretti per tutti i numerosi tentativi OLC.

| Mercato | Periodo | Delta log annuo | IC95% descrittivo | Mesi favorevoli |
|---|---|---:|---:|---:|
{chr(10).join(full_ci)}

Per USA, sull'intera finestra l'intervallo comprende zero. I mesi USA più importanti a favore della FUSION_CONF comprendono maggio e ottobre 2024; i piu' sfavorevoli giugno 2025 e giugno 2026. Questa discontinuita' e' un rischio economico non risolto.

## 6. Interventi on-policy da stato identico: cosa insegna OLC74C

Per ogni evento fino al successivo, dall'identico stato OLC19 sono stati simulati 25/50/75 sul primo ETF; la policy apprende solo il differenziale 75−25 **gia' maturato da due eventi precedenti**. Parita' bitwise di tutte e sette le matrici fra portafoglio ottenuto per segmenti e singolo replay integrale (entrambi i mercati). Nessun dato futuro controlla il peso del mese corrente.

| Mercato | Correlazione effetto causale simulato e semplice spread prezzi | Mesi con diverso numero di stop fra pesi25/75 | Premio mensile medio 75−25 |
|---|---:|---:|---:|
{chr(10).join(links)}

L'alto accordo con lo spread dei prezzi conferma che l'assetto contabile non e' il principale *ostacolo alla misurazione* del vantaggio della concentrazione. Ma il target corretto e' ancora difficile da prevedere: nello schema on-policy il Ridge e' peggiore di una media storica e non batte il 50/50 nel FULL in entrambi i mercati.

Nota: un numero di stop invariato non dimostra assenza di effetti economici degli stop; dimensione delle posizioni, fees, slippage convenzionale e capitalizzazione cambiano. Lo stato del modello conserva tali effetti.

## 7. Decisione causale e prossimi dati da acquisire

**Non promuovere una nuova allocazione dinamica in produzione.** Le condizioni fissate prima dei risultati richiedevano skill predittiva MAIN, miglioramento di CAGR MAIN/FULL in entrambi i mercati e MaxDD non peggiorato oltre 3pp. Nessuna policy nuova ha superato tutti i gate. Il modello OLC19 50/50 e' il benchmark conservativo; OLC67 resta la candidata research europea/USA gia' nota. Il tilt FUSION_CONF e' un'ipotesi americana per **paper testing**, non un metodo comprovato comune.

La spiegazione piu' concreta e' che stiamo condizionando su due ETF gia' selezionati come molto promettenti: la loro **differenza futura** e' molto piu' rumorosa del vantaggio comune sul resto dell'universo. Le 125 feature Return e i rami Hybrid che sono sufficienti per la selezione non contengono, nei test finora, un segnale abbastanza affidabile per dimensionare i Top2 ogni mese. Le grandi differenze retrospettive 75/25 ↔ 25/75 sono un [0m*opportunity ceiling*, non una previsione disponibile.

Per migliorare davvero, prima di ritentare la stima del peso, serve verificare informazioni **ortogonali e point-in-time** che possano anticipare differenze economiche fra i due ETF: composizione e overlap effettivi, flussi/ownership, premi settoriali e valutazioni, curva volatilita' implicita e liquidita' negoziabile, purché disponibili storicamente senza revisione retrospettiva. Tutto va validato prima sul segno del rendimento relativo e sull'errore di previsione rispetto alla media, con un vero periodo prospettico non esplorato. Non si possono rivendicare nuovi CAGR live usando pochi mesi gia' studiati.

## 8. QA / riproducibilita'

- OLC74A: 56 replay; OLC74B: 16 replay; OLC74C: 4 replay, totale **76**. Controlli indipendenti: {ia['period_CAGR_MaxDD_recalculations']}+{ic['independently_recomputed_periods']}={ia['period_CAGR_MaxDD_recalculations']+ic['independently_recomputed_periods']} CAGR/MaxDD, {ia['annual_return_recalculations']}+{ic['recomputed_annual_rows']}={ia['annual_return_recalculations']+ic['recomputed_annual_rows']} rendimenti annuali. Parita' esatta OLC19 originale 7 array per entrambi i mercati, OLC73 per HALF/MINVAR63 e replay a stato comune OLC74C bitwise.
- OLC74A/B source scoring OLC16 originale: SHA [0m`ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7`; OLC19 [0m`3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`; OLC73 [0m`af6fe36e5a2d6f2ea202d48800316ecbae5872c7ca89caf10bd343b1bf9899c6`.
- I 90 eventi per mercato e i ticker contestuali sono identici ai checkpoint. Tutti i Top2 effettivi appartengono al Top10 storico, selezionato senza conoscere il futuro.
- Label training event−2 e input ultimo Close precedenti verificati. Europa usa la maschera originale [0m`observed`; per USA questa maschera non e' disponibile nella copia nativa e la validita' USA e' quindi limitata all'OHLC fornito.
- Mancano prezzi reali di stop/fill, original observation mask USA, universe point-in-time completo, adjusted total return e un nuovo holdout autonomo; la significativita' economica del CAGR puo' cambiare.

Per replicare gli output, vedere [0m`README.md`, i tre protocolli pre-results, [0m`run_olc74.py`, [0m`run_olc74b.py`, [0m`run_olc74c.py` e i verificatori indipendenti. Non sono necessari nuovi download di quotazioni se i checkpoint originali OLC19/OLC73/OLC16 della Library sono disponibili.
'''
report=report.replace('\x1b[0m','')
(root/'REPORT_OLC74_IT.md').write_text(report,encoding='utf-8')
print('report chars',len(report))