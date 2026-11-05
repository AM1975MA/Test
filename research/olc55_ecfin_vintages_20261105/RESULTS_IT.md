# OLC55 — DG ECFIN original point-in-time vintage audit (5 novembre 2026)

**Stato: source/readiness audit, nessun nuovo modello ML addestrato, NO PROMOTION.** Baseline OLC19 e OLC52 preservate.

## Risultato

Fonte primaria: [archivio ufficiale DG ECFIN](https://economy-finance.ec.europa.eu/economic-forecast-and-surveys/business-and-consumer-surveys/download-business-and-consumer-survey-data/press-releases_en). Dieci comunicati originali datati (2021-05..2026-04) sono stati letti e i valori headline ESI/EEI UE/eurozona trascritti con URL sorgente. Il confronto è stato eseguito sui 90 eventi mensili EU165 del checkpoint OLC52 (SHA256 input 1ccfff0e4fd362836aab37b21b7e62bf7559b18eb1884b409b1678b0c8793e71).

| Gate original vintage | Conteggio |
|---|---:|
| Press releases originali numerici | 10 |
| Eventi OLC52 complessivi | 90 |
| Eventi con dato original-vintage validamente disponibile | **11** |
| Eventi senza copertura sufficiente | **79** |
| Vintage prima del 2021 | **0** |
| Eventi validi 2021–2024 | **8** |
| Eventi validi 2025–luglio2026 | **3** |

Regola: dato ESI utilizzabile non prima del giorno successivo alla pubblicazione, ma non più tardi del primo giorno successivo alla pubblicazione successiva; anzianità massima 45 giorni e stessa policy di maturità `valid_63` OLC52. Per il comunicato novembre 2022 l'archivio visualizza date ambigue (titolo 29/11 e posting 1/12): usata **29 novembre**, più conservativa. Un PDF mancante non implica che il dato non fosse pubblicato.

## Revisioni: esempi audit, indice UE

| Mese | ESI originale in release | serie corrente 2026-10-23 | scostamento |
|---|---:|---:|---:|
| giugno 2024 | 96,4 | 96,6 | +0,2 |
| ottobre 2024 | 96,0 | 96,3 | +0,3 |
| maggio 2025 | 95,2 | 95,7 | +0,5 |

Fonte storico corrente: [RAC-EU che dichiara dati Eurostat ECFIN](https://rac-eu.economiaeficiente.org/en/country/euro-area-2/economic-sentiment-indicator/), aggiornamento indicato ottobre 2026; usato **esclusivamente** per la misura delle revisioni, non come input dell'ipotetico ML.

## Decisione

Con 11 eventi contro 90, e senza training originale 2019–20, non è possibile affermare che ECFIN migliori o peggiori OLC52. Nessun CAGR OLC55 è stato calcolato né inventato. Documento di ricerca e codice `build_olc55.py` che applica il gate, CSV dei 10 valori originali, confronto revisioni, join alle 90 etichette OLC52, audit e tool opzionale di download PDF con gestione 429 sono conservati nella **ChatGPT Library** `/ETF_Research/OLC55_ECFIN_PIT_20261105/`, pacchetto `OLC55_ECFIN_PIT_AUDIT_20261105.zip`, checksum SHA256 `9916655e1698d1224df0c7270b09c910f0ef9488bea48656a309bb61262144f6`.

Per test causale completo occorre reperire tutti i vintage reali mese per mese (2020/2021 warmup e 2021–2026), certificare le date effettive e fissare ex ante il modello. Dati 2019–luglio2026 già ampiamente esplorati; eventuale backtest ricostruito sarebbe diagnostico, non nuova prova vergine.