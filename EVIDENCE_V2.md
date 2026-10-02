# Evidence V2

## Scopo

Evidence V1 e' chiusa. Original149 resta un development set fortemente burned e Holdout70 resta diagnostico/burned. Evidence V2 non riapre reranker, K sweep, allocation sweep o layer Hybrid24 respinti in V1.

La domanda generale e': **quale informazione realmente nuova, disponibile causalmente prima del segnale, puo' migliorare il retrieval cross-sectional senza riciclare varianti gia' respinte?**

## Regole

1. Ogni test salva nel repository sorgente, preregistrazione, workflow, provenance e risultati.
2. Un solo blocco informativo nuovo per test; nessuno sweep ex-post.
3. Original149 puo' produrre solo development evidence.
4. Holdout70 non puo' essere usato per promotion.
5. Se una nuova architettura supera il gate preregistrato, il passo successivo e' congelare un nuovo Holdout-B disgiunto prima di qualunque claim di promotion.
6. Una linea informativa respinta non viene riaperta con subset, trasformazioni, lookback, serie alternative o parametri vicini sullo stesso Original149.

## V2.1 — macro context — REJECT / LINEA CHIUSA

Dataset congelato: `evidence_v2/data/macro_context_v1/`.

Test valido:
- run `37069663860`;
- risultati `evidence_v2/results/retriever_macro_context_v1/`.

| Metrica | Frozen LTR | LTR + macro |
|---|---:|---:|
| Top1 global winner | 10/114 | 10/114 |
| Top5 global winner | 32/114 | 32/114 |
| Top10 global winner | 47/114 | 53/114 |
| winner rank mediano | 13.0 | 11.5 |
| mean IC21 | 0.0060 | -0.0017 |
| Top1 CAGR proxy | 22.06% | 13.85% |
| Top5-EW CAGR proxy | 20.36% | 15.40% |

Gate: Top5 FAIL; Top10 PASS; Top1 PASS; Top1 CAGR FAIL.

**Verdetto: REJECT.** Nessun subset delle serie, lookback alternativo, diversa trasformazione, normalizzazione o tuning vicino e' consentito su Original149.

## V2.2 — semantic category context — REJECT / LINEA CHIUSA

Nuova informazione: i sei valori statici e frozen di `macro_category` presenti in `evidence_v1/data/original149/universe.csv`, codificati one-hot:
- `C01_US_BROAD_STYLE`;
- `C02_US_SECTOR_THEME`;
- `C03_DEVELOPED_GLOBAL`;
- `C04_EMERGING`;
- `C05_BONDS_CASH_CREDIT`;
- `C06_REAL_ASSETS`.

Il test mantiene identici modello LTR, target, hyperparametri, annual expanding walk-forward e maturity gate; unica modifica: `FEATURES_42 + 6 category one-hot`.

Preregistrazione: `evidence_v2/protocols/RETRIEVER_CATEGORY_CONTEXT_V1_PREREG.md`.

Run valido `37071806933`; risultati durabili in `evidence_v2/results/retriever_category_context_v1/`.

Artifact:
- id `11254929144`;
- SHA256 `07aa9d0046cfaa4b506b429a5ccf332785f68c1b15b2a1c89e600a94b54c59a5`.

| Metrica | Frozen LTR | LTR + category |
|---|---:|---:|
| Top1 global winner | 10/114 | 8/114 |
| Top3 global winner | 21/114 | 20/114 |
| Top5 global winner | 32/114 | 38/114 |
| Top10 global winner | 47/114 | 55/114 |
| winner rank mediano | 13.0 | 11.0 |
| mean IC21 | 0.0060 | 0.0135 |
| Top1 CAGR proxy | 22.06% | 12.21% |
| Top5-EW CAGR proxy | 20.36% | 17.21% |

Gate:
- Top5 >32: PASS;
- Top10 >47: PASS;
- Top1 >=10: **FAIL**;
- Top1 CAGR >=22.06%: **FAIL**.

**Verdetto vincolante: REJECT.** La categoria semantica migliora la recall larga ma non la scelta estrema. Non sono consentiti category subset, encoding alternativi, embedding, interactions o model tuning vicino su Original149.

## V2.3 — calendar context — ULTIMO TEST ORIGINAL149

V2.3 introduce una classe informativa differente sia dalle feature tecniche/cluster, sia dal macro-context, sia dalla tassonomia semantica: **mese dell'anno noto ex-ante**.

Una sola modifica ammessa:
- aggiungere 12 indicatori binari `month_01` ... `month_12`, derivati esclusivamente da `signal_date`.

Modello, target, hyperparametri, walk-forward, maturity gate e comparator restano identici al frozen LTR v1.

Gate identico e preregistrato, tutti contemporaneamente:
1. Top5 > 32/114;
2. Top10 > 47/114;
3. Top1 >= 10/114;
4. Top1 CAGR proxy >= 22.0630708412%.

**Stop rule:** V2.3 e' l'ultimo nuovo information-block test su Original149. Se fallisce, Evidence V2 viene chiusa sul development set e non si provano quarter, weekday, Fourier seasonality, alternate calendar encodings o altre varianti. Se passa, non si fanno altri test su Original149: si congela un nuovo disjoint Holdout-B prima di promotion.

## Stato ipotesi

1. Frozen LTR resta il riferimento: Top5 32/114, Top10 47/114, Top1 10/114, Top1 CAGR 22.06%.
2. Macro context: respinto; migliora solo Top10 e peggiora l'economia del vertice.
3. Semantic category context: respinto; migliora Top5/Top10 ma peggiora Top1 e CAGR.
4. V2.3 calendar context e' l'ultimo test Original149 consentito.
5. Holdout70 resta escluso da promotion.

## Frozen state V2

- Branch: `research/evidence-v2`.
- V1 closure base commit: `071090ba85bfb4da9dff2b4b7d0a982b16d45aff`.
- Valid macro run: `37069663860`.
- Valid category run: `37071806933`.
- Category result commit before this source-of-truth update: `2dd67f8a86db610a6757865e09c83f73a09f80dc`.
- Original149: burned development only.
- Holdout70: burned diagnostic only, never promotion.
