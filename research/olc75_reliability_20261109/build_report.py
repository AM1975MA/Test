from pathlib import Path
import pandas as pd,json,numpy as np
P=Path(__file__).resolve().parent;R=P/'results'
sk=pd.read_csv(R/'OLC75_FORECAST_SKILL.csv');sc=pd.read_csv(R/'OLC75_SCORECARD.csv');ann=pd.read_csv(R/'OLC75_ANNUAL.csv');diag=pd.read_csv(R/'OLC75_CONSENSUS_DIAGNOSTIC.csv');b=pd.read_csv(R/'OLC75_PAIRED_BRIER_CI.csv');qa=json.load(open(R/'OLC75_QA.json'))
pol=['HALF','H1_CONSENSUS','SCORE_P','RELIABILITY_P','RELIABILITY_SELECTIVE']
nam={'HALF':'OLC19 50/50','H1_CONSENSUS':'Consenso unanime 65/35','SCORE_P':'Logit score FUSION','RELIABILITY_P':'Logit affidabilità','RELIABILITY_SELECTIVE':'Logit selettivo'}
fmt=lambda a:f'{100*a:.2f}%';fdd=lambda a:f'{100*a:.2f}%'
main=[]
for market in ['EU','USA']:
 for method in ['p_prior','p_score','p_reliability']:
  s=sk[(sk.market==market)&(sk.period=='MAIN')&(sk.model==method)].iloc[0]
  main.append((market,method,s.brier,s.logloss,s.accuracy,s.n))
# Markdown report with reproduced values from result files
lines=[]
add=lines.append
add('# OLC75 — Affidabilità dei segnali e allocazione Top2: audit completo')
add('**9 novembre 2026 · ricerca retrospettiva · esito negativo per l’allocazione ML.** Nessun cambiamento a OLC19, OLC67 o `main`. Gli anni fino a luglio 2026 sono stati esaminati ripetutamente in OLC01–74 e non sono un holdout vergine. Tutte le cifre qui riportate provengono dai replay OLC75 o dai checkpoint originali; non sono rendimenti di trading reale.')
add('')
add('## Executive summary')
add('OLC75 testa una nuova ipotesi: il disaccordo/consenso fra Return125, ET e XGB, la dispersione dei seed e la persistenza della preferenza fra due ETF possono quantificare l’affidabilità della leadership prima dell’investimento? **No nel test eseguito:** un classificatore prequential che usa queste caratteristiche ha Brier score peggiore sia della probabilità storica sia del solo differenziale FUSION, in entrambi i mercati sul 2021–2024. Le allocazioni risultanti non superano il gate economico congiunto. La baseline OLC19 resta invariata.')
add('**Dato indisponibile:** gli score originali terminano al 30 giugno 2026, e l’ultimo evento del motore è il 1 luglio 2026. Non è stato trovato nei checkpoint di ricerca un pannello verificato agosto–ottobre 2026 con gli stessi titoli, convenzioni e calendario. NON è stata costruita una falsa validazione OOS.')
add('')
add('## 1. Predizione cronologica, 2021–2024')
add('La label è `1{ETF1 batte ETF2 alla prossima apertura mensile}`. Per la previsione del mese t si utilizzano soltanto label fino a t−2 e feature già note al segnale. Brier score e log-loss sono perdite probabilistiche: minore è meglio.')
add('| Mercato | Metodo | N previsioni | Brier ↓ | Log-loss ↓ | Accuratezza direzione |')
add('|---|---|---:|---:|---:|---:|')
for market,method,brier,loss,acc,n in main:add(f'| {market} | {method} | {n} | {brier:.4f} | {loss:.4f} | {100*acc:.1f}% |')
add('')
add('La probabilità storica è il controllo prequential più efficace sul MAIN in entrambi i mercati. Le differenze Brier di Reliability meno prior sono positive: EU +0,01447, USA +0,01704. Il bootstrap descrittivo a blocchi di sei mesi ha intervallo EU [−0,00354; +0,03406], USA [+0,00497; +0,02915]; gli intervalli non correggono gli oltre 70 lotti di ricerca storica.')
add('')
add('## 2. Quanto vale il consenso dei tre esperti?')
add('Gli head ET/XGB sono convertiti in percentili esattamente come in OLC19, mentre Return usa il suo score originale. “Unanimità” significa tre voti concordi sulla direzione relativa tra gli stessi due ETF contestuali. Non significa consenso indipendente: gli head condividono informazioni.')
add('| Mercato | Periodo | Mesi maturi | Mesi unanimi | Direzione corretta quando unanimi | Frequenza vittoria ETF1 |')
add('|---|---|---:|---:|---:|---:|')
for market in ['EU','USA']:
 for period in ['MAIN','2024','2025','2026_PART']:
  allr=diag[(diag.market==market)&(diag.period==period)&(diag.group=='all')].iloc[0]
  ur=diag[(diag.market==market)&(diag.period==period)&(diag.group=='unanimous')]
  if len(ur):
   un=ur.iloc[0];k=int(round(un.n*un.unanimous_direction_accuracy));a=f'{k}/{int(un.n)}'
   n=int(un.n)
  else:n=0;a='—'
  add(f'| {market} | {period} | {int(allr.n)} | {n} | {a} | {100*allr.first_win_rate:.1f}% |')
