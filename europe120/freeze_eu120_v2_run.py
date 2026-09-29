#!/usr/bin/env python3
# EU120-v2 candidate expansion and narrowly relaxed data-quality thresholds.
# No return/performance statistic is consulted by selection.
import inspect, json
from pathlib import Path
import freeze_eu120_v2 as f

f.MAX_CONSEC_ZERO = 7
src = inspect.getsource(f.download).replace('if medvol<500:', 'if medvol<250:')
exec(src, f.__dict__)

f.SEEDS['C01_EUROPE_BROAD'] += [
    'IDVY.MI','CSEMUS.MI','SXRJ.DE','CEMS.DE','IEVL.MI','IEQU.MI','CEMQ.DE','ZPRX.DE',
    'SC0E.DE','SXRT.DE','HEU.PA','DBEU','D5BL.DE','ZPRW.DE','CEMU.AS'
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

f.SEEDS['C02_EUROPE_COUNTRY'] += [
    'ISF.MI','IQQH.DE','IQQW.DE','SXRY.DE','CMB1.L','CSSMI.SW','NORW','FGM',
    'CSEMU.S','CEU1.AS','CEU1.L','IUSZ.DE','XMEU.DE','SXR1.DE'
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
    m['wrapper_note'] = 'EU120-v2 run wrapper changed only candidate pools, max zero run 5->7 and pre-2017 median-volume floor 500->250; no performance statistic used.'
    p.write_text(json.dumps(m, indent=2) + '\n')
