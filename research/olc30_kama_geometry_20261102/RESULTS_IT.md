# OLC30 — Area prezzo/KAMA e pendenza dentro il ranker

2 novembre 2026 — lotto storico esplorativo, **conclusione negativa**. Protocollo preregistrato su GitHub prima degli esiti (commit `b1c25f6e81c4934bb82e1f5be9d1fbf6f682f5b5`). Non è stato modificato `main`; nessun trading. Nessun nuovo fitting dei modelli predittivi ETF originari.

## Ipotesi e definizione

Invece di un filtro KAMA esterno, un secondo ranker ridge annuale usa il punteggio AUTH FUSION e una geometria prezzo–KAMA derivata esclusivamente da Close disponibili prima dell'ingresso:

- `AREA21` = media 21 sedute del log(Prezzo/KAMA), ovvero un integrale discreto **con segno**.
- `SLOPE21` = [log(KAMA_t)−log(KAMA_(t−21))]/21.
- `GAP_SPEED5` = variazione in cinque sedute del log(Prezzo/KAMA), divisa per cinque.

KAMA è KAMA(ER10, fast2, slow30). I quattro modelli messi a confronto sono: controllo `FUSION_ONLY` (senza KAMA), `FUSION_AREA`, `FUSION_SLOPE`, `FUSION_GEOMETRY` (tutte e tre). Tutti usano Ridge(alpha=10), StandardScaler solo sul training e un unico peso 0,80 AUTH + 0,20 percentile della previsione. Il target è il percentile cross-sectional del rendimento del successivo intervallo di esecuzione Open→Open. Tutti i label devono essere maturati **strettamente prima del 1° gennaio** dell'anno di fitting; lo stesso schema e coefficienti sono usati nei mercati EU165 e USA149 senza selezione paese-specifica. Queste soglie sono predefinite, non scelte sui risultati.

## Risultato primario: distanza dal migliore ETF ex post

Distanza finale percentuale logaritmica `100*ln(NAV_strategy/NAV_best)` (più alta è migliore), FAST_LOCK3, fee legacy 0,001, periodo principale 2021–2024. Benchmark scelto **con il senno di poi**: EU QDVE.DE, USA ARGT. Per Europa la data di fine è il 30 dicembre 2024, ultima apertura di QDVE.DE osservata; USA 31 dicembre 2024.

| Ranker | EU vs QDVE.DE | USA vs ARGT | Mesi QDVE Top2 / 48 | Prima segnalazione QDVE (periodo) |
|---|---:|---:|---:|---|
| AUTH OLC20 | -2,90 pp log | +52,68 pp log | 6 | 31 gennaio 2024 |
| FUSION_ONLY | -3,92 | +63,37 | 6 | 31 gennaio 2024 |
| FUSION_AREA | -22,31 | -47,57 | 2 | 29 dicembre 2023 |
| FUSION_SLOPE | -19,90 | -22,30 | 3 | 29 dicembre 2023 |
| FUSION_GEOMETRY | -49,15 | -48,20 | 2 | 29 dicembre 2023 |

**L'area e la pendenza anticipano di un solo segnale l'ingresso iniziale in QDVE, ma non lo mantengono. Il problema europeo NON è risolto; il gap e la performance USA peggiorano significativamente.** Le prime segnalazioni dicembre 2023 corrispondono a investimenti a gennaio 2024; il controllo segnala a fine gennaio con ingresso successivo. Il miglior ticker è un benchmark retrospettivo, non un target usato nel training.

## Persistenza: futuri leader nella top decile a 126 sedute

Stesso insieme di segnali con quotazioni future valide, 46 in EU (92 selezioni Top2) e 48 negli USA (96 selezioni); percentuali puramente diagnostiche, non feature d'inferenza.

| Variante | EU top-decile futuri | USA top-decile futuri |
|---|---:|---:|
| AUTH | 29,35% | 28,13% |
| FUSION_ONLY | 27,17% | 29,17% |
| FUSION_AREA | 28,26% | 28,13% |
| FUSION_SLOPE | 21,74% | 31,25% |
| FUSION_GEOMETRY | 27,17% | 30,21% |

