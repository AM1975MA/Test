#!/usr/bin/env python3
"""EU-only Acc migration eligibility; preserve historical baselines. Python 3.11, numpy.

Research-only, no trading or model changes. Data: OLC38_MINIMAL_EU_SOURCE.zip,
which includes original OLC19 EU_STATE_HALF.npz and original EU165 universe CSV.
"""
from pathlib import Path
import argparse, csv, hashlib, io, json, zipfile
import numpy as np

parser=argparse.ArgumentParser()
parser.add_argument('--archive',type=Path,default=None,help='OLC38_MINIMAL_EU_SOURCE.zip')
parser.add_argument('--universe',type=Path,default=None,help='EU165_original_universe.csv')
parser.add_argument('--out',type=Path,default=None,help='Output directory')
args=parser.parse_args()
ROOT=Path(__file__).resolve().parent
ARCHIVE=args.archive or ROOT/'input'/'OLC38_MINIMAL_EU_SOURCE.zip'
UNIVERSE=args.universe or ROOT/'EU165_original_universe.csv'
TARGET=args.out or ROOT/'audit'; TARGET.mkdir(exist_ok=True,parents=True)
source=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()

# All 9 distribute ETF observed among the 27 primary holdings in 2021-2024.
# Mappings without complete index/history and observed quotes remain frozen.
entries=[
('EXV9.DE','','','NO_EQUIVALENT_VERIFIED','Non identificata classe Acc dello stesso indice con storia quotazioni completa.', ''),
('EXV5.DE','EXHG.DE','DE000A2QP4A8','INSUFFICIENT_HISTORY','Classe Acc nata 2022-04-06, manca il 2019-2021.','https://www.justetf.com/it/etf-profile.html?isin=DE000A2QP4A8'),
('EXV6.DE','LBRE.DE','LU1834983550','INSUFFICIENT_HISTORY','Classe/listing Acc Xetra dal marzo 2024; la storia NAV del fondo dal 2006 NON sostituisce quella della classe.','https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-basic-resources-ucits-etf-acc/lu1834983550'),
('EXV3.DE','STEC.AS','DE000A2QP398','INSUFFICIENT_HISTORY','Classe Acc nata 2022-04-06, manca il 2019-2021.','https://www.blackrock.com/it/consulenti/products/326632/ishares-stoxx-europe-600-technology-ucits-etf-de'),
('EXV1.DE','LBNK.DE','LU1834983477','INSUFFICIENT_HISTORY','Classe/listing Xetra dal marzo 2024; la storia del comparto 2006 non basta.','https://www.amundietf.lu/en/individual/products/equity/amundi-stoxx-europe-600-banks-ucits-etf-acc/lu1834983477'),
('EXX1.DE','EXI4','DE000A2QP372','INSUFFICIENT_HISTORY','Classe Acc nata 2021-12-03; manca il warm-up e tutto il 2021. Ticker riportato correttamente EXI4, non EXA1.','https://www.justetf.com/it/etf-profile.html?isin=DE000A2QP372'),
('EXH1.DE','','','NO_EQUIVALENT_VERIFIED','Non identificato Acc same-index con storico 2019-2024 originale osservato.',''),
('EXI5.DE','','','NO_EQUIVALENT_VERIFIED','Alternative immobiliari disponibili ma non equivalenti al medesimo indice/portafoglio.',''),
('IM2A.DE','EEAA.DE','LU0950381748','CANDIDATE','Classe Acc lanciata 2013; entrambi FTSE EPRA/NAREIT Eurozone Capped. Validare indice PIT, dividendi e modalità di trading prima di qualunque replay.','https://www.bnpparibas-am.com/en-lu/fundsheet/equity/bnp-paribas-easy-ftse-epra-nareit-eurozone-capped-ucits-etf-c-lu0950381748/')]

with zipfile.ZipFile(ARCHIVE) as z:
 name=next(n for n in z.namelist() if n.endswith('EU_STATE_HALF.npz'))
 with z.open(name) as f:
  state=np.load(io.BytesIO(f.read()),allow_pickle=False)
  dates=state['dates'].astype('datetime64[D]'); ticker=state['tickers'].astype(str).tolist()
  obs=state['observed'];opens=state['O'];
  if len(ticker)!=167:raise ValueError('EU panel ticker count changed')
  valid={t:(obs[:,i]&np.isfinite(opens[:,i])&(opens[:,i]>0)) for i,t in enumerate(ticker)}

