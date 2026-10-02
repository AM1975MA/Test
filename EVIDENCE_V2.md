# Evidence V2 — CLOSED

## Scopo

Evidence V1 e' chiusa. Original149 resta un development set fortemente burned e Holdout70 resta diagnostico/burned. Evidence V2 non riapre reranker, K sweep, allocation sweep o layer Hybrid24 respinti in V1.

La domanda generale era: **quale informazione realmente nuova, disponibile causalmente prima del segnale, puo' migliorare il retrieval cross-sectional senza riciclare varianti gia' respinte?**

## Regole scientifiche applicate

1. Ogni test salva nel repository sorgente, preregistrazione, workflow, provenance e risultati.
2. Un solo blocco informativo nuovo per test; nessuno sweep ex-post.
3. Original149 produce solo development evidence.
4. Holdout70 non viene usato per promotion.
5. Un PASS avrebbe richiesto un nuovo Holdout-B disgiunto prima di qualsiasi promotion claim.
6. Una linea respinta non viene riaperta con subset, trasformazioni, lookback, encoding o parametri vicini.

## Baseline frozen LTR

Sulle 114 date 2017-01-31 -> 2026-06-30:
- Top1 global winner: **10/114**;
- Top3: **21/114**;
- Top5: **32/114**;
- Top10: **47/114**;
- winner-rank median: **13.0**;
- mean IC21: **0.0060**;
- Top1 CAGR proxy: **22.0631%**;
- Top5-EW CAGR proxy: **20.3601%**.

Gate comune V2, tutti contemporaneamente:
1. Top5 > 32/114;
2. Top10 > 47/114;
3. Top1 >= 10/114;
4. Top1 CAGR proxy >= 22.0630708412%.

## V2.1 — macro context — REJECT / LINEA CHIUSA

Nuova informazione: sei feature causali da cinque serie FRED congelate (`VIXCLS`, `DGS2`, `DGS10`, `BAA10Y`, `DTWEXBGS`).

Run valido `37069663860`; risultati in `evidence_v2/results/retriever_macro_context_v1/`.

| Metrica | Frozen LTR | LTR + macro |
|---|---:|---:|
| Top1 | 10 | 10 |
| Top5 | 32 | 32 |
| Top10 | 47 | 53 |
| winner rank mediano | 13.0 | 11.5 |
| mean IC21 | 0.0060 | -0.0017 |
| Top1 CAGR | 22.06% | 13.85% |
| Top5-EW CAGR | 20.36% | 15.40% |

Gate: Top5 FAIL; Top10 PASS; Top1 PASS; CAGR FAIL.

Verdetto: **REJECT**. Nessun macro subset, lookback, trasformazione o tuning vicino consentito.

## V2.2 — semantic category context — REJECT / LINEA CHIUSA

Nuova informazione: sei indicatori one-hot della frozen `macro_category` taxonomy di Original149.

Run valido `37071806933`; risultati in `evidence_v2/results/retriever_category_context_v1/`.

Artifact:
- id `11254929144`;
- SHA256 `07aa9d0046cfaa4b506b429a5ccf332785f68c1b15b2a1c89e600a94b54c59a5`.

| Metrica | Frozen LTR | LTR + category |
|---|---:|---:|
| Top1 | 10 | 8 |
| Top3 | 21 | 20 |
| Top5 | 32 | 38 |
| Top10 | 47 | 55 |
| winner rank mediano | 13.0 | 11.0 |
| mean IC21 | 0.0060 | 0.0135 |
| Top1 CAGR | 22.06% | 12.21% |
| Top5-EW CAGR | 20.36% | 17.21% |

Gate: Top5 PASS; Top10 PASS; Top1 FAIL; CAGR FAIL.

Verdetto: **REJECT**. La tassonomia migliora la recall larga ma deteriora il vertice. Nessun category subset, alternate encoding, embedding o interaction tuning consentito.

## V2.3 — calendar context — REJECT / STOP RULE TRIGGERED

Nuova informazione: dodici indicatori one-hot `month_01` ... `month_12`, derivati unicamente da `signal_date` e quindi noti ex-ante.

Preregistrazione: `evidence_v2/protocols/RETRIEVER_CALENDAR_CONTEXT_V1_PREREG.md`.

Run valido `37072192617`; risultati in `evidence_v2/results/retriever_calendar_context_v1/`.

Artifact:
- id `11255195341`;
- SHA256 `419d86485e3d0d27c357506d68227c04604ca1ea1888035618afc1354ce0cc44`.

Result commit prima di questa chiusura: `50cc65293e431e9e8d300a28705f57bf8a01ffe8`.

| Metrica | Frozen LTR | LTR + calendar |
|---|---:|---:|
| Top1 | 10 | 8 |
| Top3 | 21 | 21 |
| Top5 | 32 | 31 |
| Top10 | 47 | 55 |
| winner rank mediano | 13.0 | 11.0 |
| mean IC21 | 0.0060 | 0.0088 |
| Top1 CAGR | 22.06% | 17.51% |
| Top5-EW CAGR | 20.36% | 17.11% |

Gate:
- Top5 >32: **FAIL**;
- Top10 >47: PASS;
- Top1 >=10: **FAIL**;
- Top1 CAGR >=22.06%: **FAIL**.

Verdetto: **REJECT**.

La preregistrata stop-rule scatta: non sono consentiti quarter, weekday, Fourier seasonality, alternate month encoding, calendar interaction, tuning vicino o ulteriori information-block test su Original149.

## Conclusione Evidence V2

1. Il frozen LTR resta il retriever development di riferimento.
2. Due classi informative nuove (`macro`, `semantic category`) e un ultimo contesto ex-ante (`calendar`) hanno mostrato in alcuni casi migliore Top10/Top5 recall, ma nessuna ha preservato o migliorato simultaneamente il vertice economico.
3. Il pattern piu' consistente e': **piu' informazione puo' allargare la recall senza migliorare la scelta Top1**.
4. Questo rafforza la conclusione di V1: il collo di bottiglia non e' soltanto trovare candidati plausibili, ma identificare causalmente il miglior estremo del mese.
5. Original149 e' ora definitivamente chiuso per nuove iterazioni Evidence V1/V2.
6. Holdout70 resta burned diagnostic only.
7. Non viene congelato Holdout-B, perche' nessuna architettura V2 ha superato il gate development preregistrato.

## Stato finale

- Branch: `research/evidence-v2`.
- V1 closure base commit: `071090ba85bfb4da9dff2b4b7d0a982b16d45aff`.
- V2.1 valid run: `37069663860`.
- V2.2 valid run: `37071806933`.
- V2.3 valid run: `37072192617`.
- Original149: **closed burned development set**.
- Holdout70: **burned diagnostic only**.
- Evidence V2: **CLOSED**.
