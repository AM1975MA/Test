# Evidence V2

## Scopo

Evidence V1 e' chiusa. Original149 resta un development set fortemente burned e Holdout70 resta diagnostico/burned. Evidence V2 non riapre reranker, K sweep, allocation sweep o layer Hybrid24 respinti in V1.

La nuova domanda generale e': **quale informazione realmente nuova, disponibile causalmente prima del segnale, puo' migliorare il retrieval cross-sectional senza riciclare varianti gia' respinte?**

## Regole

1. Ogni test salva nel repository sorgente, preregistrazione, workflow, provenance e risultati.
2. Un solo blocco informativo nuovo per test; nessuno sweep ex-post.
3. Original149 puo' produrre solo development evidence.
4. Holdout70 non puo' essere usato per promotion.
5. Se una nuova architettura supera il gate preregistrato, il passo successivo e' congelare un nuovo Holdout-B disgiunto prima di qualunque claim di promotion.
6. Una linea informativa respinta non viene riaperta con subset, trasformazioni, lookback, serie alternative o parametri vicini sullo stesso Original149.

## V2.1 — macro context — REJECT / LINEA CHIUSA

### Dati congelati

Dataset: `evidence_v2/data/macro_context_v1/`.

Cinque serie FRED:
- `VIXCLS` — CBOE VIX;
- `DGS2` — Treasury 2Y;
- `DGS10` — Treasury 10Y;
- `BAA10Y` — Baa corporate spread vs Treasury 10Y;
- `DTWEXBGS` — broad trade-weighted US dollar index.

Sei feature preregistrate:
- `vix_z252`;
- `dgs2_delta21`;
- `dgs10_delta21`;
- `curve_10y2y_z252`;
- `baa10y_z252`;
- `usd_ret21`.

L'iniziale `BAMLH0A0HYM2` e' stato sostituito prima di qualunque model fit valido perche' FRED nel 2026 ne rende disponibile solo una storia triennale; il quality gate aveva bloccato il freeze. La correzione di disponibilita' e' documentata in `evidence_v2/protocols/MACRO_CONTEXT_V1_CREDIT_SERIES_AVAILABILITY_FIX.md`.

Macro freeze valido:
- run `37069091858`;
- artifact `11253653940`;
- artifact SHA256 `067c8441b339cdc0365267242a86ab02d35ac90a3d95b10add17eb4db85e37e9`;
- `MACRO_DAILY.csv` SHA256 `a07b47d11784e5895fbd59f4a416671d6708f06bd12619b963a5b6c83f1d0474`;
- manifest SHA256 `87da30de5f534bf369ddcba7bcab5d331c6542f08b179499d61e4504543e27f2`;
- copertura delle sei feature dal 2007: 100%.

### Test preregistrato

Modello identico Retriever LTR v1 (`rank:ndcg`, stessi hyperparametri, stessa label, annual expanding, maturity `exit_date_63 < cutoff`), con unica modifica `FEATURES_42 + 6 macro features`.

Allineamento macro: ultima osservazione con `macro_date < signal_date`.

Gate richiesto, tutti contemporaneamente:
1. Top5 > 32/114;
2. Top10 > 47/114;
3. Top1 >= 10/114;
4. Top1 CAGR proxy >= 22.0630708412%.

Il primo run modello `37069284576` e' invalido per un errore tecnico del comparator: il frozen LTR checkpoint non contiene `fwd_ret_21`; il workflow e' stato corretto unendo score congelati e outcome del panel source-only sul key `(signal_date,ticker)`, come richiesto dal checkpoint stesso. Nessuna metrica era stata persistita o stampata prima del traceback. Fix documentato in `evidence_v2/protocols/RETRIEVER_MACRO_CONTEXT_V1_BASELINE_JOIN_FIX.md`.

### Risultato valido

Run `37069663860`; risultati durabili in `evidence_v2/results/retriever_macro_context_v1/`.

| Metrica | Frozen LTR | LTR + macro |
|---|---:|---:|
| Top1 global winner | 10/114 | 10/114 |
| Top3 global winner | 21/114 | 21/114 |
| Top5 global winner | 32/114 | 32/114 |
| Top10 global winner | 47/114 | **53/114** |
| winner rank mediano | 13.0 | **11.5** |
| mean IC21 | 0.0060 | -0.0017 |
| Top1 CAGR proxy | **22.06%** | **13.85%** |
| Top5-EW CAGR proxy | **20.36%** | **15.40%** |

Gate:
- Top5 >32: **FAIL**;
- Top10 >47: PASS;
- Top1 >=10: PASS;
- Top1 CAGR >=22.06%: **FAIL**.

**Verdetto vincolante: REJECT.** Il macro-context migliora la recall profonda Top10 ma non il Top5 e deteriora materialmente il valore economico del vertice. Nessun subset delle serie, lookback alternativo, diversa trasformazione, diversa normalizzazione o tuning vicino e' consentito su Original149.

## Stato ipotesi dopo V2.1

1. LTR resta il retriever development di riferimento: Top5 32/114, Top10 47/114, Top1 CAGR proxy 22.06%.
2. Il vantaggio macro osservato solo a Top10 non e' sufficiente per avanzare e non puo' essere selezionato ex-post come nuovo obiettivo.
3. La linea macro-context e' chiusa.
4. Qualunque V2.2 deve aggiungere una **classe informativa diversa** dalle feature tecniche/cluster gia' presenti e dal macro-context appena respinto.
5. Se non esiste una classe informativa nuova con provenance causale forte, e' preferibile fermare la ricerca su Original149 piuttosto che moltiplicare tentativi.

## Frozen state V2

- Branch: `research/evidence-v2`.
- V1 closure base commit: `071090ba85bfb4da9dff2b4b7d0a982b16d45aff`.
- Macro dataset: `evidence_v2/data/macro_context_v1/`.
- Macro result: `evidence_v2/results/retriever_macro_context_v1/`.
- Valid macro test run: `37069663860`.
- Original149: burned development only.
- Holdout70: burned diagnostic only, never promotion.
