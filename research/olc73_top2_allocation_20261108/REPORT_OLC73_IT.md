# OLC73 — Allocazione fra i Top2: 64 replay nativi controllati

**8 novembre 2026 · Ricerca retrospettiva, non segnale di trading · Nessuna modifica a OLC19, OLC67 o `main`.**

## Esito principale

Non emerge **un'unica allocazione** capace di migliorare contemporaneamente Europa e USA rispetto a 50/50 nello stesso regime di timing, sul periodo principale 2021–2024 e sull'intera serie. Il risultato più informativo è una **asimmetria del valore economico del primo/secondo ETF della coppia contestuale**, che cambia nel tempo.

- Nel periodo 2021–2024, in EU il 25/75 a favore del secondo ETF tende a battere il 75/25 a favore del primo; in USA domina il 75/25 a favore del primo.
- USA 2024: 75% sul primo avrebbe reso 115,91% nell'anno contro 78,61% del 50/50. USA 2025: lo stesso 75/25 sul primo rende appena 1,92% contro 13,57% del 50/50; il 75% sul secondo rende 26,62%. Le differenze non sono CAGR ma rendimenti annuali nativi.
- Gli USA del 2025–2026 e l'Europa del 2026 mostrano un'inversione dell'efficacia della preferenza per l'ordine dei Top2. **Non sappiamo ancora anticipare questa inversione** con segnali osservabili al momento della decisione.

Tutti i confronti modificano **soltanto** il peso tra i due ETF già selezionati da `TOP2_CONTEXT_REVALUE`. FUSION Return/ET/XGB, V6, FAST_LOCK3, prezzi, calendari e stop restano congelati.

## Otto politiche preregistrate, ingresso immediato

| Pesi | EU CAGR 2021–24 | USA CAGR 2021–24 | EU CAGR FULL | USA CAGR FULL |
| --- | --- | --- | --- | --- |
| 50/50 (OLC19) | 23.20% | 50.77% | 19.76% | 39.48% |
| 65/35 sul primo | 21.07% | 59.53% | 17.85% | 42.79% |
| 75/25 sul primo | 19.84% | 65.46% | 16.30% | 44.43% |
| 35/65 sul secondo | 24.75% | 42.30% | 20.89% | 35.62% |
| 25/75 sul secondo | 27.35% | 36.94% | 22.43% | 33.24% |
| Inverso volatilità 63 (25–75) | 25.19% | 48.74% | 20.16% | 39.09% |
| 65% al maggiore momentum 63 | 22.70% | 48.83% | 18.49% | 42.55% |
| MinVar63 (25–75, OLC56) | 29.31% | 47.73% | 20.84% | 38.98% |

FULL = febbraio 2019 → prima apertura luglio 2026; 2026 parziale; CAGR su 252 sedute contabili/anno. Commissioni legacy=0,001, stop friction=0,001. Non sono quotazioni broker.

## Stesse politiche con DELAY3

| Pesi | EU CAGR 2021–24 | USA CAGR 2021–24 | EU CAGR FULL | USA CAGR FULL |
| --- | --- | --- | --- | --- |
| 50/50 (OLC19) | 28.11% | 55.31% | 22.05% | 43.26% |
| 65/35 sul primo | 25.44% | 61.96% | 19.54% | 46.03% |
| 75/25 sul primo | 23.66% | 66.33% | 17.48% | 47.27% |
| 35/65 sul secondo | 30.58% | 48.71% | 23.97% | 39.87% |
| 25/75 sul secondo | 33.89% | 44.47% | 26.08% | 38.39% |
| Inverso volatilità 63 (25–75) | 29.87% | 52.17% | 21.89% | 41.98% |
| 65% al maggiore momentum 63 | 27.30% | 54.74% | 20.34% | 46.32% |
| MinVar63 (25–75, OLC56) | 34.43% | 51.27% | 22.61% | 42.10% |

La precedente OLC67 coincide esattamente con MINVAR63+DELAY3+FAST_LOCK3: **EU 34,43% / USA 51,27% CAGR 2021–24**, **EU 22,61% / USA 42,10% FULL**. Non è una nuova scoperta OLC73.

## Il cambio di leadership nel 2024–2026

| Mercato | Anno | 50/50 | 75% primo | 75% secondo | 65% momentum leader |
| --- | --- | --- | --- | --- | --- |
| EU | 2024 | 22.44% | 20.80% | 23.74% | 19.44% |
| EU | 2025 | 17.95% | 10.99% | 17.18% | 12.86% |
| EU | 2026* | 16.51% | 20.52% | 12.36% | 19.29% |
| USA | 2024 | 78.61% | 115.91% | 46.22% | 81.99% |
| USA | 2025 | 13.57% | 1.92% | 26.62% | 27.80% |
| USA | 2026* | 62.44% | 51.77% | 68.25% | 77.99% |

*2026 cumulato sino alla prima apertura di luglio; non annualizzato. Nel ramo contabile nativo `d1` è il primo ETF ordinato dal ranking contestuale discendente, non necessariamente il più redditizio in futuro.

## Rischio e costi

