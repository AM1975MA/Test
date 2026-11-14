"""Resolve listing identifiers from official Borsa Italiana pages; no price-history requests."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,hashlib
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'exchange_metadata';OUT.mkdir(exist_ok=True)

def parse_identity(html,isin):
    text=BeautifulSoup(html,'html.parser').get_text(' ',strip=True)
    im=re.search(r'Codice Isin\s+([A-Z0-9]{12})',text,re.I)
    tm=re.search(r'Codice Alfanumerico\s+([A-Z0-9]{2,12})',text,re.I)
    return tm.group(1) if im and im.group(1)==isin and tm else None

def run(rec):
    isin=rec['isin'];url=f'https://www.borsaitaliana.it/borsa/etf/scheda/{isin}-ETFP.html?lang=it'
    try:
        r=requests.get(url,timeout=35);r.raise_for_status()
        (OUT/(isin+'.html')).write_text(r.text,encoding='utf-8')
        ticker=parse_identity(r.text,isin)
        return dict(rec,source_url=url,exchange_symbol=ticker or '',yahoo_symbol=(ticker+'.MI') if ticker else '',status='OFFICIAL_ISIN_MAPPING' if ticker else 'IDENTITY_NOT_RESOLVED',page_sha256=hashlib.sha256(r.content).hexdigest())
    except Exception as e:return dict(rec,source_url=url,status='FETCH_FAILED',error=repr(e))

def main():
    assert parse_identity('<div>Codice Isin IE00BFY0GT14 Codice Alfanumerico SWRD</div>','IE00BFY0GT14')=='SWRD'
    assert parse_identity('<div>Codice Isin IE00BFY0GT14 Codice Alfanumerico SWRD</div>','IE00B3YLTY66') is None
    with ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(run,pd.read_csv(ROOT/'CANDIDATES_FROZEN.csv').to_dict('records')))
    pd.DataFrame(rows).to_csv(OUT/'OFFICIAL_LISTING_MAP.csv',index=False)
    (OUT/'MANIFEST.json').write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'metadata_only':True,'candidate_roster_unchanged':True,'rows':rows},indent=2))
    print(pd.DataFrame(rows)[['isin','yahoo_symbol','status']].to_string(index=False),flush=True)
if __name__=='__main__':main()
