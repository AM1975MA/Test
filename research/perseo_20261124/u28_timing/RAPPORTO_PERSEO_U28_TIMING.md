# Perseo U28 · Prima, seconda, terza, quarta o quinta apertura

25 novembre 2026. **L'attesa variabile è il confronto più interessante: USA e Trade Republic migliorano, Europa cede rendimento. U27 rimane la base comune.** La scelta walk-forward della durata tramite Ridge non supera U27 a costi ordinari su nessuno dei tre panieri.

## Quanto aspettare

CAGR netto, con massimo drawdown misurato alle aperture, dal 2 gennaio 2020 al 1º luglio 2026. Ticket pari a 1 unità per ordine, più 15 bp per lato. Salvo il confronto OLC67, la coppia conserva pesi 50/50. Seconda apertura significa una seduta dopo U27, quinta significa quattro sedute dopo. Il ranker ha già scelto la nuova coppia alla chiusura precedente la prima apertura. Durante l'attesa le protezioni e la difesa rimangono attive.

| Durata o regola | Europa CAGR / MaxDD | USA CAGR / MaxDD | Trade Republic CAGR / MaxDD |
|---|---:|---:|---:|
| Prima · U27 | 23,91% / −27,43% | 42,75% / −26,59% | 26,41% / −26,85% |
| Seconda | 19,27% / −29,97% | 45,60% / −28,14% | 28,71% / −26,82% |
| Terza | 21,01% / −31,50% | 45,26% / −29,98% | 28,84% / −26,64% |
| Quarta | 22,55% / −31,93% | 43,20% / −28,93% | 26,64% / −27,67% |
| Quinta | 23,70% / −27,81% | 43,01% / −27,38% | 28,48% / −27,07% |
| Terza + MINVAR63 · confronto OLC67 | 20,69% / −29,74% | 41,50% / −29,98% | 30,42% / −26,49% |
| Condizionale · prima o terza | 22,40% / −30,84% | 43,86% / −29,98% | 26,97% / −27,17% |
| **Condizionale · fino alla quinta** | **22,22% / −27,43%** | **46,95% / −28,14%** | **30,37% / −27,45%** |
| Ridge walk-forward · prima o terza | 22,63% / −29,65% | 41,55% / −25,61% | 24,80% / −26,68% |
| Ridge walk-forward · da prima a quinta | 21,34% / −29,78% | 41,86% / −25,61% | 24,93% / −26,67% |

## La regola comune con attesa variabile

Alla prima apertura programmata, si attende solo se cambia almeno metà della coppia, la nuova coppia ha sottoperformato la vecchia nelle ultime cinque sedute, e si verifica almeno una delle due condizioni seguenti: replica debole o cambio nominale di entrambe le gambe. La replica è debole se c'è un fallback locale, se la correlazione mediana è sotto 0,80 o il tracking ratio mediano supera 0,70. Nei successivi tre giorni si entra all'apertura seguente quando la nuova coppia recupera il divario accumulato dalla chiusura precedente la prima apertura. La quinta apertura è il limite programmato. L'entrata reale segue le quotazioni e i vincoli del simulatore.

Su 218 rotazioni economicamente distinte, la regola fa attendere 120 volte. Nei tre panieri insieme, fra queste 120, programma l'ingresso **68 volte alla seconda, 10 alla terza, 4 alla quarta e 38 alla quinta**. La terza apertura è utile come controllo storico. La maggior parte delle attese termina quindi alla seconda o alla quinta apertura.

| Paniere e scenario | Δ CAGR della regola variabile vs U27 | Δ MaxDD in punti, positivo = miglioramento |
|---|---:|---:|
| Europa · 15 bp | −1,69 pp | 0,00 pp |
| USA · 15 bp | +4,20 pp | −1,55 pp |
| Trade Republic · 15 bp | +3,96 pp | −0,60 pp |
| Europa · 30 bp, una seduta e 100 bp sugli stop | +2,35 pp | −1,92 pp |
| USA · stesso stress | +2,42 pp | −1,72 pp |
| Trade Republic · stesso stress | +3,62 pp | +0,26 pp |