Per EU, nessun candidato migliora il tasso di leader futuri. Il piccolo aumento USA di alcuni candidati a 126 sedute **non** si converte in miglior valore del portafoglio sul mese effettivo: esito coerente con i negativi OLC26–27.

## Rischio e costi (guardrail, non il criterio primario)

CAGR %, periodo 2021–2024, FAST_LOCK3, fee legacy 0,001:

| Ranker | EU CAGR | USA CAGR | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|
| AUTH | 23,20 | 50,77 | -28,61 | -20,23 |
| FUSION_ONLY | 22,89 | 54,87 | -28,61 | -20,23 |
| FUSION_AREA | 17,46 | 17,26 | -26,87 | -34,26 |
| FUSION_SLOPE | 18,16 | 24,93 | -26,97 | -24,56 |
| FUSION_GEOMETRY | 9,97 | 17,16 | -33,49 | -27,06 |

Con commissione legacy 0,003, i CAGR EU/USA sono AUTH 19,88/42,73; AREA 14,39/9,70; SLOPE 14,90/16,98; GEOMETRY 7,13/10,62%. Il costo non spiega il fallimento. La convenzione di fee legacy non è automaticamente un costo per lato.

## Diagnosi del fallimento

La geometria aggiunta aumenta in alcuni mesi la posizione di QDVE (nel 2023 la posizione mediana scende numericamente da 27 a 20,5 con GEOMETRY), ma nel 2024 peggiora la posizione mediana da 2,5 a 7. L'area e la pendenza, singolarmente, peggiorano anche il rank mediano 2024 (circa 7 e 6,5). Questo spiega la minore **permanenza** nel Top2 nonostante l'anticipo iniziale.

Tra il 2021 e il 2024 il coefficiente standardizzato della pendenza KAMA nel modello a due feature è sempre negativo (2021 -0,0149; 2022 -0,0061; 2023 -0,0054; 2024 -0,0043). Il modello addestrato sul prossimo mese tende a trattare la pendenza recente come segnale di esaurimento; non dimostra che una pendenza positiva sia universalmente sfavorevole, ma aiuta a spiegare perché il modello non mantiene i leader di lungo termine. La geometria completa è soggetta anche a collinearità area/pendenza/velocità.

## Verifiche

- 24 fit annuali complessivi (quattro ricette × 2021–2026) senza re-training dei predittori ETF originali.
- 32 nuovi conti economici (quattro ranker × due mercati × ALARM/FAST_LOCK3 × fee 0,001/0,003) e 8 AUTH già autenticati.
- Stesso supporto di training delle quattro ricette; maturity strictly before 1 gennaio verificata per tutti gli anni. Al 2021 il training include 4.916 osservazioni, ultima maturazione 1 dicembre 2020; al 2026 21.709 osservazioni, ultima maturazione 1 dicembre 2025.
- KAMA calcolata solo da Close prima/durante il segnale; in EU richieste maschere `observed`, negli USA maschera originale assente, si usano Close preparati finiti e positivi.
- V6 ricalcolata per ciascun Top2 senza duplicare titoli; il motore `validate_book` ha verificato tutti i conti. Ricostruzione di NAV dai rendimenti di intervallo su 40 account, confronto con NAV salvato per FAST_LOCK3/fee0,001.
- Eventi di stop e costi conservati nella contabilità. Il 2019–2020 è identico ad AUTH nel ranker perché gli annual fit partono dal 2021: non è un test di recupero della leadership QDVE nel 2020.

## Decisione

**NON integrare automaticamente `AREA21`, `SLOPE21` o `GAP_SPEED5` nel ranker investibile con questa ricetta.** L'informazione è causalmente utilizzabile, ma non ha dimostrato di saper correggere la perdita dei leader. Un test successivo, se giustificato, dovrebbe distinguere un target di selezione *mensile* dal valore di **permanenza a più mesi**, preservando però il rendimento del mese e usando un nuovo periodo veramente prospettico.

Limiti generali: 2019–2026 riutilizzato in molte esplorazioni, selection/survivorship bias del miglior ETF visto ex post, incompletezza original USA observed masks, dati total-return, FX e fill intraday non certificati. I risultati sono evidenza storica descrittiva, non alpha prospettico.
