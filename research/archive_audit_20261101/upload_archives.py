"""Verify and optionally upload ETF research archives to the existing archival release.
Usage: python upload_archives.py DIRECTORY [--upload]
Python >=3.10. Upload requires an authenticated GitHub CLI. Default: verify only.
Never overwrites a remote asset, changes main, or uses a third-party public host.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,shutil,subprocess,sys
from pathlib import Path
REPO='AM1975MA/Test'
TAG='research-preserved-20261101'

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def validate_local(path:Path,expected:dict)->str:
    if not path.is_file():raise FileNotFoundError(path)
    if path.stat().st_size!=int(expected['bytes']):raise ValueError(f'Size mismatch: {path.name}')
    actual=sha256(path)
    if actual!=expected['sha256']:raise ValueError(f'SHA256 mismatch: {path.name}')
    return actual

def equal_remote(asset:dict,expected:dict)->bool:
    return asset.get('size')==int(expected['bytes']) and asset.get('digest')=='sha256:'+expected['sha256']

def gh(*args:str)->str:
    return subprocess.check_output(['gh',*args],text=True,stderr=subprocess.PIPE)

def release_assets()->dict:
    release=json.loads(gh('api',f'repos/{REPO}/releases/tags/{TAG}'))
    return {a['name']:a for a in release['assets']}

def already_tracked(record:dict)->bool:
    return record.get('remote_status',record.get('status'))=='EXACT_ARCHIVE_TRACKED'

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('LOCAL_ARCHIVES_SHA256.csv'))
    parser.add_argument('--upload',action='store_true',help='Explicitly request authenticated uploads; default only verifies local bytes.')
    args=parser.parse_args()
    records=list(csv.DictReader(args.manifest.open(encoding='utf-8')))
    if args.upload:
        if not shutil.which('gh'):raise RuntimeError('GitHub CLI not found; no upload performed.')
        gh('auth','status');assets=release_assets()
    else:assets={}
    status=[]
    for e in records:
        name=e['archive'];row={'archive':name,'sha256':e['sha256'],'state':'pending'}
        if already_tracked(e):
            row['state']='already_byte_verified_in_tracked_snapshot';status.append(row);continue
        p=args.directory/name
        try:
            validate_local(p,e)
            if not args.upload:row['state']='local_verified_upload_not_requested'
            elif name in assets:
                if not equal_remote(assets[name],e):raise ValueError(f'Existing asset differs or has no digest: {name}; not overwritten')
                row['state']='remote_digest_verified'
            else:
                gh('release','upload',TAG,str(p),'--repo',REPO)
                assets=release_assets()
                if name not in assets or not equal_remote(assets[name],e):raise ValueError('Remote SHA256 verification failed after upload')
                row['state']='uploaded_and_remote_digest_verified'
        except (OSError,ValueError,subprocess.CalledProcessError) as ex:
            row['state']='incomplete';row['error']=str(ex)
        status.append(row);print(name,row['state'],flush=True)
    dest=args.directory/'GITHUB_UPLOAD_STATUS.json'
    dest.write_text(json.dumps({'repository':REPO,'release':TAG,'upload_requested':args.upload,'files':status},indent=2),encoding='utf-8')
    return 1 if any(x['state']=='incomplete' for x in status) else 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:print(str(exc),file=sys.stderr);sys.exit(2)
