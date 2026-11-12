from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, os, zipfile, io
p=Path('/mnt/data/olc100_full_native');r=p/'results'
s=pd.read_csv(r/'OLC100_NATIVE_FORWARD_SCORECARD.csv')
ref=pd.read_csv(r/'OLC100_OLC67_DAILY_PARITY.csv')
ind=pd.read_csv(r/'OLC100_INDEPENDENT_FORWARD_QA.csv')
mont=pd.read_csv(r/'OLC100_FORWARD_MONTHLY_NATIVE.csv')
weights=pd.read_csv(r/'OLC100_NATIVE_FORWARD_WEIGHTS.csv')
stop=pd.read_csv(r/'OLC100_NEW_NATIVE_STOPS.csv')
coverage=pd.read_csv(r/'OLC100_NATIVE_SOURCE_COVERAGE.csv')
assert len(s)==144 and len(ref)==20 and np.max(ind.abs_error)<1e-12
assert len(weights)==8 and len(stop)>0
base=s.query("fee==.001 and stop_friction==.001 and period=='AUG3_NOV2'")
base=base.pivot(index='arm',columns='market')
order=[('B_BASE','OLC19 — 50/50 immediato'),('C_CANDIDATE','OLC67 — MINVAR63 + DELAY3'),('D_SELECTION','FUSION senza contesto'),('D_ALLOCATION','Solo MINVAR63'),('D_TIMING','Solo DELAY3'),('D_PROTECTION','Senza FAST_LOCK3')]
def pct(x):return f'{x*100:+.2f}%'.replace('.',',')
def pp(x):return f'{x:+.2f} pp'.replace('.',',')
def rn(x):return str(x).replace('.',',')
full_rows=[]
for arm,label in order:
 u=base['gross_return'].loc[arm]; dd=base['maxdd_local'].loc[arm];ex=base['stop_events'].loc[arm]
 full_rows.append(f'| {label} | {pct(u.EU)} | {pct(u.USA)} | {pct(dd.EU)} | {pct(dd.USA)} | {int(ex.EU)}/{int(ex.USA)} |')
months=[]
for m in ['EU','USA']:
 q=mont[mont.market==m].pivot(index='month',columns='arm',values='return_pct')
 for mo in ['Aug','Sep','Oct']:
  a=float(q.loc[mo,'B_BASE']);b=float(q.loc[mo,'C_CANDIDATE'])
  months.append(f"| {m} | {mo} 2026 | {pct(a/100)} | {pct(b/100)} | {pp(b-a)} |")
stress=[]
for m in ['EU','USA']:
 for fee in [.001,.003]:
  for fr in [.001,.005]:
   q=s[(s.market==m)&(s.period=='AUG3_NOV2')&np.isclose(s.fee,fee)&np.isclose(s.stop_friction,fr)].set_index('arm')
   b=q.loc['B_BASE','gross_return'];c=q.loc['C_CANDIDATE','gross_return']
   stress.append(f'| {m} | {fee:.3f} | {fr:.3f} | {pct(b)} | {pct(c)} | {pp(100*(c-b))} |')
ww=[]
for row in weights.itertuples():
 ww.append(f'| {row.market} | {row.signal_date} | {row.ticker1} | {row.ticker2} | {row.minvar_w1*100:.2f}% |')
