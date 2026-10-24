# ETF Trader V3 Corrected — Prova 2026 successiva al periodo di ricerca (24 ottobre 2026)

**STATO:** SUCCESS. Continuazione first-stage con esatta parità gennaio–giugno, confronto giugno–agosto 2026 compiuto, indipendente June-archived-before-label check confermato. Nessuna promozione di challenger e nessuna modifica alla strategia operativa.

## Catena delle evidenze

- [149 ETF nuovi prezzi fino al 23 ottobre, append-only su OHLCV 1 luglio](https://github.com/AM1975MA/Test/actions/runs/40082539622). **149/149**, nessun ETF escluso; verifica del fattore di aggiustamento su overlap; vecchie osservazioni preservate.
- [Regenerazione first stage e test di identità](https://github.com/AM1975MA/Test/actions/runs/40083752344). Ranker `CORRECTED125` + 5 regressori tutti equivalenti gennaio–giugno 2026: massima differenza raw ranker `8.48e-8` e **0 cambiamenti nel Top1 su 500 panieri × 6 mesi**, per ciascuno dei sei modelli. OOS training originario eseguito esclusivamente su 24.663 righe con etichette maturate prima del 1 gennaio 2026; tre seed originali e parametri fissati.
- [Confronto 3 mesi con albero nested originale + tre meta-utility challenger](https://github.com/AM1975MA/Test/actions/runs/40084221662). **PASS** su test di parità per tutte e 36 le decision tree a maggio 2026, per la precedente scelta nested dell'iperparametro e per ciascuna delle tre utility rule candidate. Metà layer e benchmark non modificati.
- [Controllo indipendente giugno con segnali originali già archiviati senza target](https://github.com/AM1975MA/Test/actions/runs/40084390775). **PASS**. Lo snapshot modello originale (run `40016809498`) conteneva sei varianti × 149 punteggi del 30 giugno 2026 con `fwd_ret_21 = NaN`: sono previsioni realmente precedenti alla maturazione delle etichette di giugno. Abbiamo usato solo questi punteggi e nuove quotazioni per calcolare rendimento effettivo al giorno di ingresso next-open e al ventunesimo giorno successivo. Metriche originali e scelte nested corrispondono alla pipeline rigenerata.

**Fondamentale:** lo studio giugno–agosto è una **continuazione retrospettiva non usata nella ricerca precedente** con parametri bloccati, **non** un holdout prospettico puro di 3 mesi. Solo giugno vantava un primo stadio archiviato esplicitamente prima delle etichette; luglio/agosto sono stati ricostruiti successivamente ai relativi rendimenti, anche se train e parametri erano congelati. Il numero di mesi nuovi, appena **3**, è inadatto a trarre conclusioni statistiche sulla robustezza del CAGR. Il target dei modelli è il **forward per 21 sedute da apertura successiva**; non è un CAGR né un risultato al netto dei costi di portafoglio.

## Risultati di competenza sull'insieme di tre mesi

Tutte le righe: 149 ETF, 500 panieri canonici da 24 ETF, 3 mesi = 1.500 decisioni paniere-mese. Tutti i layer modificano solo l'ordine originale Top3; coverage invariata 33,1333%.

| Policy congelata | Top1 winner capture | Top3 winner capture | Selected excess 21D rispetto media paniere | Frequenza di scelta <=-10% | Cambiamenti (corretti/errati) |
|---|---:|---:|---:|---:|---:|
| CORRECTED125 solo | 9,8667% | 33,1333% | **+3,0801%** | 3,6667% | 0 |
| **NESTED_24_TOP1_GUARD incumbent** | **9,8667%** | 33,1333% | **+3,0801%** | **3,6667%** | **0** |
| UTILITY_DT14_L1.5 | 9,8667% | 33,1333% | +3,0801% | 3,6667% | 0 |
| UTILITY_HGB_REGIME_L1.5 | 11,4000% | 33,1333% | +2,6127% | 6,6667% | 186 (80/106) |
| UTILITY_RF_REGIME_L1 | 8,6000% | 33,1333% | +0,7722% | 9,5333% | 714 (231/483) |

Il checkpoint cronologico, utilizzando solo storico di 24 mesi maturato con 60 giorni di embargo, sceglie **`TREE_expanding_D1_N100_P0.55`** per tutti e tre i nuovi mesi. Tale variante non emette sostituzioni in queste tre condizioni: resta identico al ranker base. Non possiamo distinguere su 3 mesi *vera intelligenza dell'astensione* da una policy sistematicamente inattiva in questi regimi.

La RF perde rispetto al checkpoint **-2,3079 punti percentuali di selected excess 21D**, pur avendo registrato nel campione storico precedente rendimenti apparentemente superiori in regimi concentrati nel 2026. Nel nuovo segmento scende a 32,35% di correzioni effettivamente migliorative, contro solo 43,01% del modello HGB. Il modello HGB migliora Top1 ma fa peggiorare selezione media e frequenza di perdite oltre 10%. 

I **714 interventi RF** sono soltanto **252 eventi ETF originale/alternativo/data distinti**, e i **186 HGB** soltanto **56**: i 500 panieri sono sovrapposti e non costituiscono osservazioni indipendenti. Su 3 date non viene costruito alcun intervallo bootstrap fittiziamente preciso.

## Andamento mensile: fa emergere la vera causa

Selected excess forward 21D (percentuale sopra media dello stesso paniere):

| Segnale | Ranker & incumbent | DT14 lambda1.5 | HGB lambda1.5 | RF lambda1 | RF sostituzioni migliorative |
|---|---:|---:|---:|---:|---:|
| 30 giugno 2026 | +3,0541% | +3,0541% | +1,1028% | **-4,3044%** | **50 / 376 = 13,30%** |
| 31 luglio 2026 | +5,1156% | +5,1156% | +5,8209% | **+6,0399%** | 93 / 108 = 86,11% |
| 31 agosto 2026 | +1,0705% | +1,0705% | +0,9143% | **+0,5811%** | 88 / 230 = 38,26% |

**Non c'è segnale di robustezza multi-regime della RF**: nel giugno 2026 cambia il Top1 in 376/500 panieri e peggiora in 326 casi. A luglio aiuta spesso, ad agosto sbaglia più frequentemente di quanto aiuti. HGB fa 72 modifiche a giugno, 71 peggiorative, ma 56/56 corrette a luglio. Questo suggerisce un problema di affidabilità/calibrazione/decisioni sensibili al regime da diagnosticare prima di migliorare qualsiasi altro layer.

## Protocollo futuro e interpretazione

1. **Mantieni in ricerca** `CORRECTED125 + NESTED_24_TOP1_GUARD`; non promuovere nessuno degli sfidanti e non scegliere nuovi lambda/soglie dopo aver visto giugno–agosto.
2. **Settembre 2026:** primo stadio presente ma target 21 giorni ancora immaturo il 24 ottobre; preserviamo le predizioni in un CSV separato senza scoring. Le predizioni di settembre sono ricostruite a ottobre (quindi non sono un vero record precedente al segnale), anche se future-label still immature.
3. Per un vero test prospettico, produrre/pre-registrare e archiviare prima del loro target le previsioni dei segnali futuri, con versionamento, data di compilazione, 149 OHLCV as-of e log completo di algoritmo e allocazioni.
4. Non confondere *precisione di sostituzione* con *rendimento di un portafoglio vero*. Su sole 3 decisioni mensili, la valutazione corretta è meta-layer competence e fragilità per regime, non il CAGR di una NAV aggregata o il max drawdown.
5. Come nuova ricerca **prima della promozione**: diagnosticare il perché delle ~376 sostituzioni RF a giugno e le variazioni nelle distribuzioni `utility_pred`/calibrazione. Questo studio sarebbe esplorativo, non una nuova conferma del modello.

## Archiviazione

Sorgenti ricerca nella cartella `etf-trader-v3 corrected/experiments/l00_rank_reg_fusion`, nuovi workflow nello spazio `.github/workflows/`. Pacchetti completi comprensivi della continuazione dei 149 raw, punteggi delle 6 teste, tabella mese a mese, decision log/eventi ETF, verifiche di parità e manifest SHA256 salvati in `results/forward_20261024/`. Nessun codice di produzione V2, V3 o layer operativo modificato.
