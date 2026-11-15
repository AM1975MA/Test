"""Protocol-derived OLC110 two-slot policy; no production imports.

A separate account reconstruction supplies actual quantities, completed buys,
cash and outstanding instructions. This policy never reads a recorded target,
trade, state, or trace to choose an action. Recorded output is compared later.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, asdict
from collections import Counter
import numpy as np


@dataclass
class Slot:
    primary: int | None
    asset: int | None
    state: str
    level: float
    width: float | None
    entry_signal: int | None
    first_fill_idx: int | None
    new_assignment_at: int
    vacancy_confirmed: bool


class PolicyReference:
    def __init__(self, selector, arm):
        self.s = selector
        self.p, self.f, self.n = selector.p, selector.f, selector.n
        self.arm = arm
        self.exit_rule = 'EXIT63' if arm.startswith('EXIT63') else 'TRAIL15' if arm.startswith('TRAIL15') else 'VOLTRAIL' if arm.startswith('VOLTRAIL') else 'EXIT21'
        self.entry_rule = 'MONTHLY' if arm.endswith('_MONTHLY') else 'SLOW' if arm.endswith('_SLOW') else 'FAST' if arm.endswith('_FAST') else 'STAGED'
        self.fresh = 'W' if arm.endswith('_FRESHW') else 'D' if arm.endswith('_FRESHD') else None
        self.slots = []
        self.requested = np.zeros(self.n)
        self.counts = Counter()
        self.events = []

    def width(self, k, j):
        deviation = self.f['sigma21'][k,j]
        return float(np.clip(2.5 * np.sqrt(5) * deviation, .05, .20)) if np.isfinite(deviation) else .20

    def observed(self, k, j):
        return j is not None and bool(self.p['observed'][k,j])

    def exit(self, k, j, frozen=None):
        if not self.observed(k, j):
            return False
        f, c = self.f, self.f['C'][k,j]
        if self.exit_rule == 'EXIT21':
            return bool(c < f['sma21'][k,j] and f['m5'][k,j] < 0)
        if self.exit_rule == 'EXIT63':
            return bool(c < f['sma63'][k,j] and f['m21'][k,j] < 0)
        width = .15 if self.exit_rule == 'TRAIL15' else self.width(k,j) if frozen is None else frozen
        return bool(c / f['peak63'][k,j] - 1 <= -width)

    def slow(self, k, j, frozen=None):
        if not self.observed(k,j):
            return False
        f = self.f
        return bool(f['C'][k,j] > f['sma63'][k,j] and f['m21'][k,j] > 0
                    and not self.exit(k,j,frozen)
                    and (self.exit_rule != 'VOLTRAIL' or not self.exit(k,j,self.width(k,j))))

    def fast(self, k, j):
        if not self.observed(k,j):
            return False
        f = self.f
        return bool(f['C'][k,j] > f['high5_prev'][k,j] and f['C'][k,j] > f['sma10'][k,j] and f['m5'][k,j] > 0)

    def failed_probe(self, k, j):
        return bool(self.observed(k,j) and self.f['C'][k,j] < self.f['sma10'][k,j] and self.f['m5'][k,j] < 0)

    def new_assignment(self, k, j):
        if j is None:
            return Slot(None, None, 'CASH', 0., None, None, None, k, True)
        width = self.width(k,j)
        denied = not self.observed(k,j) or self.exit(k,j,width)
        if denied:
            self.counts['blocked_new_assignments'] += 1
        return Slot(j,j,'CASH' if denied else 'NORMAL',0. if denied else 1.,width,None if denied else k,None,k,False)

    def update_month(self, k):
        _, metadata = self.s.selection(k)
        previous = deepcopy(self.slots)
        retained, refreshed = set(), []
        for asset in metadata['selected_indices'][:2]:
            owners = [(i,slot) for i,slot in enumerate(previous) if i not in retained and slot.asset == asset]
            owners.sort(key=lambda pair: (0 if pair[1].level > 0 else 1,
                                           1 if pair[1].vacancy_confirmed else 0,
                                           0 if pair[1].primary == asset else 1,pair[0]))
            if owners:
                old_position, slot = owners[0]
                retained.add(old_position)
                slot.primary = asset
                self.counts['monthly_asset_state_retained'] += 1
                self.counts['monthly_cash_state_retained'] += int(slot.state == 'CASH')
                self.counts['monthly_probe_state_retained'] += int(slot.state == 'REBOUND')
            else:
                slot = self.new_assignment(k,asset)
            refreshed.append(slot)
        while len(refreshed) < 2:
            refreshed.append(self.new_assignment(k,None))
        self.slots = refreshed
        return deepcopy(metadata)

    def candidate(self, k, pos, units):
        held = set(map(int, np.flatnonzero(units > 1e-10)))
        exclusions, comparisons = set(held), set(held)
        for otherpos, other in enumerate(self.slots):
            if otherpos == pos or other.asset is None:
                continue
            exclusions.add(other.asset)
            if other.level > 0:
                comparisons.add(other.asset)
        for asset in self.s.opportunity_pool(k, True):
            if asset in exclusions:
                self.counts['fresh_held_or_assigned_exclusions'] += 1
                continue
            compatible = True
            for other in comparisons:
                self.counts['fresh_pair_correlations_checked'] += 1
                if self.s.correlation(k,asset,other) > .85 + 1e-12:
                    self.counts['fresh_correlation_rejections'] += 1
                    compatible = False
                    break
            if compatible:
                return asset
        return None

    def set_entry(self, slot, k, asset, mode, level):
        slot.asset, slot.state, slot.level = asset, mode, level
        slot.entry_signal, slot.first_fill_idx, slot.vacancy_confirmed = k, None, False
        if mode == 'NORMAL':
            slot.width = self.width(k,asset)

    def decide(self, k, current, units, cash, nav, last_buy, pending, queued, *, initial=False, scheduled=False):
        full = initial or scheduled
        busy = pending is not None or bool(queued)
        selection = self.update_month(k) if full else {}
        assert len(self.slots) == 2
        changes = []
        classes = {category:set() for category in ('exit','entry','confirm','fresh')}
        start_states = deepcopy(self.slots)
        for position, slot in enumerate(self.slots):
            asset = slot.asset
            if asset is None:
                continue
            if slot.state == 'NORMAL' and self.exit(k,asset,slot.width):
                slot.state, slot.level, slot.first_fill_idx, slot.vacancy_confirmed = 'CASH', 0., None, False
                changes.append(f'EXIT:{position}:{asset}')
                classes['exit'].add(asset)
                self.counts['normal_exits'] += 1
            elif slot.state == 'REBOUND':
                if slot.first_fill_idx is None and units[asset] > 1e-10 and last_buy[asset] >= slot.entry_signal + 1:
                    slot.first_fill_idx = int(last_buy[asset])
                    self.counts['actual_probe_fills_identified'] += 1
                if self.failed_probe(k,asset):
                    slot.state, slot.level, slot.first_fill_idx, slot.vacancy_confirmed = 'CASH', 0., None, False
                    changes.append(f'REBOUND_EXIT:{position}:{asset}')
                    classes['exit'].add(asset)
                    self.counts['probe_exits'] += 1
                elif slot.first_fill_idx is not None and k > slot.first_fill_idx and self.slow(k,asset,slot.width):
                    assert slot.first_fill_idx >= slot.entry_signal + 1
                    slot.state, slot.level, slot.width = 'NORMAL', 1., self.width(k,asset)
                    changes.append(f'CONFIRM:{position}:{asset}')
                    classes['confirm'].add(asset)
                    self.counts['confirmations_after_actual_fill'] += 1
                elif self.slow(k,asset,slot.width):
                    self.counts['premature_confirmations_suppressed'] += 1

        for slot in self.slots:
            if slot.state == 'CASH' and not busy and (slot.asset is None or units[slot.asset] <= 1e-10):
                if not slot.vacancy_confirmed:
                    self.counts['actual_vacancies_confirmed'] += 1
                slot.vacancy_confirmed = True
        spendable = cash > max(1e-8, .03 * nav)
        for position, slot in enumerate(self.slots):
            if slot.state != 'CASH':
                continue
            if not spendable or busy:
                self.counts['cash_admission_blocked_busy' if busy else 'cash_admission_blocked_budget'] += 1
                continue
            if slot.new_assignment_at == k:
                continue
            previous_asset = slot.asset
            if not slot.vacancy_confirmed or previous_asset in classes['exit']:
                self.counts['cash_admission_blocked_unsold'] += 1
                continue
            base = slot.primary
            occupied_elsewhere = base is not None and any(i != position and other.asset == base and other.level > 0 for i,other in enumerate(self.slots))
            frozen = slot.width if base == slot.asset else None
            slow_allowed = (self.entry_rule != 'MONTHLY' or full) and not occupied_elsewhere and self.slow(k,base,frozen)
            fast_allowed = self.entry_rule in ('FAST','STAGED') and not occupied_elsewhere and self.fast(k,base)
            if slow_allowed:
                self.set_entry(slot,k,base,'NORMAL',1.)
                changes.append(f'REENTER_SLOW:{position}:{base}')
                classes['entry'].add(base)
                self.counts['slow_cash_reentries'] += 1
            elif fast_allowed:
                self.set_entry(slot,k,base,'REBOUND',1. if self.entry_rule == 'FAST' else .5)
                changes.append(f'REENTER_FAST:{position}:{base}')
                classes['entry'].add(base)
                self.counts['fast_cash_reentries'] += 1
            elif self.fresh is not None and not full and (self.fresh == 'D' or self.s.weekly[k]):
                fresh = self.candidate(k,position,units)
                if fresh is not None:
                    self.set_entry(slot,k,fresh,'REBOUND',.5)
                    changes.append(f'FRESH:{position}:{fresh}')
                    classes['fresh'].add(fresh)
                    self.counts['fresh_half_slot_entries'] += 1
                    self.counts['fresh_after_primary_occupied_elsewhere'] += int(occupied_elsewhere)

        intended = np.zeros(self.n)
        for slot in self.slots:
            if slot.asset is not None and slot.level > 0:
                intended[slot.asset] += .5 * slot.level
        assert intended.max() <= .5 + 1e-12 and intended.sum() <= 1 + 1e-12, 'DUPLICATE_ACTIVE_SLOTS'
        affected = np.abs(intended - self.requested) > 1e-12
        issue = full or (not busy and bool(affected.any()))
        reason = ('INITIAL' if initial else 'SCHEDULED' if full else
                  'MIXED' if sum(bool(value) for value in classes.values()) > 1 else
                  'EXIT' if classes['exit'] else 'REENTRY' if classes['entry'] else
                  'CONFIRM' if classes['confirm'] else 'FRESH' if classes['fresh'] else 'DEFERRED_STATE')
        answer = None
        if issue:
            reduction = not full and bool(np.all(intended[affected] <= current[affected] + 1e-12))
            # The raw vector records nominal slot intentions; only the action
            # mask authorizes changes. Execution restores untouched weights.
            raw = intended.copy()
            answer = dict(raw=raw, nominal=intended.copy(), action_mask=None if full else affected.copy(),
                          sell_only=reduction, force=bool(initial or reduction or classes['exit']), reason=reason,
                          meta=dict(arm=self.arm, changes=changes, slots=[asdict(slot) for slot in self.slots],
                                    book_busy=busy, selection=selection))
            self.requested = intended.copy()
            self.counts['full_instructions' if full else 'targeted_instructions'] += 1
        elif busy and affected.any():
            self.counts['busy_events_suppressed'] += 1
        assert not (busy and not full and issue), 'BUSY_BOOK_TARGETED_ACTION'

        trace = []
        for pos, slot in enumerate(self.slots):
            asset = slot.asset
            trace.append(dict(k=k, date=str(self.p['dates'][k].date()), arm=self.arm, slot=pos,
                              primary_index=slot.primary, asset_index=asset,
                              primary_isin=None if slot.primary is None else str(self.p['names'][slot.primary]),
                              asset_isin=None if asset is None else str(self.p['names'][asset]),
                              state=slot.state, level=slot.level, nominal_weight=.5*slot.level,
                              actual_weight=0. if asset is None else float(current[asset]),
                              first_fill_idx=slot.first_fill_idx, entry_signal=slot.entry_signal, width=slot.width,
                              vacancy_confirmed=slot.vacancy_confirmed,
                              busy=busy, scheduled=full, action_emitted=issue, reason=reason,
                              observed=self.observed(k,asset), exit_condition=self.exit(k,asset,slot.width),
                              slow_condition=self.slow(k,asset,slot.width), fast_condition=self.fast(k,asset),
                              rebound_failure=self.failed_probe(k,asset)))
            if (start_states[pos].state, start_states[pos].asset, start_states[pos].level) != (slot.state,slot.asset,slot.level):
                self.events.append(dict(k=k, date=str(self.p['dates'][k].date()), slot=pos,
                                        previous_asset=start_states[pos].asset, previous_state=start_states[pos].state,
                                        asset=slot.asset, state=slot.state, level=slot.level, busy=busy,
                                        first_fill_idx=slot.first_fill_idx, action_emitted=issue, reason=reason))
        return answer, trace
