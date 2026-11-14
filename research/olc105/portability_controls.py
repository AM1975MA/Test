"""OLC105 declared CONTROLS ONLY. Never substitutes these curves for OLC19/OLC67.

Prices are adjusted total-return proxies, fractional economic units, NOT broker
whole shares. No V6 or FAST_LOCK3 is applied to these standalone benchmarks.
All sources/rosters are frozen; the module does not download prices or train ML.
"""
from __future__ import annotations
import hashlib,json,os,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'control_results'
WORLD='IE00BFY0GT14'
SECTOR_START='2016-05-03'

def rebalance(units,cash,prices,weights,ticket,impact):
    units=np.asarray(units,float);prices=np.asarray(prices,float);weights=np.asarray(weights,float)
    if units.shape!=prices.shape or prices.shape!=weights.shape:raise ValueError('SHAPE')
    if not np.isfinite(prices).all() or (prices<=0).any():raise ValueError('PRICE')
    if not np.isfinite(weights).all() or (weights<0).any() or abs(weights.sum()-1)>1e-10:raise ValueError('WEIGHTS')
    if ticket<0 or impact<0 or impact>=1 or cash< -1e-7 or (units<0).any():raise ValueError('ACCOUNT')
    old=units*prices;wealth=float(old.sum()+cash)
    if wealth<=0:raise ValueError('INSOLVENT')
    eps=max(1e-9,wealth*1e-12)
    if np.all(np.abs(wealth*weights-old)<eps):return units.copy(),float(cash),0.,0
    def cost(eq):
        diff=eq*weights-old;mask=np.abs(diff)>eps
        return float(ticket*mask.sum()+impact*np.abs(diff[mask]).sum()),int(mask.sum())
    lo,hi=0.,wealth
    if cost(lo)[0]>=wealth:raise ValueError('TRANSACTION_COST_EXCEEDS_CAPITAL')
    for _ in range(100):
        mid=(lo+hi)/2
        if mid+cost(mid)[0]>wealth:hi=mid
        else:lo=mid
    eq=lo;fee,n=cost(eq);new=eq*weights/prices
    remaining=float(wealth-fee-new@prices)
    if remaining< -1e-7 or abs(float(new@prices+remaining+fee)-wealth)>1e-7:raise AssertionError('SELF_FINANCING')
    return new,max(0.,remaining),fee,n

def momentum_asof(series,signal_date):
    s=series.loc[:pd.Timestamp(signal_date)].dropna()
    s=s[np.isfinite(s)&(s>0)]
    if len(s)<253 or (pd.Timestamp(signal_date)-s.index[-1]).days>5:return None
    return float(np.log(s.iloc[-1]/s.iloc[-253]))

def metrics(equity,initial,dates):
    equity=np.asarray(equity,float);dates=pd.DatetimeIndex(dates)
    if len(equity)!=len(dates) or len(equity)<1 or np.any(equity<=0):raise ValueError('NAV')
    chain=np.r_[initial,equity];lr=np.diff(np.log(chain));dd=chain/np.maximum.accumulate(chain)-1
    days=max(1,(dates[-1]-dates[0]).days+1)
    return dict(net_cumulative=float(equity[-1]/initial-1),cagr_calendar=float((equity[-1]/initial)**(365.2425/days)-1),cagr_252=float(np.expm1(lr.mean()*252)),max_drawdown=float(dd.min()),volatility_252=float(np.std(lr,ddof=1)*np.sqrt(252)) if len(lr)>1 else 0.,end_equity=float(equity[-1]),sessions=len(equity),calendar_days=days)

