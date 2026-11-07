# OLC70 — Controfattuali allo stesso stato e apprendimento adattivo

**7 novembre 2026 · RESEARCH ONLY · Nessuna modifica a OLC19 o `main`.**

Questo è un esperimento eseguito nel motore OLC19, non un progetto teorico. Il periodo febbraio 2019–prima apertura luglio 2026 è già stato esplorato ripetutamente negli esperimenti OLC01–69. Nessuna finestra è un nuovo holdout indipendente. La conclusione è **NEGATIVA** per l'apprendimento adattivo; i protocolli sono fissati nei commit GitHub prima dei rispettivi esiti.

## 1. Risultati CAGR verificati

Tutte le varianti usano selezioni TOP2_CONTEXT_REVALUE, V6, FAST_LOCK3, stop-friction .001, e fee legacy .001. La nuova variante OLC70B parte in ciascun mese dal proprio stato contabile effettivo, genera 4 azioni controfattuali e aggiorna il learner solo su label precedenti e mature.

| Mercato e periodo | OLC19 (50/50 immediato) | OLC67 (MINVAR63 + DELAY3) | OLC70A (labels su stato OLC19) | OLC70B (labels on-policy) |
|---|---:|---:|---:|---:|
| Europa 2021–2024 | 23.20% | 34.43% | 29.04% | 29.04% |
| Europa FULL 2019–lug2026* | 19.76% | 22.61% | 21.83% | 21.90% |
| USA 2021–2024 | 50.77% | 51.27% | 46.10% | 46.10% |
| USA FULL 2019–lug2026* | 39.48% | 42.10% | 35.99% | 35.72% |

*Luglio 2026 contiene soltanto la prima apertura. Il CAGR segue la convenzione 252 valorizzazioni/anno dell'engine OLC19, non l'annualizzazione del solo 2026.*

### Max drawdown completo

| Mercato | OLC19 | OLC67 | OLC70A | OLC70B |
|---|---:|---:|---:|---:|
| Europa | -28.61% | -26.59% | -26.47% | -26.47% |
| USA | -26.12% | -27.60% | -26.12% | -26.12% |

### Rendimenti annuali 2024–2026 (2026 parziale, NON annualizzato)

| Mercato e anno | OLC19 | OLC67 | OLC70A | OLC70B |
|---|---:|---:|---:|---:|
| Europa 2024 | 22.44% | 35.17% | 30.30% | 30.30% |
| Europa 2025 | 17.95% | 10.15% | 15.53% | 16.01% |
| Europa 2026* | 16.51% | 15.28% | 12.03% | 12.03% |
| USA 2024 | 78.61% | 68.88% | 68.51% | 68.51% |
| USA 2025 | 13.57% | 17.83% | 10.39% | 9.10% |
| USA 2026* | 62.44% | 52.06% | 57.12% | 56.62% |

Nel 2024 OLC70B intercetta parte del vantaggio europeo rispetto alla vecchia strategia ma non preserva il rally USA. Nel 2025 è inferiore a entrambe le strategie USA; nel 2026 parziale non conserva il rendimento completo della vecchia strategia nei due mercati.

**Gate ex ante:** fallito. OLC70B presenta CAGR FULL e MAIN inferiori a OLC19 negli USA. Nessuna promozione; il ramo operativo resta quello originale.

## 2. Nuovo meccanismo: 4 azioni dalla stessa fotografia del conto

A ogni apertura mensile la simulazione originale OLC19 fornisce lo stato pre-trade: quantità ETF, strumenti difensivi, liquidità, cooldown, lock, stop, target e scheduler. Le quattro alternative sono A=50/50+IMMEDIATE, B=MINVAR63+IMMEDIATE, C=50/50+DELAY3, D=MINVAR63+DELAY3. I quattro rami partono dallo stesso capitale e stato e corrono fino all'apertura del mese successivo.

- **OLC70A:** addestra usando questi differenziali da snapshot della policy OLC19 sempre mantenuta.
- **OLC70B:** ad ogni mese sceglie e consolida **solo** il ramo realmente selezionato. Conserva lo stato risultante per il mese successivo; le etichette delle quattro azioni vengono aggiunte alla storia soltanto dopo il mese. Non si mescolano NAV di strategie indipendenti.
- Learner volutamente invariato da OLC69: 4 feature ex-ante, StandardScaler train-only, Ridge α25 per ciascuna delle alternative B/C/D, almeno 24 osservazioni e training fino a t−2; A se nessun vantaggio stimato superiore a 5 logbp.

I dati del 2019–2026 sono già stati utilizzati per costruire questa famiglia di esperimenti: i risultati di OLC70B NON rappresentano validazione indipendente.

## 3. Perché il risultato resta negativo: test sulla capacità di previsione

Ogni cella della tabella indica RMSE sul vantaggio mensile relativo all'azione A, in **log-basis-point**; più basso è migliore. Il riferimento è una previsione train-only della media degli outcome maturi, disponibile con le medesime informazioni. I periodi iniziali prima del minimo training sono esclusi.

