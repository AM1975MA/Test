# T149-M — PRECOMMITTED before the first execution
2026-10-19 | Branch research/149-selected-nominal-tail-20261019

## Question, fixed assets, and biases
Can a **selected-position-only**, chronologically fitted, strongly regularized probability model estimate **absolute losses** among the ORIGINAL F3/H1 basket members better than historical event frequencies AND a plain volatility model? Can a separate correlated-basket model predict full-portfolio nominal loss and intraperiod downside better than historical frequency and frozen Gaussian covariance estimates?

Original 149 US survivor ETFs, frozen F3 and H1 top-five candidates, 64 non-overlapping forward 21-trading-session anchors (2021–26). H3 remains an unchanged external reference. No selection of new names. The 2021–26 panel has already been mined repeatedly, so this is **retrospective**, NOT a new independent holdout. Do not promote to production regardless of result.

## Precise label and risk clock
At signal previous **completed Close**, compute as-of features ONLY from past closes. Execution at the next session Open. Individual ETF label: gross Open-to-Open 21-session nominal return < -5%, no relative-to-SPY/AGG labels. Fixed baseline 50% F3 + 50% H1 actual underlying merged positions (duplicates summed) has separate basket label gross return < -5% over the 21-session holding period. A second basket target is the worst opening-price mark *relative to the entry Open* < -8% within the 21 sessions, i.e. maximum adverse excursion from entry, NOT full peak-to-trough MaxDD. No monthly future close or current trade Open enters predictor inputs.

The joint-basket proxy uses the prior 63 daily log Close returns for every held ETF, the full pairwise covariance matrix (50% sample covariance + 50% diagonal), basket exposure-weighted 21-session volatility and prior downside-volatility; it therefore does NOT falsely multiply independent loss odds for correlated ETFs. SPY prior momentum and volatility may be included as frozen macro covariates.

## Frozen algorithms and controls
Ticker-level:
- M_TAIL: 8 covariates: selected ETF 21-day annualization-free volatility, negative semideviation, prior 21 and 63-day momentum, mean correlation to other selected ETF exposures, within-149 F3 rank, within-149 H1 rank, portfolio 21-day volatility.
- VOL_ONLY: same regularized logistic training protocol but ONLY ETF realized-volatility covariate, to test whether additional features contribute.
- ONLINE_PRIOR: matured earlier selected-position loss frequency only. Strict one-block embargo: every training maturity must be earlier than today's previous Close. At least 16 matured dates, at least six positive and six negative events for a logistic fit; otherwise forecast historical frequency. Both logistic models C=.05, sklearn liblinear, standard scaling, random_state 20261019, refit each new anchor on matured history, equal aggregate date weights. No search.

Portfolio-level:
- M_BASKET: same fixed strong logistic estimator, six frozen prior-state features: basket 21d vol, mean 63d pair-correlation, prior basket 63d momentum, prior SPY 63d momentum, prior SPY 21d volatility, prior basket 21d negative semideviation.
- ONLINE_PRIOR: earlier matured basket loss/negative excursion frequency.
- GAUSSIAN: pre-fixed prior63 50%-diagonal-shrunk covariance normal lower tail (one-sided event), and reflection-principle proxy for first-passage negative excursion. Its inadequacy is a falsifier. Portfolio warmup requires at least 20 matured anchor blocks, six positive and six negative event labels; otherwise use historical prior. For ticker and basket, each testing anchor, NOT each ETF observation, is independent unit for statistical uncertainty.

The economically scored exploratory policy M_TAIL_WITHIN **retains each expert's original 50% capital**, retains all frozen Top5 names, shifts weights within each Top5 by clip((.10+mean P_loss5)/(.10+own P_loss5),.70,1.30). VOL_ONLY_WITHIN uses the exact same tilting rule on the benchmark volatility head. During forecast warmup all portfolios are EXACT original static 50:50. Rebalance only once every 21 sessions at the same Open, real shares merged across expert overlap and no invented fee-free NAV averaging. Fixed 10bp per buy/sell, no leverage, no extra cash; compare all 1345 daily points exactly with frozen reference.

## Precommitted evaluation and decision
Evaluation primary: 43 fully out-of-fit basket dates following 21 warmup dates. Per-anchor selected-position Brier gain of model vs online prior and volatility-only, measured in grouped three-anchor circular-block bootstrap (2500 replicates), together with basket *two* proper-score targets vs their prior and Gaussian controls. Also report actual class prevalence, date-block paired gains with 95% CI, monthly net signed log portfolio return improvement relative to original static, historical CAGR/maxDD/daily ES5, and early 2021–23 vs late 2024–26 split. Never treat repeated ETF-month rows as independent draw samples.

Strict scientific GO requires: BOTH selected ETF logistic predictions (full and vol only) beat matured baseline in positive 95% lower block CI, both basket binary heads beat BOTH prior AND Gaussian in positive 95% lower CIs, and M_TAIL_WITHIN has positive lower CI net costed 21-day log growth with daily max drawdown and ES5 no worse AND mean improvement in both calendar eras. If any fail, scientific FAIL. This is intentionally difficult and NO posthoc threshold/model tuning is allowed. Genuine future point-in-time ETF membership and disjoint test chronology are essential to validate a production model.

## Guarantees and reproducibility
Frozen original Top5 picks unchanged on every date, held union unchanged. Audit previous Close < next Open, training maturity < previous Close, 149-member roster SHA256, 64×21 period and 1345 Opening-price points, baseline entire share-portfolio equity within 1e-9 of original. Files: source + tests, individual and basket OOF scores, actual target events, weights, costed daily NAV, machine-readable RESULT.json, SHA256 manifest. Do not change production etf_trader repository or branch.
