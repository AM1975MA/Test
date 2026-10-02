# Evidence V1

## Regola di avanzamento

Questo file è la **source of truth** della linea Evidence V1. Prima di promuovere ogni nuova evidenza:
1. sorgenti eseguiti presenti nel repository e identificati da hash/commit;
2. dati ticker usati congelati nel repository e identificati da manifest/hash;
3. test causale/reproducibile con artifact e metriche;
4. questo file viene aggiornato: restano solo evidenze ancora valide; risultati smentiti/non comparabili vengono rimossi dallo stato corrente.

**Regola operativa:** i test Evidence V1 devono leggere sorgenti e dati dai path congelati `evidence_v1/source/` e `evidence_v1/data/`. Nessun risultato che dipenda solo da artifact temporanei, download live o codice esterno al branch può essere promosso.

## Baseline verificata

- Producer: **Hybrid24 / ETF_trader V2 canonico**.
- Sorgenti core verificati byte-equivalenti alla revisione produttiva ETF_trader V2 usata dalla linea storica.
- Confronto controllato, stessa vintage dati e stesso motore full-universe:
  - Original149: **31.60% CAGR**
  - Holdout70 disgiunto: **18.89% CAGR**
- EW buy&hold: ~10.35% vs ~10.62%: il gap non è spiegato da un universo 70 passivamente peggiore.

## Evidenze producer confermate

- Hybrid24 mantiene IC cross-sectional positivo in entrambi gli universi.
- La qualità del **top-tail** è molto più debole della qualità media del ranking.
- Il margin top1-top2 non è una confidence calibrata, soprattutto sul Holdout70.
- Smoothing 40/30/30 e blend BASE/TAIL possono migliorare l'IC medio ma peggiorare l'estremo tradato.
- BASE, ET e tail contengono informazione complementare; il blend lineare fisso non è universe-invariant.
- Un semplice meta-router logistic top1/top2 non risolve il problema.
- Learning-to-Rank mostra potenziale come **retriever top-k**, non ancora come selettore top1 diretto.

## Linea attiva

Obiettivo: pipeline causale e walk-forward:

`Retriever top-k -> Pairwise reranker -> calibrated top1/top2 probability -> sizing`

Vincoli:
- training solo su label mature;
- prediction OOS del producer per il training dei livelli successivi;
- Holdout70 = diagnostico/burned, non promotion holdout;
- nuovo Holdout-B congelato **prima** di osservare performance;
- nessuna ottimizzazione ex-post promossa come strategia.

## Prossimi test

1. Baseline retriever LTR su Original149 in expanding walk-forward.
2. Reranker pairwise solo su shortlist OOS mature.
3. Calibrazione probabilità top1>top2 e sizing usando solo storia OOS.
4. Normalizzazione rispetto a reference universe stabile, separato dall'universo investibile.
5. Freeze Holdout-B e singolo test di promotion.

## Frozen state

- Branch: `research/evidence-v1`
- Baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- Data repository paths:
  - `evidence_v1/data/original149/`
  - `evidence_v1/data/holdout70/`
- Source snapshot: `evidence_v1/source/baseline/`
- Original149 files: **151**
- Holdout70 files: **72**
- Data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- Source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- Provenance: `evidence_v1/PROVENANCE.json`
- Hybrid24 diagnostic: Action `37035270407`, artifact `11240321050`, SHA256 `deb4127a221ed5c8ef62f27508e01b4f50ada3256bae54940b4edaf5af7e590a`.
