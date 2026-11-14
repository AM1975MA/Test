from settings import *
import data_transfer as d
import importlib.util,hashlib,json,sys
src=BASE/'source/calendar07/olc07_calendar_20261101/phases/P0/src/calendar_rebuild.py'
sys.path.insert(0,str(src.parent))
# Only extend the monthly cutoff; keep source feature/cluster algorithms unchanged.
original=src.read_text();assert original.count("'2026-06-30'")==1
code=original.replace("'2026-06-30'","'2026-10-31'")
ns={'__file__':str(src),'__name__':'olc105_calendar'};exec(compile(code,str(src), 'exec'),ns)
ns['OLD']=BASE/'source/legacy';ns['VENDOR']=VENDOR;ns['OUT']=ROOT/'data/panels';ns['OUT'].mkdir(exist_ok=True,parents=True)
ns['raw_frames']=lambda market:d.anchored_data()
(ROOT/'results/FEATURE_SOURCE_ADAPTER.json').write_text(json.dumps({'source_sha256':hashlib.sha256(original.encode()).hexdigest(),'adapted_sha256':hashlib.sha256(code.encode()).hexdigest(),'only_source_edit':'monthly final date 2026-06-30 to 2026-10-31','anchors_investable':False,'model_refit':False},indent=2))
ns['build']('EU')
