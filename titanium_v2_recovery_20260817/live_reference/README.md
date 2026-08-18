# METEOR Titanium V2 + Opportunity V3 — regenerated live package

Generated directly from the ticker OHLCV matrices with a complete annual expanding walk-forward retraining.

## Configuration

- Downside volatility definition: `zero_std`
- Compact: three XGBRanker models, seeds 101/202/303, 360 trees
- TailMix: Ridge alpha 30
- Blend: 70% Compact / 30% TailMix
- Conditional macro bonus: +0.15
- Confidence-adaptive concentration: 100/0 or 75/25 at margin 0.12
- S3B clusters and four-model Opportunity layer
- Common causal 12-month Router schedule
- D+1 open execution, one-way costs, systemic governor and conditional stop

## Regenerated results

- Mean Router CAGR over 500 baskets: **18.5998%**
- Median Router CAGR: **17.9892%**
- Mean Base CAGR: **18.7349%**
- Global Router CAGR: **23.2613%**
- Global Direct CAGR: **23.5386%**

Frozen historical reference: Titanium V2 21.6541%, Opportunity Router 22.7428%. The regenerated result is explicitly reported separately and is not silently substituted for the frozen result.

## Usage

```bash
pip install -r requirements.txt
python METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE.py
```

Use `--basket SPY,QQQ,...` to restrict the live selection universe.