| Mercato | Azione da prevedere | Media storica RMSE | OLC70B Ridge RMSE | Delta Ridge − media |
|---|---|---:|---:|---:|
| Europa | B | 133.9 | 137.3 | +3.4 |
| Europa | C | 142.3 | 146.6 | +4.3 |
| Europa | D | 173.9 | 172.6 | -1.3 |
| USA | B | 204.3 | 206.8 | +2.5 |
| USA | C | 241.6 | 254.6 | +13.0 |
| USA | D | 294.0 | 306.4 | +12.4 |

**Cinque confronti su sei sono peggiori della media storica.** Correggere il target rende il confronto causale sullo stato, ma non aggiunge capacità di prevedere in anticipo la miglior azione.

## 4. Quanto importa davvero la differenza di stato?

La differenza fra etichette on-policy e quelle calcolate dagli stati della baseline non è nulla, soprattutto per le azioni con ritardo (C/D):

| Mercato | Azione | Eventi con differenza osservabile | 95° percentile dello scarto assoluto in logbp |
|---|---|---:|---:|
| Europa | B | 10.1% | 1.7 |
| Europa | C | 33.7% | 45.5 |
| Europa | D | 33.7% | 45.5 |
| USA | B | 7.9% | 0.0 |
| USA | C | 22.5% | 26.3 |
| USA | D | 22.5% | 26.3 |

Gli scostamenti dimostrano che il problema di OLC69 (conti con stati diversi) era concreto. Ma passare da OLC70A a OLC70B produce solo un piccolo cambiamento nel CAGR; il limite dominante è la **debolezza dei segnali disponibili per prevedere il vantaggio relativo**, non un semplice bug di contabilità.

## 5. Audit delle azioni effettivamente scelte

OLC70B usa fallback A fino alla maturazione del training e in altri mesi non convenienti, ma sceglie frequentemente DELAY3 (C/D). I risultati ex-post della decisione rispetto all'alternativa A che parte dallo stesso stato sono registrati a parte. Segue il conteggio delle scelte per mercato su 82 eventi con input pre-signal:

| Mercato | A 50/50 immediato | B MINVAR immediato | C 50/50 DELAY3 | D MINVAR DELAY3 |
|---|---:|---:|---:|---:|
| Europa | 47 | 0 | 7 | 28 |
| USA | 46 | 0 | 23 | 13 |

### Validazioni tecniche

- Hash SHA256 degli archivi originali OLC67 e OLC68 verificati.
- OLC70A: replay A e D bitwise sui sette array nativi OLC19 per entrambi i mercati; **356 rami** da uno snapshot OLC19 (89 mesi × 4) per ciascun mercato, con ogni ramo A coincidente con il segmento originale.
- OLC70B: **356 rami** on-policy per mercato (89 × 4); tutti gli eventi consolidati producono le **sette matrici del replay completo identiche bitwise** alla simulazione giornaliera non spezzata.
- 178 osservazioni mese×mercato per ciascuno dei due insiemi di label; 164 mesi×mercato con quattro feature disponibili; 342 previsioni per ciascuna variante; 40 coppie CAGR/MaxDD ricalcolate indipendentemente con errore numerico massimo <1e−10.
- Date as-of precedenti alle aperture; training t−2; conteggio training e azioni ricostruiti, nessuna label futura come input. L'OLC70B è osservazionale retrospettivo, non un out-of-sample incontaminato.
- Il costo .003 è applicato agli stessi piani decisionali, senza riottimizzarli. Lo storico delle quotazioni di stop è modellistico (OHLC), non broker grade.

## 6. Decisione e prossima ipotesi rigorosa

**OLC70A e OLC70B NON PROMOSSI.** Una simulazione controfattuale rigorosa evita di apprendere differenziali fra stati incompatibili, ma non crea automaticamente informazione sui movimenti futuri. Il risultato USA rimane inferiore alla baseline e nel 2024–2026 non recupera sufficientemente i rally; per migliorare occorre un predittore realmente incrementale del vantaggio dei due ETF, sviluppato e congelato su dati non minati o con una verifica prospettica.

Se in futuro si riapre la ricerca, usare i dati on-policy per valutare separatamente: (i) guadagno da concentrazione sul leader, (ii) costo di perdere le prime due sedute e (iii) probabilità di permanenza della leadership, accompagnati da controlli cronologici e un periodo prospettico. Non creare ora una nuova griglia per ottimizzare 2024/2025/2026.

**Riferimenti originali:** OLC19 FAST_LOCK3; OLC67 MINVAR63+DELAY3; OLC68 prezzi/indicatori pre-signal; OLC69 precedente selettore. Protocolli OLC70A e OLC70B congelati su GitHub (branch `research/olc70-common-state-counterfactual-20261107`).