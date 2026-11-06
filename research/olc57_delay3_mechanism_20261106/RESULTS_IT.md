# OLC57 — Diagnostica del meccanismo DELAY3 (6 novembre 2026)

**Stato: SOLO DIAGNOSTICA / NON PROMUOVERE.** Analisi nuova degli output giornalieri *già congelati* OLC56. Nessun nuovo backtest prezzi, nessun parametro di trading ottimizzato, nessuna nuova conferma OOS. Main, modello OLC19 e OLC56 invariati.

## Scopo, fonte e controllo di riproducibilità

Fonte: archivio originale `/ETF_Research/OLC56_Robust_Timing_20261106/OLC56_TESTS_20261106_VERIFICATI.zip`, SHA256 `f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573`. File: `results/{EU,USA}_TIMING_DAILY.csv` e `results/{EU,USA}_TIMING_MONTHLY_DELTA.csv` dentro `OLC56_ROBUST_20261106/`.

Confronto **soltanto** OLC56 DELAY3 rispetto a IMMEDIATE, costo legacy 0,001. Su ogni giorno di negoziazione calcolo `d_t = logR_DELAY3,t - logR_IMMEDIATE,t`. Per ogni mese distinguo i **primi due giorni di valorizzazione/negoziazione** e il resto; per il periodo MAIN 2021–2024 ricalcolo la somma dei `d_t` omettendo a turno un anno, annualizzando come `100 * sum(d_t) * 12 / n_mesi` in punti percentuali di **log-rendimento annualizzato**, non delta CAGR. È una scomposizione dei risultati già conosciuti, non una simulazione di una nuova policy.

QA: per ciascun mercato, 90 mesi ricostruiti e riconciliati con il CSV mensile congelato. Massimo errore di parità mensile: EU `5,92e-12` log-bp, USA `5,86e-12` log-bp. Il segnale di febbraio 2019 ha entry 1 febbraio ma la prima valorizzazione giornaliera è il 4 febbraio; il delta DELAY3–IMMEDIATE in quel mese è zero.

## Scomposizione delle differenze (somma log-bp, NON CAGR)

| Finestra | Mercato | Prime 2 sedute | Resto mese | Totale |
|---|---|---:|---:|---:|
| MAIN 2021–24 | EU | +900,270 | +689,658 | +1.589,928 |
| MAIN 2021–24 | USA | +3.080,066 | −1.896,785 | +1.183,282 |
| LATE 2025–lug 2026 | EU | −119,234 | +2,499 | −116,735 |
| LATE 2025–lug 2026 | USA | −312,137 | +201,078 | −111,059 |
| EARLY 2019–20 | EU | −35,842 | −16,280 | −52,123 |
| EARLY 2019–20 | USA | +1.213,360 | −314,170 | +899,190 |

Luglio 2026 è **parziale** (fino alla prima apertura); LATE comprende 19 eventi mensili. In USA 2021–24 l'effetto nei primi due giorni è circa il 260% del vantaggio netto: le sedute successive lo riducono fortemente. Europa: il 57% del vantaggio netto nasce nelle prime due sedute.

## MAIN 2021–24: leave-one-calendar-year-out

| Anno escluso | EU: annualized paired log-pp | USA: annualized paired log-pp |
|---|---:|---:|
| 2021 | +4,212 | **−3,707** |
| 2022 | +3,732 | +6,773 |
| 2023 | +3,571 | +5,148 |
| 2024 | +4,384 | +3,620 |

36 mesi restanti per ogni riga e mercato. Anche questi valori sono descrittivi e non test inferenziali indipendenti.

## Interpretazione e prossima verifica

**USA:** il beneficio MAIN del DELAY3 è altamente dipendente dal 2021; senza quell'anno diventa negativo. Il principale contributo positivo è concentrato nelle primissime sedute, per le quali OLC56 non dispone di prezzi reali d'asta, bid/ask/slippage o stop eseguibili certificati. Non considerare questo un miglioramento robusto.

**Europa:** tutte e quattro le esclusioni annuali 2021–24 restano positive, ma OLC56 mostrava che i tre migliori mesi spiegano ~84% del vantaggio e che il 2025 ha deteriorato il risultato. Il campione 2019–luglio2026 è già ampiamente esplorato.

**Decisione:** nessuna promozione; non aggiungere una griglia di giorni di ritardo né una regola condizionata ricavata da questi dati. La prossima verifica prioritaria è l'eseguibilità dei primi due giorni con dati originali di borsa/asta, spread e fill, e test su date realmente nuove dopo il congelamento della policy. Il controllo OLC57 non sostituisce la verifica OLC56 con blocchi bootstrap (intervalli FULL contenenti zero).

Il codice di questa diagnostica è disponibile in questo branch. Il checkpoint OLC56 è documentato nel branch `research/olc56-robust-sizing-delay3-20261106`.