# V2 historical retention and Compact21 2017 warm-up gate — 2026-10-11

## Duplication check
Searched PR descriptions for warmup, history cutoff, training window and eligibility. Historic PR #19 concerned fixed 500 basket eligibility, PRs #52/#64–#67 audited **per-feature** incomplete panels; no prior **complete temporal cut-off equivalence certification** found. Full V2/Tail/MA3/Macro temporal truncation is not proven by previous Compact21 NaN root-cause audits.

## Result
GitHub Actions [38171032263](https://github.com/AM1975MA/Test/actions/runs/38171032263): **SUCCESS**. Frozen α=1 Compact21 panels from run 38094232042, three Yahoo acquisitions, no retraining. First ticker/date with 30/125 valid Compact21 features: **2004-02-27** in restored research panel (not a fully-trained first prediction or model-cutoff date). Exported historical 2017 training availability by year, ticker and acquisition; no historical observations deleted.

**Retention verdict: NO CUTOFF CERTIFIED.** In frozen vendor source `fit_predict_all`, yearly 2017 Compact XGBoost uses **all** pre-2017 rows with 30/125 input features, strict `exit_date_21<2017-01-01` label maturity, and a minimum of 60 unique training dates. The 60 dates are an admission *minimum*, not a maximum or rolling horizon. Removing older mature training rows would change the training set and can therefore change fits/rankings; merely satisfying the minimum number of dates or a 253-bar warm-up is not proof of equivalence. Tail/macro/opportunity also use expanding training windows; MA3/Stage19 require a separate full dependency audit.

**Source observation boundary**: the availability of a 2004-02-27 signal is not a safe raw OHLC cut-off. All warm-up observations used to generate that signal and earlier training examples must be retained. Source earliest date is defined by Original149 frozen panel acquisition; independent pre-history cannot simply be discarded.

## Recommended application
1. Keep immutable frozen source as verified research evidence.
2. Require signal-date point-in-time eligibility, preserving each ETF's actual inception date and complete raw formula lookbacks; a new ticker becomes eligible only after sufficient valid inputs and model-specific requirements.
3. If smaller operational storage is desirable, first generate a throwaway *derived* window, compare full-source vs truncated-source per-date model training rows, feature panel values, OOS prediction vectors and portfolio/replay equivalence; do not adopt any cutoff unless all mandated gates pass with exact causal semantics.
4. Without a passed end-to-end comparison, do **not** remove pre-2017 training history. Disk-size reduction is not a scientific justification for silently changing the tested trading policy.

No training, model changes, economic replay or production repository edits were performed.
