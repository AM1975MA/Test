# K13_A — Original149 three-repeat confirmation

K13_A is confirmed on the exact three sequential Original149 Yahoo downloads.

Lineage:
- raw acquisition run: `37121749852`
- artifact: `yfinance-repeatability-v1-raw`
- repeats: `_repeat1`, `_repeat2`, `_repeat3`
- 149 ETFs in every repeat
- Titanium internal run `37150436612` explicitly downloaded that raw artifact and rebuilt each repeat from its corresponding raw directory before producing the three `TI_COMPACT` panels.

## K13_A result

K13_A = K12 + `autocorr1_63`.

| Metric | K13_A |
|---|---:|
| Rank-MAD | 0.042381 |
| Rank-MAD improvement vs BASE | 20.72% |
| Stability Spearman | 0.977912 |
| Top1 disagreement | 47.50% |
| NDCG@5 | 0.534279 |
| NDCG@5 vs BASE | 97.75% |
| Top5 realized overlap | 11.89% |
| Top5 vs BASE | 95.03% |

Pairwise Top1 disagreement:
- Repeat1 vs Repeat2: 51.67%
- Repeat1 vs Repeat3: 48.33%
- Repeat2 vs Repeat3: 42.50%

## Decision

**KEEP AS LEADING CANDIDATE, NOT ADOPTED.**

The predictive-quality floors are preserved on the exact Original149 three-repeat lineage. Stability improves materially, but Rank-MAD improves by 20.72%, below the preregistered 25% requirement, and the first-ranked ETF still changes too often.
