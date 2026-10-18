# OASIS diagnostic preregistration: conditional opportunity value | 18 Oct 2026

**This is POST-RESULT scientific diagnosis**, NOT an untouched validation or a new strategy. The economic P0–P6 backtest is already frozen in `oasis/results/frozen_daily`; do not modify policy weights or tune thresholds. The aim is to understand why economic switches underperform specifically in crisis continuations, and whether factor-adjusted relative opportunity has any positive *conditional cross-sectional predictive rank skill*.

Use exact completed OASIS daily 2389-session calendar, 60 retrospective symbols and unmodified raw daily Open/Close from source. Signals are the close on `signal_date` (strictly before portfolio execution day). Future 5 and 21 session outcomes are used ONLY for **ex post auditing of prior signals**. Never feed future outcomes into a trading policy or call best-of-60 a realistically achievable return.

A) Conditional by as-of regime BREATHING / SHOCK / CONTINUATION / RECOVERY, report pooled mean and median same-day cross-sectional Spearman of OASIS factor-adjusted predicted relative efficiency and *subsequent* 5- and 21-session ETF Open-to-Open returns. Require >=20 eligible observed names per date. These labels overlap in time: not independent tests, no inferential p-values from naive daily observations.

B) Report as-of 21-session candidate Top2 realized next-21-session average log return **less cross-sectional realized median** and ex-post P90-P10 dispersion as an opportunity-richness upper-bound diagnostic, NOT an investable trade; report how many opportunities the score actually ranked correctly.

C) For each 1-for-1 economic switch P2, compare the newly acquired ticker's actual subsequent 21-session gross log return versus the removed ticker (at the SAME future opening dates), grouped by the as-of regime on switch day. This is diagnostic of decision quality only; returns of forward prices are not used for switches. Distinguish 0/1/multiple replacements and absence of future open prices.

D) Regime onset exploratory statistics: number of entries into SHOCK/CONTINUATION/RECOVERY, not just long series day counts; note when shifts occur in a short period.

E) Preserve exact diagnostics in immutable Git with source hashes. If crisis-relative predictability is weak, the correct next architectural change is factor-normalized **conditional predictive-calibration study**, not extra arbitrary switch triggers. No tuning on old EUR60.
