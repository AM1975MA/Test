# Evidence V1

## Regola di avanzamento

Questo file è la **source of truth** della linea Evidence V1. Prima di promuovere ogni nuova evidenza:
1. sorgenti eseguiti presenti nel repository e identificati da hash/commit;
2. dati ticker usati congelati nel repository e identificati da manifest/hash;
3. test causale/reproducibile con artifact e metriche;
4. questo file viene aggiornato: restano solo evidenze ancora valide; risultati smentiti/non comparabili vengono rimossi dallo stato corrente.

**Regola operativa:** i test Evidence V1 leggono sorgenti e dati solo da `evidence_v1/source/` e `evidence_v1/data/`. Nessun risultato dipendente solo da artifact temporanei, download live o codice esterno al branch può essere promosso.

**Data gate:** ogni nuovo download ticker va congelato prima del test e verificato con quality checks + seconda fonte esterna per prezzi/corporate actions.

## VALIDATED / baseline verificata

- Hybrid24 / ETF_trader V2 canonico, source byte-equivalente alla revisione produttiva storica.
- Full-universe, stessa vintage/motore:
  - Original149: **31.60% CAGR**
  - Holdout70 disgiunto: **18.89% CAGR**
- EW buy&hold ~10.35% vs ~10.62%: il gap non deriva da un Holdout70 passivamente peggiore.
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

## DIAGNOSTIC / BURNED

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

### Nonlinear reranker v2 — SCARTATO

Top10 LTR OOS -> XGBoost `rank:pairwise`, shallow/regularized, singola configurazione preregistrata, 42 feature + posizione LTR normalizzata; annual expanding e maturity gate 63d. Il winner è valutato sul **full Original149**, mentre il reranker può scegliere solo nella shortlist OOS Top10.

114 periodi:
- LTR exact-winner Top1: **8.77%**;
- v2 exact-winner Top1: **7.02%**;
- LTR winner nel Top2: **13.16%**;
- v2 winner nel Top2: **9.65%**;
- LTR winner nel Top3: **18.42%**;
- v2 winner nel Top3: **14.04%**;
- top1 21d CAGR proxy: **22.06% -> 25.51%**, ma era metrica diagnostica e non criterio di avanzamento;
- margin v2 vs successivo differenziale ritorni: Spearman **-0.006** circa;
- 2023-2026: exact-winner **9.52% -> 2.38%**, Top2 **11.90% -> 2.38%**, CAGR proxy **19.27% -> 12.57%**.

La regola preregistrata richiedeva Top2 migliore dell'LTR e Top1 non peggiore: **fallita**. Quindi il v2 non viene promosso e non viene ritoccato ex-post.

Run valido `37046279447`; artifact `11244841228`; artifact SHA256 `ea8d03b91db5aa7fa3643dc7b93f575ea6d0b874599465cfa5a7b05e1e3865f4`; risultati in `evidence_v1/results/reranker_v2_nonlinear/`.

Audit: il precedente run tecnico `37045478600` è **INVALIDO COME EVIDENZA** perché l'evaluator definiva erroneamente il winner dentro la Top10 anziché sul full universe. È stato escluso prima di qualsiasi tuning; modello/configurazione non sono stati modificati nel rerun valido. Protocollo: `evidence_v1/protocols/RERANKER_V2_EVALFIX.md`.

**Holdout70 resta BURNED**: può essere usato solo per diagnostica e progettazione di ipotesi, non per promozione.

## HYPOTHESIS corrente

Dopo due reranker causalmente corretti ma falliti, l'evidenza non supporta l'idea che basti aumentare la capacità del reranker mantenendo invariati representation/target.

Ipotesi da testare prima di un v3:
- la rappresentazione dipende troppo dall'universo corrente;
- il target multi-horizon usato dal producer è adatto al retrieval ma non necessariamente all'ordinamento fine del top-tail;
- la non-stazionarietà 2023-2026 è troppo forte per un reranker statico sulle stesse feature;
- il valore del retriever LTR è soprattutto **recall**, non top1 selection.

Linea ancora supportata:

`LTR top-k retriever -> representation/target diagnostics -> eventuale reranker preregistrato -> calibrated top1/top2 probability -> sizing`

Vincoli:
- label mature;
- training dei livelli successivi solo su prediction OOS precedenti;
- Holdout70 = burned/diagnostico;
- nuovo Holdout-B congelato prima di osservare performance;
- nessuna ottimizzazione ex-post promossa.

## NEXT TEST

1. Materializzare in repository il checkpoint riutilizzabile del Retriever LTR v1: prediction OOS + shortlist Top5/Top10 + fit audit, senza cambiare il modello.
2. Test separato della sensibilità all'universo / normalizzazione su **reference universe stabile**, preregistrato e senza usare Holdout70 come promotion evidence.
3. Solo se emerge una representation più universe-invariant, definire un reranker v3 con ipotesi nuova e singola configurazione preregistrata; niente sweep sul 149.
4. Calibrazione confidence/sizing solo dopo un reranker che migliori stabilmente il ranking.
5. Data-validation gate esterno per i nuovi ticker.
6. Freeze Holdout-B e singolo test di promotion.

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
- Results/artifacts registry: `evidence_v1/RESULTS_REGISTRY.md`
