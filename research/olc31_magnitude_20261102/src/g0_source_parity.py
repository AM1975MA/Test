"""OLC31 G0: read-only source and contract audit; NO modelling, training or backtests.
Use immutable checkpoint ZIP contents, inspect raw predictions and cached portfolio accounts.
"""
from __future__ import annotations
import io, json, hashlib, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

D=Path('/mnt/data')
S=D/'magnitude_audit_sources'
OUT=D/'OLC31_Magnitude_Study'
ARCH={
    'OLC08':S/'OLC08_03_RSI_Confronto_Verificato_20261101.zip',
    'OLC11':S/'OLC11_Selezione_Risultati_20261101.zip',
    'OLC12':S/'OLC12_Integrazione_Risultati_20261101.zip',
    'OLC19':S/'OLC19_Rischio_Rientro_Checkpoint_20261102.zip',
    'OLC20':D/'OLC20_Regime_Validation_Final_20261102.zip',
}
SHA={
 'OLC08':'0dbcb8ee93cd0acaefd7505a202fbf30c9fda8df1804d90a0dd1578abd704f4b',
 'OLC11':'fc536d786f42f724df8102544c33e3da0e347d216d16b871f805525d9f467b6c',
 'OLC12':'f899576dcb3230ceab98cb59a939f4ceb7e9bd9215a7f2c140f0a1df8131b3dd',
 'OLC19':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
 'OLC20':'a81be0fad1da73b48ba0af0080985657ee33e18a10f278db2318f9da06738a9c',
}
P19='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'


def readcsv(z,name):
    return pd.read_csv(io.BytesIO(z.read(name)),compression='gzip' if name.endswith('.gz') else None, float_precision='round_trip')

def readnpz(z,name):
    with np.load(io.BytesIO(z.read(name)),allow_pickle=False) as ar:
        return {k:ar[k].copy() for k in ar.files}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def key_count(df,keys):
    if df.duplicated(keys).any(): raise AssertionError('Duplicate keys: '+str(keys))
    return int(df[keys].drop_duplicates().shape[0])