def load_frozen():
    sources={};checked=[]
    for folder in ['source_capture','source_complete','source_alternates']:
        directory=ROOT/folder;manifest=json.loads((directory/'MANIFEST.json').read_text())
        for rel,digest in manifest['files'].items():
            path=directory/rel
            if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise AssertionError(('SOURCE_HASH',folder,rel))
            checked.append((folder,rel,digest))
        if folder=='source_capture':continue
        for r in manifest.get('sources',[]):
            if r.get('role')=='candidate' and r.get('status','').startswith('CAPTURED'):
                sources[r['isin']]=(folder,r)
    frozen=pd.read_csv(ROOT/'CANDIDATES_FROZEN.csv').set_index('isin')
    frames={};qa=[]
    for isin,(folder,rec) in sorted(sources.items()):
        assert isin in frozen.index and rec['currency']=='EUR'
        path=ROOT/folder/'prices'/(rec['symbol']+'.csv.gz')
        f=pd.read_csv(path,parse_dates=['date'],float_precision='round_trip').set_index('date').sort_index()
        assert f.index.is_unique
        before=0
        if str(frozen.loc[isin,'macro_category'])=='C02_US_SECTOR_THEME':
            before=int((f.index<pd.Timestamp(SECTOR_START)).sum());f=f.loc[SECTOR_START:].copy()
        assert f.index.max()<=pd.Timestamp('2026-11-13')
        for x in ['Open','High','Low','Close','Adj Close']:f[x]=pd.to_numeric(f[x],errors='coerce')
        ratio=f['Adj Close']/f['Close']
        f['adjusted_open']=f['Open']*ratio
        f['adjusted_close']=f['Adj Close']
        bad=(f['Low']>f[['Open','Close']].min(axis=1)+1e-6*f[['Open','Close']].abs().max(axis=1).clip(lower=1))|(f['High']<f[['Open','Close']].max(axis=1)-1e-6*f[['Open','Close']].abs().max(axis=1).clip(lower=1))
        f['geometry_flag']=bad
        frames[isin]=f
        qa.append(dict(isin=isin,symbol=rec['symbol'],macro_category=frozen.loc[isin,'macro_category'],source=folder,rows=len(f),first_date=str(f.index.min().date()),last_date=str(f.index.max().date()),pre_listing_rows_excluded=before,geometry_bad=int(bad.sum()),zero_volume=int(f['Volume'].fillna(0).eq(0).sum()),nonfinite_open=int((~np.isfinite(f['adjusted_open'])|(f['adjusted_open']<=0)).sum()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    assert len(frames)==29 and WORLD in frames,(len(frames),WORLD in frames)
    return frames,pd.DataFrame(qa),checked

def signals(frames,roster):
    dates=pd.DatetimeIndex(sorted(set().union(*(set(f.index) for f in frames.values()))))
    periods=dates.to_period('M');monthly=pd.Series(dates,index=dates).groupby(periods).max()
    # Current November is incomplete at the frozen cutoff: no November signal.
    monthly=monthly.loc[monthly.index<dates[-1].to_period('M')]
    categories=roster.set_index('isin').macro_category.to_dict();needed=set(categories.values())
    events=[];elig=[]
    for signal in monthly:
        values={i:momentum_asof(f.adjusted_close,signal) for i,f in frames.items()}
        values={i:v for i,v in values.items() if v is not None}
        valid=len(values)>=12 and {categories[i] for i in values}==needed and WORLD in values
        if not valid:continue
        idx=dates.searchsorted(signal,side='right')
        if idx>=len(dates):continue
        ranked=sorted(values,key=lambda i:(-values[i],i))
        events.append(dict(signal_date=signal,effective_date=dates[idx],isin1=ranked[0],isin2=ranked[1],n_eligible=len(values),score1=values[ranked[0]],score2=values[ranked[1]]))
        for i,v in values.items():elig.append(dict(signal_date=signal,isin=i,momentum_log_252=v,category=categories[i]))
    if not events:raise RuntimeError('NO_COMPLETE_SIX_GROUP_MONTH')
    return dates,pd.DataFrame(events),pd.DataFrame(elig)

def replay(frames,dates,events,arm,initial,ticket,impact):
    names=sorted(frames);lookup={n:i for i,n in enumerate(names)}
    start=events.effective_date.iloc[0];dates=dates[dates>=start]
    op=pd.DataFrame({i:f.adjusted_open for i,f in frames.items()}).reindex(dates)[names]
    # Prior values are used only for marking a closed venue, never a fill.
    marks=pd.DataFrame({i:f.adjusted_close for i,f in frames.items()}).sort_index().ffill().reindex(dates).ffill()[names]
    flags=pd.DataFrame({i:f.geometry_flag for i,f in frames.items()}).reindex(dates)[names].fillna(False).astype(bool)
    eventmap={pd.Timestamp(x.effective_date):x for x in events.itertuples()}
    units=np.zeros(len(names));cash=float(initial);pending=None;logs=[];trades=[];max_error=0.;entered=False
    for k,date in enumerate(dates):
        if arm=='WORLD_PASSIVE' and not entered:
            w=np.zeros(len(names));w[lookup[WORLD]]=1.;pending=(w,events.signal_date.iloc[0])
        elif arm=='MOM252_TOP2_HALF_IMMEDIATE' and date in eventmap:
            e=eventmap[date];w=np.zeros(len(names));w[lookup[e.isin1]]=w[lookup[e.isin2]]=.5;pending=(w,e.signal_date)
        costs=0.;orders=0;unfilled=False;turnover=0.;held_anomaly=int(flags.iloc[k].to_numpy()[units>0].sum())
        if pending is not None:
            w,sig=pending
            if not pd.Timestamp(sig)<date:raise AssertionError('LOOKAHEAD_SIGNAL')
            observed=op.iloc[k].to_numpy(float);involved=(units>1e-15)|(w>0)
            if np.isfinite(observed[involved]).all() and (observed[involved]>0).all():
                px=np.where(involved,observed,1.)
                prior=units.copy();oldwealth=float(prior@px+cash)
                units,cash,costs,orders=rebalance(units,cash,px,w,ticket,impact)
                turnover=float(np.abs((units-prior)*px).sum()/oldwealth)
                max_error=max(max_error,abs(float(units@px+cash+costs)-oldwealth))
                for j in np.flatnonzero(np.abs(units-prior)>1e-10):
                    trades.append(dict(date=date,signal_date=sig,isin=names[j],delta_adjusted_units=float(units[j]-prior[j]),adjusted_open=float(px[j]),proxy_notional=float(abs(units[j]-prior[j])*px[j]),geometry_bad=bool(flags.iloc[k,j])))
                pending=None;entered=True
            else:unfilled=True
        mark=marks.iloc[k].to_numpy(float)
        if not np.isfinite(mark[units>0]).all():raise AssertionError('UNMARKABLE_HOLDING')
        equity=float(np.dot(units,np.where(units>0,mark,0.))+cash)
        logs.append(dict(date=date,equity=equity,cash=cash,costs=costs,orders=orders,turnover=turnover,pending_missing_open=unfilled,held_geometry_flags=held_anomaly))
    return pd.DataFrame(logs),pd.DataFrame(trades),max_error

def main():
    OUT.mkdir(exist_ok=True)
    frames,qa,checks=load_frozen();roster=pd.read_csv(ROOT/'CANDIDATES_FROZEN.csv')
    dates,events,eligible=signals(frames,roster)
    qa.to_csv(OUT/'FROZEN_INSTRUMENT_QA.csv',index=False);events.to_csv(OUT/'MOMENTUM_SIGNALS.csv',index=False);eligible.to_csv(OUT/'ASOF_ELIGIBILITY.csv',index=False)
    summaries=[];ledgers=[];trade_logs=[];maxerror=0.
    scenarios=[(c,f,b) for c in [5000.,10000.,50000.] for f in [1.,2.] for b in [5.,15.,30.]]+[(10000.,0.,0.)]
    for arm in ['WORLD_PASSIVE','MOM252_TOP2_HALF_IMMEDIATE']:
        for initial,fee,bp in scenarios:
            ledger,trades,error=replay(frames,dates,events,arm,initial,fee,bp/10000.)
            maxerror=max(error,maxerror)
            identity=dict(arm=arm,initial_eur=initial,ticket_fee_eur=fee,shortfall_bps_per_side=bp)
            complete_end=pd.Timestamp('2026-10-31')
            for window,data in [('THROUGH_2026_11_13_PARTIAL_MONTH',ledger),('THROUGH_2026_10_COMPLETED_MONTHS',ledger[ledger.date<=complete_end])]:
                calc=metrics(data.equity,initial,data.date)
                summaries.append({**identity,'window':window,'start_open':str(data.date.iloc[0].date()),'end_close':str(data.date.iloc[-1].date()),**calc,'orders':int(data.orders.sum()),'total_modelled_cost_eur':float(data.costs.sum()),'total_turnover':float(data.turnover.sum()),'deferred_open_sessions':int(data.pending_missing_open.sum()),'held_bad_geometry_days':int((data.held_geometry_flags>0).sum())})
            for k,v in identity.items():ledger[k]=v;trades[k]=v
            ledgers.append(ledger);trade_logs.append(trades)
    score=pd.DataFrame(summaries);score.to_csv(OUT/'CONTROL_SCORECARD.csv',index=False)
    pd.concat(ledgers,ignore_index=True).to_csv(OUT/'CONTROL_DAILY.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.concat(trade_logs,ignore_index=True).to_csv(OUT/'CONTROL_ORDERS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    # Independent arithmetic verification without importing the replay function.
    verify=[]
    for l in ledgers:
        initial=float(l.initial_eur.iloc[0]);v=list(l.equity.astype(float));peak=initial;dd=0.
        for x in v:peak=max(peak,x);dd=min(dd,x/peak-1)
        ref=score[(score.arm==l.arm.iloc[0])&(score.initial_eur==initial)&(score.ticket_fee_eur==l.ticket_fee_eur.iloc[0])&(score.shortfall_bps_per_side==l.shortfall_bps_per_side.iloc[0])&(score.window=='THROUGH_2026_11_13_PARTIAL_MONTH')].iloc[0]
        diff=max(abs(dd-ref.max_drawdown),abs(v[-1]/initial-1-ref.net_cumulative))
        if diff>1e-12:raise AssertionError('INDEPENDENT_METRIC_CHECK')
        verify.append(diff)
    native={'status':'BLOCKED_FROZEN_MODEL_TRANSPORT','olc19_new_results':False,'olc67_new_results':False,'candidate_labels_used_for_fit':False,'native_upstream_models_loaded':False,'world_and_momentum_are_not_substitutes_for_native_ML':True,'missing_original_inputs':['OLC14_Heads_Checkpoint_20261101.zip','OLC19_Rischio_Rientro_Checkpoint_20261102.zip','original annual Return125/ET models and their input/parity panels'],'reason':'Original model archives exist in the user Library but not in the authenticated GitHub checkout/retained public source snapshot. Local computation/file-byte transport failed in this session. No substitute learner is fitted.'}
    (OUT/'NATIVE_ML_GATE.json').write_text(json.dumps(native,indent=2)+'\n')
    validation={'status':'PASS_DECLARED_CONTROLS_ONLY_NATIVE_ML_BLOCKED','run_id':os.getenv('OLC_RUN_ID'),'code_commit':os.getenv('OLC_CODE_SHA'),'captured_input_checksums':len(checks),'candidate_funds':len(frames),'monthly_decisions':len(events),'replays':len(ledgers),'metric_rows':len(score),'max_self_financing_error_eur':maxerror,'max_independent_metric_error':max(verify),'fractional_adjusted_economic_units':True,'whole_share_broker_simulation':False,'V6_or_FAST_LOCK3_applied':False,'TradeRepublic_actual_quotes_used':False,'personal_taxes_included':False,'raw_sources_unchanged':True,'asof_cutoff':'2026-11-13','prospective':False,'generated_at_utc':datetime.now(timezone.utc).isoformat()}
    (OUT/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n')
    base=score[(score.initial_eur==10000.)&(score.ticket_fee_eur==1.)&(score.shortfall_bps_per_side==15.)&(score.window=='THROUGH_2026_11_13_PARTIAL_MONTH')]
    table=['| Controllo | CAGR calendario | Cumulato | MaxDD chiusure | Ordini | Costi simulati |','|---|---:|---:|---:|---:|---:|']
    for r in base.itertuples():table.append(f'| {r.arm} | {r.cagr_calendar:.2%} | {r.net_cumulative:.2%} | {r.max_drawdown:.2%} | {r.orders} | EUR {r.total_modelled_cost_eur:.2f} |')
    text='\n'.join(['# OLC105 — Risultati dei controlli, NON risultati OLC19/OLC67','',
      '**Completamento parziale: World e momentum eseguiti; i quattro bracci ML restano bloccati.**','',
      f"Finestra: apertura {base.start_open.iloc[0]} → chiusura {base.end_close.iloc[0]}; novembre parziale. {len(events)} segnali mensili eleggibili. Scenario illustrativo EUR 10.000, EUR 1 per ordine e shortfall ipotetico 15 bp per lato.",'',*table,'',
      '## Definizioni e limiti',
      '- World fisso: ISIN IE00BFY0GT14, scelto prima degli outcome, acquisto alla prima apertura eleggibile e mantenimento.',
      '- MOM252: due maggiori rendimenti a 252 osservazioni precedenti, 50/50, ribilanciamento mensile alla prima apertura successiva. Nessun apprendimento, V6 o FAST_LOCK3: solo controllo semplice.',
      '- Universo: i 29 ISIN congelati, con le fonti alternative dello stesso ISIN già preregistrate. Le sei serie settoriali sono tagliate prima del 3 maggio 2016. Nessun fondo aggiunto dopo gli outcome.',
      '- Elegibilità: 252 rendimenti richiedono 253 osservazioni; ultima quota al massimo cinque giorni prima del segnale, almeno 12 fondi e tutti i sei macro-gruppi presenti. Il controllo World ha la stessa partenza.',
      '- Contabilità con unita economiche frazionarie su OHLC rettificate per total return Yahoo: NON quote intere né fill reali Trade Republic. Le distribuzioni sono incorporate nei prezzi rettificati, non accrediti cash broker.',
      '- Commissioni e shortfall sono detratti dal capitale disponibile, per ogni strumento effettivamente comprato/venduto. I 5/15/30 bp non sono spread osservati. Cash non remunerato, fiscalita esclusa.',
      '- Nessuna esecuzione su Open mancante: il ribilanciamento viene rinviato, non riempito usando prezzi inventati. Il Close precedente è usato soltanto per valorizzare posizioni durante assenza di quota.',
      '- I flag OHLC rimangono invariati e non servono a scegliere i vincitori. Questa prova non usa i Low per simulare stop; non certifica le barre.',
      '- Si tratta di uno studio retrospettivo su nuovi fondi, non di mercati o periodi indipendenti e non di una previsione dei rendimenti futuri.',
      '', '## Stato del test richiesto',
      'Non è lecito confrontare queste due curve con i CAGR OLC19/OLC67 dei vecchi universi e concludere che il ML funzioni o fallisca. Il test ANCHORED_TRANSFER non è stato eseguito: i modelli binari originali non sono stati trasportati al runner.',
      'Sono state censite 1.287 registrazioni di artifact e verificato lo snapshot pubblico dei sorgenti, ma ciò non sostituisce gli archivi congelati della Library. Nessun dato mancante è stato inventato.',
      '', '## Verifiche',json.dumps(validation,indent=2),'',
      'File: CONTROL_SCORECARD.csv, CONTROL_DAILY.csv.gz, CONTROL_ORDERS.csv.gz, MOMENTUM_SIGNALS.csv, ASOF_ELIGIBILITY.csv, FROZEN_INSTRUMENT_QA.csv, NATIVE_ML_GATE.json. Nessuna modifica a main o alle automazioni.',''])
    (OUT/'REPORT_CONTROLS_IT.md').write_text(text)
    manifest={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='MANIFEST_SHA256.json'}
    (OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(text)

if __name__=='__main__':main()
