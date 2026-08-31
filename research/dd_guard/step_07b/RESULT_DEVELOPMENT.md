# STEP07B — development result

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remained sealed.

Development 2021–2022 versus frozen FUSION1:

- B1 EXPECTED_EXPOSURE: ΔCAGR **-0.3054 pp**, Δmean MaxDD **-0.3690 pp**, Δp10 **-0.5227 pp**.
- B2 EXPECTED_SUBSTITUTION: ΔCAGR **-0.3171 pp**, Δmean MaxDD **-0.3770 pp**, Δp10 **-0.5048 pp**.
- B3 Q10_FULL: ΔCAGR **-0.5787 pp**, Δmean MaxDD **-0.4150 pp**, Δp10 **-0.4825 pp**.

All three fail the preregistered quality-jump gate and both-year DD sign requirement.

A development-only oracle diagnostic is also negative for the DD-first objective: even perfect hindsight selection of the best 10-session utility action improves CAGR strongly but does not improve the FUSION1 mean-DD frontier materially and leaves p10 about 0.419 pp worse than FUSION1. A DD-only oracle also remains worse than FUSION1 mean MaxDD. This indicates that the one-day/terminal-episode implementation cannot reproduce FUSION1's sustained deep-tail protection even with perfect action labels.

This motivates a separate, explicitly preregistered persistent-state follow-up rather than retuning STEP07B.
