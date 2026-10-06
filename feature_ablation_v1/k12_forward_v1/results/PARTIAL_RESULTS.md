# K12 forward ablation — partial results

Source run: `37530678164`

| Variant | N | Rank-MAD improvement | Top1 disagreement | NDCG@5 ratio | Top5 ratio | Advance |
|---|---:|---:|---:|---:|---:|---|
| K13_A | 13 | 20.72% | 47.50% | 97.75% | 95.03% | NO |
| K13_M | 13 | 16.87% | 41.94% | 93.59% | 78.42% | NO |
| K14_ES | 14 | 12.33% | 47.50% | 95.76% | 79.40% | NO |
| K14_SM | 14 | 16.29% | 39.17% | 93.28% | 73.27% | NO |
| K15_AEM | 15 | 16.53% | 40.00% | 93.83% | 89.17% | NO |
| K15_ASM | 15 | 20.52% | 35.56% | 94.20% | 86.86% | NO |

Current lead: **K13_A = K12 + autocorr1_63**. It preserves both predictive gates (NDCG 97.75% of BASE, Top5 95.03% of BASE) but improves Rank-MAD by 20.72%, below the frozen 25% stability threshold.

These are partial results; no adoption decision is made until the preregistered decisive A-combinations finish.
