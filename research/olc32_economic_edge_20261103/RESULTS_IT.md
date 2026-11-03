# OLC32 — Correzione delle etichette di prezzo e modello economico Open→Open

**3 novembre 2026 · Ricerca retrospettiva · Nuovi training eseguiti, nessun trade · Nessuna modifica a `main`.**

## Risposta in sintesi

La correzione del calendario Xetra ha recuperato 278 etichette economiche EU in due segnali del 2020, usando **date e quotazioni realmente osservate**, non interpolazioni o prezzi inventati. Il modello diretto di vantaggio economico è stato addestrato cronologicamente su dati corretti; le due architetture candidate **non superano la baseline FUSION-only su EU165 e USA149 nel periodo principale 2021–2024**. Non è giustificata una nuova selezione Top2 o un backtest con stop.

## 1. Correzioni dati: cosa è realmente stato riparato

- Il calendario storico Xetra/Börse Frankfurt 2020 esclude il 1° giugno 2020 dal trading; calendario ufficiale: https://www.deutsche-boerse.com/resource/blob/1665534/112856375187d3e93671aa3d731d09d3/data/xetra-trading-calendar-2020.pdf.
- Nel nuovo dataset di **etichette**, solo due righe calendario EU sono modificate: uscita del segnale 30/04/2020 e ingresso del segnale 29/05/2020, entrambe spostate dal 01/06 al **02/06/2020** (primo giorno comune successivo osservato).
- Copertura etichette EU 30/04/2020 **9/148 → 148/148**; EU 29/05/2020 **9/148 → 148/148**. In totale 278 osservazioni mese×ETF recuperate; le quotazioni originali **non sono state modificate**.
- Il cambio data comune posticipa di una seduta anche gli ETF non tedeschi che erano trattabili il 01/06: è una scelta di convenzione multi-venue valida per la ricerca, non un fill reale garantito.
- EU `LEEU.DE` al 02/05/2024: Open archiviato non osservato e identico al 30/04. **Non corretto per mancanza di fonte daily Open affidabile; escluso dalle etichette rilevanti**. Non va mascherato come 0% di rendimento.
- USA149: tutti i valori usati sono finiti e positivi nella matrice preparata, ma **manca la maschera originaria `observed`**. Non si dichiara originale/indipendentemente verificata una quotazione solo perché è finita.
- Segnale terminale 30/06/2026 con 01/07/2026 Open ingresso=uscita resta senza etichetta futura, non “zero”.

Lo stato e i portafogli OLC19/20 rimangono congelati; la correzione riguarda solo il nuovo target di training. Valori aggregati per data in `CORRECTION_DELTA_BY_MONTH.csv`, calendari prima/dopo in `REPAIRED_CALENDAR_AUDIT.csv`.

## 2. Ipotesi fissata prima dei fit

Obiettivo nuovo: vantaggio \(a_i=10^4[\log(O^{exit}_i/O^{entry}_i)-\operatorname{median}_j\log(O^{exit}_j/O^{entry}_j)]\) in **bp**, quindi differenza monetaria relativa al peer medio (mediana), **non** un percentile o la probabilità di essere leader.

Le etichette sono usate solo se la data di uscita corretta precede strettamente il 1° gennaio dell'anno del fit. Tutti i training bilanciano EU e USA 50/50 e danno peso uguale ai mesi all'interno del mercato. I 17 input numerici predefiniti includono FUSION e informazioni di prezzo originali (momento, trend, volatilità, drawdown), non informazione futura né ID ticker.

- **B1:** StandardScaler/Ridge alpha10, solo score FUSION, su supporto comune a tutti.
- **E1:** StandardScaler/Ridge alpha100, FUSION + 16 feature originali numeriche.
- **E2:** HistGradientBoostingRegressor (100 iter, max 7 foglie, min 100 campioni/foglia, l2=50, learning rate .04, seed 32001), stessi 17 input.

Sono stati eseguiti **18 fitting**: 6 anni annuali (2021–2026) ×3 modelli, senza rifare i learner di ETF originali. Output out-of-time per anno e saved models dentro archivio, ricaricati e verificati. I prediction scores sono disponibili anche per ticker il cui esito futuro non è noto, senza filtro sul rendimento futuro.

## 3. Risultati economico-predittivi principali 2021–2024

Comparazione su **48 mesi per mercato**, matched complete-case. 7.137 osservazioni EU e 7.152 USA. RMSE/MAE in bp e direzione del differenziale fra coppie dei Top5 quando la differenza effettiva ha magnitudine di almeno 100bp:

| Mercato | Modello | RMSE (bp) ↓ | MAE (bp) ↓ | Errore medio spread Top5 (bp) ↓ | Segno corretto per spread ≥100bp ↑ |
|---|---|---:|---:|---:|---:|
| EU | B1 | 301.94 | 216.05 | 419.99 | 51.91% (n=341) |
| EU | E1 | 306.51 | 220.01 | 423.01 | 46.63% (n=341) |
| EU | E2 | 305.01 | 218.27 | 427.90 | 47.80% (n=341) |
| USA | B1 | 468.97 | 319.54 | 753.58 | 58.17% (n=404) |
| USA | E1 | 476.31 | 325.78 | 772.70 | 43.32% (n=404) |
| USA | E2 | 471.24 | 321.70 | 760.72 | 50.99% (n=404) |