add('')
add('Nel 2021–2024, la precisione del voto unanime è 6/13 per Europa e 9/17 per USA. Nel 2026 parziale USA è 0/2: campione minuscolo, ma non a favore di un tilt automatico. La media dei margini e gli score dei seed non sostituiscono una prova di calibrazione predittiva.')
add('')
add('## 3. Cinque policy di peso continuo: backtest contabile nativo')
add('Stessi Top2 `TOP2_CONTEXT_REVALUE` del motore OLC19, stessi stop V6/FAST_LOCK3 e convenzioni costo legacy 0,001; confronto a timing IMMEDIATE identico.')
add('| Pesi / Regola | EU CAGR MAIN | USA CAGR MAIN | EU CAGR FULL | USA CAGR FULL | EU MaxDD FULL | USA MaxDD FULL |')
add('|---|---:|---:|---:|---:|---:|---:|')
for policy in pol:
 vals={}
 for m in ['EU','USA']:
  z=sc[(sc.market==m)&(sc.policy==policy)&(sc.timing=='IMMEDIATE')&(sc.fee==.001)].set_index('period')
  vals[m]=z
 add(f"| {nam[policy]} | {fmt(vals['EU'].loc['ACTIVE2021_2024','cagr'])} | {fmt(vals['USA'].loc['ACTIVE2021_2024','cagr'])} | {fmt(vals['EU'].loc['FULL','cagr'])} | {fmt(vals['USA'].loc['FULL','cagr'])} | {fdd(vals['EU'].loc['FULL','maxdd'])} | {fdd(vals['USA'].loc['FULL','maxdd'])} |")
add('')
add('Tutti i 40 percorsi (cinque pesi × due timing × EU/USA × due tariffe) sono stati realmente eseguiti con il motore OLC19. La policy 65/35 di puro consenso può apparire leggermente favorevole in EU MAIN, ma è sfavorevole nel 2024/2025 EU e sul FULL USA. Il peso selettivo è quasi 50/50 e porta solo differenze marginali: non ha skill probabilistica aggiuntiva. **Nessuna policy supera il gate preregistrato.**')
add('')
add('### Singoli anni critici con ingresso immediato, 0,001')
add('| Mercato, anno | 50/50 | Consenso 65/35 | Affidabilità continua | Affidabilità selettiva |')
add('|---|---:|---:|---:|---:|')
for market in ['EU','USA']:
 for year in [2024,2025,2026]:
  values=[]
  for policy in ['HALF','H1_CONSENSUS','RELIABILITY_P','RELIABILITY_SELECTIVE']:
   v=ann[(ann.market==market)&(ann.year==year)&(ann.fee==.001)&(ann.timing=='IMMEDIATE')&(ann.policy==policy)].iloc[0]
   values.append(fmt(v['return']))
  add(f'| {market} {year}{"*" if year==2026 else ""} | '+ ' | '.join(values)+' |')
add('*2026 comprende soltanto gennaio–prima apertura di luglio, rendimento cumulato non annualizzato.*')
add('')
add('Nel 2024 USA il primo ETF batte il secondo in 10/12 mesi; nel 2025 soltanto 6/12 e nel 2026 2/6. Il modello Reliability attribuisce in media probabilità al primo ETF USA rispettivamente 0,553, 0,627 e 0,620: si trova dalla parte sbagliata quando cambia il regime. Non abbiamo un segnale ex ante che riconosca questa inversione.')
add('')
add('### Robustezza a costo legacy 0,003')
add('| Mercato, FULL | HALF | RELIABILITY_P | RELIABILITY_SELECTIVE |')
add('|---|---:|---:|---:|')
for m in ['EU','USA']:
 zz=sc[(sc.market==m)&(sc.timing=='IMMEDIATE')&(sc.fee==.003)&(sc.period=='FULL')].set_index('policy')
 add('| '+m+' | '+' | '.join(fmt(zz.loc[p,'cagr']) for p in ['HALF','RELIABILITY_P','RELIABILITY_SELECTIVE'])+' |')
