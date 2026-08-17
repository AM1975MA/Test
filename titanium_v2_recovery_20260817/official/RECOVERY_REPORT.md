# Meteor Titanium V2 — rapporto di recupero ufficiale

Data di chiusura: 17 agosto 2026  
Stato: **ranking storico recuperato integralmente; percorsi congelati originali recuperati**.

## Esito

Il recupero della strategia Titanium è riuscito nei due elementi necessari per preservare il backtest ufficiale:

1. il pannello autentico `TIT_R` ricostruisce esattamente il selettore top-1 congelato;
2. i percorsi giornalieri originali dei 500 panieri, inclusa la variante Titanium V2 `BALANCED`, sono nuovamente disponibili.

La parità è stata verificata su **56.500 decisioni su 56.500 (100,0000%)**, cioè 500 panieri × 113 date di segnale. Non sono emerse mappature ticker ambigue.

## Definizione congelata

Titanium V2 `BALANCED`:

- ranking: score autentico `TIT_R`;
- concentrazione adattiva: top-1 al 100% quando il margine top-1/top-2 supera il 12%;
- sotto soglia: 75% top-1 e 25% top-2;
- governor sistemico ereditato da Titanium V1: `RC0.25_RW0.25_RE0.25_CD3_S1`;
- esecuzione point-in-time D+1;
- periodo dei percorsi congelati: 1 febbraio 2017 – 1 luglio 2026.

## Risultati ufficiali sui 500 panieri

Le statistiche seguenti derivano direttamente dai percorsi congelati originali, non da una rigenerazione con prezzi successivamente aggiornati.

| Metrica | Titanium V2 |
|---|---:|
| CAGR medio | 21,6541% |
| CAGR mediano | 21,5584% |
| CAGR P5 / P95 | 7,5903% / 35,9695% |
| CAGR minimo / massimo | -2,8561% / 47,2272% |
| MaxDD medio | -33,9351% |
| MaxDD mediano | -32,5062% |
| Sharpe medio | 0,8681 |

Il percorso `BALANCED` coincide con il risultato ufficiale precedentemente documentato: CAGR medio 21,6541%.

## Test controfattuale sull'universo completo

È stato inoltre eseguito un test separato utilizzando il ranking autentico su tutti i ticker disponibili nel pannello: 149 ticker scored su 150 colonne prezzo (PIN non utilizzabile). Questo test **non** sostituisce la distribuzione ufficiale dei 500 panieri.

| Strategia | CAGR | MaxDD | Sharpe |
|---|---:|---:|---:|
| Titanium V1, universo completo | 39,7313% | -33,6618% | 1,1866 |
| Titanium V2, universo completo | 37,0676% | -30,8012% | 1,2364 |

L'ultima data del pannello autentico è il 29 maggio 2026; la selezione risultante è BNO / USL. Le selezioni live successive, ottenute con un produttore riaddestrato, appartengono a una versione distinta.

## Diagnosi della discrepanza precedente

La differenza osservata nel tentativo di agosto non proveniva dalla strategia congelata. Era stata causata dall'uso di un produttore riaddestrato al posto del pannello autentico `TIT_R`. Il pacchetto live rigenerato di agosto riportava infatti circa 18,60% di CAGR del router, contro il 21,6541% ufficiale di Titanium V2.

Per evitare contaminazioni:

- i file in `authentic/` e `frozen_paths/` sono le fonti di verità del recupero storico;
- ogni motore live riaddestrato deve essere etichettato come nuova versione e sottoposto a calibrazione/parità prima della promozione;
- non si devono sovrascrivere i percorsi congelati con replay basati su prezzi aggiornati.

## Integrità delle fonti principali

| File | SHA-256 |
|---|---|
| `ORTHOGONAL_SCORE_PANEL.pkl` | `57caef7e4b824d0a7c75cea389d7e957b2da23bb0925a15b696ca0bfdaa2af88` |
| `SUPER_GOLD_BASKET_MEMBERSHIP.csv` | `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e` |
| `REG_W24_F005_S008_PATHS.npz` | `831b426d3a59b7132686555f4591212ddad999e79a1c5c7a118f1bfdd72d166b` |
| `TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz` | `7bf8441c66d0256dd3e5897df8f0a2271b00faf0c1d6d5ed9bc2440d614adc54` |

## Contenuto del pacchetto

- `authentic/`: score panel e membership originali;
- `frozen_paths/`: matrice delle selezioni ufficiali e percorsi V1/V2 dei 500 panieri;
- `results/`: metriche per paniere, distribuzioni, parità, test universo completo e grafico;
- `code/`: script di replay, controllo della parità e produzione dei risultati;
- `original_specs/`: specifiche e codice sorgente congelato di riferimento;
- `SHA256SUMS.txt`: impronte di tutti i file inclusi.

## Limite operativo residuo

Il recupero storico è concluso. Resta separato il lavoro di produzione live: un nuovo score producer deve dimostrare parità o essere promosso con un nuovo nome/versione. Non è corretto presentare il motore riaddestrato di agosto come una ricostruzione bit-identica di Titanium V2.
