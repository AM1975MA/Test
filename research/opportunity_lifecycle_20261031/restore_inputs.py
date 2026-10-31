"""Restore the exact previously delivered archives; no network access."""
from pathlib import Path
import argparse,hashlib,json,zipfile,subprocess,sys
R=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--archives',type=Path,required=True);a=p.parse_args()
    hashes=json.loads((R/'REQUIRED_ARCHIVES.json').read_text())
    for name,expected in hashes.items():
        source=a.archives/name
        if not source.is_file():raise FileNotFoundError(source)
        if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise ValueError('Unexpected source archive: '+name)
    dest=R/'inputs/frontier';dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.archives/'ETF_Frontiera_USA_Europa_Risultati_20261031.zip') as z:
        for n in z.namelist():
            path=Path(n)
            if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive member')
            if '/src/' in n or '/tests/' in n or '/results/calendar/' in n or '/results/rebuilt/' in n or n.endswith(('DELIVERY_MANIFEST.json','README.md','restore_dependencies.py')):
                out=dest/path.relative_to('paired_frontier_20261031');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(n))
    subprocess.run([sys.executable,str(dest/'restore_dependencies.py'),'--archives',str(a.archives.resolve())],check=True)
    print('Authenticated input archives restored; run tests and diagnostic scripts separately.')
if __name__=='__main__':main()
