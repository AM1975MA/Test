# OLC51 — Flexible weights checkpoint (5 novembre 2026)

**Stato: RESEARCH ONLY.** Non modifica `Etf_trader`, OLC19 o i panieri operativi. Fonte integrale dei risultati: `/ETF_Research/OLC51_OLC52_Regime_20261105/OLC51_confronto_pesi_EU_USA_20261105.xlsx` nella ChatGPT Library. L'archivio consolidato del progetto è `/ETF_Research/OLC51_OLC52_Regime_20261105/ETF_Research_OLC47_OLC52_ARCHIVIO_20261105.zip` (SHA256 `44ced35101726f00a4da1ad98957b1a8a523f20a8b27cbe067d40f59b9a015e8`).

## Risultati principali (EU165 / OLC19 FAST_LOCK3)

| Allocazione | CAGR 2021–2024 | CAGR 2025–luglio 2026 annualizzato | CAGR febbraio 2019–luglio 2026 | MaxDD 2021–2024 |
|---|---:|---:|---:|---:|
| B0, 50/50 | 23,20% | 23,40% | 19,76% | -28,61% |
| Min-var totale, 63d, 35/65, shrink 50% | 25,61% | 20,49% | 19,81% | -25,74% |
| Min-var totale, 63d, 25/75, shrink 100% | **29,31%** | **18,57%** | **20,84%** | **-21,52%** |
| Min-var totale, 63d, 5/95, shrink 100% | 30,34% | 15,05% | 20,10% | -21,94% |
| Min-var residuale 2F, 63d, 25/75 | 26,68% | 20,84% | 20,08% | -26,91% |
| Inverse residual vol 2F, 63d, 25/75 | 25,45% | 22,67% | 20,62% | -27,82% |
| Regime proxy (correlazione e divario rendimenti passati) | **22,94%** | 19,52% | 18,30% | -28,61% |

2026 è parziale fino al 1 luglio, non annualizzato nella tabella dei singoli anni. Costi legacy 0,001, salvo quando indicato. Stress costo 0,003: EU 50/50 19,88%, min-var totale 25/75 25,71% sul 2021–2024.

**USA149 come controllo:** 50/50 50,77% CAGR 2021–2024; min-var totale 25/75 47,73%; non estendere automaticamente la regola europea agli USA.

## Evidenza contraria al gate ingenuo per «ticker poco differenziati»

Una proxy preventiva `abs(ret63_1-ret63_2)<=5%` identifica 21/48 mesi EU 2021–2024. Per min-var totale 25/75, il vantaggio medio relativo è **-1,6 log bp/mese** in questi mesi, contro **+74,3 bp/mese** negli altri 27. La regola con correlazione >=0,75 **non migliora** la baseline (22,94% CAGR). Una classe di regime va quindi **prevista**, non ricostruita ex-post dall'anno o dalla sola vicinanza di prezzo.

## Metodo e limiti

Sono stati provati 54 bracci x 2 mercati x 2 costi = 216 replay su OLC19 originale con medesimi tickers, stop, V6, risk overlay e calendario; regressioni fattoriali sui dati passati (EU EUNL.DE/EXSA.DE; USA SPY/TLT). Le matrici baseline sono dichiarate identiche dal rapporto OLC51. `2025–2026` è già stato visto durante la ricerca, **non è un holdout vergine**. I 54 confronti e le numerose precedenti prove OLC rendono il `29,31%` un risultato esplorativo, NON un alpha validato. Limitazioni persistenti: quotazioni US observed mask, prezzi d'asta/stop/spread, universo storico PIT, ETF delisted, dividendi, valuta e survivorship.

**Riproducibilità:** il salvataggio include workbook e rapporto più i controlli consolidati; il sorgente originario `run_olc51.py` e i dettagli `results/*` citati dal report non erano negli allegati disponibili alla creazione di questo branch. Non affermare che il checkout da solo riesegua i 216 replay.

Prossimo passo: [protocollo OLC52](OLC52_REGIME_ALLOCATION_PROTOCOL_IT.md).