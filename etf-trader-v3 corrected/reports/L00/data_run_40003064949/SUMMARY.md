# V3 L00 CS2: adaptive 125 original + 46 normalized

Frozen corrected-125 raw feature definitions and same 149 original ETF records. This report deliberately contains no CAGR or backtested portfolio P&L. The 101 months are exploratory historical, NOT a previously untouched holdout.

| variant       |   months |   universe_ic |   universe_top1 |   universe_top3 |   basket_top1 |   basket_top3 |   basket_ndcg3 |   basket_mrr_selected |   basket_selected_true_rank |   basket_regret |   basket_selected_excess |
|:--------------|---------:|--------------:|----------------:|----------------:|--------------:|--------------:|---------------:|----------------------:|----------------------------:|----------------:|-------------------------:|
| CORRECTED     |      101 |      0.038536 |        0.089109 |        0.168317 |      0.145525 |      0.354713 |       0.542279 |              0.268193 |                     11.7674 |        0.104115 |                 0.007122 |
| L00_CS_ADD171 |      101 |      0.019145 |        0.049505 |        0.158416 |      0.143941 |      0.368713 |       0.532253 |              0.261674 |                     12.2367 |        0.106405 |                 0.004832 |

| variant       | metric        |   n_months |     delta |   ci95_low |   ci95_high |   exploratory_two_sided_p | unit                                                     |
|:--------------|:--------------|-----------:|----------:|-----------:|------------:|--------------------------:|:---------------------------------------------------------|
| L00_CS_ADD171 | universe_ic   |        101 | -0.01939  |  -0.034551 |   -0.004536 |                  0.009667 | paired calendar-month 6-month circular blocks, 6000 reps |
| L00_CS_ADD171 | basket_top3   |        101 |  0.014    |  -0.006119 |    0.034713 |                  0.198    | paired calendar-month 6-month circular blocks, 6000 reps |
| L00_CS_ADD171 | basket_ndcg3  |        101 | -0.010026 |  -0.022826 |    0.003622 |                  0.140333 | paired calendar-month 6-month circular blocks, 6000 reps |
| L00_CS_ADD171 | basket_regret |        101 |  0.00229  |  -0.001102 |    0.005598 |                  0.170667 | paired calendar-month 6-month circular blocks, 6000 reps |
