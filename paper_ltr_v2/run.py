"""Adapter del runner v1: split e metriche invariati, due learner registrati."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from paper_ltr_v2.learner import configured_fit,sha,_original

ROOT=Path(__file__).resolve().parents[1]

def verify_diagnostic(path,hashes,original_digest):
    audit=json.loads(Path(path).read_text())
    if (audit.get('status')!='PAPER_LTR_V2_NOFIT_AUDIT_COMPLETE'
        or audit.get('input_sha256')!=hashes
        or audit.get('result_sha256')!=original_digest
        or audit.get('new_fits_executed')!=0):
        raise ValueError('Audit senza fit assente o non collegato agli input originali')
    records=audit.get('validation_records',[])
    if len(records)!=90 or sum(r.get('stop_reason')=='max_epochs' for r in records)!=63:
        raise ValueError('Audit originale non copre i 90 checkpoint e i 63 arresti al limite')
    return audit

def adapter_source(source):
    """Siti esatti verificati; non si riscrive il file né il modulo v1."""
    replacements={
        'LINE = "PAPER_LTR_V1"':'LINE = "PAPER_LTR_V2"',
        'VARIANT = "LISTNET_DECILE_64"':'VARIANT = registered_variant',
        '    from paper_ltr_v1.learner import fit':'    fit = registered_fit',
        '                         [ROOT / "ranker_stability_v1/run_ranker_benchmark_full.py"]))':
        '                         [ROOT / "ranker_stability_v1/run_ranker_benchmark_full.py"] + list((ROOT / "paper_ltr_v2").glob("*.py"))))',
        '"preregistration_sha256": sha(ROOT / "paper_ltr_v1/PREREGISTRATION.md")':
        '"preregistration_sha256": sha(ROOT / "paper_ltr_v2/PREREGISTRATION.md")',
        '"determinism_scope": "solo rifit indipendente Repeat2 del 2017; nessuna certificazione degli altri anni"':
        '"determinism_scope": "nessun rifit duplicato; BUDGET300 prefisso v1 esatto, LINEAR residuo e solver deterministico"',
    }
    for old,new in replacements.items():
        if source.count(old)!=1:raise ValueError(f'Runner v1 non previsto: {old}')
        source=source.replace(old,new)
    start=source.index('            if year == 2017:\n')
    end=source.index('            qualities = {}',start)
    source=source[:start]+source[end:]
    contract_line='    (out / "INPUT_CONTRACT.json").write_text('
    if source.count(contract_line)!=1:raise ValueError('Sito contratto runner non previsto')
    source=source.replace(contract_line,'    result["original_reference"] = original_reference\n'+contract_line)
    complete='        result["status"] = LINE + "_COMPLETE"'
    if source.count(complete)!=1:raise ValueError('Sito completamento runner non previsto')
    source=source.replace(complete,
        '        metas=[t for c in result["per_year"].values() for t in c["transforms"].values()]\n'
        '        result["new_seed_fits"]=sum(t["new_seed_fits"] for t in metas)\n'
        '        result["cached_checkpoint_count"]=sum(t["reused_seeds"] for t in metas)\n'
        '        result["prefix100_ALL_PASS"]=all(t.get("prefix100_PASS",False) for t in metas) if VARIANT=="BUDGET300" else None\n'+complete)
    return source

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',choices=['BUDGET300','LINEAR'],required=True)
    parser.add_argument('--original',required=True)
    parser.add_argument('--diagnostic',required=True)
    parser.add_argument('--baseline',required=True)
    for i in (1,2,3):parser.add_argument(f'--r{i}',required=True)
    parser.add_argument('--out',required=True)
    parser.add_argument('--years',default='2017,2018,2019,2020,2021,2022,2023,2024,2025,2026')
    args=parser.parse_args()
    original,result=_original(args.original)
    hashes={str(i):sha(Path(getattr(args,f'r{i}'))/'TI_COMPACT.parquet') for i in (1,2,3)}
    if result.get('input_sha256')!=hashes:raise ValueError('Input diversi dall’originale ListNet')
    verify_diagnostic(args.diagnostic,hashes,sha(original/'RESULT.json'))
    path=ROOT/'paper_ltr_v1/run.py'
    if result.get('sources',{}).get('paper_ltr_v1/run.py')!=sha(path):
        raise ValueError('Runner originale diverso dal fit conservato')
    source=adapter_source(path.read_text())
    namespace=dict(__name__='paper_ltr_v2_registered_runner',__file__=str(path),
        registered_variant=args.variant,registered_fit=configured_fit(args.variant,original),
        original_reference=dict(result_sha256=sha(original/'RESULT.json'),
                                diagnostic_sha256=sha(args.diagnostic),
                                original_runner_sha256=sha(path),
                                variant=args.variant,original_fit_run=38179662587,
                                independent_determinism_refits_executed=0))
    exec(compile(source,str(path), 'exec'),namespace)
    previous=sys.argv
    sys.argv=[str(path),'--baseline',args.baseline,'--out',args.out,'--years',args.years]
    for i in (1,2,3):sys.argv.extend([f'--r{i}',getattr(args,f'r{i}')])
    try:namespace['main']()
    finally:sys.argv=previous

if __name__=='__main__':main()
