# Evidence V1

## Regola di avanzamento

Questo file è la **source of truth** della linea Evidence V1. Prima di promuovere ogni nuova evidenza:
1. sorgenti eseguiti presenti nel repository e identificati da hash/commit;
2. dati ticker usati congelati nel repository e identificati da manifest/hash;
3. test causale/reproducibile con artifact e metriche;
4. questo file viene aggiornato: restano solo evidenze ancora valide; risultati smentiti/non comparabili vengono rimossi dallo stato corrente.

**Regola operativa:** i test Evidence V1 leggono sorgenti e dati solo da `evidence_v1/source/` e `evidence_v1/data/`. Nessun risultato dipendente solo da artifact temporanei, download live o codice esterno al branch può essere promosso.

**Data gate:** ogni nuovo download ticker va congelato prima del test e verificato con quality checks + seconda fonte esterna per prezzi/corporate actions.

## Baseline verificata

- Hybrid24 / ETF_trader V2 canonico, source byte-equivalente alla revisione produttiva storica.
- Full-universe, stessa vintage/motore:
  - Original149: **31.60% CAGR**
  - Holdout70 disgiunto: **18.89% CAGR**
- EW buy&hold ~10.35% vs ~10.62%: il gap non deriva da un Holdout70 passivamente peggiore.

## Evidenze producer confermate

- Hybrid24 ha segnale cross-sectional, ma il **top-tail** è molto meno affidabile del ranking medio.
- Il margin top1-top2 non è una confidence calibrata.
- Smoothing 40/30/30 e blend BASE/TAIL possono alzare IC medio ma peggiorare l'estremo tradato.
- BASE, ET e tail hanno informazione complementare; il blend fisso non è universe-invariant.

### Retriever LTR v1 — CONFERMATO come development evidence

XGBoost `rank:ndcg`, stessi 42 feature e hyperparameter XGB_B di Hybrid24 salvo l'obiettivo ranking; annual expanding, maturity gate 63d, Original149.

114 periodi 21d:
- winner nel top5: **28.07%** vs Hybrid24 **19.30%**;
- winner nel top10: **41.23%** vs Hybrid24 **28.07%**;
- rank mediano winner: **13**;
- top1 proxy: **22.06% CAGR**;
- IC medio: **0.006**.

Conclusione: **LTR migliora il retrieval top-k sacrificando ranking globale; non è ancora un selettore finale.**

Action `37040547189`; artifact `11241807171`; SHA256 `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead`; risultati in `evidence_v1/results/retriever_ltr_v1/`.

### Pairwise reranker v1 — SCARTATO

Top10 LTR OOS -> logistic pairwise L2 sulle differenze delle 42 feature + rank LTR; training annual expanding solo su shortlist OOS mature.

114 periodi:
- LTR top1 proxy: **22.06% CAGR**;
- reranker top1 proxy: **19.81% CAGR**;
- exact-winner: **8.77% -> 7.02%**;
- winner nel top2: **13.16% -> 8.77%**;
- margin reranker vs successivo differenziale ritorni: Spearman **0.065**;
- forte instabilità: **11.70%** nel 2017-2022, **35.10%** nel 2023-2026.

Conclusione: **la forma lineare pairwise v1 non risolve l'ordinamento della shortlist e non viene portata avanti.**

Action `37041677418`; artifact `11242493662`; SHA256 `13e227467d5f6a52624c71ac2e06b9a1d7fabb58d30fe2a4ff55250e2c829aad`; risultati in `evidence_v1/results/pairwise_reranker_v1/`.

## Linea attiva

`LTR top-k retriever -> nonlinear / richer reranker -> calibrated top1/top2 probability -> sizing`

Vincoli:
- label mature;
- training dei livelli successivi solo su prediction OOS precedenti;
- Holdout70 = burned/diagnostico;
- nuovo Holdout-B congelato prima di osservare performance;
- nessuna ottimizzazione ex-post promossa.

## Prossimi test

1. Reranker v2 non lineare sulla shortlist OOS, con configurazione preregistrata e senza sweep.
2. Test separato della normalizzazione su reference universe stabile.
3. Calibrazione confidence/sizing solo dopo un reranker che migliori stabilmente il ranking.
4. Data-validation gate esterno per i nuovi ticker.
5. Freeze Holdout-B e singolo test di promotion.

## Frozen state

- Branch: `research/evidence-v1`
- Baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- Data: `evidence_v1/data/original149/`, `evidence_v1/data/holdout70/`
- Source baseline: `evidence_v1/source/baseline/`
- Original149 files: **151**; Holdout70 files: **72**
- Data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- Source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- Environment: `evidence_v1/ENVIRONMENT.lock.txt`, `evidence_v1/requirements.lock.txt`
- Frozen-data provenance: `evidence_v1/PROVENANCE.json`
