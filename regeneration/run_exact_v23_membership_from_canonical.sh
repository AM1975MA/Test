#!/usr/bin/env bash
set -euo pipefail

rm -rf upstream outer pkg prior EXACT_V23_CANONICAL || true
mkdir -p upstream/gzpayload upstream/reconstruction prior/titanium_retrained_output

# Reconstruct verified source modules.
for f in gz_00.b64 gz_01.b64 gz_02.b64; do
  curl -fsSL "https://raw.githubusercontent.com/AM1975MA/Test/titanium-source-faithful-20260803/gzpayload/$f" -o "upstream/gzpayload/$f"
done
cat upstream/gzpayload/gz_*.b64 | base64 -d | gzip -dc > upstream/titanium_retrained_current_data_audit.py
echo '76b5da95c865a069d967189d61b1c8df3338eacc5a0e8941e8ee7025c42caf60  upstream/titanium_retrained_current_data_audit.py' | sha256sum -c -

for f in rv5_00.b64 rv5_01.b64 rv5_02.b64 rv5_04.b64; do
  curl -fsSL "https://raw.githubusercontent.com/AM1975MA/Test/titanium-reconstruction-v5-20260803/reconstruction/$f" -o "upstream/reconstruction/$f"
done
for f in rv5_03a.b64 rv5_03b.b64 rv5_03c.b64 rv5_03d.b64; do
  curl -fsSL "https://raw.githubusercontent.com/AM1975MA/Test/titanium-reconstruction-v5-20260803/reconstruction/$f" -o "upstream/reconstruction/$f"
done
cat upstream/reconstruction/rv5_00.b64 upstream/reconstruction/rv5_01.b64 upstream/reconstruction/rv5_02.b64 upstream/reconstruction/rv5_03a.b64 upstream/reconstruction/rv5_03b.b64 upstream/reconstruction/rv5_03c.b64 upstream/reconstruction/rv5_03d.b64 upstream/reconstruction/rv5_04.b64 | base64 -d | gzip -dc > upstream/titanium_reconstruction_v5.py
echo 'ba99f9ce08d96e6b56567d44bf18b5caa7a76ccf13a7d44546e6d1416d79d65a  upstream/titanium_reconstruction_v5.py' | sha256sum -c -
sed -i 's/@njit(cache=True)/@njit(cache=False)/g; s/@njit(parallel=True,cache=True)/@njit(parallel=True,cache=False)/g' upstream/titanium_reconstruction_v5.py

# Apply the recovered canonical V2.3 membership generator only.
python regeneration/patch_v23_generator.py
python -m py_compile upstream/titanium_retrained_current_data_audit.py upstream/titanium_reconstruction_v5.py regeneration/regenerate_live_package.py

# Reuse the exact OHLCV matrices from the canonical package artifact.
curl -L --fail -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/AM1975MA/Test/actions/artifacts/9007704034/zip -o outer.zip
mkdir outer && unzip -q outer.zip -d outer
inner=$(find outer -name 'METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE.zip' -print -quit)
test -n "$inner"
mkdir pkg && unzip -q "$inner" -d pkg
canon=$(find pkg -type d -name 'METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE' -print -quit)
test -n "$canon"
for f in OPEN HIGH LOW CLOSE VOLUME; do
  cp "$canon/data/${f}.parquet" "prior/titanium_retrained_output/${f}.parquet"
done
sha256sum prior/titanium_retrained_output/{OPEN,HIGH,LOW,CLOSE,VOLUME}.parquet > INPUT_CANONICAL_OHLCV_SHA256.txt

# Full 360-tree / 3-seed / 500-basket regeneration, changing only membership.
python regeneration/regenerate_live_package.py \
  --base-module upstream/titanium_retrained_current_data_audit.py \
  --v5-module upstream/titanium_reconstruction_v5.py \
  --data-dir prior/titanium_retrained_output \
  --output-parent . \
  --downvol-mode downside_rms \
  --n-estimators 360 \
  --n-baskets 500 | tee EXACT_V23_CANONICAL_RUN_LOG.txt

root=METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE
test -s "$root/panels/V23_BASKET_MEMBERSHIP.csv"
test -s "$root/backtest/BASKET_RESULTS_500.csv"
test -s "$root/backtest/GLOBAL_SCORECARD.csv"

python - <<'PY'
import json, pandas as pd
from pathlib import Path
root=Path('METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE')
m=pd.read_csv(root/'panels/V23_BASKET_MEMBERSHIP.csv')
sz=m.groupby('basket').ticker.nunique()
assert len(sz)==500 and sz.eq(24).all(), (len(sz),sz.min(),sz.max())
r=pd.read_csv(root/'backtest/BASKET_RESULTS_500.csv')
g=pd.read_csv(root/'backtest/GLOBAL_SCORECARD.csv')
assert r.basket.nunique()==500
out={
 'membership_baskets':int(len(sz)),
 'membership_size':int(sz.iloc[0]),
 'base_mean_cagr':float(r.loc[r.strategy.eq('BASE'),'cagr'].mean()),
 'direct_mean_cagr':float(r.loc[r.strategy.eq('DIRECT'),'cagr'].mean()),
 'router_mean_cagr':float(r.loc[r.strategy.eq('ROUTER'),'cagr'].mean()),
 'router_median_cagr':float(r.loc[r.strategy.eq('ROUTER'),'cagr'].median()),
 'router_p05':float(r.loc[r.strategy.eq('ROUTER'),'cagr'].quantile(.05)),
 'router_p95':float(r.loc[r.strategy.eq('ROUTER'),'cagr'].quantile(.95)),
 'global':g.set_index('strategy').to_dict('index'),
}
Path('EXACT_V23_CANONICAL_VALIDATION.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
PY

sha256sum "$root/panels/V23_BASKET_MEMBERSHIP.csv" > V23_BASKET_MEMBERSHIP_SHA256.txt
sha256sum METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE.zip > METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE_SHA256.txt