| Mercato | Peso | DD FULL immediato | DD FULL DELAY3 | CAGR FULL immediato costi 0,003 | CAGR FULL DELAY3 costi 0,003 |
| --- | --- | --- | --- | --- | --- |
| EU | 50/50 (OLC19) | -28.61% | -28.65% | 16.18% | 18.37% |
| EU | 75/25 sul primo | -30.05% | -30.61% | 12.68% | 13.85% |
| EU | 25/75 sul secondo | -25.36% | -27.56% | 18.63% | 22.15% |
| EU | MinVar63 (25–75, OLC56) | -23.76% | -26.59% | 17.09% | 18.81% |
| EU | 65% al maggiore momentum 63 | -28.44% | -28.66% | 14.79% | 16.59% |
| USA | 50/50 (OLC19) | -26.12% | -30.40% | 31.34% | 34.80% |
| USA | 75/25 sul primo | -27.66% | -30.65% | 35.91% | 38.47% |
| USA | 25/75 sul secondo | -26.06% | -29.33% | 25.30% | 30.15% |
| USA | MinVar63 (25–75, OLC56) | -25.23% | -27.60% | 30.98% | 33.89% |
| USA | 65% al maggiore momentum 63 | -26.07% | -31.09% | 34.36% | 37.83% |

Aumento dei costi da coefficiente 0,001 a 0,003: le differenze di direzione sul peso del primo/secondo ETF rimangono visibili, ma i CAGR sono più bassi. Il rischio USA di TOP1_75 con DELAY3 arriva a circa −30,65% FULL, contro −26,12% della baseline OLC19 immediata. Evitare di confondere questo confronto fra timing diversi con la sola variazione dei pesi.

## Incertezza e verifica di robustezza

| Mercato | Peso | Timing | Periodo | Δ log rendimento annualizzato vs 50/50 | IC95% block6 descrittivo |
| --- | --- | --- | --- | --- | --- |
| EU | 25/75 sul secondo | IMMEDIATE | MAIN2021_2024 | +3.17 pp | [-2.92 pp; +9.60 pp] |
| EU | 25/75 sul secondo | IMMEDIATE | FULL | +2.20 pp | [-1.32 pp; +6.02 pp] |
| USA | 75/25 sul primo | IMMEDIATE | MAIN2021_2024 | +8.80 pp | [+2.94 pp; +14.91 pp] |
| USA | 75/25 sul primo | IMMEDIATE | FULL | +3.48 pp | [-2.65 pp; +9.19 pp] |
| EU | 25/75 sul secondo | DELAY3 | MAIN2021_2024 | +4.17 pp | [-1.33 pp; +9.89 pp] |
| EU | 25/75 sul secondo | DELAY3 | FULL | +3.25 pp | [-0.41 pp; +6.85 pp] |
| USA | 75/25 sul primo | DELAY3 | MAIN2021_2024 | +6.51 pp | [+1.16 pp; +12.76 pp] |
| USA | 75/25 sul primo | DELAY3 | FULL | +2.77 pp | [-2.09 pp; +7.72 pp] |

I bootstrap sono appaiati su blocchi circolari di 6 mesi (4.000 repliche); non correggono la ricerca su decine di test OLC01–72. **Tutti gli intervalli FULL riportati qui includono zero.** La performance del 2024/2025 e la selezione dell'allocazione vincente sono dati già esplorati: non c'è un holdout indipendente.
La verifica preregistrata richiedeva per una sola regola comune: miglioramento del FULL CAGR in *entrambi* EU/USA, MAIN non inferiore in entrambi e FULL MaxDD non deteriorato di oltre 3pp rispetto al 50/50 con lo stesso timing. **Nessuna delle sette politiche alternative supera tutti questi gate**. Non viene promossa alcuna strategia.

## QA e limiti delle fonti

- **64 replay nativi** = 8 pesi × 2 timing × 2 mercati × 2 coefficienti di costo; **576 periodi/metriche** ricalcolati autonomamente da rendimenti giornalieri.
- Parità **esatta dei 7 array** nativi di OLC19 sulla baseline 50/50/IMMEDIATE per entrambi i mercati; **16 serie log-rendimento** precedentemente eseguite in OLC67 coincidono (HALF e MINVAR, immediato/delay3, fee 0,001/0,003). 90 eventi mensili per mercato, le identità delle due posizioni sono fisse.
- Per MOM63 e INVOL63, i prezzi sono SOLO gli ultimi 64 Close completati prima dell'ingresso. In EU la disponibilità dei flag `observed` obbliga a fallback 50/50 in **34 su 90** eventi per ciascuna policy; in USA 4/90. I dati USA originali non includono i flag osservati, quindi il codice segue la convenzione storica OLC56 `observed = finite(C)&(C>0)`: **non certifica la reale osservabilità dei prezzi USA**.
- Come già noto, restano non certificati universo point-in-time, maschera quote USA, adjusted/total-return/dividendi omogenei, prezzi di esecuzione degli stop/bid-ask, costi broker effettivi e impatto della liquidità. Sono limiti rilevanti per ogni CAGR, non soltanto per OLC73.

## Prossimo problema da studiare (nessun nuovo backtest in questo report)

La prima posizione della coppia contestuale ha un vantaggio economico **che cambia segno nel tempo**. Piuttosto che una media di portafogli o un semplice selettore di policy (OLC69/70), il passo metodologicamente utile sarebbe un *modello pairwise* sulle stesse due opportunità, con target cronologicamente maturo `log((1+r_1)/(1+r_2))` a 21 e 42 sedute, e input ex ante originari Return/ET/XGB, margine contestuale, momentum e volatilità della coppia. Un test isolerebbe la capacità di prevedere quale ETF meriti più capitale, senza cambiare Top2 né timing. Fissare a priori la calibrazione/regularizzazione e valutare il 2024/2025 come date già esplorate, mai come nuovo OOS. È un progetto, NON un miglioramento dimostrato.

**Decisione:** conservare OLC19 come baseline e OLC67 come candidato paper; registrare OLC73 come evidenza che la costruzione dei pesi Top2 è una leva importante, non ancora sfruttabile con una regola universale affidabile.