refmax=float(ref.max_abs_daily_log_error.max());indmax=float(ind.abs_error.max())
stop_aug=stop[(stop.market=='USA')&(stop.arm=='B_BASE')&(stop.date=='2026-08-03')]
assert set(stop_aug.ticker)=={'BNO','USO'} and stop_aug.newly_bought_quantity.gt(0).all()
assert len(coverage)==314
summary={'status':'RETROSPECTIVE_NATIVE_REPLAY_PASS_NOT_PROSPECTIVE','asof_quote':'2026-11-12','created_utc':'2026-11-13','baseline':'OLC19 50/50 IMMEDIATE FAST_LOCK3','candidate':'OLC67 MINVAR63 DELAY3 FAST_LOCK3','market_data_quality':'NOT_CERTIFIED','forward_period':'2026-08-03/2026-11-02','completed_new_signal_months':3,'n_native_paths':48,'n_native_reference_daily_checks':len(ref),'max_ref_daily_log_abs_error':refmax,'max_independent_return_abs_error':indmax,'sources':{'frozen_olc19_sha256':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540','new_prices_asof':'2026-11-12','source_quotes_bad_OHLC':79,'source_quotes_bad_OHLC_tickers':15,'new_primary_ticker_bad_OHLC_overlap':0,'new_V6_alt_activations':0,'new_quote_missing_ticker_days_EU':1,'new_quote_missing_ticker_days_USA':0},'comparison':{},'file_schema':['market','arm','fee','stop_friction','period','gross_return','stop_events','turnover','mean_target_gross','maxdd_local']}
for m in ['EU','USA']:
 q=base['gross_return'][m]
 summary['comparison'][m]={'baseline_net_cumulative':float(q.loc['B_BASE']),'candidate_net_cumulative':float(q.loc['C_CANDIDATE']),'delta_pp':float(100*(q.loc['C_CANDIDATE']-q.loc['B_BASE'])),'baseline_maxdd_from_openings':float(base['maxdd_local'][m].loc['B_BASE']),'candidate_maxdd_from_openings':float(base['maxdd_local'][m].loc['C_CANDIDATE'])}
(r/'OLC100_NATIVE_VERIFICATION_SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
report=f'''# OLC100 — Replay contabile nativo luglio–novembre 2026

**Esecuzione e audit: 13 novembre 2026. Snapshot prezzi: 12 novembre 2026.**  
**Stato: replay retrospettivo VERIFICATO; validazione prospettica NON ANCORA AVVIATA; nessuna promozione.**

## Decisione

Le selezioni Top2 del modello originale, già rigenerate per luglio–ottobre 2026 senza refit, sono state applicate al **motore originale OLC19** conservando l'intero stato pregresso: liquidità, posizioni, V6, stop, blocchi e riacquisti. I replay partono dal febbraio 2019 e proseguono fino al 12 novembre 2026. Nessun azzeramento del portafoglio al 1° luglio. Le quattro architetture componenti sono state mantenute separate dal candidato completo.

Confronto principale: **dal 3 agosto al 2 novembre**, tre decisioni nuove con outcome mensile maturato. I rendimenti sono cumulativi, **non CAGR**; netti delle commissioni e della frizione stop interne al simulatore OLC19, non netti di spread/impact broker certificati.

| Architettura | EU rendimento | USA rendimento | EU MaxDD¹ | USA MaxDD¹ | Stop EU/USA |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(full_rows)+f'''

¹ MaxDD misurato sulle aperture del solo intervallo, non intraday; non è il MaxDD dell'intero storico.

Il differenziale candidato – baseline è **{pp(summary['comparison']['EU']['delta_pp'])} in Europa** e **{pp(summary['comparison']['USA']['delta_pp'])} negli USA**, ma non ha significatività prospettica con tre osservazioni mensili.

## Evoluzione mensile del conto

| Mercato | Intervallo dalla prima apertura | OLC19 | OLC67 | Delta OLC67 – OLC19 |
|---|---|---:|---:|---:|
'''+ '\n'.join(months)+f'''

Il vantaggio USA si concentra in **agosto**. Escludendo agosto, la differenza cumulata su settembre–ottobre è modesta: OLC19 **−13,01%** contro OLC67 **−12,06%**. Il test non dimostra stabilità interregime.

## Forensic: esecuzione del 3 agosto USA

Al segnale di venerdì 31 luglio, Top2 contestuale **BNO/USO**. Il 3 agosto OLC19 immediato apre entrambe le posizioni e il motore le ferma nella stessa seduta:

- **BNO:** stop intraday sul livello 47,6091, apertura superiore alla barriera; quantità appena acquistata positiva.
- **USO:** apertura 120,80 inferiore alla barriera 122,0656, quindi stop modellato all'apertura, ancora su quantità appena acquistata positiva.

DELAY3 trattiene invece temporaneamente **PPLT/PALL**. Dal 3 al 4 agosto i loro prezzi Open→Open salgono rispettivamente di **6,77%** e **6,73%**, mentre BNO/USO scendono di **6,77%** e **3,15%**. Il rendimento giornaliero simulato al 3 agosto è **−0,43% OLC19** contro **+6,76% OLC67**: un differenziale di **7,18 punti** nella sola prima seduta.

**Questo è il principale meccanismo economico identificato**, ma espone la conclusione a ipotesi di fill intraday, ordini di ingresso/stop contestuali e lockout. Un modello di stop basato su O/L/C giornalieri non prova che i due ordini avrebbero avuto realmente quei fill.

## Stress costi già congelato

Commissione 0,001 e 0,003; frizione stop 0,001 e 0,005. Nessuna scelta a posteriori di un costo favorevole.

| Mercato | Fee | Frizione stop | OLC19 | OLC67 | Differenziale |
|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(stress)+f'''

I differenziali rimangono favorevoli a OLC67 in tutte e quattro le ipotesi, ma nel caso più oneroso il suo rendimento EU è negativo. Lo stress è un test interno del simulatore, non una verifica delle condizioni di negoziazione.

## Pesi congelati sul nuovo periodo

MINVAR63 usa i 63 rendimenti log giornalieri completi precedenti alla prima apertura della decisione, con cap [25%,75%] e fallback 50/50.

| Mercato | Segnale | Top1 | Top2 | Peso Top1 MINVAR63 |
|---|---|---|---|---:|
'''+ '\n'.join(ww)+f'''

Lo score originale di Return125, ET/XGB, memoria, FUSION e rivalutazione contestuale non è stato modificato. Futures e posizioni short non sono introdotti come strumenti acquistabili.

## Audit indipendente e parità

- **48 percorsi nativi** = 6 configurazioni × 2 mercati × 2 commissioni × 2 frizioni stop.
- **20 verifiche** della serie giornaliera dei cinque bracci già presenti in OLC67 su entrambi i mercati e commissioni, **massimo errore assoluto log {refmax:.2e}**.
- I due baseline OLC19, EU/USA, e il controllo selezione originale riproducono esattamente le **sette matrici contabili archiviate** fino al punto di raccordo. La seduta finale storica (1 luglio) diventa normalmente negoziabile nel replay esteso.
- Le **180 decisioni storiche MINVAR63** riproducono i pesi congelati OLC56 entro 1e−10; ulteriori otto pesi luglio–ottobre calcolati senza dati successivi al segnale.
- I segnali giornalieri di stop/rischio ricostruiti coincidono negli **ultimi 250 giorni congelati**; il gross V6 coincide negli **ultimi 180 giorni** per entrambi i mercati.
- Ricalcolo indipendente del rendimento per la finestra principale dal logaritmo dei rendimenti giornalieri: errore massimo **{indmax:.2e}**; il MaxDD del sotto-periodo è calcolato dalle aperture.

## Qualità dati e limiti ancora bloccanti

Lo snapshot contiene **314 ETF**, 79 barre OHLC segnalate su 15 ticker. **Nessuno dei ticker dei nuovi Top2 (compreso il controllo FUSION originale) coincide con quei 15 ticker**. Nelle nuove sedute V6 non ha selezionato alcun ETF alternativo; il controller V6 ha livelli gross 0,95 o 1,00 e la trasformazione congelata mantiene esposizione teorica 1,00 in assenza di altri blocchi. La sensibilità principale deriva quindi da timing e FAST_LOCK3.

Ciò **non certifica** qualità complessiva della fonte: i prezzi sono stati scaricati/ricalibrati il 12 novembre dopo che erano noti gli outcome luglio–ottobre, e il dataset non è un archivio autentico di quote point-in-time alla data dei vecchi segnali. Mancano ancora certificazione storica dell'universo ETF, maschera originale USA, dividendi/total-return/FX, prezzi bid/ask e verifica degli stop realmente eseguibili. Il rischio di errori per split, restatement o contratti di stop resta aperto.

I contrasti di layer derivano da **replay completi con stati contabili diversi**, non da counterfactual perfettamente matched-state al medesimo evento. Non vanno interpretati come effetti causali puri di singole feature; per questi serve un esperimento cloned-state separato, predefinito e con fill certificato.

## Conclusione operativa

**Mantenere OLC19 come baseline e OLC67 come candidato di ricerca**, senza promozione. Congelare questi risultati e non usare il comportamento di agosto per ottimizzare ulteriormente ritardi, pesi, stop o parametri. Il vero test prospettico comincia quando il segnale di fine novembre viene prodotto e registrato prima della prima apertura di dicembre, con dati verificati. Nessun ordine è stato inviato e `main` non è stato modificato.

## Riproduzione e provenienza

Sorgenti congelate: OLC19 ZIP SHA256 `{summary['sources']['frozen_olc19_sha256']}`. Materiali richiesti da Library: OLC19, OLC56, OLC67, archivio OLC100 Top2 luglio–ottobre e snapshot sorgenti 314 ETF del 12 novembre. Il pacchetto allegato contiene il runner, il forensic stop e tutti i risultati numerici, ma non include i binari degli archivi originali (oltre 100 MB).
'''
report=report.replace('`0main`','`main`').replace('`0'+summary['sources']['frozen_olc19_sha256']+'`','`'+summary['sources']['frozen_olc19_sha256']+'`')
(p/'OLC100_REPORT_REPLAY_NATIVE_20261113.md').write_text(report)
(p/'README.md').write_text('''# OLC100 native retrospective research replay (2026-11-13)\n\nFull account replay of the six predeclared policies on frozen 2026H2 Top2, not new strategy fit, not prospective, not broker certification.\n\n## Inputs (external, original archives remain immutable)\n\n- `/mnt/data/frozen_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip` with required SHA256 in runner.\n- `/mnt/data/olc100_workspace/OLC98_Model_Review_20261112/native/...` original OLC19 extracted engine and parent.\n- `/mnt/data/olc100_workspace/OLC56_ROBUST_20261106/results/{market}_DECISIONS.csv` (frozen MinVar weights).\n- `/mnt/data/olc100_native/p0/results/calendar/{market}_{OPEN,CLOSE}.pkl` and `/mnt/data/olc100_native/p0/legacy/` original and appended adjusted OHLC per ticker.\n- `/mnt/data/OLC100_FORWARD_RESULT_20261112/` originally reconstructed Top2+FUSION score CSVs.\n- `/mnt/data/OLC100_CAPTURE_RECHECK_20261112.zip` provider QA.\n\nThe runner uses the original engine and a minimal source extraction (`srcfreeze` contains source copies from frozen OLC19 and early V2 archives, no training re-fit). Paths can be re-pointed to the original packages. The artifact is research-only and should not be used as a trading executor.\n\n## Reproduction\n\n`OPENBLAS_NUM_THREADS=1 python run_forward_native.py` then `python forensic_stops.py` and `python build_report.py`. These scripts are in this package; original archives and input panels must be present.\n\n## Classification\n\n`SOURCE_INTEGRITY_PASS`, `HISTORICAL_MODEL_PARITY_PASS`, `ACCOUNTING_REPLAY_PASS`; `PIT_DATA_NOT_CERTIFIED`, `EXECUTION_NOT_CERTIFIED`, `PROSPECTIVE_OOS_NOT_STARTED`.\n''')
print('REPORT WRITTEN', len(report),'chars')
