# OLC74 — Gestione causale delle esposizioni tra i due ETF: audit e replay nativi

**8 novembre 2026 · Ricerca retrospettiva, nessuna promozione in produzione.** Il periodo febbraio 2019–prima apertura luglio 2026 e' gia' stato esplorato in OLC01–73; OLC74 NON costituisce una nuova validazione indipendente dell'alpha.

## Decisione in sintesi

**Fra le policy testate, nessuna allocazione dinamica supera i controlli prestabiliti in Europa e negli USA.** La differenza di score `ORIGINAL_FUSION` e' l'indicatore semplice piu' interessante negli USA, ma penalizza l'Europa e il suo beneficio americano sull'intera finestra non e' robusto al ricampionamento a blocchi. I tre modelli di previsione diretta (OLC74A, OLC74B, OLC74C) NON superano i rispettivi predittori banali nel 2021–24. Anche 45 coppie Top10/mese aggiungono informazione sui ticker, ma non decine di regimi indipendenti per mese.

**Causalita' verificata e suo limite:** il vantaggio della concentrazione in un ETF si puo' calcolare con interventi diversi **da identico stato contabile** nel motore OLC19 (stesse posizioni, free cash, V6, stop/lock, OHLC esogeni). L'effetto `do(w1=.75)` meno `do(w1=.25)` e' causalmente identificato *nel simulatore a prezzi fissi*. La correlazione di questo effetto con score/indicatori storici non e' causalita' economica ne' dimostra profittabilita' futura.

## 1. Contratto e disegno preregistrato

GitHub research branch: `research/olc74-top2-exante-allocation-20261108`. I tre protocolli sono stati congelati **prima dei rispettivi risultati**: OLC74A originale, OLC74B dopo la prima diagnostica negativa, OLC74C dopo A/B. Per B/C non viene falsamente dichiarata un'indipendenza della scelta dell'esperimento. Nessun post-outcome tuning.

- **Scelta ETF invariata:** originali FUSION → TOP2_CONTEXT_REVALUE, 90 segnali mensili EU e USA, V6, FAST_LOCK3, stop friction 0,001.
- **Informazione utilizzata:** punteggi RETURN, ORIGINAL_SMOOTH, ORIGINAL_FUSION, momentum 21 e 63 sedute, volatilita' relativa 63 e correlazione fra i due ETF, calcolati usando esclusivamente Close precedenti all'apertura dell'evento. Due mesi di maturazione minima delle label prima dell'addestramento.
- **A:** Ridge e LogisticRegression con sei caratteristiche; i target prevedono rendimenti OPEN-next-month relativi. Politiche di controllo: 50/50, MINVAR63, tilt su differenza FUSION, tilt su differenza RETURN, Ridge, Logit e MINVAR più Ridge.
- **B:** tutte le 45 coppie possibili del Top10 originale al mese, training simmetrico (`ETF1↔ETF2` → segno predizione invertito), pesi per gruppo mensile; Ridge e Logit, nessuna identita' ticker.
- **C:** tre interventi `.25/.50/.75` sul primo ETF da stesso stato completo on-policy; 89 episodi maturi per mercato, tre rami controfattuali ognuno, training Ridge sulle loro differenze effettive nel mese t solo da t−2. Unico portafoglio reale simulato con stato persistente.
- **Replay:** 56 A +16 B +4 C = **76 percorsi completi**, con commissioni simulate coefficienti legacy .001 e .003; prequential e regole di stop originali. Le commissioni non equivalgono a prezzi bid/ask verificati.

## 2. Evidenza: correlazioni ex ante con il vincitore della coppia

La grandezza obiettivo e' `log(Open1_next/Open1_now) - log(Open2_next/Open2_now)`, dopo la scelta della coppia originale. Coefficiente Spearman su **2021–2024**:

