# 2026-10-28: verificata prova residual momentum EU148/EU155 vs US149

**Stato: 60 backtest REALMENTE ESEGUITI localmente, research only. Non validato come miglioramento.**

Fonti 6 studi accademici su residual/time-series momentum, crash, risk scaling, intermediate return e statistical backtest overfitting: Blitz/Huij/Martens JEF 2011 DOI 10.1016/j.jempfin.2011.01.003; Moskowitz/Ooi/Pedersen JFE 2012 DOI 10.1016/j.jfineco.2011.11.003; Daniel/Moskowitz JFE 2016 DOI 10.1016/j.jfineco.2015.12.002; Barroso/Santa-Clara JFE 2015 DOI 10.1016/j.jfineco.2014.11.010; Novy-Marx JFE 2012 DOI 10.1016/j.jfineco.2011.05.003; Bailey et al. Journal Computational Finance DOI 10.21314/JCF.2016.322. Titoli e abstract verificati in fonti editoriali, non si pretende lettura integrale dell'intera letteratura.

**Metodologia:** 101 segnali mensili, B0 stesso calendario mercati 2076 giornate, capitale EUR, 0.1% fee one-way, same next real Open. ETF EU148 original frozen, EU155 repaired plus 7 new, 149 US original. EU quality gate as-of: last 63 sessions 90% volume positive + ADV median >50k; US nessun filtro. Single local market beta rolling prior 126 sessions; resid12-1 = ETF close(t-21)/close(t-252)-1 minus beta(t)_prior126 × benchmark MOM12-1 (EXSA Europe or SPY US). **Proxy monofattoriale** del residual momentum, non portafoglio multifattoriale azionario della ricerca originale. Fixed Top3/Top5; 6 scorers (MOM252, MOM12-1, residual12-1, residual/vol126, momentum-residual half rank, LM reference): **60 arms**.

## Top5 annual CAGR netto EUR

| Model | EU148 as-of liquid | EU155 as-of liquid | US149 baseline |
|---|---:|---:|---:|
| MOM252 | **+8.2164%** | **+8.7995%** | **+21.2274%** |
| MOM12-1 | +6.0738% | +6.2849% | +13.5656% |
| RESIDUAL12-1 | +7.2330% | +7.2365% | +12.2940% |
| RESIDUAL12-1/vol126 | +6.6086% | +6.4749% | +6.4271% |
| blended 50/50 ranks | +8.483% | +8.157% | +11.536% |

On EU155 residual/vol DD −23.4848%, versus momentum252 DD −35.3486%, BUT lower CAGR. EU155 liquid residual-vs-MOM12-1 monthly log-return annual improvement +0.917pp nominal 6m block CI95 [-1.130,+3.176], zero included; EU148 +1.112pp CI [-0.817,+3.227]. No statistical proof. Top5 US residual-versus-MOM12-1 +0.078pp log-ann with interval [-5.093,+6.145]; relative to **MOM252** US loses almost 9pp CAGR.

**Parity audit**: EU148 frozen MOM252 Top5 daily NAV against B0 original **EXACT zero max abs error** across 2076 dates. US149 diff daily NAV max 0.00505 due to FX proxy, CAGR −~0.01pp from original. No holding execution missing Open; EU occasional Yahoo zero volume trades (not executable price verification).

All original code, 60 economics arms, 101 monthly full selections per arm, causal beta/score vectors for three universes, 2076x60 daily NAV, 4000 bootstrap paired draws stored in ChatGPT file `V3_RESIDUAL_MOMENTUM_EU155_USA149_60_BACKTEST_20261028.zip`, reproducible source `residual_momentum_20261028.py`, input frozen zips retained. Data EU155 chosen in 2026 have survivorship/lookback; 2018–26 repeatedly explored, not genuine unseen OOS. Stock residual momentum academic results **do not automatically transfer** to these ETF sets. No production updates. **Reject** as economic replacement; optional risk-related study only.
