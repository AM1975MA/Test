# OLC41 — Complete EU165 Acc / Dist census and historically admissible migration audit

2026-11-03. Supplement to OLC39 EU Acc historicity report (commit `c5f8393d014a425cfcb889f534df6a77bb2387ac`), before running the **full-universe** census. No USA analysis, no main modifications, no retraining, no portfolio strategy changes and no historical result replacement.

## Sources and evidence
1. Frozen original EU165 tickers `research/olc39_eu_holdings_identity_20261103/migration_acc_guarded_20261103/EU165_original_universe.csv`; exactly 165 symbols with venue suffix.
2. Independent **secondary, snapshot-current** public EU ETF metadata: `albertored/etfdb`, `csv/basic_info.csv`, **blob SHA adc45320a58233b4e744b95d419df5b454a9f57d**, 4,651 rows as retrieved 2026-11-03. It supplies ISIN, index, payouts, inception, provider, hedging, but **no venue-specific ticker** and is not a dated PIT holdings record. Match base ticker only provisionally; ambiguous or missing identities remain unverified. Material cases require issuer/exchange evidence separately. A 2026 fact-sheet is not proof of 2019 fund identity.
3. Historical EU OLC19 native state `EU_STATE_HALF.npz` within `OLC38_MINIMAL_EU_SOURCE.zip`, preserving 1,898 date ×167 symbol observed price mask, original `O`, timestamps, and no synthetic prelaunch Open. Relevant signals 2019-02-01 through 2026-06-30 and matched 2021–24. No imputed/cross-listed price accepted.

## Hard no-short-history and economic-equivalence rules
A **research-only eligible internal substitution** requires at minimum:
(a) original unambiguously identified Dist with issuer/index supported; candidate Acc unambiguously identified by ISIN; policy same benchmark **including index methodology**, hedged status, trading currency, and share-class type; (b) candidate's original observed Open series must start no later than 2019-02-01, yield >=500 genuine observed daily Opens before the 2021 first signal and >=1021/1026 observed Opens in 2021–24; (c) observed dates of overlap and first entry must be valid for each signal; (d) candidate must already be represented in EU165 for in-panel exact price verification, otherwise status `EXTERNAL_HISTORY_NOT_VERIFIED`; (e) no duplicate ticker/ISIN and no retrospective relabeling, pre-inception reconstruction, borrowed fund history or hidden universe-size decrease. An Acc matching an index but not an identical share class is `SAME_INDEX_DIFFERENT_FUND_REVIEW` even if data pass.

When any identity, payout, inception, tracking index, listing or observed-series check is incomplete, output `UNCHANGED_PENDING_VERIFICATION` and **retain Dist**. No action is taken on any candidate based solely on a secondary matching ticker. Potential replacements with equivalent index but changed hedging/FX/TER are not automatic.

## Audit procedures and gates
- Census all 165 and classify current status `ACC_MATCHED_SECONDARY`, `DIST_MATCHED_SECONDARY`, `UNKNOWN`. Preserve original 9 held Dist historicity statuses and compare against them; do not overwrite prior results silently.
- List possible Acc existing *inside* EU165 with exact normalized underlying index and economic exposure; validate observed mask/history/duplication. Other candidates outside EU165 must remain unverified until issuer/exchange identity and actual observed Xetra/other-venue history can be sourced.
- Produce unique full-universe CSV with each status, ISIN, effective inception if known, source version, candidate/economic eligibility reason, observed coverage; separate unresolved 12 with suggested targeted evidence requests.
- Report evidence by confidence level; never call current metadata PIT certification. A candidate with past price data but issuer merger / class renaming remains conditional until history is independently established.
- **Do not apply a substitution or infer CAGR** until a distinct approved experiment restores data quality, dividend total returns, identical universe dimensionality, model refits, and fully comparable execution accounting. Preserve USA 50.7722% OLC19 and 52.3006% OLC17 as historical benchmarks only.

Stop after census and report remaining gaps; no algorithm search, new model, or portfolio NAV in this audit. Source names and index from 2026 may not represent historical 2019–24 holdings or listing codes.
