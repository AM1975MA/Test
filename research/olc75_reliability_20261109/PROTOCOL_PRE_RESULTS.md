# OLC75 — affidabilità ex-ante dei Top2 e allocazione controllata

**Protocollo preregistrato 9 novembre 2026, prima dei nuovi outcome OLC75.** Ricerca soltanto. Nessuna modifica a main, OLC19 o OLC67. Il periodo 2019–luglio 2026 è già esplorato; risultati NON sono OOS indipendente. Gli score mensili OLC16 terminano 2026-06-30 e l'ultimo evento è 2026-07-01. Non esistono nella fonte verificata prezzi e segnali agosto–ottobre 2026: nessun holdout simulato.

## Fonte, unità, temporalità
- Originali OLC74 (coppie contestuali e loro rendimenti relativi Open→Open), OLC16 (fitting frame con ORIGINAL_P15_ET/XGB, score Return e ORIGINAL_FUSION), OLC14 risultati (score per seed 101/211/307) e OLC19 (stato contabile, stesso V6+FAST_LOCK3). Hash SHA256 registrati nel QA.
- 90 coppie/eventi per mercato EU/USA, 89 label mensili mature per mercato. Date as-of score prima dell'apertura evento. Target direzione: ETF1 supera ETF2 nel mese successivo, senza usare dati futuri per l'input. Fit mensili cronologici per mercato con target fino a evento t−2 soltanto, almeno 24 eventi maturi; altrimenti fallback 50/50.
- ET e XGB: percentili cross-sectional intra-data dei raw ORIGINAL_P15_ET e ORIGINAL_P15_XGB, combinazione originale 60/40. Tre esperti RETURN/ET/XGB votano la leadership della coppia. H1: unanimità e precisione. H2: dispersione per seed originale CURRENT e concordanza segno. H3: ordine contestuale invertito rispetto a FUSION. H4: differenziale FUSION della stessa coppia un mese prima, se entrambi erano presenti (no riempimento di ticker). Associazioni con vincitore effettivo e stabilità per 2021–24/2024/2025/2026, intervalli descrittivi Wilson e block6 B=4000 seed75009 senza correzione per test precedenti.

## Unico learner prespecificato e controlli
- Logit regolarizzato C=.1, solver lbfgs, max_iter=1000, train-only median imputation + scaling; no ETF ID, anno o target as future feature.
- B0: prequential prior probabilità storica che ETF1 vinca.
- B1 SCOREONLY: logit soltanto sulla differenza FUSION contemporanea.
- B2 RELIABILITY: logit su differenza FUSION, somma voti (−3,−1,+1,+3), flag unanimità, sd tra tre seed di CURRENT (differenza sulla coppia), differenziale FUSION al mese precedente, inversione del ranking contestuale.
- Skill: Brier, log-loss, accuratezza direzionale e calibrazione su mesi MAIN 2021–24, 2024, 2025, 2026 parziale (solo label maturate), oltre alla baseline B0. No hyperparameter search.

## Pesi fissi prima degli esiti
Sempre stessi due ETF selezionati da OLC19, stesse barriere di rischio. Cinque bracci: HALF 50/50; H1_CONSENSUS 65% sull'ETF favorito unanimemente da tutti i tre rami, altrimenti 50/50; SCORE_P w1=.25+.5*p_SCOREONLY; RELIABILITY_P w1=.25+.5*p_RELIABILITY; RELIABILITY_SELECTIVE: w1=50% quando |p_RELIABILITY-.5| <= .10, altrimenti w1=.25+.5*p_RELIABILITY. Fallback 50/50 senza storico sufficiente. Tutti i pesi nell'intervallo 25–75% e computabili al tempo del segnale.
- Replay OLC19 nativo e path-dependent: cinque policy × due timing (IMMEDIATE/DELAY3) × due mercati × due coefficienti di costo legacy (.001/.003) = 40 percorsi. V6+FAST_LOCK3 invariati; nessun editing di stop o FUSION. Metriche CAGR e MaxDD FULL febbraio2019–luglio2026 e MAIN 2021–24, rendimenti 2024,2025,2026 parziale; confronto con benchmark OLC19 e OLC67. QA esatta su sette array per HALF/IMMEDIATE; logreturn parity con OLC73 HALF. Metriche giornaliere verificate indipendentemente.
- Gate per sola candidatura a paper test: RELIABILITY Brier migliore sia del prior sia di SCOREONLY nel MAIN in ENTRAMBI mercati; FULL e MAIN CAGR >= HALF in entrambe, MaxDD FULL non peggiorato di >3 punti e vantaggio non concentrato <=2 mesi. Altrimenti nessuna promozione, anche se il CAGR storico è elevato.

## Ortogonalità e limiti
Cercare nelle fonti disponibili composizione ETF e overlap, settori/fattori, valutazioni e flussi *point-in-time*; valori odierni non possono essere retrodatati. Se assenti per i due mercati, segnare UNAVAILABLE e non simulare l'utilizzo. Nessun dato di bid/ask o prezzo stop eseguito; USA original observation mask mancante, universe survivorship e total return non certificati.