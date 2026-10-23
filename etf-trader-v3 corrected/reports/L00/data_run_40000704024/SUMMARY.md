# V3 L00 CS: cross-sectional day-local minmax feature normalization

Frozen corrected-125 raw feature definitions and same 149 original ETF records. This report deliberately contains no CAGR or backtested portfolio P&L. The 101 months are exploratory historical, NOT a previously untouched holdout.

| variant          |   months |   universe_ic |   universe_top1 |   universe_top3 |   basket_top1 |   basket_top3 |   basket_ndcg3 |   basket_mrr_selected |   basket_selected_true_rank |   basket_regret |   basket_selected_excess |
|:-----------------|---------:|--------------:|----------------:|----------------:|--------------:|--------------:|---------------:|----------------------:|----------------------------:|----------------:|-------------------------:|
| CORRECTED        |      101 |      0.038536 |        0.089109 |        0.168317 |      0.145525 |      0.354713 |       0.542279 |              0.268193 |                     11.7674 |        0.104115 |                 0.007122 |
| L00_CS_MINMAX125 |      101 |      0.01436  |        0.079208 |        0.138614 |      0.146812 |      0.369861 |       0.52775  |              0.262046 |                     12.2958 |        0.106932 |                 0.004305 |

| variant          | metric        |   n_months |     delta |   ci95_low |   ci95_high |   exploratory_two_sided_p | unit                                                     |
|:-----------------|:--------------|-----------:|----------:|-----------:|------------:|--------------------------:|:---------------------------------------------------------|
| L00_CS_MINMAX125 | universe_ic   |        101 | -0.024176 |  -0.046422 |   -0.003623 |                  0.034    | paired calendar-month 6-month circular blocks, 6000 reps |
| L00_CS_MINMAX125 | basket_top3   |        101 |  0.015149 |  -0.012079 |    0.041802 |                  0.260333 | paired calendar-month 6-month circular blocks, 6000 reps |
| L00_CS_MINMAX125 | basket_ndcg3  |        101 | -0.01453  |  -0.029734 |    0.001591 |                  0.061667 | paired calendar-month 6-month circular blocks, 6000 reps |
| L00_CS_MINMAX125 | basket_regret |        101 |  0.002817 |  -0.001431 |    0.006697 |                  0.175333 | paired calendar-month 6-month circular blocks, 6000 reps |
