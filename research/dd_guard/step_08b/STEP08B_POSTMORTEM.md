# STEP08B post-mortem — persistent diversification

## Core result
Persistent diversification changes the MaxDD frontier strongly, unlike stress-only STEP08A. Every 10% persistent sleeve improved mean MaxDD by roughly 2.1–2.5 pp and p10 by roughly 2.8–3.3 pp. However the CAGR cost was 1.76–2.77 pp, far above the preregistered -0.50 pp guard.

The fixed-trio static frontier is nearly monotone: 5% BIL/IEF/GLD buys +1.05 pp mean MaxDD and +1.44 pp p10 but costs -1.15 pp CAGR; 10% buys +2.10/+2.86 pp but costs -2.31 pp CAGR. Thus the failure is not inability to reduce drawdown; it is an unfavorable structural exchange rate between return and defensive ballast.

## Variant interpretation
- PERSIST_BIL10 is the most efficient eligible 10% ballast by the simple MaxDD/CAGR tradeoff: -1.765 pp CAGR for +2.415 pp mean MaxDD and +3.237 pp p10.
- PERSIST_TRIAD_TREND10 preserves more CAGR than the fixed BIL/IEF/GLD trio, but still costs -1.829 pp and improves mean MaxDD by +2.201 pp.
- PERSIST_TRIO10_SYS20 buys slightly more protection, +2.488 pp mean MaxDD, but costs -2.772 pp CAGR; increasing structural defense in systemic states does not solve the return budget.
- All eligible variants improve annual mean MaxDD in both 2021 and 2022, so temporal sign replication is not the problem.

## Scientific implication
The persistent defensive-sleeve lane has enough mechanical power to reduce drawdown, but not at the required return budget. The diagnostic frontier shows that even the smallest preregistered nonzero fixed-trio point (5%) already violates the CAGR guard by more than 2x.

Per the preregistered stop rule, do not tune 2%, 3%, 4%, alternative thresholds, trio constituents, or momentum lookbacks after seeing this frontier. The next defensible research lane is not a smaller defensive sleeve; it is **core risk budgeting / diversification inside the alpha portfolio itself**, where capital is reweighted among return-seeking exposures rather than removed from the alpha engine.
