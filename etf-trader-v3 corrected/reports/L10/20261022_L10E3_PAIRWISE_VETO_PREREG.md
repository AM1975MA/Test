# L10.E3 — Review of specific ML-chosen ETF against its next-ranked substitute (PREREGISTERED)

22 October 2026. E3 test results NOT seen when this protocol was committed. Frozen V2 and V3 untouched.

## Exact experimental intervention

Keep frozen CORRECTED Pairwise127 Top3 as authoritative original ranking. Only originally selected incumbents with the OLD E1 warning (negative trailing 21-session log return AND <= -10% 63-session peak drawdown) are eligible for review. Identify their specific replacement as the first non-E1-flagged CORRECTED rank4+ name not already selected, in original ML order. When multiple incumbents flagged, visit slots 1 to 3 in order and never use the same substitute twice. The auxiliary model only says YES/NO to replacing an original selected incumbent in its unchanged slot; does not globally re-rank any ETF or choose alternative candidates.

7 fixed features: historical 21D log momentum, 63D log momentum, drawdown63, 21D Kaufman directional efficiency, downside volatility63, 21D acceleration (recent 21D return less preceding 21D return) each expressed as challenger minus incumbent divided by the within-date universe interquartile range (floor 0.0001), clipped +/-5; plus frozen ML percentile-score rank gap challenger minus incumbent. Adjusted historical closes at signal date only.

Outcome target (TRAIN ONLY): challenger realized next-open-to-21 trading session return beats incumbent by >=1 absolute percentage point. Fit standardized L2 logistic regression C=0.25, maximum 2000 iterations, no class weighting; expand yearly, refit at Jan 1 strictly on previous fully matured monthly outcomes. Unique date+incumbent+challenger pairs are deduplicated across 500 heavily overlapping baskets and then per-month equal sample weights. Must have >=18 prior monthly signals and >=150 distinct unique pair examples, both classes, otherwise abstain (do not change any ML picks). Frozen vote threshold: probability >=0.70. No threshold sweep, no parameter search, no online label adjustment.

Calendar label exit computed from frozen OHLCV next available trading day plus 21 further trading days; include TRAIN pair only when signal_date < annual cutoff and label_exit_date < annual cutoff, strict. No future outcome anywhere in signal feature calculation.

Matched 149 ETFs, 500 24-name canonical baskets SHA256 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e, 101 fully mature months (2018-2026). Reference raw run 39482809691, frozen OOS model scores 39700865721. Evaluation compare BASE unchanged, E1 re-run, E3 pair-specific vote; always same 50/30/20 slot weights and forward21D labels. 500 baskets aggregated within date; 6000 paired six-calendar-month circular bootstrap CIs, year sensitivity, flag/error precision, winner false veto, severe loss weight, 21D average rank, regret, weighted return, fraction changed. Verify model fit-year audits and original BASE/E1 numeric parity; synthetic causal prefix perturbation.

RUN ECONOMIC NEXT-OPEN CAGR only if E3 shows a plausible FUNCTIONAL gain vs BASE: less severe-loss invested weight or improved forward weighted realized return, WITHOUT material degradation in winner-weight or Top3 winner capture, with manageable modification/turnover. No strategy claim without 10bp transaction fee and exact original next-open execution; do not guess figures. Otherwise label research rejection and archive, no economic experiment.

Existing 2018-2026 history has been explored repeatedly; it is NOT a virgin independent holdout, and any new test here is descriptive hypothesis exploration, not confirmatory. V2 production, frozen ranker and registry historical experiments must not be overwritten.

## Engineering amendment before E3 numeric outcomes

Initial Actions run **39752728805** stopped before model fitting or score output on an overly restrictive assertion that every month must contain at least one E1 warning/pair. Some months have zero warnings; they correctly have no candidates and are handled as abstentions. The assertion is revised to permit this state (at least 18 pair-generating prior signal dates exist), without changing the frozen E1 trigger, seven features, paired labels, annual fits, >=0.70 veto cutoff, dataset or evaluation metrics. Also correct numpy numeric serialization in the output manifest. All outcomes remain unread at amendment time.
