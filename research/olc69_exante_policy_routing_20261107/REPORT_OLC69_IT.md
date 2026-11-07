# OLC69 — Routing adattivo ex ante di allocazione e timing: esito verificato

**7 novembre 2026. RESEARCH ONLY. Nessuna modifica a `main`, OLC19 o trading.**

## Obiettivo e modifica rispetto al precedente 50/50

OLC68 aveva misurato una strategia composta da due sleeve indipendenti, non un riconoscitore di regime. OLC69 testa invece una politica decisionale mensile: per ciascun mercato, un learner expanding addestrato solo su esiti precedenti seleziona **una sola combinazione** di pesi ed esecuzione dentro un singolo motore OLC19 con gestione contabile e stop persistenti. Non è la media fra due curve di NAV né uno stitch mensile di rendimenti.

Quattro azioni: A=HALF/IMMEDIATE (OLC19), B=MINVAR63/IMMEDIATE, C=HALF/DELAY3, D=MINVAR63/DELAY3 (OLC67), tutte con **FAST_LOCK3**. Target di training: differenziale logbp netto rispetto A, ricavato dalle quattro contabilità native congelate di OLC67; **ATTENZIONE: sono differenziali di percorsi con stati di rischio potenzialmente diversi all'inizio di ogni mese, non effetti causali di ciascuna azione da uno stato comune.** Un test decisionale più rigoroso deve clonare lo stesso stato del motore prima di ogni scelta.

Input disponibili alla data del segnale: breadth dei momentum dell'universo a 63 sedute, momentum medio della coppia a 63 sedute, vantaggio momentum del tilt di minima varianza, correlazione trailing 63 sedute della coppia. A ogni segnale per mercato, 3 Ridge indipendenti (alpha=25, StandardScaler fit sul train) stimano B/C/D e la decisione sceglie il massimo tra A=0 e forecast B/C/D, con vantaggio minimo di +5 log-bp per lasciare A. Fit expanding richiede almeno 24 mesi **maturati due eventi prima**; prima usa sempre A. Nessun parametro ritoccato dopo l'esito. Altre regole STOP/V6, costi e universo originari.

## Risultato economico completo — costo legacy 0,001

| Mercato/periodo | OLC19 CAGR | OLC67 CAGR | OLC69 CAGR | OLC69 MaxDD |
|---|---:|---:|---:|---:|
| EU 2021–2024 | 23,20% | **34,43%** | 27,23% | -26,97% |
| USA 2021–2024 | **50,77%** | 51,27% | 46,75% | -20,23% |
| EU FULL Feb2019–lug2026 parziale | 19,76% | **22,61%** | 20,48% | -26,97% |
| USA FULL Feb2019–lug2026 parziale | 39,48% | **42,10%** | 36,36% | -26,12% |

La colonna 2021–2024 non usa i rendimenti annuali aritmetici moltiplicati: è CAGR giornaliero a 252 sessioni secondo l'engine.

### Rendimento aritmetico annuale (costo 0,001)

| Mercato/anno | OLC19 | OLC67 | OLC69 |
|---|---:|---:|---:|
| EU 2024 | 22,44% | 35,17% | 28,15% |
| EU 2025 | 17,95% | 10,15% | 12,72% |
| EU 2026* | 16,51% | 15,28% | 11,84% |
| USA 2024 | 78,61% | 68,88% | 71,63% |
| USA 2025 | 13,57% | 17,83% | 10,59% |
| USA 2026* | 62,44% | 52,06% | 57,12% |

\* 2026 soltanto da gennaio alla prima apertura luglio: NON annualizzato.

### Stress coefficienti di costo fee=0,003

| Mercato/periodo | OLC19 | OLC67 | OLC69 |
|---|---:|---:|---:|
| EU MAIN | 19,88% | 30,72% | 23,69% |
| USA MAIN | 42,73% | 43,60% | 38,87% |
| EU FULL | 16,18% | 18,81% | 16,78% |
| USA FULL | 31,34% | 33,89% | 28,27% |

## Diagnostica di apprendimento: il segnale del routing non generalizza

Il routing ha 57 mesi con fit per mercato e 82 eventi feature disponibili per mercato, ma i controlli OLC19 hanno 90 mesi complessivi per mercato. Tutti i mesi senza train sufficiente ricadono su A. Il modello privilegia A in 54/90 mesi EU e 52/90 USA; sceglie DELAY3 in 31 mesi EU e 38 USA. In USA non sceglie mai B come azione isolata.

