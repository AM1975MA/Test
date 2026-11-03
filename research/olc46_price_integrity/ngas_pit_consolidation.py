#!/usr/bin/env python3
"""OLC46-D3 point-in-time identity for WisdomTree NGAS on Borsa Italiana.

Primary dated filing: 27 Oct 2023 regulatory announcement.
Existing ISIN GB00B15KY104 last trades 2023-12-01.
New ISIN JE00BN7KB334 first trades 2023-12-04.
1 new security for 1783 old securities. This is an identity/consolidation
correction, not reconstruction of independently verified trade prices.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parent;OUT=R/"results"
OLD="GB00B15KY104";NEW="JE00BN7KB334";SYMBOL="NGAS.MI"
FILING="https://www.lse.co.uk/rns/consolidations-of-cld-commodity-securities-uxn9emovp1a7646.html"
LAST_OLD=pd.Timestamp("2023-12-01")
FIRST_NEW=pd.Timestamp("2023-12-04")
RATIO=1783
d=pd.read_csv(OUT/"NGAS_MI_quality_masked.csv.gz",parse_dates=["date"])
d=d.sort_values("date")
before=d.date<=LAST_OLD
after=d.date>=FIRST_NEW
gap=(~before)&(~after)
if gap.any():raise ValueError("No valid trading dates expected between December 1 and 4, 2023")
d["isin_point_in_time"]=np.where(before,OLD,NEW)
d["isin_valid_from"]=np.where(before,"2006-09-22","2023-12-04")
d["issuer_commodity_security_class"]="WisdomTree Natural Gas"
d["consolidation_new_units_per_old_unit"]=np.where(before,1.0/RATIO,1.0)
d["consolidation_contemporary_units_per_adjusted_unit"]=np.where(before,float(RATIO),1.0)
d["historical_price_scale_status"]="UNVERIFIED_VENDOR_BACKADJUSTMENT"
d.to_csv(OUT/"NGAS_MI_PIT_IDENTITY_WITH_QUALITY_MASK.csv.gz",index=False,compression="gzip")
pre=d.loc[d.date==LAST_OLD]
post=d.loc[d.date==FIRST_NEW]
if len(pre)!=1 or len(post)!=1:
    ratio=None;status="MISSING_RECORD_DATE_QUOTES"
else:
    ratio=float(post.iloc[0]["open"]/pre.iloc[0]["close"])
    if ratio>100:
        status="PRICE_SERIES_MAY_RETAIN_PRE_CONSOLIDATION_UNITS"
    elif 0.5<ratio<1.5:
        status="PRICE_SERIES_LIKELY_ADJUSTED_TO_POST_CONSOLIDATION_UNITS_NOT_CERTIFIED"
    else:
        status="PRICE_UNIT_CONVENTION_UNRESOLVED"
result={
 "instrument":SYMBOL,
 "pre_dec_2023_isin":OLD,
 "post_dec_2023_isin":NEW,
 "last_old_trading_date":str(LAST_OLD.date()),
 "first_new_trading_date":str(FIRST_NEW.date()),
 "old_units_for_1_new_unit":RATIO,
 "n_bars_old_isin":int(before.sum()),
 "n_bars_new_isin":int(after.sum()),
 "yahoo_open_post_vs_close_pre_ratio":ratio,
 "provider_scale_diagnostic":status,
 "do_not_convert_prices_without_independent_reference":True,
 "corporate_action_requires_fractional_holdings_cash_in_lieu":True,
 "filing_url":FILING,
 "source":"27 Oct 2023 official issuer RNS",
 "generated_at_utc":datetime.now(timezone.utc).isoformat(),
 "no_forward_looking_isin_used_for_prior_signal":True,
}
(OUT/"NGAS_PIT_CORPORATE_ACTION_AUDIT.json").write_text(json.dumps(result,indent=2))
assert int(before.sum()+after.sum())==len(d)
assert (d.loc[d.date<FIRST_NEW,"isin_point_in_time"]==OLD).all()
assert (d.loc[d.date>=FIRST_NEW,"isin_point_in_time"]==NEW).all()
print(json.dumps(result,indent=2))
