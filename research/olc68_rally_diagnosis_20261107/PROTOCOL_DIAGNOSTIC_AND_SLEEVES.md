# OLC68 — Diagnosi del sacrificio dei rally (2024, 2025, 2026) e controllo di diversificazione delle policy

**Data 7 novembre 2026 — ESPLORATIVO.** La ricerca originaria OLC01–67 ha già esaminato ripetutamente 2019–luglio 2026: nessun risultato ha valore di holdout non contaminato. Per il test di diversificazione sottostante, il contratto è fissato PRIMA di calcolarne il risultato, ma dopo aver visto i risultati delle singole policy. OLC19 operativo e branch main restano invariati.

## Origine
Richiede gli output immutati OLC67 `OLC67_DAILY_LOGRET.csv.gz`, `OLC67_ANNUAL.csv`, `OLC67_SCORECARD.csv`, checkpoint originali OLC19/OLC56 per eventuali replay rischio. Fonti sottoposte a hash.

## Diagnosi
1. Per ciascun mercato e anno (focus 2024, 2025 e 2026 sino alla prima apertura luglio), decompone la differenza additiva di log-return fra MINVAR63+DELAY3+FAST_LOCK3 e HALF+IMMEDIATE+FAST_LOCK3 in: solo pesi, solo ritardo, interazione. Nessuna attribuzione causale additiva in aritmetica.
2. Reconcilia a livello quotidiano i log-return originali e riesegue quattro percorsi OLC19 per mercato; verifica esposizione effettiva, stop e giorni di lock. Calendario e stop-fill sono quelli del motore legacy, non eseguiti di broker.
3. Divide ex post le giornate fra OLC19 positivo e non positivo per descrivere la partecipazione ai rally. **Questa divisione NON è utilizzabile come filtro di trading**, poiché usa la performance del mese/giorno già avvenuta.
4. Confronta alcuni attributi antecedenti al segnale: breadth ETF sopra momentum 63 sedute, momentum coppia, distanza e direzione del tilt minvar; usa solo Close osservati fino al giorno prima dell'ingresso; seleziona ultimo giorno di mercato comune con >=80% copertura e 63/126 sedute comuni precedenti. Le associazioni di Spearman sono diagnostiche, non soglie ottimizzate, con denominatori non fittizi.

## Contratto di un UNICO nuovo benchmark di mitigazione, fissato prima dell'esito
**OLC68_TWO_SLEEVES_50_50_BUY_HOLD**: iniziare alla prima data di valorizzazione comune del 2019 con 50% del capitale in una sottostrategia indipendente OLC19 HALF+IMMEDIATE+FAST_LOCK3, e 50% in una sottostrategia OLC67 MINVAR63+DELAY3+FAST_LOCK3. I due engine conservano tutti i rispettivi giorni/stop/rientri e costi fee=.001/stop friction=.001 nativi. Nessun ribilanciamento successivo dei due sleeve, nessuna selezione di mesi e nessuna regola di rally. NAV aggregato self-financing `NAV_t=.5*NAV_OLC19,t+.5*NAV_OLC67,t`, NAV delle due policy ottenuto da `exp(cumsum(logR))`; usare lo stesso arco temporale e riportare CAGR annualizzato 252 sedute, MaxDD, rendimenti annuali. Separare 2019–lug2026 e MAIN 2021–2024. Confronto fee=.003 con identica regola di capitale solo se utile dopo la verifica.
**Caveat fondamentale:** il doppio conto è matematicamente esatto soltanto sotto assunzioni di operatività indipendente e costi proportional scaling; non include netting delle posizioni sovrapposte, costi minimi o spread addizionali. Nessun ribilanciamento tra sleeve significa che l'allocazione effettiva cambia col rendimento. Questo non è lo switch di regime chiesto in prospettiva e non massimizza retrospettivamente CAGR.

## Controlli
- SHA-256 origine; parità anno per anno degli array rispetto a OLC67 annuo, differenza quotidiana scomposta in peso+timing+interazione entro 1e-12.
- Il NAV misto deve restare esattamente fra i NAV dei singoli a ogni data e la sua resa quotidiana deve ricostruire CAGR/MaxDD.
- Nessun claim di capacità predittiva regime senza effettiva convalida su nuove date. No modifica OLC19.
