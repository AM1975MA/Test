# L2-I — XGB ranker distribution and cross-vintage consensus | frozen protocol

**Date 2026-10-08. Saved BEFORE inspecting L2-I performance outcomes**. Repo scope only `AM1975MA/Test` branch `research/target-redesign-level2-v1`. Canonical `Etf_trader` not modified. Original149 2017–2026 **already extensively used for research**; analysis is diagnostic, not an independent forward test or production approval.

## Question, specialists and causal caveat

XGB rankers fitted on each of the three near-identical historical Yahoo acquisitions have unstable top choices (~45–57% pairwise). Can a **distribution of existing historically causal XGB estimators** identify high-performing ETFs by agreement rather than relying on one fragile best score? Econophysics: noisy winner tails, multistability of rank and heavy-tailed errors. Quant/statistics: repeated acquisitions are same market, not independent evidence. ML: model committee and score-scale invariance. Risk/execution: avoid optimistic mean-return-only claims.

The three prices datasets were all *downloaded in 2026*. Their histories are historically revised, so this is an **as-of-reconstructed development diagnostic** and not an executable 2017 live deployment; no independent provenance-time historical vintage snapshots. Ensemble consumes three training acquisitions obtained simultaneously, never future labels in an annual fit or contemporaneous target in decision.

## Input provenance

- Frozen source-only **XGB canonical** fit 360 rounds, rank:pairwise, seeds 101/202/303, 125 features, annual fits 2017-2026 with strict exit21 before training cutoff; **not refit here**. Existing `XGB_COMMON_PREDICTIONS.csv.gz` supplies its three independently fitted acquisition models all scored on **the exact same Repeat2 input**, 2017–2026.
- Separate `XGB_NATIVE_PREDICTIONS.csv.gz` provides the same-vintage original model benchmark and realized mature 21-session outcome for every ETF. `COMMON_INPUT_PREDICTIONS.csv.gz` is the Ridge anchor scored on Repeat2 inputs by vintage-trained Ridge. Provenance from L2-D and L2-C committed reports; raw Yahoo artifact GitHub Actions run 37121749852, id 11272972639.
- From the common input select only Jan 2017–Jun 2026 monthly signals with 21-session mature labels by Jul 2026. Expected 113 × 149 = 16,837 distinct monthly ETF rows and three committee scorers for each. **One true historical evaluation frame per month**, from Repeat2 labels. Other vintages must NOT be counted as independent outcome trials.
- For ranking every learned model, rank raw scores cross-sectionally per signal_date with `rank(method='average',pct=True)`; normalize only on same-day model score, never future outcomes.

## EXACTLY TWO frozen committee rules (no post-outcome tuning)

1. `COMMITTEE_MEAN3`: for every ETF, mean of the three model's date-cross-sectional prediction percentiles; higher is better; select top1, tie break alphabetically.
2. `COMMITTEE_TOP5_VOTE2`: one ETF gets one vote per model if in that model's highest five predictions, with ties broken alphabetical; restrict to ETFs with >=2 votes; choose the ETF with highest `COMMITTEE_MEAN3` inside the restricted set. If no ETF has >=2 votes, fall back **deterministically to Repeat2 Ridge top1**. No future profit, no ensemble weights, no hindsight.

Controls: `XGB_REPEAT2` and `RIDGE_REPEAT2`, both evaluated with their existing frozen Repeat2 common-input scores and the same Repeat2 labels/costs.

## Robustness design (do not confuse trivial symmetry with true retraining stability)

A full THREE-way committee is the *same pool* regardless of which input-vintage label it is compared with; reporting 100% agreement by relabeling the pool as three vintages would be scientifically meaningless and is PROHIBITED. Instead:
- Perform a **three-way leave-one-vintage-out (LOVO)** stress: construct score consensus from the remaining two models, with the same Repeat2 inference input. For `MEAN_RANK2_LOVO` take mean of two percentile scores; for `TOP5_VOTE2_LOVO` require **both** remaining models to put ETF in their Top5 and use mean ranks, otherwise Ridge repeat2 top1. All two-model committees remain fixed recipes based on no outcomes.
- Pairwise compare the **three LOVO portfolios** for Top1 choice agreement, Top5 score overlap when defined, and rank-MAD of continuous averaged percentile scores. This is a model-contribution stress; LOVO variants share one fitted component, so reliability can be mechanically inflated. Also compare each LOVO top1 to full-three committee and quantify Top1 winner concentration and 2-of-3 vote availability.
- Report robustness of selection to one fitted-model removal separately from native baseline vintage sensitivity 45–57%, not as direct apples-to-apples equivalence.

## Prediction quality and execution proxy

- Predictive: NDCG@5 and Rank IC for `COMMITTEE_MEAN3`, Top1 realized 21-session net return (0.1% each leg label cost), actual Top5 hit, actual exact winner, realized target percentile, ex-post regret; 113 months equal-weight, by year, TOP5 vote separately top1 quality (ranking outside shortlist is not a defined continuous global score).
- Economic proxy: 112 **nonoverlapping** months from next-open entry after each monthly signal to next month's next open, 0.1% per actual traded dollar for each sell or buy including first/last, no phantom terminal trade, deterministic self-financing; compare exactly with L2-F corrected baseline, using Repeat2 source price data (downloaded frozen zip) and **same evaluation boundaries**; no MA3, no basket, no Hybrid24; no full-strategy CAGR.
- Paired moving-block bootstrap, 3-month block 10,000 seeded reps on calendar months (113 realized 21-session Top1 and TOP5; 112 proxy log monthly returns), CI 95% *descriptive unadjusted*; no repeated vintages as independent samples.
- Record yearly difference and leave-one-out disagreement, any tail/winner concentration.

## Failure/success gate (for research only)

**COMMITTEE may continue to new prospective evaluation** only if all: (a) three LOVO Top1 pairwise agreements **>=90%**; (b) three LOVO pairwise mean rank-MAD **<0.01**; (c) realized Top5 hit **>=15%** on Repeat2; (d) realized mean next21 return **>= Repeat2 Ridge**, and (e) no chronology/coverage/price/portfolio QA failures. If either candidate fails, do not change K/threshold/weight in response to results. True future model assessment requires independently observed post-2026 acquisition and a genuine prospective period, no production promotion.

## Independence and QA

Before numerical conclusions verify SHA256 source files, labels/key uniqueness, parity Repeat2 XGB native=Repeat2 common and Repeat2 Ridge native=Repeat2 common within numerical tolerance, exact 149 ETF/date panel. Preserve individual model scores and full committee scores, vote maps, all monthly selections, code and results. Independent audit recomputes committee selections and costs without using code that constructs scores. Do not claim expert agents were independently run unless tool actually provides such agents; use distinct specialist review protocols within one analysis.
