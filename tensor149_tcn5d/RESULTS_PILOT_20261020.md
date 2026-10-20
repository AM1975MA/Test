# Original149 Tensor 5D — listwise pilot and negative-control results (2026-10-20)

Research branch: research/original149-tcn-listwise-20261020. Source of truth: 149 frozen original ETF CSVs, roster SHA256 7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6. Production unchanged.

## Matched pilot 2024–2025, 100 weekly 5-session next-open decisions, long-only equally-weighted Top5, 20bp full roundtrip

| Model | CAGR net | MaxDD | Sharpe | RankIC | true Top5 overlap |
|---|---:|---:|---:|---:|---:|
| TCN SmoothL1 pointwise frozen | 10.0677% | −27.5291% | .5561 | +.05879 | 5.2% |
| Ridge125 | 8.2333% | −25.4719% | .4595 | +.07438 | 4.8% |
| Past21 momentum | 10.4242% | −24.8602% | .5026 | −.03721 | 15.2% |
| ListNet full 149 | 22.0920% | −25.3024% | .8648 | +.02240 | 19.2% |
| ListMLE true Top5 | 13.1720% | −23.0711% | .5934 | +.02382 | 19.2% |
| ListNet + relative-return Huber | **26.8993%** | **−22.3077%** | **.9971** | +.03187 | **20.2%** |

Listwise primary artifact: https://github.com/AM1975MA/Test/actions/runs/39457056544
Original Pointwise baseline: https://github.com/AM1975MA/Test/actions/runs/39455195643

Independent date-aligned paired bootstrap: https://github.com/AM1975MA/Test/actions/runs/39457712305
Hybrid minus Pointwise mean true Top5 overlap +15pp, descriptive 95% 5-week circular-block CI [+10,+20]pp. Mean RankIC difference −0.02692, CI [−.0810,+.0286], indistinguishable from zero under this exploratory block assumption. All three challenged objectives pass query permutation gradient checks and 125-feature canonical monthly parity.

## Risk-only negative controls

Same frozen 149 and 100 dates: max vol21 alone gives CAGR −5.3753%, MaxDD −29.9917%, Top5 overlap 19.2%; max vol63 CAGR +13.7786%, MaxDD −22.7474%, overlap 18.8%; downside vol21 CAGR +13.2294%, MaxDD −29.2974%, overlap 14.2%. Control action: https://github.com/AM1975MA/Test/actions/runs/39458064851. True Top5 winner-hit statistic can arise almost entirely from the volatility exposure, so economic superiority and risk-adjusted matched tests matter.

## Earlier registered full Pointwise baseline (2017–2026; 476 decisions)

SmoothL1 TCN CAGR 5.1942%, MaxDD −48.4929%, RankIC .05609; Ridge CAGR 5.1314%, MaxDD −50.4393%, RankIC .05434; past21 momentum CAGR 13.4143%, MaxDD −34.9415%, RankIC −.00565. Source https://github.com/AM1975MA/Test/actions/runs/39455244701.

Full 2017–2026 LISTWISE replay is a separate required result. No unverified figures or production adoption. Historical original ETF universe has survival/selection bias and previously explored data; Yahoo adjusted open is not broker-fill evidence.