| Mercato | Braccio previsto | RMSE del Ridge (log-bp) | RMSE della semplice media *train-only* | Correlazione forecast/realizzato |
|---|---|---:|---:|---:|
| EU | Solo MINVAR | 146,65 | **140,36** | -0,42 |
| EU | Solo DELAY3 | 139,37 | **136,23** | -0,01 |
| EU | MINVAR+DELAY3 | **180,17** | 181,99 | +0,07 |
| USA | Solo MINVAR | 206,61 | **204,13** | -0,04 |
| USA | Solo DELAY3 | 256,17 | **242,96** | -0,27 |
| USA | MINVAR+DELAY3 | 303,19 | **291,04** | -0,20 |

In **5 dei 6** confronti il Ridge è meno accurato di una media storica calcolata sui medesimi soli dati passati. Gli input testati non sono sufficienti a prevedere il vantaggio degli interventi di pesi e timing. In particolare, il modello USA sovrastima spesso il vantaggio del ritardo e perde partecipazione ai rally.

Esempi ex post di abbinamenti previsti male (differenziali log-bp da quattro percorsi originali, **non** causal effect a stato comune): USA 2024-06 la policy combinata D è prevista a +67bp ma realizza −450bp rispetto A; USA 2026-03 prevista a +56bp, realizza −640bp; EU 2025-05 B prevista a +17bp ma realizza −243bp. Nessuna di queste date è un nuovo holdout.

## Cosa non basta, e correzione architetturale proposta (OLC70, non eseguita)

Il 50/50 tra portafogli non è una strategia adattiva. Ma anche la regressione mensile su quattro percorsi autonomi NON è un target corretto per una decisione che modifica lo stato del medesimo portafoglio. Per migliorare davvero occorre creare un **motore di effetti controfattuali d'azione**:

1. Al segnale t, fotografare **uno stesso stato contabile reale del motore**: posizioni, cash, esposizione V6, stop armati, lock/cooldown, target pendenti.
2. Clonare quello stato e simulare A/B/C/D sulle successive 21 sedute con stesse barre, costi, stops; assegnare quattro outcome con il medesimo stato iniziale, distinguendo vantaggio dei pesi, costo del ritardo (prime due sedute) e conseguenze di percorso.
3. Usare input **asset-specifici** di opportunità, non un classificatore universale rialzo/ribasso: differenza dei due forecast ET/Return, variazione della forza relativa dei due ETF, loro trend/dispersione e rischio di perdita di leadership a 21/42 sedute. Questi input devono essere disponibili prima dell'ordine; le predizioni percentile non sono automaticamente rendimenti attesi.
4. Addestrare un modello multi-task regolarizzato a stimare il vantaggio netto **per azione** e la penalità downside. La scelta nasce da utilità attesa e costo di occasione del rally, non dal calendario o dal valore realizzato.
5. Proteggere la ricerca con confronto su tempi davvero nuovi, embargo delle label 21/42, validazione per mercato e audit di causalità. Nessuna ricerca di parametri post-hoc su OLC69.

Questa è una proposta di sviluppo, **non una strategia nuova con CAGR misurato**. Il prossimo passo più utile è rendere il motore OLC19 serializzabile per giorno/clone, con golden-test bitwise sulla baseline prima di addestrare altro.

## Integrità e limiti

- OLC67 source SHA256 dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4; OLC68 feature SHA256 b7911d1346f6d78a19513547fd4b91b8a68a1806b2332f3a95815fcaf2caf330.
- OLC69 motore ADAPTIVE implementato in una copia privata del generatore originale; **parità bitwise su sette matrici OLC19** per EU/USA con lag costante=1 e lag=3.
- Controlli indipendenti: tutti i 164 eventi feature, 342 previsioni con Ridge ricalcolato a matrici numpy, 32 rendimenti annuali e 20 coppie CAGR/MaxDD ricalcolate da giornalieri. Errore max della previsione 1,14e-13 log-bp; QA PASS.
- Le 82 date/mercato per le feature non includono i primi mesi dell'originale. Fallback A fino a 24 osservazioni mature. OLC69 è *in-sample di ricerca* anche quando il fit è cronologico, perché il periodo è stato ripetutamente studiato in OLC01–68.
- Stop/fill legacy su OHLC, universo ETF PIT, USA observed mask, total-return/dividendi/FX e costi reali non verificati. Nessun trading eseguito.

**Decisione:** OLC69 respinto; mantenere OLC19 produzione e OLC67 shadow. Non selezionare una variante sulla base delle anomalie 2024–26; cambiare prima il **target causale del routing** e la qualità informativa delle opportunità.