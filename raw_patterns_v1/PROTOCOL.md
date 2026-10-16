# Bounded Flatten pilot - frozen before first fit

Only AM1975MA/Test; original frozen Yahoo download r2. No new downloads from Yahoo. No production access. OHLCV before 2011-01-01 is excluded before forming any window; 2011 warms inputs, supervised queries start in 2012.

Three fixed views of 21 candles: last 21 sessions at daily scale, last 63 sessions aggregated in consecutive 3-session OHLCV candles, last 126 sessions aggregated in 6-session candles. Each uses first Open, maximum High, minimum Low, last Close and summed Volume per candle. Prices are log ratios to first Close of that view; volume is log(1+volume/mean volume of that view)-log(2), with all-zero-volume views encoded zero. Flatten 3x21x5 = 315 inputs. Overlapping scales are correlated, not independent data.

Monthly signals; target uses next-session Open through Open 21 sessions later, ranked across the eligible ETF query. This matches the canonical 21-session label convention. Eligibility requires finite positive prices and nonnegative volume on all 126 preceding union-calendar sessions, with no future filling. At least 100 eligible ETFs per query; support, exclusions and full universe hash are saved. Actual count may be less than 149 because of missing history.

Annual expanding fits at January 1, 2014/2015/2016. All training label exits strictly precede fit cutoff. Last 12 mature queries are validation; training query exits must precede first validation signal. Preprocessing uses subtraining only. No permanent-holdout policy claim of equivalence with original LINEAR125; this pilot is a matched raw-input architecture comparison.

Controls: regularized LINEAR on 315 local inputs; Dense315->32ReLU->8ReLU->1 local; Dense630->32ReLU->8ReLU->1 with local and leave-one-out mean context of eligible peers. Shared weights across ETFs. Context concatenation allows nonlinear interactions. Context model has more parameters, so any difference is not a capacity-controlled context effect. No clusters, attention or architecture grid in this pilot.

Neural ListNet decile target, Adam LR0.0001, dropout0.2, gradient clip1, seeds101/202/303, maximum20 epochs, patience10, validation-best including initialization; fixed additional weight gradient0.001*W (L2/weight decay on weights, not biases). Reuse existing tested NumPy learner. All seeds retained, equal score ensemble, no best-seed selection. LINEAR uses existing repaired solver and L2=0.001. Maximum18 neural fits +3 linear fits; Actions hard timeout45min and one CPU math thread.

Evaluation restricted to signals2014-2016 with labels exited before2017-01-01. Quality: Top1 realized percentile, top-decile hit rate, NDCG5, RankIC, and seed Top1 disagreement. Report all candidates and all seeds. No portfolio replay, no CAGR claim, no 2017-2026 tuning. This is an engineering/feasibility pilot, not a statistically powered strategy selection. Passing finite/causal/maturity checks is mandatory; raw neural ensemble Top1 percentile and NDCG5 must each preserve >=95% of matched raw linear control as an exploratory screen only. A pass does not authorize adoption or prove improvement.

Implementation ledger: execute inline with one final independent review; reuse existing completed controls, no duplicate PCA95/full LINEAR fits. This protocol supersedes inconsistent alternatives in EXPERIMENT_DESIGN.md for this pilot only.
