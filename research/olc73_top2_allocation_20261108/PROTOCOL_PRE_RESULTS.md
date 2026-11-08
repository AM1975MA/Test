# OLC73 — Solo allocazione Top2, motore nativo OLC19 (PRE-RESULTS)
Registrato **8 novembre 2026 prima dei nuovi outcome OLC73**. Ricerca retrospettiva, nessun nuovo OOS vergine per il 2019–2026. Non modificare OLC19, OLC67 né il branch main.

## Obiettivo e leve congelate
Misurare se, a **parità degli stessi due ETF TOP2_CONTEXT_REVALUE di OLC19 e senza modifiche agli score, alla fusione e ai segnali**, la diversa ripartizione del capitale aumenta la partecipazione ai rally senza aggravare le perdite. Tutti i candidati usano lo stesso gross exposure V6/OLC19, stessa regola stop FAST_LOCK3, stessa contabilità, stesso evento e gli stessi prezzi OHLC. **Nessuna scelta di pesi ex post in singoli anni**.

## 8 regole fisse (peso del primo ETF nei dati nativi d1/d2)
A HALF = 50%; B TOP1_65 =65%; C TOP1_75 =75%; D TOP2_65 =35%; E TOP2_75 =25%; F INVVOL63_CAP25: peso inversamente proporzionale alla volatilità 63 sedute, limitato [0.25,0.75]; G MOM63_65: 65% sull'ETF con momentum a 63 sedute maggiore, 35% sull'altro (tie/fallback 50%); H MINVAR63_CAP25: stesse ponderazioni congelate OLC56 con cap25/75. Nessuna variazione di queste fra EU e USA. Per F/G, solo dati **pre-signal**: ultime 64 Close precedenti l'apertura evento, 63 rendimenti log, 64 observed flags, nessun dato futuro; per G si confronta log(C_last/C_first). Fallback 0.5 se copertura insufficiente/non validi; zero cost/turnover se nessun nuovo evento. Per H prior OLC56 frozen, check keys/monthly dates.
Il primo ETF d1 **non è necessariamente** il più forte secondo un singolo ramo; rappresenta il primo della coppia contestuale nativa.

## Incrocio prefissato con timing, non grid di ottimizzazione
Eseguire le stesse 8 allocazioni con **IMMEDIATE** e **DELAY3** nativo, rischio FAST_LOCK3 e fee=.001 primaria, fee=.003 stress; 8 × 2 timing × 2 mercati × 2 costi=64 replay completi. Raffronti nativi parity A immediate (OLC19) e A delay3/H immediate/H delay3 (OLC56/67). Evitare di riusare questi stessi anni come conferma statistica di un vincitore. Non cercare nuovi cap, tempi o finestre dopo i risultati.

## Misure preregistrate
MAIN 2021–2024, FULL feb2019–prima apertura luglio2026, singoli 2024/2025/2026 parziale, 2020 stress, 2021–2023; CAGR annualizzato con 252 giorni di valorizzazione, MaxDD, rendimenti anno solare, turnover/costi quando ricostruibili. Analisi di attribuzione: vantaggio di B..H rispetto A a parità timing; confronti con OLC67 H+DELAY3. Blocchi descrittivi bootstrap paired 6-month circular, seed 73008, 4000 repliche sui rendimenti giornalieri aggregati per mesi; NO p-value certificazione su dati già mined. Non dichiarare un CAGR di combinazioni non simulate.
Criterio per candidatura **paper-only**: FULL CAGR migliorato rispetto A in **entrambi** EU/USA, MAIN non peggiorato in nessuno, FULL MaxDD non deteriorato di oltre 3pp in nessuno, e risultato non concentrato esclusivamente in uno/due mesi. Registrare anche se una policy eccelle soltanto in un mercato, senza concludere che possa essere selezionata con dati ex post.

## Controlli
SHA256 OLC19 3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540, OLC56 f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573. Richiesta parità 7 array OLC19 A+IMMEDIATE fee=.001; controllo A DELAY3 e H IMMEDIATE+FAST_LOCK3 vs OLC56; H DELAY3 vs OLC67. Validate on-date market events exactly 90 per market, only contemporaneously observed trailing prices; 64 replay and independent recomputation of cagr+maxDD from daily logs. Salvataggio di codice, QA e annual.
