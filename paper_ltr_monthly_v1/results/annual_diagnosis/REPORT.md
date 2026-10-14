# Diagnosi LINEAR annuale: 2021 e 2023

Analisi descrittiva su percorsi congelati gia verificati. Nessun nuovo fit, nessuna modifica dei prezzi, nessuna modifica al repository produttivo. Il calcolo riguarda tutti gli anni disponibili per evitare una selezione esclusiva degli anni peggiori; 2021 e 2023 sono i periodi richiesti, non test indipendenti non osservati.

## Risultato riconciliato

| Anno | LINEAR r1 | LINEAR r2 | LINEAR r3 | LINEAR medio | BASE medio | Differenza media |
|---|---:|---:|---:|---:|---:|---:|
| 2021 | 7.0154% | -4.8597% | 3.3561% | 1.8373% | 3.1074% | -1.2701 pp |
| 2023 | 2.0544% | 5.8560% | 8.5194% | 5.4766% | 29.2643% | -23.7877 pp |

Il 2021 mostra debolezza comune ai due sistemi; nel 2023 emerge una forte sottoperformance specifica di LINEAR rispetto alla ricetta BASE. Non sono la stessa diagnosi.

La differenza additiva nei log-rendimenti del 2023 e -0.20234294 in media sui tre download. Giugno contribuisce -0.063300, ottobre -0.040144 e novembre -0.058412: insieme 79.99% del divario logaritmico netto annuo. Queste quantita non sono punti percentuali di rendimento semplice. I contributi dei mesi positivi compensano parzialmente quelli negativi.

Il 98.68% del divario logaritmico netto 2023 cade nelle giornate con coppia Top1/Top2 ordinata diversa tra sistemi. E una scomposizione contabile, non una misura causale dell'effetto della selezione: patrimonio, pesi e stati di esecuzione dipendono anche dai giorni precedenti. Esempi segnali di allocazione: giugno LINEAR XBI/SOXX o XBI/TUR, BASE con SOXX primo; ottobre LINEAR PALL/EDV, BASE EDV primo; novembre LINEAR PALL/ARGT, BASE ARGT/PALL nei download 1 e 3. Non sono un inventario completo delle posizioni eseguite.

Nel settembre 2021 LINEAR perde mediamente 10.60% e BASE 10.05%: la principale perdita mensile osservata e comune, pur con differenti pesi/coppie. Non e ancora dimostrato quale modifica al controllo del rischio possa migliorarla senza danneggiare gli altri anni.

## Diagnosi apprendimento

Qualita standalone di Compact21, media per data dei 12 segnali di ciascun anno; etichette a 21 giorni, distinta dall'anno di contabilizzazione del portafoglio:

| Anno | Percentile Top1 LINEAR | Percentile Top1 BASE | RankIC LINEAR | RankIC BASE |
|---|---:|---:|---:|---:|
| 2021 | 49.9441% | 62.1365% | -0.002723 | 0.021383 |
| 2023 | 44.407% | 57.420% | -0.10474 | -0.00965 |

Il Top1 Compact21 LINEAR e identico sui tre download in tutti i 12 segnali di entrambi gli anni. La concordanza non implica qualita; non estendere questo fatto al Top1 finale dell'ensemble, che puo differire.

Nel fit 2021 l'ultima uscita di etichetta allenata e il 2019-03-05, contro ultima matura disponibile 2020-12-31; nel fit 2023 e il 2020-12-02, contro 2022-12-01. L'esclusione del 10% finale delle date per validazione, con purge e senza refit completo, lascia quindi fuori informazione recente matura. Non e dimostrato che questo sia la causa dei risultati. BASE e LINEAR non isolano la sola architettura perche differiscono anche nell'insieme effettivamente allenato e in altre parti della ricetta.

## Rettifica sui layer

L'audit del percorso effettivo corregge l'affermazione precedente che tutti i layer, incluso Opportunity, fossero attivi. Il replay conserva Compact/Tail/Macro, ensemble MA3, confidence dei pesi, trasformazione dell'esposizione DD-first e motore di esecuzione/V6. Non invoca il router Opportunity storico, `opportunity_cap` o lo `shock_caps` opzionale. Questo vale ugualmente per BASE e LINEAR; non invalida i confronti eseguiti, ma impedisce di presentarli come un test con Opportunity attivo. Il rischio e effettivamente gestito, ma non tutti i moduli opzionali sono inclusi.

## Conclusione congiunta degli esperti

Gli agenti di apprendimento e rischio hanno esaminato fonti separate e discusso tra loro. Entrambi raccomandano prima una registrazione dettagliata del replay senza nuovi fit: esposizione effettiva, posizioni, costi e interventi di rischio. Gli NPZ disponibili non salvano il registro completo di esposizione e posizioni alternative, quindi da questi soli archivi non e possibile assegnare causalmente il divario a stop o protezioni. `weight1` e il peso relativo del primo ETF, non l'esposizione rischiosa totale.

Successivo candidato metodologico: un solo confronto annuale LINEAR con fit finale su tutte le etichette mature, stessa ricetta altrimenti congelata, su tutti gli anni 2017–2026 e tre download. Prima va verificata la storia remota delle PR per escludere un test gia eseguito; la sola ricerca nei file locali non lo trova. Il test non e stato eseguito in questa diagnosi e non esistono nuovi CAGR da dichiarare. Non selezionare una variante perche recupera soltanto il 2021/2023: valutare rendimento, drawdown e stabilita sull'intero periodo, mantenendo visibili tutti i risultati.

## Riproducibilita

Comando: `python paper_ltr_monthly_v1/diagnose_annual_years.py` dalla radice del repository con gli artefatti annuali verificati estratti in `_evidence/listnet-linear-relative-repair`. Output: ANNUAL.csv, MONTHLY.csv, AGREEMENT_ATTRIBUTION.csv, SELECTION_DAYS.csv e PROVENANCE.json. I 60 rendimenti annui BASE/LINEAR sono riconciliati con i CSV pubblicati entro 1.6653345369377348e-16. La somma dei contributi logaritmici viene controllata per ogni anno e download. Le tre revisioni Yahoo sono correlate e non costituiscono tre mercati indipendenti.

Fonti e audit specialistici: ML_FINDINGS.json, RISK_FINDINGS.md, PROVENANCE.json. Fonte archivio annuale: artefatto `listnet-linear-relative-repair`, [run 38580178650](https://github.com/AM1975MA/Test/actions/runs/38580178650). [PR di ricerca 73](https://github.com/AM1975MA/Test/pull/73).
