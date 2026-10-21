# V3 L07 — integration stack reproducibility preflight

**21 October 2026: completed PASS_RESEARCH_PREFLIGHT_ONLY. Full integrated backtest NOT executed.** [Successful Actions 39676155405](https://github.com/AM1975MA/Test/actions/runs/39676155405), artifact **12381996439**.

## Verified conditions

- Exact original raw lineage run **39482809691**, 149 ETFs and 500 canonical fixed baskets of 24, authenticated original basket SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- Full initial model score stream **102 calendar months** and 149 ETF rows each; exactly same tickers, dates and next21D forward-return targets for independently fitted **CORRECTED125 + pairwise127** (run 39652989033) and **TAIL_EVENT_LOGIT45** (run 39655513813), plus frozen 50/50/static score experiment (39659903643).
- **101 fully mature next21D months**, with future-label maturity verified explicitly from **18 ranker annual fits**, **9 Tail annual fits** and **5 absolute-risk calibration annual fits**.
- Frozen selection: no adaptive regime gate L03, no empirically advantaged L04 blend; Tail45 top three by basket, target weights **50%,30%,20%** (run 39661273577).
- Risk is a separate, opt-in research **alternative**, never a hard veto: annual train-only calibrated absolute next21D <=−10% probability (run 39671493979); soft weight treatment `normalize([.5,.3,.2] × exp(-3 × p_abs_loss10))` (run 39672320747) evaluated on **53** matched later mature months and 2,281 distinct ETF-month risk observations.
- The first and second arms have matching future event labels and original 50/30/20 weight-only reference; the risk alternative **does not alter selected ETF names**. V2 production file trees untouched.
- No CAGR, Sharpe, maximum drawdown or long-run strategy performance was used for selection of layer winners or promoted during the preflight.

## Important limits

This preflight is a source- and event-lineage certification **only**: **it does NOT validate live execution economics, real spread, portfolio constraints, costs, drawdown or generalization**. All 2018–2026 historical calendars have already been repeatedly analyzed; there is **no virgin test set**. Therefore do not label the V3 strategy financially validated, do not claim an unbiased performance gain, and do not deploy risk or ranking changes.

Next: the **complete integrated diagnostic backtest** can be run with the above candidates **strictly frozen** on their common 53-month 2022–2026 OOS window, and independently on new future data once available. Report economic metrics only after full layer-selection freeze, never select hyperparameters by maximizing CAGR on these same 53 months.