def compare_npzs(a,b):
    assert set(a)==set(b)
    errors={}
    for key in a:
        x,y=a[key],b[key]
        if x.shape!=y.shape or x.dtype!=y.dtype: errors[key]='shape_or_type'
        elif not (np.array_equal(x,y,equal_nan=True) if np.issubdtype(x.dtype,np.inexact) else np.array_equal(x,y)):
            errors[key] = float(np.nanmax(np.abs(x-y))) if np.issubdtype(x.dtype,np.number) else 'different'
    return errors


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest={k:{'path':str(p.name),'bytes':p.stat().st_size,'sha256':digest(p),'verified':digest(p)==SHA[k]} for k,p in ARCH.items()}
    assert all(v['verified'] for v in manifest.values()),manifest
    all_cohorts=[];monthly=[];parity=[];risk=[]
    with zipfile.ZipFile(ARCH['OLC08']) as z08,zipfile.ZipFile(ARCH['OLC11']) as z11,zipfile.ZipFile(ARCH['OLC12']) as z12,zipfile.ZipFile(ARCH['OLC19']) as z19,zipfile.ZipFile(ARCH['OLC20']) as z20:
        for market in ['EU','USA']:
            scores=readcsv(z20,f'results/trials/AUTH/{market}_SCORES.csv.gz')
            original=readcsv(z08,f'results/{market}_R_RSI_DOMAIN_FORECASTS.csv.gz')
            frame=readcsv(z19,P19+f'{market}_FITTING_FRAME.csv.gz')
            cal=readcsv(z19,P19+f'{market}_CALENDAR.csv')
            state=readnpz(z19,P19+f'{market}_STATE_HALF.npz')
            refs=readcsv(z12,f'olc12_integration_20261101/results/{market}_INTEGRATED_SCORES.csv.gz')
            pred=[readcsv(z11,f'results/{market}_S{s}_PREDICTIONS.csv.gz') for s in (101,211,307)]
            for d,typ in [(scores,'OLC20_AUTH'),(original,'OLC08_RETURN'),(frame,'OLC16_FRAME'),(refs,'OLC12_SCORES')]:
                keys=['signal_date','ticker'];key_count(d,keys)
                all_cohorts.append({'market':market,'source':typ,'rows':len(d),'months':d.signal_date.nunique(),'tickers':d.ticker.nunique(),'first':d.signal_date.min(),'last':d.signal_date.max()})
            for i,p in enumerate(pred):
                key_count(p,['signal_date','ticker']);all_cohorts.append({'market':market,'source':f'OLC11_SEED{(101,211,307)[i]}','rows':len(p),'months':p.signal_date.nunique(),'tickers':p.ticker.nunique(),'first':p.signal_date.min(),'last':p.signal_date.max()})
            assert not cal.duplicated(['signal_date']).any()
            assert not (pd.to_datetime(cal.entry_date)<=pd.to_datetime(cal.signal_date)).any()
            assert not (pd.to_datetime(cal.exit_date)<pd.to_datetime(cal.entry_date)).any()
            # Terminal 2026-07-01 row: exit==entry, NOT a matured next-month label.
            terminal=(pd.to_datetime(cal.exit_date)==pd.to_datetime(cal.entry_date))
            assert terminal.sum()==1 and pd.Timestamp(cal.loc[terminal,'entry_date'].iloc[0])==pd.Timestamp('2026-07-01')
            # Cross-check source rank construction, exact nan/tie handling.
            for raw,percentile in [('RETURN_RAW','RETURN'),('ET_RAW','ET'),('XGB_RAW','XGB')]:
                rep=original.groupby('signal_date')[raw].rank(method='average',pct=True).to_numpy(float)
                y=original[percentile].to_numpy(float)
                parity.append({'market':market,'check':f'RECONSTRUCT_{raw}_TO_{percentile}','n':len(y),'mask_equal':bool(np.array_equal(np.isfinite(rep),np.isfinite(y))),'max_abs':float(np.nanmax(np.abs(rep-y)))})
                assert np.allclose(rep,y,rtol=0,atol=1e-12,equal_nan=True), (market,raw)
            # Compare reference RETURN percentiles across archive generations and record support drift, not assume perfect matching.
            for src,d,col in [('OLC08',original,'RETURN'),('OLC16',frame,'RETURN')]:
                j=scores[['signal_date','ticker','RETURN']].merge(d[['signal_date','ticker',col]],on=['signal_date','ticker'],how='left',indicator=True,suffixes=('_ref','_test'),validate='one_to_one')
                y=j.RETURN_test.to_numpy(float);x=j.RETURN_ref.to_numpy(float);good=np.isfinite(y)&np.isfinite(x)
                parity.append({'market':market,'check':f'AUTH_RETURN_VS_{src}','n':int(good.sum()),'unmatched':int((j['_merge']!='both').sum()),'mask_equal':bool(np.array_equal(np.isfinite(x),np.isfinite(y))),'max_abs':float(np.max(np.abs(x[good]-y[good]))) if good.sum() else None})
            # Verify recorded entry-exit dates, compare staged O2O data masks. No outcome model fitting in G0.
            entry=cal[['signal_date','entry_date','exit_date']].copy();entry['entry_date']=pd.to_datetime(entry.entry_date);entry['exit_date']=pd.to_datetime(entry.exit_date)
            indexed={d:i for i,d in enumerate(pd.DatetimeIndex(state['dates']))};tickmap={t:i for i,t in enumerate(state['tickers'])}
            c=scores[['signal_date','ticker']].merge(entry,on='signal_date',how='left',validate='many_to_one');c['signal_date']=pd.to_datetime(c.signal_date)
            c['entry_idx']=c.entry_date.map(indexed);c['exit_idx']=c.exit_date.map(indexed);c['ticker_idx']=c.ticker.map(tickmap)
            assert c.entry_idx.notna().all() and c.ticker_idx.notna().all(),(market,'bad date/ticker maps')
            ix=c.entry_idx.to_numpy(int);ti=c.ticker_idx.to_numpy(int)
            have=(c.exit_idx.notna() & (c.exit_date>c.entry_date)).to_numpy();yy=np.zeros(len(c),bool);yy[have]=True
            # skip last unavailable exit, never use the next past cutoff from fabricated terminal dates
            o0=state['O'][ix,ti]
            ok0=np.isfinite(o0)&(o0>0)
            if 'observed' in state: ok0&=state['observed'][ix,ti]
            ok1=np.zeros(len(c),bool)
            if have.any():
                ei=c.exit_idx[have].to_numpy(int);ee=state['O'][ei,ti[have]]
                ok1[have]=np.isfinite(ee)&(ee>0)
                if 'observed' in state:ok1[have]&=state['observed'][ei,ti[have]]
            valid=ok0&ok1&have
            c['valid_price_label']=valid
            for month,g in c.groupby('signal_date'):
                monthly.append({'market':market,'signal_date':month.strftime('%Y-%m-%d'),'scores':len(g),'price_labels_valid':int(g.valid_price_label.sum()),'valid_fraction':float(g.valid_price_label.mean()),'calendar_entry':str(g.entry_date.iloc[0].date()) if g.entry_date.notna().any() else '', 'calendar_exit':str(g.exit_date.iloc[0].date()) if g.exit_date.notna().any() else ''})
            # 32 OLC19 reference portfolios vs AUTH / ORIGINAL / CUM_FIT / STATIC in OLC20.
            refmap={'AUTH':'TOP2_CONTEXT_REVALUE','STATIC':'TOP2_STATIC_REVALUE','ORIGINAL':'ORIGINAL','CUM_FIT':'CUM_FIT'}
            for trial,prefix in refmap.items():
                for contract in ['ALARM','FAST_LOCK3']:
                    for fee in ['10','30']:
                        p19=f'olc19_combined_risk_20261102/results/paths/{market}_{prefix}_{contract}_F{fee}_S10.npz'
                        p20=f'results/portfolios/{trial}/{market}_{contract}_{fee}.npz'
                        if p19 not in z19.namelist():raise AssertionError(('missing parent reference',p19))
                        aa=readnpz(z19,p19);bb=readnpz(z20,p20);diff=compare_npzs(aa,bb)
                        risk.append({'market':market,'trial':trial,'contract':contract,'fee':fee,'arrays':len(aa),'matching':len(diff)==0,'errors':str(diff)[:600]})
                        assert not diff, (market,trial,contract,fee,diff)
    df=pd.DataFrame(monthly);coh=pd.DataFrame(all_cohorts);pd.DataFrame(parity).to_csv(OUT/'02_SCORE_LINEAGE_G0.csv',index=False);coh.to_csv(OUT/'01_KEY_COVERAGE_G0.csv',index=False);df.to_csv(OUT/'03_O2O_LABEL_COVERAGE_G0.csv',index=False)
    record={'status':'G0_PRIMARY_PASS_FULL_HISTORY_PRICE_MASK_EXCEPTION','input_manifest':manifest,'source_cohorts':coh.to_dict('records'),'score_parity':parity,'portfolio_checks':risk,'return_contracts':{'EU':'EU observed masks at entry+exit','USA':'finite prepared Open only; original observed mask missing'},'price_monthly_coverage':{'EU':df[df.market=='EU'].valid_fraction.describe().to_dict(),'USA':df[df.market=='USA'].valid_fraction.describe().to_dict()},'note':'Main 2021-24 labels nearly complete, but EU 2020-06-01 is a Frankfurt/Xetra holiday (only 11/167 originally observed), causing two poor-coverage monthly exit/entry labels. Treat full-history Open-to-Open magnitudes as incomplete, do not fill. USA original observed mask unavailable. Terminal 2026-07-01 entry==exit excluded. No models fitted or new portfolios simulated.'}
    (OUT/'00_SOURCE_MANIFEST_G0.json').write_text(json.dumps(record,indent=2,default=str,ensure_ascii=False))
    print(json.dumps({'gate':record['status'],'cohorts':coh.to_dict('records'),'parity':parity,'risk_accounts':len(risk),'valid_label_by_market':df.groupby('market').agg(months=('signal_date','size'),median_fraction=('valid_fraction','median'),min_fraction=('valid_fraction','min')).round(5).to_dict('index')},indent=2,default=str))

if __name__=='__main__':main()
