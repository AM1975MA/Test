"""Independent end-to-end OLC110 account, instruction and policy audit.

Order sizing and accounting were adapted from the independent OLC109 audit.
No production engine/core/policy/selector imports are allowed. Every action is
re-derived from prices and independently rebuilt account state before checking
saved instructions, targets, quantities, cost, dates, cash and NAV. After sizing
agrees, exact serialized fill quantities/notionals are posted to the ledger to
preserve its floating-point zero residues; targets/states are never an oracle.
Fees, quote validity and all account valuations are recalculated independently.
"""
from __future__ import annotations

from collections import deque, Counter
from pathlib import Path
import json
import numpy as np
import pandas as pd

from signal_reference import ARMS, SCENARIOS
from policy_reference import PolicyReference


def json_value(value):
    return json.loads(value) if isinstance(value,str) else None if pd.isna(value) else value


def compare(actual, expected, where):
    if isinstance(expected, dict):
        assert isinstance(actual,dict), ('MAPPING',where)
        assert set(expected) <= set(actual), ('MISSING_KEYS',where,set(expected)-set(actual))
        for key,value in expected.items():
            compare(actual[key],value,(where,key))
    elif isinstance(expected,(list,tuple)):
        assert isinstance(actual,(list,tuple)) and len(actual) == len(expected), ('LIST',where,actual,expected)
        for i,(a,b) in enumerate(zip(actual,expected)):
            compare(a,b,(where,i))
    elif expected is None:
        assert actual is None or (isinstance(actual,float) and np.isnan(actual)), ('NONE',where,actual)
    elif isinstance(expected,(float,np.floating)):
        assert actual is not None and np.isclose(float(actual),expected,rtol=1e-10,atol=1e-10,equal_nan=True), ('FLOAT',where,actual,expected)
    elif isinstance(expected,(bool,np.bool_)):
        assert isinstance(actual,(bool,np.bool_)) and bool(actual) == bool(expected), ('BOOL',where,actual,expected)
    else:
        assert actual == expected, ('VALUE',where,actual,expected)


def read_path(folder):
    folder = Path(folder)
    loaded = {key:pd.read_csv(folder/name,float_precision='round_trip') for key,name in
              [('daily','DAILY.csv.gz'),('orders','ORDERS.csv.gz'),('instructions','INSTRUCTIONS.csv.gz'),('decisions','DECISIONS.csv')]}
    with np.load(folder/'DECISIONS.npz',allow_pickle=False) as arrays:
        loaded['decision_arrays'] = {key:arrays[key] for key in arrays.files}
    loaded['metadata'] = json.loads((folder/'METRICS.json').read_text())
    trace = folder/'POLICY_TRACE.csv.gz'
    loaded['trace'] = pd.read_csv(trace,float_precision='round_trip') if trace.exists() else None
    return loaded


def independent_orders(units, cash, executable_prices, marks, weights, ticket, spread, force):
    """Price the whole account, sell eligible excesses, reserve buy tickets.

    Only executable_prices authorizes a trade; marks continue to value all
    holdings. The shared financing fraction explicitly limits aggregate buys
    to available cash after sales and fixed fees.
    """
    held = units.copy()
    marks = np.nan_to_num(marks,nan=0.)
    wealth = float(cash + np.sum(held * marks))
    desired = wealth * weights
    threshold = max(1e-8,0. if force else .03 * wealth)
    quoted = np.isfinite(executable_prices) & (executable_prices > 0)
    sales = np.flatnonzero(quoted & (held * marks - desired > 1e-8))
    trades, money = [], float(cash)
    for j in sales:
        excess = held[j] * marks[j] - desired[j]
        if excess < threshold and weights[j] != 0:
            continue
        qty = min(held[j], excess / executable_prices[j])
        value = float(qty * executable_prices[j])
        fee = ticket + spread * value
        if value <= fee and money + value < fee:
            continue
        held[j] -= qty
        money += value - fee
        trades.append(dict(j=int(j),side='SELL',quantity=float(qty),price=float(executable_prices[j]),notional=value,cost=float(fee)))
    requests = desired - held * marks
    buys = np.flatnonzero(quoted & (requests > 1e-8) & (requests >= threshold) & (requests > ticket))
    if len(buys) and money > ticket * len(buys):
        fraction = min(1., (money - ticket * len(buys)) / ((1. + spread) * requests[buys].sum()))
        for j in buys:
            value = float(requests[j] * fraction)
            if value <= 1e-8:
                continue
            trades.append(dict(j=int(j),side='BUY',quantity=float(value/executable_prices[j]),price=float(executable_prices[j]),notional=value,cost=float(ticket+spread*value)))
    return trades


