"""Package frozen research and its minimal prior-study dependencies.

No financial result is recomputed or edited. Run after final documentation QA.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import zipfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def package(root, destination):
    root = Path(root).resolve()
    previous = root.parent / 'olc108'
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = {}

    def add(path, archive_path):
        if not path.is_file():
            raise FileNotFoundError(path)
        if archive_path in entries:
            assert entries[archive_path] == path
        entries[archive_path] = path

    for path in sorted(root.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            add(path, 'olc109/' + path.relative_to(root).as_posix())

    liquidity = json.loads((root / 'data/LIQUIDITY_MANIFEST.json').read_text())
    assert len(liquidity['sources']) == 2096
    for source in liquidity['sources']:
        path = previous / source['price_file']
        assert digest(path) == source['sha256'], path
        add(path, 'olc108/' + source['price_file'])

    for name in ('data/UNIVERSE_COVERAGE.csv', 'data/ADJUSTMENT_ANOMALIES_REVIEW.csv',
                 'results/V3_SOURCE_SCOPE_CHECK.json',
                 'superseded_v2/results/V2_HELD_SOURCE_REVIEW.csv'):
        add(previous / name, 'olc108/' + name)

    baseline_count = 0
    for arm in ('LEADERS', 'DUAL_SELECTIVE_21', 'PASSIVE'):
        for scenario in ('BASE', 'ZERO_COST', 'DOUBLE_COST', 'LAG1', 'LAG2'):
            folder = previous / 'results/XETRA_EUR_ETF' / f'{arm}__MONTHLY__RAW__{scenario}'
            if arm == 'PASSIVE' and scenario != 'BASE':
                assert not (folder / 'METRICS.json').exists()
                continue
            for name in ('METRICS.json', 'DAILY.csv.gz', 'ORDERS.csv.gz',
                         'INSTRUCTIONS.csv.gz', 'DECISIONS.npz', 'DECISIONS.csv'):
                path = folder / name
                add(path, 'olc108/' + path.relative_to(previous).as_posix())
            baseline_count += 1
    assert baseline_count == 11

    files = {name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
             for name, path in sorted(entries.items())}
    manifest = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'description': 'OLC109 complete study plus minimal OLC108 support dependencies',
        'objective': 'CAGR >= 30% BASE; drawdown and Calmar descriptive; protection deferred',
        'financial_paths': 200,
        'strategy_configurations': 40,
        'prior_baseline_paths': baseline_count,
        'prior_source_price_csvs': len(liquidity['sources']),
        'full_olc108_acquisition_pipeline_included': False,
        'bytecode_excluded': True,
        'manifest_self_excluded': True,
        'files': files,
    }
    payload = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6,
                         allowZip64=True) as archive:
        for name, path in sorted(entries.items()):
            compression = zipfile.ZIP_STORED if path.suffix in {'.gz', '.npz', '.png'} else zipfile.ZIP_DEFLATED
            archive.write(path, name, compress_type=compression)
        archive.writestr('BUNDLE_MANIFEST.json', payload)

    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(entries) | {'BUNDLE_MANIFEST.json'}
        for name, metadata in files.items():
            with archive.open(name) as handle:
                h = hashlib.sha256()
                count = 0
                for block in iter(lambda: handle.read(1 << 20), b''):
                    h.update(block)
                    count += len(block)
            assert h.hexdigest() == metadata['sha256'], name
            assert count == metadata['bytes'], name
    verification = {
        'status': 'PASS_COMPLETE_ARCHIVE_CRC_AND_EVERY_FILE_SHA256',
        'archive': str(destination),
        'archive_bytes': destination.stat().st_size,
        'archive_sha256': digest(destination),
        'files_checked': len(files),
        'prior_baseline_paths': baseline_count,
        'prior_source_price_csvs': len(liquidity['sources']),
    }
    destination.with_suffix('.verification.json').write_text(json.dumps(verification, indent=2) + '\n')
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root')
    parser.add_argument('destination')
    args = parser.parse_args()
    package(args.root, args.destination)