**Esito:** entrambi i candidati aumentano RMSE e MAE rispetto a B1 in entrambi i mercati; peggiorano anche la qualità delle differenze economiche fra i candidati Top5 e la precisione del segno per opportunità materiali. L'errore non si limita al ranking generale.

### Interpretazione

La deviazione standard osservata del vantaggio mensile è circa 302bp in EU e 469bp negli USA. La previsione B1 ha deviazione standard di appena 4,7/5,2bp; E1 45,7/63,0bp ed E2 37,0/58,3bp. Le feature aggiuntive generano previsioni più disperse, ma in media non predicono correttamente quali ETF otterranno le differenze più grandi. **Forza del segnale numerico non equivale a potenza economica predittiva**.

I rendimenti 2025 e 2026 parziale restano separati, già esplorati storicamente e non forniscono un holdout nuovo. I risultati del 2025 sono misti; non vengono scelti per rimettere in gioco un candidato sconfitto nel periodo prefissato.

## 4. Incertezza

Intervallo descrittivo bootstrap a blocchi di sei mesi, 3000 ricampionamenti con gli stessi mesi EU/USA. Differenza MSE = B1 − candidato; valori negativi = candidato peggiore. Non sono probabilità posteriori, né corrette per tutta la ricerca precedente.

| Modello | Mercato | Differenza MSE (bp²) | Intervallo 95% bootstrap |
|---|---|---:|---|
| E1 | EU | -2,777 | [-5,706; -21] |
| E1 | USA | -6,939 | [-12,644; -2,742] |
| E2 | EU | -1,858 | [-4,502; +434] |
| E2 | USA | -2,140 | [-4,879; +323] |

Le CI a zero non sono un veto automatico, ma in assenza di beneficio puntuale su entrambi i mercati e nella scelta Top5 non c'è base per procedere all'integrazione economica.

## 5. Collaudo indipendente e limiti

- SHA-256 dei quattro checkpoint originari controllato; source quotes/decisioni/strategie non modificati.
- **278** nuovi label endpoints validi nei due segnali 2020; nessun altro mese cambiato.
- Ricostruzione indipendente di TUTTE le etichette O2O da matrice O originale: errore massimo **0bp**; centering alla mediana: massimo **0bp**.
- Controllo `source_date <= signal_date`, assenza duplicati (mercato,data,ticker), esclusione LEEU non osservato e riga terminale.
- Tutti i **18 modelli** salvati e ricaricati: previsioni coincidenti; nessun label futuro entra nei fit passati; metriche mensili riconciliate indipendentemente.
- B1/E1/E2 sullo **stesso supporto**: i missing di feature non favoriscono artificiosamente un candidato.

**Limiti non risolti:** maschera delle quote US, dati point-in-time, ETF delistati, dividendi/total-return, FX, bid/ask e fill intraday; le date multi-borsa non garantiscono una singola asta comune o stesso prezzo eseguibile. I risultati 2019–2026 sono già stati esplorati molte volte, il bootstrap non elimina questa distorsione.

## Decisione e prossimo obiettivo

La nuova previsione del vantaggio economico Open→Open è stata addestrata e collaudata ma **non supera il gate di qualità**: nessun nuovo Top2, nessun backtest rischio/V6, nessuna promozione. Non sarebbe corretto forzare una rete più complessa o scegliere altri iperparametri dopo aver visto i risultati.

Per cercare un miglioramento sostanziale servirebbero **nuova informazione indipendente** oppure un obiettivo specifico per la coda degli eventi economici (spread grandi davvero prevedibili) da preregistrare in un lotto differente, con un orizzonte prospettico nuovo. Un diverso target sarebbe una nuova ipotesi, non la prosecuzione forzata di questo test negativo.

## File e riproducibilità

- `INPUT_MANIFEST.json`, `REPAIRED_CALENDAR_AUDIT.csv`, `CORRECTION_DELTA_BY_MONTH.csv`, `PER_MONTH_COVERAGE.csv`, `OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz`.
- `models/2021..2026` per B1/E1/E2, `PREQUENTIAL_DIRECT_ECONOMIC_EDGE.csv.gz`, `MATCHED_MONTHLY_MODEL_ERRORS.csv`, `TOP5_PAIRWISE_SPREADS.csv`, `MATCHED_SUMMARY.csv`, `BLOCK6_BOOTSTRAP.csv`, `VERIFICATION_INDEPENDENT.json`.
- `olc32_economic_edge.py`, `verify_olc32.py`, protocolli e sorgenti originali identificati per SHA256.
- I binary bytes sono nel pacchetto scaricabile / Library, non implicitamente nel repository GitHub.
