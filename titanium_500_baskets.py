from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path('titanium_500_baskets_output')
OUT.mkdir(parents=True, exist_ok=True)
START_DOWNLOAD = '2005-01-01'
END_DOWNLOAD = '2026-08-02'
BACKTEST_START = pd.Timestamp('2017-01-31')
COST_ONE_WAY = 0.001
N_BASKETS = 500
PER_CATEGORY = 5
SEED = 20260802

CATEGORY_TICKERS = {
'C01_US_BROAD_STYLE': ['DIA','IJR','SCHD','QQQ','QUAL','RSP','DGRO','IJH','IWF','HDV','MDY','SCHB','IWM','MTUM','SCHX','SPY','IVV','VTI','VO','VB','VUG','VTV','IWD','IWN','SPLV'],
'C02_US_SECTOR_THEME': ['PPA','SMH','SOXX','IGV','IHI','KBE','HACK','IYT','KRE','IBB','ICLN','ITA','FDN','TAN','XBI','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XRT'],
'C03_DEVELOPED_GLOBAL': ['ACWI','EWL','EWP','EWA','EWN','IEFA','EFA','EWH','EWQ','EWC','EWD','EWJ','EWG','EWI','EWU','VEA','VEU','VGK','EWK','EWO','EIRL','EIS','EPOL','ENZL','EPP'],
'C04_EMERGING': ['EWS','EWY','FXI','ASHR','INDA','VWO','EWT','IEMG','KWEB','EEM','MCHI','TUR','AAXJ','EWZ','EZA','EIDO','EWM','THD','EPHE','SCHE','DEM','DGS','EPI','PIN','ARGT'],
'C05_BONDS_CASH_CREDIT': ['AGG','BIL','EMB','IEF','IEI','LQD','BNDX','HYG','MUB','BND','JNK','SCHP','EDV','SHY','TLT','TIP','SHV','VGSH','VGIT','VGLT','VCIT','VCSH','MBB','BKLN','ANGL'],
'C06_REAL_ASSETS': ['COMT','GLD','SLV','GSG','IYR','PPLT','CPER','DBB','VNQ','DBC','GDX','PALL','BNO','DBA','GDXJ','IAU','USO','UNG','DBO','USL','RWO','RWX','WOOD','CORN','URA'],
}
ALL_TICKERS = [t for xs in CATEGORY_TICKERS.values() for t in xs]
TICKER_TO_CATEGORY = {t:c for c,xs in CATEGORY_TICKERS.items() for t in xs}


def download_prices() -> pd.DataFrame:
    chunks, logs = [], []
    for i in range(0, len(ALL_TICKERS), 30):
        tickers = ALL_TICKERS[i:i+30]
        for attempt in range(4):
            try:
                raw = yf.download(tickers=tickers, start=START_DOWNLOAD, end=END_DOWNLOAD,
                                  auto_adjust=True, progress=False, threads=True,
                                  group_by='column', timeout=30)
                if raw.empty:
                    raise RuntimeError('empty download')
                if isinstance(raw.columns, pd.MultiIndex):
                    close = raw['Close'].copy()
                else:
                    close = raw[['Close']].rename(columns={'Close': tickers[0]})
                close.columns = [str(c).upper() for c in close.columns]
                chunks.append(close)
                logs.extend({'ticker':t, 'downloaded': t in close.columns and close[t].notna().sum() > 300} for t in tickers)
                break
            except Exception as exc:
                if attempt == 3:
                    logs.extend({'ticker':t, 'downloaded':False, 'error':repr(exc)} for t in tickers)
                time.sleep(2 ** attempt)
    if not chunks:
        raise RuntimeError('No market data downloaded')
    prices = pd.concat(chunks, axis=1)
    prices = prices.loc[:, ~prices.columns.duplicated()].sort_index()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices = prices.dropna(axis=1, how='all').ffill(limit=5)
    pd.DataFrame(logs).to_csv(OUT/'DOWNLOAD_LOG.csv', index=False)
    prices.to_parquet(OUT/'ADJ_CLOSE_DOWNLOADED.parquet')
    return prices