| Feature ante-segnale | EU | USA |
|---|---:|---:|
| d_return | -0.039 (n=48) | -0.060 (n=48) |
| d_hybrid_smooth | +0.129 (n=48) | +0.044 (n=48) |
| d_fusion | +0.148 (n=48) | +0.036 (n=48) |
| d_mom21 | -0.230 (n=43) | -0.128 (n=48) |
| d_mom63 | -0.030 (n=38) | +0.026 (n=48) |
| d_log_vol63 | -0.441 (n=38) | +0.046 (n=48) |
| corr63 | +0.042 (n=38) | +0.126 (n=48) |

**Interpretazione:** il differenziale FUSION ha associazione debole con la vittoria relativa, e negli USA e' quasi nullo sulla semplice differenza di rendimento mensile. La volatilita' relativa e' piu' associata in Europa, ma con soli 38 mesi maturi e NON si replica negli USA. Queste sono associazioni condizionate alla selezione delle coppie Top2, non evidenze causali indipendenti; i sette confronti e decine di ricerche precedenti impongono cautela statistica.

### Chi vince: primo o secondo ETF?

| Mercato | Anno | Mesi vinti dal primo ETF | Spread medio mensile primo−secondo |
|---|---|---:|---:|
| EU | 2024 | 4/12 | -0.80% |
| EU | 2025 | 5/12 | +0.06% |
| EU | 2026 | 4/6 | +2.30% |
| USA | 2024 | 10/12 | +6.13% |
| USA | 2025 | 6/12 | -3.99% |
| USA | 2026 | 2/6 | -5.31% |

Il regime di efficacia relativa cambia: nel 2024 il primo ETF vince spesso negli USA, nel 2025/2026 il vantaggio si ribalta. Un classificatore di regime deve anticipare tali inversioni, non scegliere retrospettivamente i pesi vincenti.

## 3. Skill prequential: modelli complessi contro semplici controlli

| Mercato | OLC74A Ridge MSE vs mean-only | OLC74A Logit Brier vs frequenza storica | OLC74B Top10 Ridge MSE vs predizione nulla | OLC74C eff. causale Ridge vs mean-only, bp² |
|---|---:|---:|---:|---:|
| EU | 0.00556 / 0.00469 | 0.274 / 0.256 | 0.00489 / 0.00462 | 126,474 / 108,215 |
| USA | 0.01555 / 0.01386 | 0.254 / 0.242 | 0.01494 / 0.01437 | 174,053 / 161,134 |

I benchmark B sono volutamente semplici (previsione zero/0,5) mentre A/C usano la rispettiva media delle etichette storiche; i valori MSE per prezzi sono in **log-return²** e quelli C in **bp²**, non vanno confrontati direttamente. **Tutti i nostri nuovi learner incrementali hanno errore maggiore dei controlli MAIN nei due mercati**, anche con training sulle altre coppie del Top10. Il target C e' stato misurato sotto il percorso proprio effettivo, non sullo stato diverso di un'altra strategia.

## 4. Performance del motore OLC19 su periodi perfettamente comparabili

Tutte le righe sono con **IMMEDIATE, FAST_LOCK3 e fee 0,001**; differenti soltanto nei pesi fra gli stessi due ETF (nessuna modifica FUSION o stop). Il periodo principale MAIN e' 2021–2024; FULL febbraio 2019–luglio 2026 parziale. **CAGR e MaxDD**:

| Policy peso primo ETF | EU MAIN | USA MAIN | EU FULL | USA FULL | EU FULL MaxDD | USA FULL MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| HALF | +23,20% | +50,77% | +19,76% | +39,48% | -28,61% | -26,12% |
| MINVAR63 | +29,31% | +47,73% | +20,84% | +38,98% | -23,76% | -25,23% |
| FUSION_CONF | +22,93% | +56,04% | +18,97% | +41,18% | -28,27% | -25,96% |
| RETURN_CONF | +22,76% | +49,24% | +19,21% | +38,06% | -28,27% | -27,20% |
| PAIR_RIDGE | +22,78% | +51,73% | +19,39% | +38,54% | -29,63% | -26,12% |
| PAIR_LOGIT | +22,05% | +50,25% | +19,25% | +38,68% | -29,23% | -26,12% |
| RISK_PLUS_RIDGE | +27,26% | +47,81% | +19,83% | +38,20% | -24,12% | -25,23% |
| TOP10_RIDGE | +22,90% | +50,18% | +19,79% | +39,49% | -28,92% | -26,12% |
| TOP10_LOGIT | +22,96% | +50,62% | +19,78% | +39,25% | -28,83% | -26,12% |
| OLC74C_ONPOLICY | +22,93% | +53,07% | +19,62% | +39,00% | -29,93% | -26,12% |

