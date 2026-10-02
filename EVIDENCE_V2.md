# Evidence V2

## Scopo

Evidence V1 e' chiusa. Original149 resta un development set fortemente burned e Holdout70 resta diagnostico/burned. Evidence V2 non riapre reranker, K sweep, allocation sweep o layer Hybrid24 respinti in V1.

La nuova domanda e': **informazione macro esterna, disponibile causalmente prima del segnale, migliora il ranking cross-sectional del retriever LTR senza cambiare modello, label o hyperparametri?**

## Regole

1. Ogni test salva nel repository sorgente, preregistrazione, workflow, provenance e risultati.
2. Un solo blocco informativo nuovo per test; nessuno sweep ex-post.
3. Original149 puo' produrre solo development evidence.
4. Holdout70 non puo' essere usato per promotion.
5. Se una nuova architettura supera il gate preregistrato, il passo successivo e' congelare un nuovo Holdout-B disgiunto prima di qualunque claim di promotion.
6. Se il test macro-context fallisce, non si provano subset, trasformazioni, lookback o serie alternative sugli stessi 149 ETF.

## V2.1 — macro context

### Nuova informazione

Cinque serie FRED di mercato, non presenti nelle 42 feature del retriever LTR v1:
- `VIXCLS` — CBOE VIX;
- `DGS2` — Treasury 2Y;
- `DGS10` — Treasury 10Y;
- `BAMLH0A0HYM2` — US High Yield option-adjusted spread;
- `DTWEXBGS` — broad trade-weighted US dollar index.

Da queste vengono congelate **esattamente sei** feature di contesto, definite prima del test:
- `vix_z252`;
- `dgs2_delta21`;
- `dgs10_delta21`;
- `curve_10y2y_z252`;
- `hy_oas_z252`;
- `usd_ret21`.

Per evitare ambiguita' temporali, al segnale mensile il modello puo' usare solo l'ultima osservazione macro con data **strettamente precedente** alla `signal_date`.

### Modello

Identico Retriever LTR v1:
- XGBoost `rank:ndcg`;
- stessi hyperparametri;
- stessa label `target_relevance`;
- stesso annual expanding walk-forward;
- stesso maturity gate `exit_date_63 < cutoff`.

Unica modifica ammessa: `FEATURES_42 + 6 macro-context features`.

### Gate development preregistrato

Il modello macro-context avanza solo se, sulle stesse 114 date 2017-01-31 -> 2026-06-30:
1. Top5 global-winner count > **32/114**;
2. Top10 global-winner count > **47/114**;
3. Top1 exact-winner count >= **10/114**;
4. Top1 21d CAGR proxy >= **22.0630708412%**.

Tutti e quattro devono essere veri. IC, NDCG, subperiodi e altre metriche sono diagnostici.

## Fase corrente

A. Congelare il blocco macro in `evidence_v2/data/macro_context_v1/` con URL, raw files, hash e trasformazioni.
B. Solo dopo il freeze, preregistrare e lanciare un singolo retriever macro-context.
