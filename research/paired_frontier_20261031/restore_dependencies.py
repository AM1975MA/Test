"""Restore only the two authenticated prior conversation checkpoints.
Usage: python restore_dependencies.py --archives /path/to/downloads
No network access and no execution of downloaded code in this restoration step.
"""
from pathlib import Path
import argparse,hashlib,zipfile
R=Path(__file__).resolve().parent
SPECS=[('EU_Original39_RH50_Checkpoint_20261031.zip','826d2b03865e58317e6edb4aa920cc309d3fcfa164d3779499a648b1620b98b8','eu_original_retest_20261031','legacy'),('ETF_Rimedi_2020_2023_USA_Europa.zip','3b7a381d8f515c8fe2edb12633079bf6d5aab7c67e231671e3b2fbf43c6d18ff','risk_remedies_20261031','previous')]
def main():
 p=argparse.ArgumentParser();p.add_argument('--archives',type=Path,required=True);a=p.parse_args();dest=R/'dependencies';dest.mkdir(exist_ok=True)
 for name,sha,folder,link in SPECS:
  path=a.archives/name
  if not path.is_file():raise FileNotFoundError(path)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Input digest differs: '+name)
  with zipfile.ZipFile(path) as z:
   for info in z.infolist():
    n=Path(info.filename)
    if n.is_absolute() or '..' in n.parts:raise ValueError('Unsafe archive path')
   z.extractall(dest)
  target=dest/folder
  if not target.is_dir():raise FileNotFoundError(target)
  ln=R/link
  if ln.is_symlink():ln.unlink()
  if not ln.exists():ln.symlink_to(target,target_is_directory=True)
 old=R/'legacy';sel=old/'selected'
 if not sel.exists():sel.symlink_to('source',target_is_directory=True)
 previous=R/'previous';nested=previous/'source/eu_original_retest_20261031';nested.parent.mkdir(exist_ok=True)
 if nested.is_symlink():nested.unlink()
 if not nested.exists():nested.symlink_to(old.resolve(),target_is_directory=True)
 for name in ['native','rebuilt','calendar','analysis','verification','execution']:(R/'results'/name).mkdir(parents=True,exist_ok=True)
 print('Verified dependencies restored. Run tests before research code; do not load unknown pickle files.')
if __name__=='__main__':main()
