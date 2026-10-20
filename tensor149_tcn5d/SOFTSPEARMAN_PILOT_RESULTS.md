# Genuine torchsort SoftSpearman pilot results, Original149, 2026-10-20

Test protocol frozen in SOFTSPEARMAN_PREREGISTRATION.md. Unchanged immutable Original149 149 daily ETF datasets, 125 daily features, 30-session causal TinyTCN, 5-session forward next-open returns, annual walk-forward splits, 100 out-of-sample weekly decision dates 2024–25, same fixed top5 long allocation and roundtrip fees 20bps. PyTorch 2.6.0 CPU with official prebuilt torchsort 0.1.10 pt26cpu wheel; prior 2026 Pointwise used torch2.7.1.

| Model | Net CAGR | MaxDD | Sharpe | Mean raw future RankIC | Raw oracle Top5 overlap |
|---|---:|---:|---:|---:|---:|
| Original Pointwise TCN | +10.0677% | −27.5291% | .5561 | +.05879 | 5.2% |
| Original MOM21 | +10.4242% | −24.8602% | .5026 | −.03721 | 15.2% |
| SOFTSPEARMAN | +4.0455% | −19.3039% | .3260 | +.04865 | 0.8% |
| SOFTSPEARMAN_RETURN (0.30 relative return) | −4.8778% | −25.7999% | −.1819 | +.04836 | 2.4% |
| SOFTSPEARMAN_TOP5 (5× truth-top5 weighted correlation) | +24.2102% | −19.0824% | .9511 | +.05503 | 19.8% |

The Top5-weighted variant improves pilot costed CAGR and reduces maxdrawdown compared to Pointwise and MOM21, and has high raw top5 oracle overlap, but does NOT improve the all ETF mean RankIC vs Pointwise. Positive pilot alone is not primary evidence, because previous 2026 ListNet hybrid similarly showed +26.90% net CAGR 2024–25 but −1.58% over 2017–26.

No change of hyperparameters or variants after this pilot. Primary test is all 476 weekly decisions 2017–2026. True differentiability tests of continuous ranks, sign, permutation and gradients passed for all 3 losses and all 6 runners; genuine torchsort soft_rank used in each gradient step.

Pilot action: https://github.com/AM1975MA/Test/actions/runs/39473836762
