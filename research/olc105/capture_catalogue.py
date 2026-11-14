"""Metadata-only capture. Does not request market returns or produce trading signals."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, json, re
import requests
import fitz

URL = 'https://assets.traderepublic.com/assets/files/IT/Instrument_Universe_IT_en.pdf'

def parse_page(text, page):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    out = []
    for i, line in enumerate(lines):
        m = re.match(r'^([A-Z]{2}[A-Z0-9]{9}[0-9])(?:\s+(.*))?$', line)
        if m:
            name = (m.group(2) or (lines[i+1] if i+1 < len(lines) else '')).strip(' -—')
            out.append({'isin':m.group(1), 'name':name, 'pdf_page':page})
    return out

def main():
    assert parse_page('IE00BFY0GT14\nMSCI World USD (Acc)',1)[0]['name'] == 'MSCI World USD (Acc)'
    assert parse_page('NOT_AN_ISIN\nSomething',1) == []
    out=Path('olc105_catalogue');out.mkdir(exist_ok=True)
    r=requests.get(URL,timeout=90);r.raise_for_status()
    assert r.content.startswith(b'%PDF'), 'Not a PDF'
    (out/'TR_Instrument_Universe_IT.pdf').write_bytes(r.content)
    doc=fitz.open(stream=r.content,filetype='pdf');rows=[];texts=[]
    for j,p in enumerate(doc):
        text=p.get_text(sort=True);texts.append(f'\n===PAGE {j+1}===\n'+text)
        rows.extend(parse_page(text,j+1))
    (out/'catalogue_text.txt').write_text(''.join(texts),encoding='utf-8')
    with (out/'catalogue.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['isin','name','pdf_page']);w.writeheader();w.writerows(rows)
    assert len(rows)>1000, f'Incomplete catalogue parse: {len(rows)}'
    manifest={'status':'METADATA_ONLY_CAPTURE_PASS','downloaded_at_utc':datetime.now(timezone.utc).isoformat(),
      'url':URL,'last_modified':r.headers.get('Last-Modified'),'pages':len(doc),'rows':len(rows),
      'unique_isins':len(set(x['isin'] for x in rows)),
      'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},
      'caveat':'Published Italy catalogue only; account-specific and historical availability not certified; no price outcomes requested.'}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)
if __name__=='__main__':main()
