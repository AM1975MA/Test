# Evidence V1

## Regola di avanzamento

Questo file è la **source of truth** della linea Evidence V1. Prima di promuovere ogni nuova evidenza:
1. sorgenti eseguiti presenti nel repository e identificati da hash/commit;
2. dati ticker usati congelati nel repository e identificati da manifest/hash;
3. test causale/reproducibile con artifact e metriche;
4. questo file viene aggiornato: restano solo evidenze ancora valide; risultati smentiti/non comparabili vengono rimossi dallo stato corrente.

**Regola operativa:** i test Evidence V1 devono leggere sorgenti e dati dai path congelati `evidence_v1/source/` e `evidence_v1/data/`. Nessun risultato che dipenda solo da artifact temporanei, download live o codice esterno al branch può essere promosso.

**Data gate:** ogni nuovo download ticker deve essere congelato prima del test e sottoposto a controllo di qualità + verifica esterna dei prezzi/corporate actions su una seconda fonte prima di diventare dato Evidence V1.

## Baseline verificata

- Producer: **Hybrid24 / ETF_trader V2 canonico**.
- Sorgenti core byte-equivalenti alla revisione produttiva ETF_trader V2 della linea storica.
- Confronto controllato full-universe, stessa vintage dati e stesso motore:
  - Original149: **31.60% CAGR**
  - Holdout70 disgiunto: **18.89% CAGR**
- EW buy&hold: ~10.35% vs ~10.62%: il gap non è spiegato da un universo 70 passivamente peggiore.

## Evidenze producer confermate

- Hybrid24 mantiene IC cross-sectional positivo, ma la qualità del **top-tail** è molto più debole del ranking medio.
- Il margin top1-top2 non è una confidence calibrata, soprattutto sul Holdout70.
- Smoothing 40/30/30 e blend BASE/TAIL possono migliorare IC medio ma peggiorare l'estremo tradato.
- BASE, ET e tail contengono informazione complementare; il blend lineare fisso non è universe-invariant.
- Un semplice meta-router logistic top1/top2 non risolve il problema.

### Evidence V1 — Retriever LTR v1

Test: XGBoost `rank:ndcg`, stessi 42 feature e stessi hyperparameter XGB_B di Hybrid24 salvo l'obiettivo ranking; annual expanding walk-forward con maturity gate 63d. **Original149 soltanto; development evidence, non promotion.**

Risultato sui 114 periodi 21d:
- vero winner nel top5: **28.07%** vs Hybrid24 **19.30%**;
- vero winner nel top10: **41.23%** vs Hybrid24 **28.07%**;
- rank mediano del vero winner: **13**;
- top1 proxy: **22.06% CAGR**;
- IC medio 21d: **0.006**, quindi il miglioramento di retrieval avviene sacrificando il ranking globale.

Interpretazione valida: **LTR è promettente come retriever top-k, non ancora come selettore finale**. Il prossimo livello deve rerankare causalmente la shortlist OOS.

Provenance: Action `37040547189`, artifact `11241807171`, SHA256 `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead`; risultati salvati in `evidence_v1/results/retriever_ltr_v1/`.

## Linea attiva

`Retriever top-k -> Pairwise reranker -> calibrated top1/top2 probability -> sizing`

Vincoli:
- training solo su label mature;
- prediction OOS del producer per il training dei livelli successivi;
- Holdout70 = diagnostico/burned, non promotion holdout;
- nuovo Holdout-B congelato **prima** di osservare performance;
- nessuna ottimizzazione ex-post promossa come strategia.

## Prossimi test

1. **Pairwise reranker v1** sulla shortlist LTR OOS, addestrato solo su shortlist storiche già mature.
2. Calibrazione probabilità top1>top2 e sizing usando solo storia OOS.
3. Normalizzazione rispetto a reference universe stabile, separato dall'universo investibile.
4. Data-validation gate esterno per i nuovi ticker.
5. Freeze Holdout-B e singolo test di promotion.

## Frozen state

- Branch: `research/evidence-v1`
- Baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- Data: `evidence_v1/data/original149/`, `evidence_v1/data/holdout70/`
- Source snapshot: `evidence_v1/source/baseline/`
- Original149 files: **151**; Holdout70 files: **72**
- Data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- Source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- Environment: `evidence_v1/ENVIRONMENT.lock.txt`, `evidence_v1/requirements.lock.txt`
- Frozen-data provenance: `evidence_v1/PROVENANCE.json`
