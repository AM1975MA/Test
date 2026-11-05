# OLC52 — Risultati del selettore ML di allocazione (5 novembre 2026)

**Stato: RESEARCH ONLY / NO PROMOTION.** OLC19 operativo invariato. Ricostruzione nativa di OLC19 e di OLC51 min-var 63d cap25/75 verificata su sette array contabili; tutti i replay ricalcolano stop, risk state e costi.

## CAGR EU165, costo legacy 0,001

| Policy | 2021–2024 | 2025–luglio2026, annualizzato | Feb2019–luglio2026 |
|---|---:|---:|---:|
| 50/50 OLC19 | 23,20% | 23,40% | 19,76% |
| Min-var totale 25/75 sempre | 29,31% | 18,57% | 20,84% |
| Gate media dei rendimenti passati | 26,18% | 18,57% | 20,36% |
| Ridge 3 feature di rischio | **25,85%** | 22,87% | **21,05%** |
| Ridge 6 feature | 24,20% | 22,31% | 20,07% |
| Ridge 6 con margine prudenziale | 23,68% | 22,93% | 19,92% |

Con costo legacy 0,003 nel 2021–2024: EU 50/50 19,88%; min-var 25/75 25,71%; Ridge 3 feature 22,35%. USA 2021–24 con costo 0,001: 50/50 50,77%; min-var25/75 47,73%; Ridge3 49,21%; Ridge6 50,54%. Nessuna promozione USA.

## Diagnostica ML e correzioni di qualità

Il target ML è il differenziale netto mensile tra min-var 25/75 e 50/50, fit Ridge expanding cronologico con etichette mature e soli dati precedenti al trade. Nel 2021–24 la Ridge 3-feature ha RMSE economico 142,0 bp su 45 mesi contro 135,6 bp per una previsione train-only basata sulla media storica. La Ridge 6-feature ha 147,8 bp contro 135,3. Quindi NON è dimostrata una migliore capacità di riconoscere i regimi.

Due correzioni sono state effettuate dopo il primo risultato e sono documentate: breadth di mercato sui 22 Close effettivamente osservati invece di giorni d'indice festivi; e gate di ammissibilità della Ridge rischio-only calcolato sulle sole tre feature effettivamente usate. Il dato EU rischio-only finale è **25,85%**, non il 26,54% provvisorio. Nel 2025 il selettore rischio-only sceglie ancora il 25/75 in 9 su 12 mesi: non riconosce in modo convincente il regime sfavorevole.

## Provenienza e limiti

Rapporto integrale, workbook con rendimenti e scelte mensili e bundle riproducibile (45 file) salvati nella Library dell'utente sotto /ETF_Research/OLC51_OLC52_Regime_20261105. I grandi input originali restano nelle rispettive cartelle OLC19 e OLC32; il solo checkout GitHub non è autosufficiente.

Lo storico fino a luglio 2026 è stato ripetutamente esplorato (OLC01–51); niente holdout vergine, nessun nuovo alpha validato. Restano verifiche su universo ETF point-in-time, osservabilità originaria USA, esecuzione asta/stop, spread, FX e distribuzioni. La ricerca proseguirà solo con dati ulteriori non già esplorati e parametri preregistrati.

**Decisione:** mantenere OLC19 congelato; modelli di regime solo nel laboratorio di ricerca.