add('')
add('## 4. Intervento nel simulatore, NON causalità economica identificata')
add('Il motore OLC19 modifica i pesi delle due posizioni selezionate, tenendo fissi OHLC, selection e contratti stop. Come OLC74, questo fornisce un effetto causale **entro il simulatore, a prezzi esogeni**, ma non stabilisce che il segnale di consenso causi la sovraperformance futura del titolo. Resta inoltre la dipendenza dei prezzi da market impact, fill alle aste e qualità degli adjusted returns, non verificati.')
add('')
add('## 5. Informazioni ortogonali: fattibilità delle fonti')
add('Nei 180 eventi (90 per mercato) sono rappresentati 42 ETF EU distinti e 48 ETF USA distinti, quindi un pilot di composizione può concentrarsi sui titoli effettivamente selezionati senza ricostruire per ora l’intera matrice di 314 ETF ogni mese.')
add('- Nelle fonti ZIP originali di OLC74/16/19 non esiste un archivio verificato di composizioni/valutazioni/flussi **point-in-time**. Non abbiamo quindi calcolato overlap, flussi, valutazioni né regressioni con tali dati: sarebbe metodologicamente scorretto retrodatare holdings correnti.')
add('- **Pista iShares USA:** lo scraper open-source di talsan/ishares documenta download mensili e storici di fondi iShares; va verificato ticker per ticker, licenza e data di pubblicazione: https://github.com/talsan/ishares')
add('- **Pista vendor storica per US e UCITS:** ORTEX documenta holdings per data, inclusi ISIN, pesi e i limiti di freschezza dei file del fondo: https://docs.ortex.com/reference/etf_holdings_retrieve ; Intrinio richiede un abbonamento storico e un campo as_of_date: https://docs.intrinio.com/documentation/web_api/get_etf_holdings_v2')
add('- **Pista SEC N-PORT USA:** fondi idonei hanno filing storici; devono essere usati soltanto dopo la data di pubblicazione effettiva, non dalla fine del trimestre di riferimento. La copertura UCITS non è sovrapponibile a quella USA.')
add('Il prossimo test dovrebbe essere anzitutto un **pilot di source coverage** su tutte le coppie selezionate dei mesi 2024, 2025 e gennaio–giugno 2026, con mappatura ticker→ISIN, fonte/issuer, reporting_date, publication_date, age days, report currency e share-class. Se la copertura PIT supera un minimo preregistrato, calcolare overlap delle partecipazioni e differenziali settoriali/fattoriali; non addestrare o ottimizzare un modello usando soltanto gli ETF per cui il dato è disponibile dopo aver visto il target.')
add('')
add('## 6. QA, stato e riproduzione')
ind=json.load(open(R/'OLC75_INDEPENDENT_QA.json'))
add(f"**QA indipendente PASS:** {ind['n_event_rows']} decisioni, {ind['event_labels_by_market']['EU']} label mature EU e {ind['event_labels_by_market']['USA']} USA, {ind['n_policy_paths']} replay nativi, {ind['n_scorecard_periods']} calcoli di CAGR/drawdown e {ind['n_annual_verified']} rendimenti annuali verificati indipendentemente. B0 HALF IMMEDIATE coincede **bit per bit** su sette matrici con OLC19; HALF DELAY3 e fee=.001/.003 coincidono con OLC74. Le fonti etichettate includono due buchi EU 2020 e il mese finale non osservato 2026, non imputati.")
add('')
add('L’implementazione richiede i quattro ZIP originali che sono già nella Library. `prepare_native.py` ripristina le dipendenze OLC19 senza modificarle; `run_olc75.py` ripete modelli e contabilità; `verify_olc75_independent.py` ricalcola le metriche senza importare il motore. I digest sono in `results/OLC75_QA.json` e `MANIFEST.json`. Nessuna nuova esecuzione su agosto–ottobre 2026 è stata effettuata.')
add('**Decisione: OLC75 non promosso.** L’evidenza corrente non giustifica né uno switch 25/75 né una nuova concentrazione 65/35 guidata dall’unanimità. L’informazione necessaria per prevedere il vincitore relativo resta non dimostrata. OLC19 baseline e OLC67 candidato di ricerca invariati.')

formatted=[]
for line in lines:
 if line.startswith('|') and formatted and not formatted[-1].startswith('|') and formatted[-1]!='':formatted.append('')
 if line.startswith('#') and formatted and formatted[-1]!='':formatted.append('')
 formatted.append(line)
out=P/'REPORT_OLC75_IT.md';out.write_text('\n'.join(formatted)+'\n',encoding='utf-8')
print('report written',out,len(lines),'sections',out.stat().st_size)