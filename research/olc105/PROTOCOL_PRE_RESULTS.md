# OLC105 — Trade Republic / fresh instrument portability test

Registered 2026-11-14 before acquiring candidate returns. Research only. No orders, no change to main, OLC19, OLC67 or existing scheduled tasks.

## Question
Can the frozen OLC19 and OLC67 recipes transfer to previously unused European-listed instruments representing the original six US economic macro-groups, including global/World exposures, under Trade Republic-aware costs and execution constraints?

## Source and novelty contract
1. Download the official Italy Trade Republic instrument catalogue. Identify funds by ISIN, not by trading ticker alone. Catalogue inclusion is evidence of published offering, not certification of availability in a specific account or historical availability.
2. Screen candidate ISINs and listing aliases against the original EU165/USA149 rosters, the October repository evidence export and available subsequent research artifacts. Mark the coverage and limitations; absence of a string is not proof that an exposure was never studied.
3. Freeze the candidate roster and deterministic data eligibility rules in a second metadata-only commit BEFORE inspecting investment outcomes. Prefer EUR listings of unlevered UCITS ETFs. Do not silently substitute ETCs, leveraged products, inverse products or a different share class.
4. New Yahoo downloads are retrospective data vintages. Different funds on the same indices are not independent economic holdouts. No past period will be relabelled prospective.
5. yfinance capture stores unadjusted OHLCV, adjusted prices, dividends and splits, provider metadata, download timestamp and SHA256; original histories remain unchanged. As-of upper limit 2026-11-13, only completed sessions. No invented prices or backfill of an ETF before inception.

## Model and comparison contract
Primary test: portability of the original annual frozen models and original OLC19/OLC67 recipes to a separately normalized candidate universe, without fitting to candidate outcomes or choosing a winner after results. This changes the investment universe and hence is NOT a byte-identical production strategy. Historical source model parity is required before attributing results to the original model family.
Keep selection, allocation, timing and protection separate: contextual Top2; HALF vs MINVAR63 cap25/75 at original signal date; IMMEDIATE vs native DELAY3; V6/FAST_LOCK3 fixed. Use an eligible broad World passive and a simple same-universe momentum reference as controls. No parameter sweeps. Report all declared arms, including negative results and failed gates.
If source models or a required data contract cannot be reproduced, fail the affected ML arm explicitly; never substitute a momentum strategy and name it OLC19.

## Broker and accounting contract
Review current official Trade Republic Italy pricing, execution venues, order types and fractional-order limitations. Use EUR as portfolio numeraire for European listings. Run declared sensitivity scenarios for account sizes EUR 5,000 / 10,000 / 50,000 (scenarios, not the user's capital), ticket fee EUR 1 and EUR 2 according to currently documented execution modes, and assumed per-side implementation shortfall of 5/15/30 bp, separately labelled assumptions rather than observed spreads. Never map daily Yahoo Open/Low to a certified Trade Republic fill. Whole-share / fractional constraints and same-session buy-stop sequencing are explicit readiness checks.
No live trading recommendation from historical CAGR. Stop barriers are not guaranteed maximum losses. Broker quote/fill history, account availability, taxes and point-in-time universes remain separate gates.

## Delivery and safety
Publish code, roster, source capture audit, complete results or explicit blockers, tests and report on this research branch. Preserve raw downloads and manifests. No credentials or account details. No execution permissions beyond GitHub research-file writes. Separate mechanical reproducibility, predictive evidence, legal/product accessibility and executable brokerage readiness.
