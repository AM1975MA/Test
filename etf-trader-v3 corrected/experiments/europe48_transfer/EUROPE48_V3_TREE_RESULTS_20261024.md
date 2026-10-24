# ETF Trader V3 Corrected — test autentico 48 ETF europei in EUR, V3 127 foglie + decision tree

**Esito verificato il 24 ottobre 2026.** Due run complete `40086735687` e `40087054494` riproducono gli stessi valori numerici (comprese curve economiche, scelta mensile nested, KPI basket e punteggi predictivi). Six first-stage annual jobs `40086216896` tutti PASS.

## Domanda e benchmark corretto

Il precedente V2 su soli 48 ETF a esposizione **strettamente europea**, in EUR, con **48 ISIN legalmente distinti**, aveva mostrato CAGR molto basso. Il [replay V2 originale Stage19](https://github.com/AM1975MA/Test/blob/research/canonical-v2-source-us149-eu48-20261020/isin_first2026/canonical_v2_same_period/results/EUROPE_48_ORIGINAL_FULL_V2_STAGE19.json) riporta CAGR **−0,1549%**, drawdown **−39,91%**. È un **sistema diverso**, perché include Stage19, rischi, allocazione e riferimenti difensivi USD, e non costituisce il confronto isolato del solo ranker.

Il confronto economicamente **diretto, verificato al livello 1e−10**, è l'originale [Compact21 EU48 BASE 125F standalone](https://github.com/AM1975MA/Test/blob/research/canonical-v2-source-us149-eu48-20261020/isin_first2026/compact21_base48/results/RESULT.json), certificato con primo stadio europeo 2021–26 e Open EUR: Top1 CAGR **+4,7279%**, MaxDD **−25,8932%**, Sharpe log +0,2346, con costo per lato 0,1%.

### Cosa è stato testato davvero

- Universo certificato 48 ETF, 6 bucket (4 broad, 23 settoriali, 4 country, 4 factor, 7 bond e 6 property), **48 ISIN distinti** con listini EUR e sottostante Europa.
- Dati di input originali europei 2015–1 luglio 2026 (preparazione source-only certificata, 49 sole correzioni High/Low in un derivato, Open/Close storici invariati).
- Fattore SPY originale all'**ultimo close USA precedente all'apertura europea**, mai ticker eleggibile; label `Open+1→Open+21` del calendario comune osservato di 48 venue europee.
- Training annuale 2021–2026 maturato prima del primo gennaio, 2017+ storico, **XGBRanker pairwise 125F a 127 foglie, 360 boost round e tre seed 101,202,303**; cinque regressori OOS di V3 su 125/101 feature e target forward 21D. Nessun modello 149 USA riutilizzato.
- Meta-tree: **14 feature originali per coppia**, 36 configurazioni DecisionTree [profondità 1–3, min leaf 100/300, soglie probabilità .55/.60/.65, expanding/36 mesi], **trimestrale e 60 giorni di embargo** su target precedenti maturati. La scelta `NESTED_24_TOP1_GUARD` usa soltanto ultime 24 date già maturate e richiede incremento storico medio sia di selezione rendimenti sia di Top1 non negativo.
- 500 panieri **canonical 24 ETF** (4 per ciascuno dei sei bucket), usati per la competenza, per i pair distinti e per la scelta meta; NON sono portafogli indipendenti e **non** se ne usa la media dei CAGR come risultato finanziario principale.
- Portafoglio singolo **unrestricted48**, TOP1/TOP2/TOP3/TOP5 equal weight, unica NAV autonoma per metodo, rebalance mensile Open-EUR, costo buy/sell 10 bps per notional scambiato: 65 segnali gennaio 2021–maggio 2026, 1.374 sedute negoziate febbraio 2021–1 luglio 2026. Senza risk layer, Titan, MA3, Stage19 o V6; confronto *isola* il V3 ranker e il decision tree. Doppio controllo esatto del ranker precedente 125F su Top1, Top2 e Top5 (CAGR, capital, MaxDD, Sharpe entro 1e−10).

## Risultato primario: CAGR e rischio, stesso portafoglio europeo

| Versione | CAGR Top1 | CAGR Top2 | CAGR Top3 | CAGR Top5 | MaxDD Top1 | Sharpe log Top1 |
|---|---:|---:|---:|---:|---:|---:|
| **V2 125F europeo senza meta** | **+4,7279%** | **+3,7339%** | +1,3268% | **+4,9605%** | **−25,8932%** | +0,2346 |
| V3 127 foglie europeo senza meta | **−0,2257%** | +3,6116% | +2,7702% | +4,7139% | −41,1836% | −0,0105 |
| **V3 127 foglie + NESTED DecisionTree** | **+4,7060%** | +2,9596% | +2,7702% | +4,7139% | **−41,1836%** | +0,2371 |

Il tree recupera **+4,9317 punti di CAGR** sulla V3 base nel Top1, ma il V2 125F originale resta lievemente davanti (+0,0219 pp) con **15,29 punti percentuali meno drawdown** e Top2/Top5 migliori. Il tree non altera Top3/Top5 (decisioni possibili solo entro Top3 originale); Top2 può cambiare a causa dell'ordine modificato.

Il **−0,15% CAGR del full V2 Stage19** è un diverso benchmark e **NON** autorizza a presentare il +4,706% standalone V3+Tree come un miglioramento causato esclusivamente dal decision tree rispetto alla precedente strategia integrata. Per verificare quello servirebbe inserire sia V2 sia V3+Tree nello STESSO motore Stage19 identico.

### Decomposizione annuale Top1, costi EUR inclusi

| Anno (2021 e 2026 parziali) | Vecchio 125F | V3 ranker solo | V3 + tree |
|---|---:|---:|---:|
| 2021 (feb–dic) | +4,82% | +11,46% | +11,46% |
| 2022 | +5,84% | **−19,06%** | **−19,06%** |
| 2023 | +3,58% | +5,68% | **+27,77%** |
| 2024 | +1,83% | −0,25% | −3,85% |
| 2025 | −2,97% | −3,68% | −5,17% |
| 2026 (gen–1 lug) | +13,07% | +7,85% | +22,03% |

Il tree è rimasto inattivo nel periodo peggiore 2022 e non migliora il MaxDD. Il CAGR del nuovo modello dipende da 2023 e 2026. Non è un miglioramento di capacità predittiva uniforme su tutti i regimi.

## Cosa aggiunge il decision tree, e come spende le correzioni

Il selettore V3 `NESTED_24_TOP1_GUARD` mantiene il puro CORRECTED125 in **31/65 mesi** e sceglie una configurazione tree nei restanti 34. Sul **portafoglio unrestricted** il Top1 viene effettivamente cambiato soltanto **11 volte/65 mesi**, principalmente 2023 (6 volte), 2024 (2), 2025 (1), 2026 (2). Non vengono alterati 2021/2022.

**Controllo competence separato, 500 panieri ×65 date (dipendenti)**:

| Layer | Top1 winner capture nei panieri | Top3 coverage | Selected excess rispetto media paniere / 21D | Selezionati <=−10% |
|---|---:|---:|---:|---:|
| V3 base | 7,6154% | 20,1354% | −0,1995% | 3,8062% |
| V3 + tree nested | 7,7908% | 20,1354% | −0,1208% | 3,8062% |

Il tree migliora Top1 di **+0,1754 pp**, ed extra rendimento di **+0,0787 pp per 21D**. Ma il Top1 resterebbe inferiore al ~14,5% visto sui panieri USA149, e il rendimento rispetto al paniere medio rimane NEGATIVO.

Nell'universo pieno 48, la performance predittiva è ancora meno convincente:

| Layer | ETF #1 = vero vincitore 21D | Spearman medio | Extra selected vs 48 media 21D |
|---|---:|---:|---:|
| EU48 vecchio 125F | 2/65 (3,08%) | +0,0251 | +0,2008% |
| EU48 V3 127 foglie | 2/65 (3,08%) | +0,0389 | −0,3451% |
| EU48 V3 + tree | 2/65 (3,08%) | +0,0389 (rank base) | +0,2524% |

Incremento 21D per tree rispetto a V3 base **+0,5975 punti percentuali**; bootstrap paired 65 date, blocchi di 3 mesi IC95% **[−0,0282, +1,4487] pp**, quindi non significativo. Il miglioramento dello Spearman da 125 a 127 foglie +0,01375 ha IC95% **[−0,0163,+0,0423]**, non significativo. La chance di selezionare l'unico migliore ETF random è 1/48=2,08%; 2/65 successi non è prova di skill. Spearman positivo medio può coesistere con Top1 mediocre perché non misura specificamente la capacità di riconoscere vincitori estremi.

## Problema strutturale emerso

I panieri 500×24 condividono quasi sempre gli stessi 48 nomi. Per ogni mese il training usa una coppia (base, alternativa) solo una volta quando viene ripetuta in panieri sovrapposti; il report di run registra **il numero di coppie differenti**, che può essere MOLTO inferiore a 500 e anche inferiore alla soglia 40 tipica degli USA149. Non interpretiamo intervalli costruiti ricampionando panieri, né un alto hit rate apparentemente basato su centinaia di casi come 500 eventi indipendenti.

## Decisione

1. **V3 + tree FUNZIONA a livello algoritmico sull'Europa** e può migliorare nettamente un Top1 basato sul ranker V3 più profondo.
2. **NON ha dimostrato una strategia europea più forte del V2 125F** a costi e calendario identici. Con MaxDD Top1 da −25,89 a −41,18% si osserva una degradazione importante del rischio.
3. Non migliorare foglie/soglie dopo aver visto questa storia 2021–26: dati già riutilizzati per molte ricerche EU48 e universo del 2026, non storico point-in-time dell'universo.
4. Prossimo test davvero utile: eseguire la **stessa architettura di gestione del rischio e allocazione** per il V2 125F e V3+Tree europeo, tenendo congelate tutti i parametri, per capire se il collo di bottiglia è rank o risk execution.
5. Il tree non risolve da solo la difficoltà più profonda: **su Europa48 la capacità di estrarre il vincitore assoluto è limitata**, a differenza dei risultati precedenti su USA149. Aumentare la complessità può accrescere la varianza senza creare opportunità predittiva trasferibile.

## Riproducibilità e input

Source storico immutabile: branch `research/canonical-v2-source-us149-eu48-20261020`, file `isin_first2026/compact21_base48/results/`, `isin_first2026/v2_unrestricted48/prepare.py`; nuovi sorgenti nella cartella `etf-trader-v3 corrected/experiments/europe48_transfer/`. 6 fitting annuali [run 40086216896](https://github.com/AM1975MA/Test/actions/runs/40086216896) tutti PASS. Replay economico [run 40086735687](https://github.com/AM1975MA/Test/actions/runs/40086735687) PASS; replicato con inferenza vettoriale identica [run 40087054494](https://github.com/AM1975MA/Test/actions/runs/40087054494) PASS. Tutti i 7 artifact completi, CSV, curve NAV e log fitting sono salvati sotto `results/` con SHA256 per ogni file. Produzione V2 e V3 invariata.
