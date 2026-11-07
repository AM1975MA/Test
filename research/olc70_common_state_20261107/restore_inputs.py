#!/usr/bin/env python3
"""Restore frozen OLC67 native engine from bundled ZIP after checking digests."""
from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'inputs'
HASHES={
 'OLC67_Strategia_ETF_Verificata.zip':'dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4',
 'OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv':'b7911d1346f6d78a19513547fd4b91b8a68a1806b2332f3a95815fcaf2caf330',
 'OLC67_NATIVE_DEPENDENCIES.zip':'3fc500be03c53b45a5a04325d8a982a4baaad085704a66cda617cde3e50935d3',
}
for name,expected in HASHES.items():
 path=INPUT/name
 assert path.exists(),f'Input missing: {path}'
 h=sha256(path.read_bytes()).hexdigest()
 assert h==expected,f'Input SHA256 mismatch: {name}: {h}'
for source_zip in ['OLC67_Strategia_ETF_Verificata.zip','OLC67_NATIVE_DEPENDENCIES.zip']:
 with ZipFile(INPUT/source_zip) as z:
  for obj in z.infolist():
   target=(INPUT/obj.filename).resolve()
   if not target.is_relative_to(INPUT.resolve()):raise ValueError('Unsafe zip path')
  z.extractall(INPUT)
assert (INPUT/'OLC67/run_olc67.py').is_file()
assert (INPUT/'OLC67/native/olc19_combined_risk_20261102/src/combined_engine.py').is_file()
print('Original OLC67 native OLC19 source restored with verified hashes at',INPUT)