Le varianti A/B sono state testate anche con DELAY3 e fee 0,003. Il punto di partenza OLC67 (MINVAR63+DELAY3) mantiene EU MAIN 34,43%, USA MAIN 51,27%, EU FULL 22,61%, USA FULL 42,10%. Anche qui la relazione fra segnale e premio relativo non migliora automaticamente spostando la data di esecuzione.

### FOCUS 2024–2026, CAGR non applicabile ai singoli anni parziali

| Mercato | Anno | HALF | MINVAR63 | FUSION_CONF | OLC74C on-policy |
|---|---:|---:|---:|---:|---:|
| EU | 2024 | +22,44% | +29,22% | +19,92% | +23,10% |
| EU | 2025 | +17,95% | +14,33% | +17,93% | +18,76% |
| EU | 2026* | +16,51% | +13,16% | +17,78% | +15,73% |
| USA | 2024 | +78,61% | +73,03% | +93,10% | +89,48% |
| USA | 2025 | +13,57% | +15,32% | +10,32% | +5,54% |
| USA | 2026* | +62,44% | +60,00% | +57,41% | +60,42% |

*2026 include soltanto il periodo disponibile sino all'apertura di luglio; ritorno cumulato NON annualizzato.*

Negli USA la policy FUSION_CONF ha un MaxDD completo marginalmente inferiore alla baseline (−25,96% contro −26,12%), ma il beneficio di rendimento del 2024 viene ridotto dal 2025–2026. Confronti diretti con OLC73 TOP1_75 evidenziano un CAGR USA MAIN 65,46% e FULL 44,43%, ma con MaxDD FULL −27,66% e un 2025 gravemente sfavorevole: **non e' una validazione di un peso fisso 75/25**.

## 5. Incertezza e stabilita' temporale della FUSION_CONF USA

Intervalli bootstrap descrittivi a blocchi *circolari di sei mesi*, 4.000 ricampionamenti, di **delta log rendimento annualizzato** versus HALF; NON differenze aritmetiche di CAGR e NON corretti per tutti i numerosi tentativi OLC.

| Mercato | Periodo | Delta log annuo | IC95% descrittivo | Mesi favorevoli |
|---|---|---:|---:|---:|
| EU | MAIN | -0.22 pp | [-1.76; +1.24] pp | 23/48 |
| EU | FULL | -0.67 pp | [-1.78; +0.46] pp | 39/90 |
| USA | MAIN | +3.43 pp | [+1.14; +6.36] pp | 28/48 |
| USA | FULL | +1.20 pp | [-0.83; +3.44] pp | 50/90 |

Per USA, sull'intera finestra l'intervallo comprende zero. I mesi USA più importanti a favore della FUSION_CONF comprendono maggio e ottobre 2024; i piu' sfavorevoli giugno 2025 e giugno 2026. Questa discontinuita' e' un rischio economico non risolto.

## 6. Interventi on-policy da stato identico: cosa insegna OLC74C

Per ogni evento fino al successivo, dall'identico stato OLC19 sono stati simulati 25/50/75 sul primo ETF; la policy apprende solo il differenziale 75−25 **gia' maturato da due eventi precedenti**. Parita' bitwise di tutte e sette le matrici fra portafoglio ottenuto per segmenti e singolo replay integrale (entrambi i mercati). Nessun dato futuro controlla il peso del mese corrente.

