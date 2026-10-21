# V3 L01 — capacity vs ranking loss: completed paired predictive benchmark

**Research gate:** L01-CAPACITY/LOSS **CLOSED — TWO ALTERNATIVES REJECTED**. Maintain CORRECTED125 + 127-leaf XGBRanker with rank:pairwise for subsequent isolated layer tests. No claim that 127 is a globally optimal model.

## Provenance

[Successful GitHub Actions run 39652989033](https://github.com/AM1975MA/Test/actions/runs/39652989033), OOS artifact **12370810593** (`v3-l01-paired-ranking-results`), 2018–May 2026 **101 fully matured months**.

- Immutable 149-ETF OHLCV snapshot from run **39482809691**, 500 original baskets ×24 ETF, 2012-start expanding training, each year's forward 21-day label matured before fitting.
- Frozen **CORRECTED125** features in `etf-trader-v3 corrected/src/etf_trader_v3/source_only/kernel.py`. No feature changes. The archived and independently fitted 127-leaf pairwise baseline scores are from successful run **39515716383**.
- Newly fitted two arms, same 360 boosting rounds and seeds `101,202,303`, identical training/test membership:
  - `L01_PAIR63`: change tree leaf maximum 127 → 63, retain `rank:pairwise`.
  - `L01_NDCG127`: retain 127 leaves, change loss to `rank:ndcg` with `ndcg_exp_gain=False`, `lambdarank_pair_method=topk`, `lambdarank_num_pair_per_sample=3`.
- NO Tail, regime, expert blend, allocation, risk overlay, CAGRs or portfolio P&L. This is a **predictive-capability** benchmark, not financial-performance optimization.
- The research calendar 2018–2026 was explored previously; this is **not a virgin temporal holdout**.

## 101-month functional accuracy

| Metric | CORRECTED125-PAIR127 | L01_PAIR63 | L01_NDCG127 |
|---|---:|---:|---:|
| Spearman universe IC | 0.038536 | 0.040037 | **0.057612** |
| ETF-universe Top-1 capture | **8.911%** | 2.970% | 1.980% |
| ETF-universe Top-3 capture | **16.832%** | 12.871% | 3.960% |
| Basket Top-1 winner capture | **14.553%** | 12.816% | 5.612% |
| Basket Top-3 winner capture | **35.471%** | 32.244% | 17.774% |
| Basket nDCG@3 (linear rank relevance) | 0.542279 | 0.537899 | **0.544463** |
| Basket mean reciprocal future rank of selected | **0.268193** | 0.250572 | 0.178886 |
| Basket mean true rank of selected (1 best) | **11.767** | 11.919 | 11.901 |
| 21-trading-day mean basket regret (return points) | **0.104115** | 0.106998 | 0.108558 |

## Abbinamento mensile e incertezza

500 baskets are heavily overlapping and first aggregated **within calendar month**. Monthly paired differences use circular blocks of 6 months, 6000 replicates, and exploratory Holm adjustment for two tested arms:

- Pair63 minus Pair127 basket Top-3 **−3.228 pp**, 95% interval **[−4.408,−2.149] pp**, Holm exploratory p≈0.
- NDCG127 minus Pair127 basket Top-3 **−17.697 pp**, 95% interval **[−21.658,−13.772] pp**, Holm p≈0.
- Pair63 minus Pair127 universe IC **+0.001501**, interval **[−0.006444,+0.009046]**.
- NDCG127 minus Pair127 universe IC **+0.019076**, interval **[−0.002233,+0.039026]**.
- NDCG127 nDCG@3 improves merely **+0.002184**, interval **[−0.020403,+0.024873]** — not a substantive nDCG improvement.
- Both alternatives worsen intrinsic winner recall, especially the NDCG loss. The fact that aggregate Spearman can increase while winner retrieval deteriorates proves a single IC objective is an inadequate gate for the current user goal.

## Decision / next gate

**REJECT** both alternatives. **LOCK** L01 research reference as original `rank:pairwise` 127-leaf, corrected 125-column input, 360 rounds, three seeds. Preserve all rejected scores/artifacts and rerun a new predeclared one-variable challenger in a later L01 subgate only if supported by a specific failure mechanism. The baseline may still be imperfect; do not confuse "winner among tested arms" with "globally optimal".

**Next distinct layer:** L02 Tail. Evaluate its original objective — predicting the *upper tail of subsequent ETF winners* — and its 15 exact duplicate columns **without modifying the locked L01 ranker**. Test Tail separately on matured 63-day labels, using top-decile winner recall and tail false selections, not the CAGR of a blended strategy.
