# ETF Trader V3 Europa48 — verifica dell'allocazione nativa Top2/Top3

> **ERRATUM METODOLOGICO — 24 ottobre 2026.** Il primo stadio UE48 originale di questo rapporto è `XGBRanker` V3 a 127 foglie ma alimentato dalle **125 feature calcolate dal kernel legacy V2**, non dal kernel `etf_trader_v3.source_only.kernel` realmente corrected. L'audit sul medesimo pannello 48 ETF ×65 mesi ([run 40112742559](https://github.com/AM1975MA/Test/actions/runs/40112742559)) dimostra 9 feature downside-volatility differenti, 11.236 celle con valori numerici diversi e 16.724 differenze di disponibilità dato. I risultati finanziari qui presentati sono riproducibili ma descrivono **V3 127 foglie + feature legacy V2**, NON la V3 fully corrected. Non interpretarli come prova della capacità V3 corrected europea. Il test del vero kernel corrected viene eseguito separatamente, senza modificare dati, target, costi o iperparametri.



**24 ottobre 2026 — nuovo replay SUCCESS:** [run 40092281559](https://github.com/AM1975MA/Test/actions/runs/40092281559), [artifact originale](https://github.com/AM1975MA/Test/actions/runs/40092281559/artifacts/12558449697).

Si tratta di un **esperimento complementare**, NON della sostituzione del rapporto Europa48 già certificato in `EUROPE48_V3_TREE_RESULTS_20261024.md`. Il rapporto precedente usava pesi uniformi per il Top2 (50/50) e Top3 (1/3 ciascuno). Questo replay riproduce invece l'allocazione del test economico americano V3 `nested_economic.py`: **Top2 = 75/25, salvo gap percentile originale >=0.12 quando 100/0; Top3 = 50/30/20**. Stesso V3 EU48 127 foglie, stessi 5 regressori e 36 tree nested, stesse predizioni e 65 mesi; la decisione Top1 rimane rigorosamente identica nei due replay. Il Top5 rimane equal-weight 20%.

## Risultati su 48 ISIN europei, un solo conto EUR reale

1.374 sedute dal 1 febbraio 2021 al 1 luglio 2026, ingresso next-open EUR, ribilanciamento mensile, capitale iniziale 1, costi 10 bps **una via**, no overlay di rischio:

| Politica economica | CAGR V3 senza meta | CAGR V3 tree nested | Δ CAGR | MaxDD comune |
|---|---:|---:|---:|---:|
| Top1 100% | **−0,2257%** | **+4,7060%** | **+4,9317 pp** | −41,1836% |
| Top2 V3 condizionale 75/25 vs 100/0 | +1,8014% | +3,9576% | +2,1562 pp | −34,8829% |
| Top3 V3 50/30/20 | +2,4338% | +3,2934% | +0,8596 pp | −31,6981% |
| Top5 20% × 5 | +4,7139% | +4,7139% | 0 | −30,9050% |

**Controllo precedente allocazioni uguali, già archiviato e certificato:**

| Peso diverso, stesso ranker/tree | V3 senza meta | V3 con meta |
|---|---:|---:|
| Top2 50/50 | +3,6116% | +2,9596% |
| Top3 equal 1/3 | +2,7702% | +2,7702% |

Il Top2 con pesi uguali peggiora con il tree, il Top2 pesato V3 migliora: l'interazione fra scelta e portafoglio conta quanto il meta layer. NON scegliere un peso ex post guardando quale CAGR supera l'altro. Per i prossimi studi pre-registrare una singola regola.

## Identità numeriche e competenza layer

Il nuovo programma ha riprodotto in **identità esatta** i CAGR e la curva di modello Compact125 EU48 originale: Top1 +4,727914934%, Top2 50/50 +3,733920043%, Top5 equal +4,960506545%. I sei fitted head europei 2021–2026 sono originali del [run 40086216896](https://github.com/AM1975MA/Test/actions/runs/40086216896), source 127 foglie fixed, con 48 ISIN unici, tre seed, embargo delle etichette e fonte del market SPY precedente all'apertura europea. Nessun ETF statunitense è eleggibile.

Le 36 varianti decisionali V3 sono fit trimestrali con target maturati da 60 giorni, eventi unici di coppie ETF per data da 500 panieri canonici 24 ETF, 4 per categoria. Policy `NESTED_24_TOP1_GUARD` scelta fra le varianti per delta selected excess positivo e delta Top1 non negativo negli ultimi 24 mesi maturi, altrimenti `CORRECTED`.

In 65 mesi: 31 mesi pure baseline, 34 mesi una variante tree, ma soltanto **11 sostituzioni Top1 nel singolo portafoglio unrestricted EU48**; 8 hanno migliorato il rendimento successivo a 21 sedute, 3 lo hanno peggiorato. Il numero di mesi che individuano l'ETF assoluto vincente fra 48 resta 2/65 sia prima sia dopo il tree.

500 panieri europei dipendenti ×65 mesi: Top1 7,6154%→7,7908%, Top3 coverage 20,1354% invariato, selected excess 21D −0,1995%→−0,1208%. Quindi il tree aiuta poco la competenza generale, il vantaggio di CAGR Top1 è concentrato in **poche scelte e in specifici anni (soprattutto 2023 e 2026)**.

## Incertezza, limitazioni e decisione

Bootstrap paired temporale 21 sedute, 3.000 repliche, differenza log NAV annualizzata:
- Top1 alpha +4,7870%, IC95% [−1,6829%,+11,7902%];
- Top2 alpha +2,0796%, IC95% [−1,3197%,+5,7063%];
- Top3 alpha +0,8292%, IC95% [−0,5328%,+2,2821%].

**Tutti includono zero**; non promuovere come alpha confermato. Non confondere CAGR *V3 standalone* con V2 Stage19 completo: quest'ultimo impiega risk overlay e cash US, e su EU48 ha CAGR −0,1549% originale o +5,9763% dopo la sostituzione del suo BASE con Compact125. Una comparazione conclusiva richiede identica allocazione/rischio per entrambe.

Il vecchio standalone Compact125 europeo ottiene Top1 +4,7279%, MaxDD **−25,89%**: V3 tree Top1 +4,7060% e MaxDD **−41,18%**. **Il tree non ha quindi risolto il problema europeo, e il rischio di selezione è deteriorato.** Nessuna modifica a produzione V2/V3, nessun tuning dopo i risultati. Conservare entrambi i replay come analisi separate con differenti regole di allocazione e preparare un futuro test con risk layer unificato.

Risultati integrali (8 file): `EUR48_V3_NET_SCORECARD.csv`, `EUR48_V3_NET_DAILY_NAV.csv`, `EU48_V3_MONTHLY_NESTED_TREE.csv`, `FIT_META_AUDIT.csv`, `EUR48_FULL_UNRESTRICTED_CHOICE_LOG.csv`, `EUR48_V3_MONTHLY_TRADE_LEDGER.csv`, `PRIOR_EU48_V2_125F_EXACT_ECONOMIC_PARITY.csv` e `EU48_V3_RESULTS_MANIFEST.json`.
