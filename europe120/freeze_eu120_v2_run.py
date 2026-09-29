#!/usr/bin/env python3
# EU120-v2 candidate expansion and narrowly relaxed data-quality thresholds.
# No return/performance statistic is consulted by selection.
import inspect, json
from pathlib import Path
import freeze_eu120_v2 as f

f.MAX_CONSEC_ZERO = 7
src = inspect.getsource(f.download).replace('if medvol<500:', 'if medvol<250:')
exec(src, f.__dict__)

# Enforce uniqueness simultaneously by normalized fund name and by ISIN when
# available. This prevents duplicate listings when Yahoo exposes an ISIN only
# for one of the exchanges of the same fund.
msrc = inspect.getsource(f.main)
old = "original=original_149(); selected=[]; rejected=[]; quality=[]; data={}; used_tickers=set(); used_funds=set()"
new = "original=original_149(); selected=[]; rejected=[]; quality=[]; data={}; used_tickers=set(); used_funds=set(); used_names=set(); used_isins=set()"
assert old in msrc
msrc = msrc.replace(old, new)
old = "fundkey=meta['isin'] or norm_name(name)\n            if not fundkey:"
new = "namekey=norm_name(name); isinkey=meta['isin']; fundkey=isinkey or namekey\n            if not fundkey:"
assert old in msrc
msrc = msrc.replace(old, new)
old = "if fundkey in used_funds:"
new = "if fundkey in used_funds or namekey in used_names or (isinkey and isinkey in used_isins):"
assert old in msrc
msrc = msrc.replace(old, new)
old = "selected.append(rec); data[sym]=q; used_tickers.add(sym); used_funds.add(fundkey); chosen+=1"
new = "selected.append(rec); data[sym]=q; used_tickers.add(sym); used_funds.add(fundkey); used_names.add(namekey); used_isins.add(isinkey) if isinkey else None; chosen+=1"
assert old in msrc
msrc = msrc.replace(old, new)
exec(msrc, f.__dict__)

f.SEEDS['C01_EUROPE_BROAD'] += [
    'IDVY.MI','CSEMUS.MI','SXRJ.DE','CEMS.DE','IEVL.MI','IEQU.MI','CEMQ.DE','ZPRX.DE',
    'SC0E.DE','SXRT.DE','HEU.PA','DBEU','D5BL.DE','ZPRW.DE','CEMU.AS','IQQA.DE'
]
f.CLUSTERS['C01_EUROPE_BROAD']['queries'] += [
    'MSCI Europe small cap UCITS ETF EUR','MSCI Europe mid cap UCITS ETF EUR',
    'MSCI Europe momentum UCITS ETF EUR','MSCI Europe quality factor UCITS ETF EUR',
    'MSCI Europe high dividend UCITS ETF EUR','MSCI Europe ESG UCITS ETF EUR',
    'MSCI Europe SRI UCITS ETF EUR','MSCI Europe ex UK UCITS ETF EUR',
    'STOXX Europe 50 UCITS ETF EUR','STOXX Europe Select Dividend 30 UCITS ETF EUR',
    'EURO STOXX Select Dividend 30 UCITS ETF EUR','EURO STOXX small cap UCITS ETF EUR',
    'EURO STOXX mid cap UCITS ETF EUR','EURO STOXX total market UCITS ETF EUR'
]

# Keep C02 strictly country/national-index equity. Explicitly remove earlier
# experimental seeds that belonged to World, Clean Energy or bonds.
f.SEEDS['C02_EUROPE_COUNTRY'] = [s for s in f.SEEDS['C02_EUROPE_COUNTRY'] if s not in {
    'IQQH.DE','IQQW.DE','CMB1.L','CSSMI.SW','NORW','FGM','CSEMU.S','CEU1.AS','CEU1.L','IUSZ.DE','XMEU.DE','SXR1.DE'
}]
f.SEEDS['C02_EUROPE_COUNTRY'] += [
    'ISF.MI','SXRY.DE','C40.PA','CSMIB.MI','ATXEX.DE','XB4A.DE','CBATX.DE','CD47.DE','PPP.LS','OM3X.DE'
]
f.CLUSTERS['C02_EUROPE_COUNTRY']['exclude'] += ['government','eb.rexx','clean energy','world']
f.CLUSTERS['C02_EUROPE_COUNTRY']['queries'] += [
    'ATX Austria UCITS ETF EUR','PSI 20 Portugal UCITS ETF EUR','OMX Stockholm UCITS ETF EUR',
    'Sweden index UCITS ETF EUR','Nordic index UCITS ETF EUR','FTSE 100 UCITS ETF EUR',
    'Swiss SMI UCITS ETF EUR','MSCI Switzerland UCITS ETF EUR','MSCI Poland UCITS ETF EUR'
]

f.SEEDS['C03_US_EQUITY_EUR'] += [
    'IUSA.DE','IUS3.DE','IQQQ.DE','XSPX.DE','D5BM.DE','ZPRU.DE','ZPRV.DE',
    'SPY5.DE','SXR8.DE','SXRV.DE','EXXT.DE'
]
f.SEEDS['C04_WORLD_DEVELOPED'] += [
    'DBX1MW.DE','DBX1DA.DE','D5BI.DE','D5BE.DE','SXR1.DE','IQQ0.DE',
    'EUNL.DE','XDWD.DE','IUSQ.DE','SXR4.DE'
]
f.SEEDS['C05_EMERGING_ASIA'] += [
    'DBX1EM.DE','IQQE.DE','IQQC.DE','XCS6.DE','CINA.DE','SXRJ.DE',
    'IS3N.DE','EUNM.DE','XMME.DE'
]

if __name__ == '__main__':
    f.main()
    p = Path('europe120/v2_frozen_output/manifest.json')
    m = json.loads(p.read_text())
    m['quality_rules']['max_consecutive_zero_returns'] = 7
    m['quality_rules']['min_pre2017_median_nonzero_volume'] = 250
    m['identity_rule'] = 'ticker unique + normalized fund-name unique + ISIN unique when available'
    m['wrapper_note'] = 'EU120-v2 uses no performance statistic for selection; candidate-pool refinements are semantic/availability only.'
    p.write_text(json.dumps(m, indent=2) + '\n')