main_dates=(dates>=np.datetime64('2021-01-01'))&(dates<np.datetime64('2025-01-01'))
lookback_dates=dates<np.datetime64('2021-01-29')
first_panel=str(dates[0]); main_days=int(main_dates.sum())
print('panel',first_panel,'main days',main_days,'source_sha256',source)
rows=[]
for original,acc,isin,status,reason,url in entries:
 if original not in valid:raise ValueError('original ticker missing '+original)
 available=acc in valid
 if available:
  v=valid[acc]; start=str(dates[np.flatnonzero(v)[0]]) if np.any(v) else ''
  n_pre=int(v[lookback_dates].sum())
  n_main=int(v[main_dates].sum())
  pct=n_main/main_days
 else:
  start='NOT_IN_PANEL';n_pre=0;n_main=0;pct=0.0
 hist_pass=(available and start==first_panel and n_pre>=252 and pct>=.98)
 if status=='CANDIDATE' and not hist_pass:status='INSUFFICIENT_HISTORY';reason+=' Non supera i criteri OLC40.'
 if status=='INSUFFICIENT_HISTORY' and hist_pass:raise RuntimeError('Inconsistent historical status for '+original)
 if status=='CANDIDATE':assert original=='IM2A.DE' and acc=='EEAA.DE'
 rows.append({'original_ticker':original,'acc_candidate':acc,'acc_isin':isin,'decision':status,
 'conversion_eu_research_only':int(status=='CANDIDATE'),
 'source_EU165_candidate_present':int(available),
 'acc_first_original_observed_open':start,'acc_days_observed_before_2021_signal':n_pre,
 'acc_2021_2024_observed_opens':n_main,'all_2021_2024_panel_days':main_days,
 'acc_2021_2024_observed_rate_pct':round(pct*100,4),
 'source_notes':reason,'evidence_url':url})

p=TARGET/'EU_ACC_SUBSTITUTION_AUDIT_HELD9.csv'
with p.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

with UNIVERSE.open(newline='') as f:
 universe=[r['ticker'] for r in csv.DictReader(f)]
assert len(universe)==165 and len(set(universe))==165
removed=[r['original_ticker'] for r in rows if r['decision']=='CANDIDATE' and r['acc_candidate'] in universe]
if removed!=['IM2A.DE']:raise RuntimeError('Unexpected removals '+str(removed))
new=[x for x in universe if x not in removed]
with (TARGET/'EU_ACC_RESEARCH_UNIVERSE_NOT_APPLIED.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['ticker','market','status']);w.writerows((x,'EU', 'UNCHANGED_OR_ALREADY_ACC') for x in new)

report={
'original_universe_count':len(universe),
'held_in_2021_2024_classified':27,
'held_distributing_ETFs':len(rows),
'candidate_passes_quote_history_only':sum(r['decision']=='CANDIDATE' for r in rows),
'excluded_insufficient_history':sum(r['decision']=='INSUFFICIENT_HISTORY' for r in rows),
'excluded_no_identical_verified_acc':sum(r['decision']=='NO_EQUIVALENT_VERIFIED' for r in rows),
'candidate_verified_at_issuer_product_level_but_not_historical_constituents':True,
'candidate_already_in_original_universe':['EEAA.DE'],
'deduplicated_eu_research_universe_count':len(new),
'unscreened_original_universe_tickers':len(universe)-27,
'coverage_threshold_first_observed_day':first_panel,
'coverage_threshold_min_prior_sessions_before_first_2021_signal':252,
'coverage_threshold_min_observed_2021_2024_pct':98.0,
'original_OLC19_OLC38_OLC39_unchanged':True,
'USA149_unchanged':True,'main_unchanged':True,
'source_zip_sha256':source,'files_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [p,TARGET/'EU_ACC_RESEARCH_UNIVERSE_NOT_APPLIED.csv']}
}
(TARGET/'EU_ACC_AUDIT_SUMMARY.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