Il ritardo aggiuntivo si applica come nel motore U27: differisce anche il flusso decisionale e lascia attivi gli stop nelle sedute originali. La regola USA a maggiore CAGR comporta un drawdown più profondo. Sui log-rendimenti mensili, l'intervallo simultaneo al 95% dell'effetto della regola variabile a costi normali include zero in ogni paniere. Trade Republic: **+3,08 pp log/anno, da −2,26 a +8,43**. USA: +2,90, da −8,41 a +14,20. Europa: −1,37, da −7,47 a +4,72. Il bootstrap usa mesi appaiati a blocchi da sei, preservando l'allineamento fra mercati.

## Trade Republic nel 2020–2022

U27 segna −3,02% di CAGR. L'attesa fissa di due o quattro sedute arriva rispettivamente a **+9,02% e +9,11%**. Terza apertura con MINVAR63 arriva a **+10,19%**. La regola variabile ottiene **+2,19%**, ma dal 2023 sale al **60,76%** contro il 58,78% di U27. La combinazione terza+MINVAR63 arriva al 50,78% dal 2023. Le due varianti TR vicine al 30,4% sull'intero storico hanno quindi percorsi differenti.

Nelle simulazioni che partono dallo stesso conto e terminano dopo dieci sedute, la regola variabile aiuta TR in 16 dei 33 casi in cui attende. Valore medio di quei casi: **+60,35 bp netti**. È un beneficio economico medio dovuto alla dimensione delle vittorie e delle perdite, con una frequenza di successo vicina al 50%. Il dataset locale misura soltanto il timing a 50/50, mentre il braccio MINVAR63 viene letto sul conto in continuità.

## Cosa spiegano proxy, turnover e modello

- **Il fallback locale non è un segnale comune.** Sulle 50 rotazioni europee con almeno un fallback, aprire alla terza produce in media −28,8 bp in dieci sedute rispetto alla prima. Per TR la stessa condizione vale +19,1 bp su 30 casi, poco sotto i +21,7 bp su 45 rotazioni senza fallback.
- **Il cambio completo non identifica le rotazioni TR più favorevoli.** Nelle 18 rotazioni TR a minore turnover, la terza apertura dà +63,7 bp medi, contro +7,1 bp nelle 57 a turnover alto. Sono sottogruppi descrittivi.
- **Il Ridge non ha imparato una durata utile per un conto comune.** Le due versioni, con scelta fra prima/terza o fra tutte le aperture, iniziano a produrre segnali nell'agosto 2021. Nella versione da prima a quinta, le rotazioni ritardate realizzano in media −49 bp in EU, −4 bp USA e −9 bp TR a parità di stato. La maggiore flessibilità aumenta le scelte possibili ma il vantaggio netto stimato non si realizza.

## Riproducibilità

120 conti verificati ricostruendo gli ordini. 218 rotazioni simulate con due livelli di costo e cinque aperture, per 2.180 confronti di finestra, inclusa la prima apertura. Nove parità con U27 e 18 con i precedenti replay della terza apertura, con o senza MINVAR63. Dodici finestre di ripresa ricontrollate rifacendo l'intera storia. Sei perturbazioni dei prezzi futuri per le feature e dieci delle etichette future per il fit. Lo storico resta lo stesso campione già esplorato. Le prove riguardano backtest simulati e non nuovi periodi indipendenti.

Il pacchetto contiene i sorgenti, i CSV, i riferimenti al checkpoint U20–U27 e i dati di controllo del replay precedente. Per ricalcolare, ripristinare il checkpoint U20–U27 e posizionare `u28_timing` al livello delle cartelle `u20`, `u23`, `u24` e `u27`. Da `u28_timing`, con Python 3.12, numpy 2.3.5, pandas 2.2.3 e scikit-learn 1.8.0:

```sh
python timing28.py --prior-fixed prior_fixed.csv
python analyze.py
python verify.py
```

[Checkpoint U20–U27](https://chatgpt.com/library?file_id=libfile_fde3_f-d9c9f47eef0481918b70f765064520ff_549d1bce98388191a0aeb13709c4eff9&account_id=personal)
