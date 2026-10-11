# Decisione tecnica: mantenere lo storico originale

Confronto completo concluso sui tre download Yahoo congelati Original149: [Actions 38176821223](https://github.com/AM1975MA/Test/actions/runs/38176821223), tre replay e aggregazione SUCCESS. Periodo identico alla baseline: 2017-02-01–2026-07-01, 2.366 sedute e 149 ETF. Risultati verificati anche ricalcolando CAGR, MaxDD e Sharpe dalle tre curve di capitale: scarto inferiore a 1e-12.

| Download | CAGR originale | CAGR 2011/2012 | MaxDD originale | MaxDD 2011/2012 | Sharpe originale | Sharpe 2011/2012 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 29,7534% | 29,4846% | −34,8621% | −30,4751% | 1,0461 | 1,0059 |
| 2 | 30,8437% | 27,9470% | −25,6896% | −35,7545% | 1,0870 | 0,9791 |
| 3 | 34,6771% | 26,6565% | −36,0975% | −30,3351% | 1,1829 | 0,9646 |

| Misura | Originale | 2011/2012 |
|---|---:|---:|
| CAGR medio | 31,7581% | 28,0293% |
| Dispersione CAGR massimo–minimo | 4,9236 pp | 2,8281 pp |
| Deviazione standard dei CAGR, popolazione | 2,1115 pp | 1,1560 pp |
| MaxDD medio | −32,2164% | −32,1882% |
| Sharpe medio | 1,1053 | 0,9832 |
| Disaccordo Top1, almeno due download | 43,0262% (1018/2366) | 40,0254% (947/2366) |
| Disaccordo coppia Top1/Top2 ordinata | 76,5850% (1812/2366) | 73,1192% (1730/2366) |
| Disaccordo insieme Top2 non ordinato | 66,9907% (1585/2366) | 61,6653% (1459/2366) |

La finestra ridotta migliora la dispersione del CAGR del 42,56% e riduce moderatamente il disaccordo delle selezioni. Compromette però la performance: CAGR medio −3,7287 punti (−11,74% relativo), Sharpe medio −11,05%. Tutti i CAGR individuali e tutti gli Sharpe peggiorano. Sul download2 il MaxDD peggiora di 10,0649 punti; il MaxDD medio quasi invariato nasconde questa differenza.

**Decisione: mantenere lo storico originale.** I criteri preregistrati di stabilità sono superati, ma falliscono conservazione di almeno95% del CAGR medio, dei singoli CAGR e dello Sharpe medio. La riduzione della sensibilità ai download non compensa il deterioramento economico osservato. Le acquisizioni sono correlate e già esaminate: nessuna prova di validazione futura indipendente.

## Correzione della soglia e controlli

I 60 mesi erano una soglia di esclusione in source_only/models.py, non un requisito matematico XGBoost né una richiesta dell'utente. Con segnali ammessi dal2012 sono disponibili58 mesi Compact21 maturi prima del2017. Dopo l'istruzione “sistema e testa”, il solo controllo di ammissibilità è stato esplicitamente ridotto60→58 nella copia temporanea CI. Tutti i fit annuali2017–2026 sono stati eseguiti. Nessun esempio del2011 o etichetta immatura è stato aggiunto.

OHLCV dal2011, riscaldamento2011, training dal2012 per Compact, Tail, Macro ed Extra; MA3 ricostruito sullo stesso storico e verificato dal2012. Parametri dei modelli, feature, universo, allocazione, costi, esecuzione e ambiente numerico corrispondono alla baseline recuperata dalla PR48. Input congelati preservati e hash invariati. Sei test mirati passano; audit causali precedenti sui tre input e revisione del nuovo runner conclusi. La baseline e gli esperimenti già conclusi non sono stati ripetuti.

Opportunity è un percorso separato inattivo nel benchmark canonico: il suo difetto preesistente di feature target forward resta documentato nel rapporto di fattibilità, non viene corretto né attivato in questo confronto.

La precedente conclusione basata sul58/60 è conservata in FEASIBILITY_REPORT_SUPERSEDED.md per tracciabilità ed è superata da questo confronto empirico. Il primo run38176634299 è stato annullato per impostazioni numeriche non allineate; nessun suo risultato è utilizzato.

Evidenza: full_results/COMPARISON.json, CANDIDATE_METRICS.csv, INDEPENDENT_PATH_CHECK.json, PROVENANCE.json e repeat1–3/RESULT.json; artefatti Actions contengono curve, leader giornalieri e audit dei fit. Baseline: results/SUMMARY.json e BASELINE_VERIFIED.json. [PR71](https://github.com/AM1975MA/Test/pull/71), branch di ricerca dedicato. Ricerca solo AM1975MA/Test; produzione non modificata, nessun merge o adozione.
