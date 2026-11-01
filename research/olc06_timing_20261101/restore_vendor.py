"""Restore only the exact supplied checkpoint; never download fresh market prices."""
from pathlib import Path
import hashlib,json,sys,zipfile,subprocess
ROOT=Path(__file__).resolve().parent
EXPECTED='bf81a855e127883ac671dced7ac8dcf95fbe3f08a0339afd537c1c19a4ab6d8d'
def main():
    if len(sys.argv)!=2:raise SystemExit('Usage: python restore_vendor.py /path/OLC05_Transizioni_Checkpoint_20261031.zip')
    archive=Path(sys.argv[1])
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Archive digest mismatch')
    destination=ROOT/'vendor';destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if any(Path(n).is_absolute() or '..' in Path(n).parts for n in z.namelist()):raise ValueError('Unsafe archive member')
        z.extractall(destination)
    source=destination/'olc05_transitions_20261031';count=0
    for manifest in ['DELIVERY_MANIFEST.json','CHECKPOINT_MANIFEST.json']:
        for row in json.loads((source/manifest).read_text())['files']:
            p=source/row['path']
            if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Member digest mismatch: '+str(p))
            count+=1
    subprocess.run([sys.executable,str(ROOT/'build_engine.py')],check=True)
    print('Verified',count,'source and delivery files')
if __name__=='__main__':main()
