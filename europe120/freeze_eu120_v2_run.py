#!/usr/bin/env python3
# Candidate-pool expansion only. Selection gates and ordering logic remain in
# freeze_eu120_v2.py. No return/performance statistic is consulted here.
import freeze_eu120_v2 as f

f.SEEDS['C01_EUROPE_BROAD'] += [
    'CSEMUS.MI','SXRJ.DE','CEMS.DE','IEVL.MI','IEQU.MI','CEMQ.DE','ZPRX.DE',
    'SC0E.DE','SXRT.DE','HEU.PA','DBEU','D5BL.DE','ZPRW.DE'
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

# Additional deterministic fallbacks for later clusters. Every ticker still has
# to pass EUR currency, unique fund identity, pre-2017 history and data quality.
f.SEEDS['C02_EUROPE_COUNTRY'] += [
    'ISF.MI','IQQH.DE','IQQW.DE','SXRY.DE','CMB1.L','CSSMI.SW','NORW','FGM'
]
f.SEEDS['C03_US_EQUITY_EUR'] += [
    'IUSA.DE','IUS3.DE','IQQQ.DE','XSPX.DE','D5BM.DE','ZPRU.DE'
]
f.SEEDS['C04_WORLD_DEVELOPED'] += [
    'DBX1MW.DE','DBX1DA.DE','D5BI.DE','D5BE.DE','SXR1.DE','IQQ0.DE'
]
f.SEEDS['C05_EMERGING_ASIA'] += [
    'DBX1EM.DE','IQQE.DE','IQQC.DE','XCS6.DE','CINA.DE','SXRJ.DE'
]

if __name__ == '__main__':
    f.main()