def metrics(nav_close, nav_quote, dates, initial):
    nav_close, nav_quote = np.asarray(nav_close), np.asarray(nav_quote)
    days = (dates[-1] - dates[0]).days + 1
    cagr = float(np.expm1(np.log(nav_close[-1]/initial)*365.2425/days))
    closes = np.r_[initial,nav_close]
    samples = np.r_[initial,np.column_stack((nav_quote,nav_close)).ravel()]
    dd = float((samples/np.maximum.accumulate(samples)-1).min())
    lr = np.diff(np.log(closes))
    return dict(cagr=cagr,cumulative=float(nav_close[-1]/initial-1),
                maxdd_close=float((closes/np.maximum.accumulate(closes)-1).min()),
                maxdd_sampled=dd,calmar=cagr/abs(dd) if dd < 0 else float('nan'),
                volatility=float(lr.std(ddof=1)*np.sqrt(252)) if len(lr)>1 else 0.,
                worst_21_sessions=float(np.expm1(pd.Series(lr).rolling(min(21,len(lr))).sum().min())),
                end_equity=float(nav_close[-1]),days=int(days))


class AccountAudit:
    def __init__(self, selector, saved, *, initial=10000.):
        self.selector, self.p, self.f = selector, selector.p, selector.f
        self.saved = saved
        self.m = saved['metadata']
        self.arm, self.scenario = self.m['arm'], self.m['scenario']
        assert self.arm in ARMS and self.scenario in SCENARIOS
        self.protected = self.arm not in ARMS[:4]
        self.policy = PolicyReference(selector,self.arm) if self.protected else None
        self.ticket, self.impact, self.lag, self.fill = SCENARIOS[self.scenario]
        compare(self.m['ticket'],self.ticket,'ticket')
        compare(self.m['impact_bps'],10000*self.impact,'impact')
        compare(self.m['lag_extra'],self.lag,'lag')
        compare(self.m['fill'],self.fill,'execution_price')
        dates, n = self.p['dates'], selector.n
        self.begin = int(dates.searchsorted('2020-03-02'))
        self.finish = int(dates.searchsorted('2026-10-30',side='right'))
        self.initial = float(initial)
        self.units, self.cash = np.zeros(n), float(initial)
        self.last_buy, self.last_sell = np.full(n,-1,int), np.full(n,-1,int)
        self.queue, self.pending = deque(), None
        self.issued = 0
        self.counters = Counter()
        self.maxima = Counter()
        self.min_cash = self.cash
        self.min_units = 0.
        self.validated_orders = []
        self.orders = saved['orders'].to_dict('records')
        self.orders_by_k = {}
        for order in self.orders:
            self.orders_by_k.setdefault(int(order['execution_idx']),[]).append(order)
        self.instructions = saved['instructions'].to_dict('records')
        assert [int(row['instruction_id']) for row in self.instructions] == list(range(len(self.instructions))), 'INSTRUCTION_SEQUENCE'
        self.instruction_by_k = {int(row['signal_idx']):row for row in self.instructions}
        assert len(self.instruction_by_k) == len(self.instructions), 'DUPLICATE_SIGNAL'
        assert len(saved['decisions']) == len(self.instructions), 'DECISION_INSTRUCTION_COUNT'
        for array in saved['decision_arrays'].values():
            assert len(array) == len(self.instructions), 'DECISION_ARRAY_LENGTH'
        self.trace_by_k = {}
        if self.protected:
            assert saved['trace'] is not None
            for row in saved['trace'].to_dict('records'):
                self.trace_by_k.setdefault(int(row['k']),[]).append(row)
            assert set(self.trace_by_k) == set(range(self.begin-1,self.finish-1)), 'TRACE_CLOSE_DATES'
            assert all([int(row['slot']) for row in rows] == [0,1] for rows in self.trace_by_k.values()), 'TRACE_SLOTS'
        else:
            assert saved['trace'] is None
        expected_dates = [str(day.date()) for day in dates[self.begin:self.finish]]
        assert saved['daily'].date.tolist() == expected_dates, 'DAILY_DATE_COVERAGE'
        assert not (set(self.orders_by_k)-set(range(self.begin,self.finish))), 'ORDER_DATE_WINDOW'
        self.independent_trace = []
        self.independent_instructions = []

    def vector_check(self, actual, expected, label, *, rtol=1e-10, atol=1e-10):
        actual = np.asarray(actual,float)
        assert actual.shape == expected.shape, ('VECTOR_SHAPE',label)
        error = float(np.max(np.abs(actual-expected))) if len(actual) else 0.
        self.maxima['max_'+label+'_error'] = max(self.maxima['max_'+label+'_error'],error)
        if not np.allclose(actual,expected,rtol=rtol,atol=atol,equal_nan=True):
            j = int(np.nanargmax(np.abs(actual-expected)))
            raise AssertionError(('VECTOR',label,j,actual[j],expected[j],error))

    def signal(self, k, *, initial=False):
        scheduled = bool(self.selector.weekly[k] if self.arm == 'REFRESH_WEEKLY' else self.selector.monthly[k]) and not initial
        marked = np.nan_to_num(self.units*self.p['C'][k],nan=0.)
        nav = float(self.cash+marked.sum())
        current = marked/nav
        answer, trace = None, []
        if self.protected:
            answer, trace = self.policy.decide(k,current,self.units,self.cash,nav,self.last_buy,self.pending,self.queue,initial=initial,scheduled=scheduled)
            actual_trace = self.trace_by_k[k]
            for actual,wanted in zip(actual_trace,trace):
                compare(actual,wanted,('TRACE',k,wanted['slot']))
            self.independent_trace.extend(trace)
            self.counters['slot_trace_rows_checked'] += len(trace)
        elif initial or scheduled:
            base,meta = self.selector.selection(k)
            scale = .5 if self.arm == 'STATIC_HALF' else .75 if self.arm == 'STATIC_75' else 1.
            answer = dict(raw=base*scale,nominal=base*scale,action_mask=None,sell_only=False,force=initial,
                          reason='INITIAL' if initial else 'SCHEDULED',meta=meta)
        row = self.instruction_by_k.get(k)
        if answer is None:
            assert row is None, ('UNEXPECTED_RECORDED_INSTRUCTION',k,row and row['reason'])
            return
        assert row is not None, ('MISSING_RECORDED_INSTRUCTION',k,answer['reason'])
        iid = self.issued
        raw = np.asarray(answer['raw'])
        target = raw.copy()
        action_mask = answer['action_mask']
        if answer['sell_only']:
            scope = np.ones(len(raw),bool) if action_mask is None else action_mask
            assert np.all(raw[scope] <= current[scope]+1e-12), ('SELL_ONLY_RAW_ADDITION',k)
            target = np.minimum(target,current)
        if action_mask is not None:
            target[~action_mask] = current[~action_mask]
            budget = max(0.,1-float(current[~action_mask].sum()))
            demand = float(target[action_mask].sum())
            if demand > budget:
                target[action_mask] *= budget/demand
        assert np.min(target) >= 0 and target.sum() <= 1+1e-9
        due = k+1+self.lag
        expected_fields = dict(instruction_id=iid,signal_idx=k,signal_date=str(self.p['dates'][k].date()),
                               due_idx=due,execution_not_before=str(self.p['dates'][due].date()) if due<len(self.p['dates']) else None,
                               reason=answer['reason'],force=bool(answer['force']),
                               gross_target=float(target.sum()),positions=int((target>0).sum()))
        compare(row,expected_fields,('INSTRUCTION',k))
        self.vector_check(json_value(row['raw_weights']),raw,'raw_weights')
        self.vector_check(json_value(row['target_weights']),target,'target_weights')
        if self.protected:
            compare(json_value(row['action_indices']),None if action_mask is None else np.flatnonzero(action_mask).tolist(),('MASK',k))
            compare(row['sell_only'],answer['sell_only'],('SELL_ONLY',k))
            compare(json_value(row['meta']),answer['meta'],('POLICY_META',k))
        record = self.saved['decisions'].iloc[iid].to_dict()
        arrays = self.saved['decision_arrays']
        compare(int(arrays['k'][iid]),k,('DECISION_DATE',iid))
        self.vector_check(arrays['units'][iid],self.units,'decision_units',atol=1e-7)
        self.vector_check(arrays['current_weights'][iid],current,'decision_current_weights')
        self.vector_check(arrays['raw_weights'][iid],raw,'decision_raw_weights')
        self.vector_check(arrays['weights'][iid],target,'decision_target_weights')
        assert np.isclose(arrays['cash'][iid],self.cash,rtol=1e-10,atol=1e-7), ('DECISION_CASH',k,arrays['cash'][iid],self.cash)
        compare(json_value(record['meta_json']),answer['meta'],('DECISION_META',k))
        compare(record['signal_idx'],k,('DECISION_SIGNAL',k))
        compare(record['instruction_id'],iid,('DECISION_INSTRUCTION_ID',k))
        if self.protected:
            compare(record['reason'],answer['reason'],('DECISION_REASON',k))
            compare(record['scheduled'],bool(scheduled),('DECISION_SCHEDULED',k))
            compare(record['initial'],bool(initial),('DECISION_INITIAL',k))
            compare(record['sell_only'],answer['sell_only'],('DECISION_SELL_ONLY',k))
            compare(json_value(record['action_indices']),None if action_mask is None else np.flatnonzero(action_mask).tolist(),('DECISION_MASK',k))
        expected_instruction = dict(id=iid,signal=k,due=due,target=target.copy(),mask=None if action_mask is None else action_mask.copy(),
                                    sell_only=answer['sell_only'],force=answer['force'],reason=answer['reason'])
        self.queue.append(expected_instruction)
        self.independent_instructions.append(dict(instruction_id=iid,signal_idx=k,reason=answer['reason'],
                                                 action_indices=None if action_mask is None else np.flatnonzero(action_mask).tolist(),
                                                 nominal_indices=np.flatnonzero(answer['nominal']>0).tolist(),
                                                 nominal_weights=answer['nominal'][answer['nominal']>0].tolist()))
        self.issued += 1
        self.counters['instructions_independently_rederived'] += 1
        self.counters['targeted_masks_rederived'] += int(action_mask is not None)
        self.counters['scheduled_selections_rederived'] += int(initial or scheduled)

    def run(self):
        n, dates = self.selector.n, self.p['dates']
        attribution, costs = np.zeros(n), np.zeros(n)
        buys, sells, held_days = np.zeros(n), np.zeros(n), np.zeros(n,int)
        closes, quotes, exposure, cash_series, position_series = [], [], [], [], []
        previous_nav = self.initial
        self.signal(self.begin-1,initial=True)
        for row in self.saved['daily'].to_dict('records'):
            k = int(row['k'])
            assert row['date'] == str(dates[k].date())
            if self.fill == 'OPEN':
                executable = np.where(self.p['valid_open'][k],self.p['raw_open'][k],np.nan)
            else:
                executable = np.where(self.p['valid_close'][k],self.p['raw_close'][k],np.nan)
            marks = np.where(np.isfinite(executable),executable,self.p['C'][k-1])
            assert np.isfinite(marks[self.units>1e-12]).all(), 'MISSING_EXECUTION_MARK'
            before_units = self.units.copy()
            quote_nav = float(self.cash+np.nansum(self.units*marks))
            quotes.append(quote_nav)
            self.maxima['max_nav_cash_error'] = max(self.maxima['max_nav_cash_error'],abs(quote_nav-row['nav_open']))
            while self.queue and self.queue[0]['due'] <= k:
                self.pending = self.queue.popleft()
            actual_orders = self.orders_by_k.get(k,[])
            expected_orders = []
            if self.pending is not None:
                active = self.pending
                target = active['target'].copy()
                if active['sell_only']:
                    target = np.minimum(target,np.nan_to_num(self.units*marks,nan=0.)/quote_nav)
                missing_needed = (self.units>1e-10) | (target>0)
                trade_prices = executable.copy()
                if active['mask'] is not None:
                    trade_prices[~active['mask']] = np.nan
                    missing_needed &= active['mask']
                missing = missing_needed & ~np.isfinite(trade_prices)
                expected_orders = independent_orders(self.units,self.cash,trade_prices,marks,target,self.ticket,self.impact,active['force'])
            else:
                assert not actual_orders, ('ORDER_WITHOUT_INSTRUCTION',k)
            assert len(actual_orders) == len(expected_orders), ('ORDER_COUNT',k,len(actual_orders),len(expected_orders))
            fees, purchases_started = 0., False
            for actual,wanted in zip(actual_orders,expected_orders):
                j,qty,price,cost = wanted['j'],wanted['quantity'],wanted['price'],wanted['cost']
                assert actual['j'] == j and actual['side'] == wanted['side'], ('ORDER_ASSET_SIDE',k,actual,wanted)
                for field in ('quantity','price','notional','cost'):
                    error = abs(float(actual[field])-wanted[field])
                    self.maxima['max_order_'+field+'_error'] = max(self.maxima['max_order_'+field+'_error'],error)
                    assert np.isclose(actual[field],wanted[field],rtol=1e-10,atol=1e-7), ('ORDER_SIZING',k,field,actual[field],wanted[field])
                compare(actual,dict(instruction_id=active['id'],execution_idx=k,execution_date=row['date'],date=row['date'],
                                    signal_idx=active['signal'],signal_date=str(dates[active['signal']].date()),due_idx=active['due'],
                                    ticker=str(self.p['names'][j]),reason=active['reason']),('ORDER_CHRONOLOGY',k,j))
                assert k >= active['signal']+1+self.lag, ('EARLY_OR_SAME_CLOSE_FILL',k)
                assert np.isfinite(executable[j]) and price == executable[j], ('INVALID_EXECUTION_PRICE',k,j)
                assert active['mask'] is None or active['mask'][j], ('OUTSIDE_ACTION_MASK',k,j)
                if active['sell_only']:
                    assert wanted['side'] == 'SELL', ('SELL_ONLY_BOUGHT',k,j)
                # Post exact serialized fills only after independent sizing
                # and timing checks. This preserves strict >0 dust semantics
                # in the frozen engine without accepting targets as an oracle.
                qty, price, value = float(actual['quantity']), float(actual['price']), float(actual['notional'])
                assert abs(qty*price-value) < 1e-7
                cost = self.ticket+self.impact*value
                assert abs(cost-float(actual['cost'])) < 1e-7
                self.validated_orders.append(dict(execution_idx=k,notional=value,cost=cost))
                if wanted['side'] == 'BUY':
                    purchases_started = True
                    self.units[j] += qty
                    self.cash -= value+cost
                    self.last_buy[j] = k
                    buys[j] += value
                else:
                    assert not purchases_started, 'SALES_AFTER_PURCHASES'
                    self.units[j] -= qty
                    self.cash += value-cost
                    self.last_sell[j] = k
                    sells[j] += value
                self.min_cash = min(self.min_cash,self.cash)
                self.min_units = min(self.min_units,float(self.units.min()))
                assert self.cash >= -1e-7 and self.units.min() >= -1e-10, ('ACCOUNT_FINANCING',k,self.cash)
                costs[j] += cost
                fees += cost
                self.counters['orders_independently_sized'] += 1
                self.counters['order_timestamps_checked'] += 1
            # Match the explicit tiny-negative cleanup in the frozen account
            # contract, while retaining pre-cleanup minima as evidence.
            self.units = np.maximum(self.units,0.)
            self.cash = max(0.,float(self.cash))
            if self.pending is not None:
                conservation = abs(self.cash+np.nansum(self.units*marks)+fees-quote_nav)
                self.maxima['max_self_financing_error'] = max(self.maxima['max_self_financing_error'],conservation)
                assert conservation < max(1e-7,quote_nav*1e-10), ('SELF_FINANCING',k,conservation)
                if active['mask'] is not None:
                    assert np.array_equal(self.units[~active['mask']],before_units[~active['mask']]), ('UNTOUCHED_UNITS_CHANGED',k)
                    self.counters['targeted_execution_attempts_checked'] += 1
                    self.counters['untouched_quantities_checked'] += int((~active['mask']).sum())
                    self.counters['unrelated_missing_quotes_ignored'] += int((~active['mask'] & ~np.isfinite(executable)).sum())
                if missing.any():
                    self.counters['deferred_sessions'] += 1
                else:
                    self.pending = None
            close = self.p['C'][k]
            assert np.isfinite(close[self.units>1e-12]).all(), 'MISSING_CLOSE_MARK'
            overnight = np.nan_to_num(before_units*(marks-self.p['C'][k-1]),nan=0.)
            intraday = np.nan_to_num(self.units*(close-marks),nan=0.)
            pnl = overnight+intraday
            attribution += pnl
            held_days += ((before_units>1e-10)|(self.units>1e-10)).astype(int)
            holdings = float(np.nansum(self.units*close))
            nav = self.cash+holdings
            gross = holdings/nav
            positions = int((self.units>1e-10).sum())
            assert nav > 0 and -1e-12 <= gross <= 1+1e-9
            self.maxima['max_nav_cash_error'] = max(self.maxima['max_nav_cash_error'],abs(nav-row['nav_close']),abs(self.cash-row['cash']))
            assert np.isclose(nav,row['nav_close'],rtol=1e-10,atol=1e-5), ('CLOSE_NAV',k,nav,row['nav_close'])
            assert np.isclose(self.cash,row['cash'],rtol=1e-10,atol=1e-5), ('CASH',k,self.cash,row['cash'])
            assert abs(gross-row['gross']) < 1e-9, ('GROSS',k,gross,row['gross'])
            assert positions == int(row['positions']), ('POSITIONS',k,positions,row['positions'])
            attribution_error = abs(nav-previous_nav-pnl.sum()+fees)
            self.maxima['max_daily_pnl_attribution_error'] = max(self.maxima['max_daily_pnl_attribution_error'],attribution_error)
            assert attribution_error < 1e-7, ('PNL',k,attribution_error)
            closes.append(nav); exposure.append(gross); cash_series.append(self.cash); position_series.append(positions)
            previous_nav = nav
            if k+1 < self.finish:
                self.signal(k)
        assert self.issued == len(self.instructions), 'UNRECONSTRUCTED_INSTRUCTIONS'
        assert self.counters['orders_independently_sized'] == len(self.orders), 'UNRECONSTRUCTED_ORDERS'
        assert self.maxima['max_nav_cash_error'] < 1e-5
        assert abs(attribution.sum()-costs.sum()-(closes[-1]-self.initial)) < 1e-5, 'TOTAL_PNL_ATTRIBUTION'
        independent = metrics(closes,quotes,dates[self.begin:self.finish],self.initial)
        years = independent['days']/365.2425
        independent.update(orders=len(self.orders),costs=float(costs.sum()),instructions=self.issued,
                           trading_days=len(self.orders_by_k),trading_days_per_year=len(self.orders_by_k)/years,
                           mean_exposure=float(np.mean(exposure)),mean_cash_share=float(np.mean(1-np.asarray(exposure))),
                           mean_positions=float(np.mean(position_series)),full_cash_days=int(np.sum(np.asarray(exposure)<=1e-8)),
                           deferred_sessions=int(self.counters['deferred_sessions']),
                           two_sided_turnover_per_year=float(sum(o['notional']/quotes[int(o['execution_idx'])-self.begin] for o in self.validated_orders)/years))
        for key,value in independent.items():
            assert np.isclose(value,self.m[key],rtol=1e-10,atol=1e-8,equal_nan=True), ('METRIC',key,value,self.m[key])
        assert self.m['drawdown_sampling'] == ('OPEN_CLOSE' if self.fill == 'OPEN' else 'CLOSE_PRE_POST_FEES')
        independent.update(path_id=self.m['path_id'],arm=self.arm,scenario=self.scenario,status='PASS',
                           min_cash=float(self.min_cash),min_units=float(self.min_units),**dict(self.counters),**dict(self.maxima))
        if self.policy:
            independent.update({'policy_'+key:int(value) for key,value in self.policy.counts.items()})
        contribution = [dict(path_id=self.m['path_id'],ticker=str(self.p['names'][j]),gross_pnl=float(attribution[j]),
                             costs=float(costs[j]),net_pnl=float(attribution[j]-costs[j]),buy_notional=float(buys[j]),
                             sell_notional=float(sells[j]),held_sessions=int(held_days[j])) for j in range(n) if held_days[j] or costs[j]]
        annual = []
        years_array = dates[self.begin:self.finish].year
        close_array,quote_array = np.asarray(closes),np.asarray(quotes)
        for year in sorted(set(years_array)):
            ix = np.flatnonzero(years_array == year)
            starting = self.initial if ix[0] == 0 else closes[ix[0]-1]
            result = metrics(close_array[ix],quote_array[ix],dates[self.begin:self.finish][ix],starting)
            annual.append(dict(path_id=self.m['path_id'],year=int(year),annual_return=result['cumulative'],maxdd_in_year=result['maxdd_sampled'],partial_year=year in (2020,2026)))
        return independent,contribution,annual