| Mercato | Correlazione effetto causale simulato e semplice spread prezzi | Mesi con diverso numero di stop fra pesi25/75 | Premio mensile medio 75−25 |
|---|---:|---:|---:|
| EU | 0.929 | 0/89 | -39.7 bp |
| USA | 0.865 | 0/89 | +67.1 bp |

L'alto accordo con lo spread dei prezzi conferma che l'assetto contabile non e' il principale *ostacolo alla misurazione* del vantaggio della concentrazione. Ma il target corretto e' ancora difficile da prevedere: nello schema on-policy il Ridge e' peggiore di una media storica e non batte il 50/50 nel FULL in entrambi i mercati.

Nota: un numero di stop invariato non dimostra assenza di effetti economici degli stop; dimensione delle posizioni, fees, slippage convenzionale e capitalizzazione cambiano. Lo stato del modello conserva tali effetti.

## 7. Decisione causale e prossimi dati da acquisire

**Non promuovere una nuova allocazione dinamica in produzione.** Le condizioni fissate prima dei risultati richiedevano skill predittiva MAIN, miglioramento di CAGR MAIN/FULL in entrambi i mercati e MaxDD non peggiorato oltre 3pp. Nessuna policy nuova ha superato tutti i gate. Il modello OLC19 50/50 e' il benchmark conservativo; OLC67 resta la candidata research europea/USA gia' nota. Il tilt FUSION_CONF e' un'ipotesi americana per **paper testing**, non un metodo comprovato comune.

La spiegazione piu' concreta e' che stiamo condizionando su due ETF gia' selezionati come molto promettenti: la loro **differenza futura** e' molto piu' rumorosa del vantaggio comune sul resto dell'universo. Le 125 feature Return e i rami Hybrid che sono sufficienti per la selezione non contengono, nei test finora, un segnale abbastanza affidabile per dimensionare i Top2 ogni mese. Le grandi differenze retrospettive 75/25 ↔ 25/75 sono un *opportunity ceiling*, non una previsione disponibile.

Per migliorare davvero, prima di ritentare la stima del peso, serve verificare informazioni **ortogonali e point-in-time** che possano anticipare differenze economiche fra i due ETF: composizione e overlap effettivi, flussi/ownership, premi settoriali e valutazioni, curva volatilita' implicita e liquidita' negoziabile, purché disponibili storicamente senza revisione retrospettiva. Tutto va validato prima sul segno del rendimento relativo e sull'errore di previsione rispetto alla media, con un vero periodo prospettico non esplorato. Non si possono rivendicare nuovi CAGR live usando pochi mesi gia' studiati.

## 8. QA / riproducibilita'

- OLC74A: 56 replay; OLC74B: 16 replay; OLC74C: 4 replay, totale **76**. Controlli indipendenti: 648+36=684 CAGR/MaxDD, 576+32=608 rendimenti annuali. Parita' esatta OLC19 originale 7 array per entrambi i mercati, OLC73 per HALF/MINVAR63 e replay a stato comune OLC74C bitwise.
- OLC74A/B source scoring OLC16 originale: SHA `ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7`; OLC19 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`; OLC73 `af6fe36e5a2d6f2ea202d48800316ecbae5872c7ca89caf10bd343b1bf9899c6`.
- I 90 eventi per mercato e i ticker contestuali sono identici ai checkpoint. Tutti i Top2 effettivi appartengono al Top10 storico, selezionato senza conoscere il futuro.
- Label training event−2 e input ultimo Close precedenti verificati. Europa usa la maschera originale `observed`; per USA questa maschera non e' disponibile nella copia nativa e la validita' USA e' quindi limitata all'OHLC fornito.
- Mancano prezzi reali di stop/fill, original observation mask USA, universe point-in-time completo, adjusted total return e un nuovo holdout autonomo; la significativita' economica del CAGR puo' cambiare.

Per replicare gli output, vedere `README.md`, i tre protocolli pre-results, `run_olc74.py`, `run_olc74b.py`, `run_olc74c.py` e i verificatori indipendenti. Non sono necessari nuovi download di quotazioni se i checkpoint originali OLC19/OLC73/OLC16 della Library sono disponibili.