def percentile_rank(df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
    return df.rank(axis=1, pct=True, method='average', ascending=ascending)


def build_monthly_features(prices: pd.DataFrame):
    mclose = prices.resample('ME').last()
    daily_ret = prices.pct_change(fill_method=None)
    vol63 = (daily_ret.rolling(63, min_periods=42).std(ddof=0) * np.sqrt(252)).resample('ME').last()
    m21 = mclose.pct_change(1, fill_method=None)
    m63 = mclose.pct_change(3, fill_method=None)
    m126 = mclose.pct_change(6, fill_method=None)
    m252 = mclose.pct_change(12, fill_method=None)
    accel = m21 - m63 / 3.0
    proximity = mclose / mclose.rolling(6, min_periods=3).max() - 1.0
    base_score = (0.15*percentile_rank(m21) + 0.25*percentile_rank(m63) +
                  0.25*percentile_rank(m126) + 0.20*percentile_rank(m252) +
                  0.10*percentile_rank(accel) + 0.05*percentile_rank(-vol63))
    opp_score = (0.45*percentile_rank(m21) + 0.25*percentile_rank(accel) +
                 0.15*percentile_rank(m63) + 0.10*percentile_rank(proximity) +
                 0.05*percentile_rank(m126))
    hist = prices.notna().rolling(252, min_periods=1).sum().resample('ME').last()
    eligible = hist >= 252
    base_score, opp_score = base_score.where(eligible), opp_score.where(eligible)
    next_ret = mclose.pct_change(fill_method=None).shift(-1)
    common = base_score.index.intersection(next_ret.index)
    common = common[(common >= BACKTEST_START) & (common < next_ret.dropna(how='all').index.max())]
    return base_score.loc[common], opp_score.loc[common], next_ret.loc[common]


def make_baskets(available: set[str]) -> list[list[str]]:
    rng = np.random.default_rng(SEED)
    cats = {c:[t for t in xs if t in available] for c,xs in CATEGORY_TICKERS.items()}
    baskets, seen = [], set()
    while len(baskets) < N_BASKETS:
        selected = []
        for c in sorted(cats):
            if len(cats[c]) < PER_CATEGORY:
                raise RuntimeError(f'Category {c} has only {len(cats[c])} tickers')
            selected.extend(rng.choice(cats[c], size=PER_CATEGORY, replace=False).tolist())
        key = tuple(sorted(selected))
        if key not in seen:
            seen.add(key)
            baskets.append(selected)
    return baskets


def metrics(monthly_returns: pd.Series) -> dict[str,float]:
    r = monthly_returns.dropna().astype(float)
    eq = (1+r).cumprod()
    years = len(r)/12.0
    cagr = eq.iloc[-1]**(1/years)-1
    dd = eq/eq.cummax()-1
    sharpe = np.sqrt(12)*r.mean()/r.std(ddof=0) if r.std(ddof=0)>0 else np.nan
    return {'cagr':float(cagr),'maxdd':float(dd.min()),'sharpe':float(sharpe),
            'final_equity':float(eq.iloc[-1]),'months':int(len(r))}


def turnover_cost(old: dict[str,float], new: dict[str,float]) -> float:
    return COST_ONE_WAY*sum(abs(new.get(t,0)-old.get(t,0)) for t in set(old)|set(new))


def run_one(universe: list[str], base: pd.DataFrame, opp: pd.DataFrame, fwd: pd.DataFrame):
    old_base, old_direct, old_router = {}, {}, {}
    base_rets, direct_rets, router_rets, shadow_hist, dates = [], [], [], [], []
    active = 0
    for dt in base.index:
        bs = base.loc[dt, universe].dropna()
        os = opp.loc[dt, universe].dropna()
        valid = [t for t in bs.index.intersection(os.index) if t in fwd.columns and pd.notna(fwd.at[dt,t])]
        if len(valid) < 6:
            continue
        bs, os = bs.loc[valid].sort_values(ascending=False), os.loc[valid].sort_values(ascending=False)
        t1, t2 = bs.index[0], bs.index[1]
        margin = float(bs.iloc[0]-bs.iloc[1])
        base_w1 = 1.0 if margin >= 0.12 else 0.75
        w_base = {t1:base_w1, t2:1-base_w1}
        opp_rank_t1 = int(os.index.get_loc(t1)+1)
        oz = (os[t1]-os.mean())/(os.std(ddof=0)+1e-12)
        direct_condition = bool(base_w1 < 1.0 and opp_rank_t1 <= 3 and oz >= 0.50)
        w_direct = {t1:1.0} if direct_condition else dict(w_base)
        router_on = len(shadow_hist) >= 12 and float(np.prod(1+np.array(shadow_hist[-12:]))-1) > 0
        w_router = dict(w_direct if router_on else w_base)
        rb = sum(w*fwd.at[dt,t] for t,w in w_base.items()) - turnover_cost(old_base,w_base)
        rd = sum(w*fwd.at[dt,t] for t,w in w_direct.items()) - turnover_cost(old_direct,w_direct)
        rr = sum(w*fwd.at[dt,t] for t,w in w_router.items()) - turnover_cost(old_router,w_router)
        shadow_hist.append(sum(w*fwd.at[dt,t] for t,w in w_direct.items()) - sum(w*fwd.at[dt,t] for t,w in w_base.items()))
        active += int(router_on)
        base_rets.append(rb); direct_rets.append(rd); router_rets.append(rr); dates.append(dt)
        old_base, old_direct, old_router = w_base, w_direct, w_router
    idx = pd.DatetimeIndex(dates)
    return {'BASE':pd.Series(base_rets,index=idx), 'DIRECT':pd.Series(direct_rets,index=idx),
            'ROUTER':pd.Series(router_rets,index=idx), 'router_active_months':active}


def main():
    prices = download_prices()
    base, opp, fwd = build_monthly_features(prices)
    available = set(base.columns[base.notna().sum() >= 24])
    baskets = make_baskets(available)
    rows, membership = [], []
    for i,basket in enumerate(baskets):
        res = run_one(basket, base, opp, fwd)
        membership.extend({'basket_id':i,'ticker':t,'category':TICKER_TO_CATEGORY[t]} for t in basket)
        for strat in ['BASE','DIRECT','ROUTER']:
            rows.append({'basket_id':i,'strategy':strat,**metrics(res[strat]),
                         'router_active_months':res['router_active_months']})
    results = pd.DataFrame(rows)
    pd.DataFrame(membership).to_csv(OUT/'BASKET_MEMBERSHIP_500.csv',index=False)
    results.to_csv(OUT/'BASKET_RESULTS_500.csv',index=False)
    global_res = run_one(sorted(available), base, opp, fwd)
    global_df = pd.DataFrame([{'strategy':s,**metrics(global_res[s]),
                              'router_active_months':global_res['router_active_months']}
                             for s in ['BASE','DIRECT','ROUTER']])
    global_df.to_csv(OUT/'GLOBAL_UNRESTRICTED_SCORECARD.csv',index=False)
    router = results.query("strategy == 'ROUTER'").copy()
    router[['cagr','maxdd','sharpe']].describe(percentiles=[.05,.10,.25,.5,.75,.90,.95]).T.to_csv(OUT/'ROUTER_DISTRIBUTION_SUMMARY.csv')
    med, mean = router.cagr.median()*100, router.cagr.mean()*100
    global_cagr = float(global_df.query("strategy=='ROUTER'").cagr.iloc[0])*100
    plt.figure(figsize=(10,6)); plt.hist(router.cagr*100,bins=30,edgecolor='black',alpha=.8)
    plt.axvline(med,linestyle='--',linewidth=2,label=f'Mediana {med:.2f}%')
    plt.axvline(mean,linestyle=':',linewidth=2,label=f'Media {mean:.2f}%')
    plt.axvline(global_cagr,linewidth=2,label=f'Universo libero {global_cagr:.2f}%')
    plt.xlabel('CAGR 2017–luglio 2026 (%)'); plt.ylabel('Numero di panieri')
    plt.title('Titanium-inspired Router — CAGR su 500 panieri'); plt.legend(); plt.grid(alpha=.2); plt.tight_layout()
    plt.savefig(OUT/'CAGR_500_BASKETS_HISTOGRAM.png',dpi=180); plt.close()
    vals=np.sort(router.cagr.dropna().to_numpy()*100); y=np.arange(1,len(vals)+1)/len(vals)
    plt.figure(figsize=(10,6)); plt.plot(vals,y,linewidth=2); plt.axvline(global_cagr,linestyle='--',linewidth=2,label=f'Universo libero {global_cagr:.2f}%')
    plt.xlabel('CAGR (%)'); plt.ylabel('Quota cumulata'); plt.title('Distribuzione cumulata CAGR — 500 panieri')
    plt.legend(); plt.grid(alpha=.25); plt.tight_layout(); plt.savefig(OUT/'CAGR_500_BASKETS_ECDF.png',dpi=180); plt.close()
    g=global_df.query("strategy=='ROUTER'").iloc[0]
    plt.figure(figsize=(10,6)); plt.scatter(router.maxdd*100,router.cagr*100,s=20,alpha=.55)
    plt.scatter([g.maxdd*100],[g.cagr*100],s=120,marker='*',label='Universo libero')
    plt.xlabel('MaxDD (%)'); plt.ylabel('CAGR (%)'); plt.title('CAGR vs MaxDD — 500 panieri Router')
    plt.legend(); plt.grid(alpha=.25); plt.tight_layout(); plt.savefig(OUT/'CAGR_VS_MAXDD_500_BASKETS.png',dpi=180); plt.close()
    q=router.cagr.quantile([.05,.10,.25,.5,.75,.90,.95])*100
    report=f'''# Test reale su dati scaricati — 500 panieri\n\n- Universo richiesto: {len(ALL_TICKERS)} ETF\n- ETF utilizzabili: {len(available)}\n- Panieri: {N_BASKETS}, 30 ETF ciascuno, 5 per categoria\n- Periodo: {base.index.min().date()} – {base.index.max().date()}\n- Costi: {COST_ONE_WAY*10000:.0f} bp one-way\n\n## Router sui 500 panieri\n\n- CAGR medio: {router.cagr.mean()*100:.2f}%\n- CAGR mediano: {router.cagr.median()*100:.2f}%\n- P10/P90: {q.loc[.10]:.2f}% / {q.loc[.90]:.2f}%\n- P05/P95: {q.loc[.05]:.2f}% / {q.loc[.95]:.2f}%\n- Quota CAGR positivo: {(router.cagr>0).mean()*100:.1f}%\n- MaxDD mediano: {router.maxdd.median()*100:.2f}%\n\n## Universo libero\n\n- CAGR Router: {g.cagr*100:.2f}%\n- MaxDD: {g.maxdd*100:.2f}%\n- Sharpe: {g.sharpe:.3f}\n\nTest nuovo, non replica frozen di Titanium.\n'''
    (OUT/'REPORT.md').write_text(report,encoding='utf-8')
    (OUT/'MANIFEST.json').write_text(json.dumps({'tickers_requested':len(ALL_TICKERS),'tickers_usable':len(available),'baskets':N_BASKETS,'basket_size':30,'seed':SEED,'cost_one_way_bps':10},indent=2),encoding='utf-8')
    print(report)

if __name__=='__main__':
    main()
