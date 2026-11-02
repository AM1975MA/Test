# OLC26 — Supervisore condizionale della leadership: verifica negativa e diagnosi del target

2 novembre 2026. Ricerca esplorativa preregistrata al commit `83c511d6e06276cca43004bfbb76862ab3dd2cdd`, checkpoint pre-outcome `81469c3812448bf03cfd2aec795c6b7feb9bae65`. Parent economico OLC20, REF AUTH. **Nessuna promozione.** Nessun ETF di base riaddestrato o strategia di main modificata.

## Confronto economico 2021–2024

CAGR in %, costo legacy .001, HALF, ranking AUTH con rischio e V6 invariati:

| Contratto | EU AUTH | EU POOL | EU STRAT | USA AUTH | USA POOL | USA STRAT |
|---|---:|---:|---:|---:|---:|---:|
| FAST_LOCK3 | **23,200** | **23,200** | **23,200** | **50,772** | 47,863 | 44,669 |
| ALARM | **22,087** | **22,087** | **22,087** | **45,507** | 42,70 | 38,92 |

Con fee legacy .003 il segno non cambia: FAST_LOCK3 EU19,884 identico nei tre; USA AUTH42,733, POOL39,98, STRAT37,03. Nel FULL 2019–luglio2026 FAST_LOCK3 .001: EU AUTH/POOL/STRAT 19,764 identici, USA 39,484 /38,03 /36,41. Non è un miglioramento economico comune.

**EU identica non significa alpha:** le due varianti europee cambiano migliaia di valori di score ma *zero* coppie effettive Top2. In USA cambia una coppia col POOL e sette con STRAT, tutte sfavorevoli al risultato totale. Nei dieci controlli con etichette rimescolate (cinque per recipe) i Top2 e le curve del periodo principale rimangono identici ad AUTH in entrambi i mercati. Queste identità non sono evidenza di previsione incrementale.

Il Ridge residuale impara principalmente a correggere verso la media i punteggi FUSION; tra le correzioni non nulle la quota che tocca il clipping di ±0.05 è circa 67% EU POOL, 70% EU STRAT, 65% USA POOL e 62% USA STRAT. Perciò il correttore fa raramente la differenza nelle due posizioni estreme. Il test non dimostra che la leadership lunga sia inutile, ma che **questa specifica integrazione non la monetizza**.

## Risultato strutturale più importante: il ranking generale e il Top2 sono due problemi differenti

Per ogni segnale mensile 2021–2024 è stato calcolato il percentile cross-sectional del **rendimento futuro a 126 sedute** (solo per valutazione a posteriori, non usato per prendere decisioni). L'IC medio è la correlazione di Spearman fra score disponibile a t e rango futuro, calcolata per singola data, poi mediata per mercato:

| Indicatore | EU165 IC126 | USA149 IC126 | EU Top2 percentile futuro | USA Top2 percentile futuro |
|---|---:|---:|---:|---:|
| AUTH | -0,072 | +0,014 | 0,533 | 0,518 |
| Momentum passato 126 sedute | **+0,132** | +0,088 | **0,594** | **0,572** |
| Momentum passato 252 sedute | **+0,194** | +0,070 | 0,508 | 0,500 |
| Persistenza 3 segnali | +0,176 | +0,127 | 0,565 | 0,539 |
| Ridge POOL | -0,070 | +0,018 | 0,533 | 0,510 |
| Ridge STRAT | -0,063 | +0,014 | 0,533 | 0,487 |

Attenzione al denominatore: per EU alcune statistiche si basano su 39–46 date con label futura e input validi, e circa 149–150 ETF per data; USA fino a 48 date, 149 ETF. Gli orizzonti 126 sovrapposti riducono l'indipendenza effettiva. AUTH è stato progettato per payoff e orizzonti più brevi (21/42/63), quindi il vantaggio di un fattore 126/252 sulla metrica a 126 giorni non è un confronto equo sulla sua missione originale; è una **diagnosi di informazione a lungo orizzonte**.

Bootstrap descrittivo a blocchi di sei mesi (5000 ricampionamenti, mesi appaiati), differenziale IC rispetto ad AUTH:

| Segnale | EU differenza IC [IC95%] | USA differenza IC [IC95%] |
|---|---|---|
| Momentum 126 | +0,207 [0,087;0,319] | +0,075 [-0,049;0,180] |
| Momentum 252 | +0,266 [0,156;0,379] | +0,056 [-0,094;0,188] |
| Persistenza3 | +0,246 [0,125;0,358] | +0,114 [-0,013;0,218] |

Questi intervalli **non** tengono conto di tutta la ricerca precedente e non certificano alpha, posteriori o un nuovo holdout. L'IC positivo sul paniere completo **non basta**: il momentum 252 EU aumenta l'IC, ma i suoi primi due ticker hanno rango futuro medio 0,508 contro 0,533 per AUTH. Il salto richiesto è quindi **nella selezione della coda dei leader**, non nell'ottimizzazione di un indice generale di ordinamento.

## Integrazione e verifiche

Unico dataset: score OLC20 AUTH, prepared Close/OHLC OLC16 e motore OLC19. Sei feature (AUTH, M63, M126, M252, PERSIST3, interazione 126×PERSIST3) disponibili alla data t; target residuo future rank a126, gruppo maturo solo se t+126 precede in senso stretto 1 gennaio dell'anno di fit. Ridge alpha50, clip ±0.10 e correzione 50%, senza ottimizzazione sui risultati. 5 modelli annuali POOL e 10 STRAT veri (2022–2026), 2021 fallback AUTH; dieci controlli di training target shuffling. Pesi POOL bilanciati 50/50 EU/USA e mesi equamente pesati entro mercato. Quattro test causali/determinismo passano, otto conti AUTH identici bitwise a OLC20, V6 ricalcolato senza overlap. Totale 13 procedure score × due mercati × due contratti × due fee = **104 conti economici** con audit del ledger/NAV.

Restano limiti delle quote storiche preparate, della maschera observed USA mancante, della continuità del paniere, total-return/FX, volatilità e fill intraday. Il benchmark QDVE.DE resta scelto ex post e non è criterio per la selezione di una variante.

## Decisione

Non promuovere OLC26. La scoperta operativamente interessante è **la discontinuità fra IC long-horizon e rendimento concentrato Top2/hold mensile**. Il prossimo esperimento rigoroso dovrebbe ottimizzare esplicitamente la *probabilità di restare fra i leader a 3–6 mesi* e il payoff netto di una decisione Top2 su un orizzonte compatibile con il possesso, con almeno una nuova finestra dati non esplorata. Non fare ulteriori grid search sulla stessa storia sperando in un CAGR migliore: aumenta la selezione retrospettiva senza evidenza di generalizzazione.
