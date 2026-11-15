"""Prove the independent audit rejects materially corrupted saved evidence.

Each mutation is applied only in memory; frozen results are never changed.
"""
from copy import deepcopy
from pathlib import Path
import json
import numpy as np
from threadpoolctl import threadpool_limits

from run_independent_audit import load_reference
from account_reference import AccountAudit, read_path, json_value


def run(root):
    root = Path(root).resolve()
    reference = load_reference(root)
    path_id = 'EXIT21_STAGED_FRESHW__LAG2'
    original = read_path(root/'results'/path_id)
    baseline = AccountAudit(reference,original).run()[0]
    rows = []

    def rejected(label, mutation):
        candidate = deepcopy(original)
        mutation(candidate)
        try:
            AccountAudit(reference,candidate).run()
        except AssertionError as failure:
            rows.append(dict(test=label,status='REJECTED',assertion=str(failure)))
        else:
            raise AssertionError(('MATERIAL_TAMPER_ACCEPTED',label))

    def alter_target(data):
        target = json.loads(data['instructions'].loc[0,'target_weights'])
        j = next(i for i,value in enumerate(target) if value>0)
        target[j] -= .05
        data['instructions'].loc[0,'target_weights'] = json.dumps(target)
    def alter_raw(data):
        raw = data['decision_arrays']['raw_weights']
        j = int(np.flatnonzero(raw[0]>0)[0]);raw[0,j] -= .05
    def alter_mask(data):
        for i,row in data['instructions'].iterrows():
            mask = json_value(row['action_indices'])
            if mask is not None:
                j = next(j for j in range(reference.n) if j not in mask)
                data['instructions'].loc[i,'action_indices'] = json.dumps(mask+[j])
                return
        raise RuntimeError('No targeted action in fixture')
    def alter_state(data):
        data['trace'].loc[0,'state'] = 'REBOUND' if data['trace'].loc[0,'state'] != 'REBOUND' else 'NORMAL'
    def alter_probe(data):
        indices = data['trace'].index[data['trace'].first_fill_idx.notna()]
        assert len(indices)
        i = indices[0];data['trace'].loc[i,'first_fill_idx'] = data['trace'].loc[i,'entry_signal']
    def alter_busy(data):
        indices = data['trace'].index[data['trace'].busy]
        assert len(indices)
        data['trace'].loc[indices[0],'busy'] = False
    def alter_quantity(data):
        data['orders'].loc[0,'quantity'] *= 1.01
    def alter_cost(data):
        data['orders'].loc[0,'cost'] += 1.
    def alter_date(data):
        data['orders'].loc[0,'execution_idx'] = data['orders'].loc[0,'signal_idx']
    def alter_cash(data):
        data['daily'].loc[0,'cash'] += 10.

    for label,mutation in [('nominal_raw_selector_target',alter_raw),('executable_instruction_target',alter_target),
                           ('immutable_action_mask',alter_mask),('daily_slot_state',alter_state),
                           ('probe_fill_before_execution',alter_probe),('outstanding_book_flag',alter_busy),
                           ('order_quantity',alter_quantity),('order_fee',alter_cost),
                           ('same_close_execution',alter_date),('account_cash',alter_cash)]:
        rejected(label,mutation)
    report = dict(status='PASS_ALL_MATERIAL_TAMPERS_REJECTED',path_id=path_id,
                  clean_path_status=baseline['status'],tests=len(rows),production_results_modified=False,
                  results=rows)
    (root/'validation/TAMPER_REJECTIONS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):
        run(Path(__file__).resolve().parents[1])
