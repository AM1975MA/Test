# STEP07C — persistent action-value development result

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remained sealed.

The persistent state fixes the terminal-crash defect of STEP07A/B, but the direct treatment-advantage controller still fails the DD-first frontier:

- C1 EXPECTED_ADV_EXPOSURE: ΔCAGR vs FUSION1 **-0.5469 pp**, Δmean MaxDD **-0.4065 pp**, Δp10 **-0.6982 pp**.
- C2 EXPECTED_ADV_SUBSTITUTION: ΔCAGR **-0.6287 pp**, Δmean MaxDD **-0.4430 pp**, Δp10 **-0.7448 pp**.
- C3 Q10_ADV_FULL selects TV on 100% of decisions: ΔCAGR **+0.0296 pp**, Δmean MaxDD **-0.3610 pp**, Δp10 **-0.5227 pp**.

Development-only oracle ceiling is also decisive: a perfect-hindsight utility oracle on the persistent action set reaches roughly +1.21 pp CAGR vs FUSION1 but only +0.08 pp mean MaxDD and remains about -0.419 pp on p10. A DD-only oracle is worse than FUSION1. Thus the current action/state family cannot reach the preregistered +0.50 pp DD jump even with perfect action labels.
