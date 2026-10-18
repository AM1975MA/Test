# OASIS149 — Decisione del coordinatore e linea di ricerca dopo G0/G1/G2/G3
18 ottobre 2026 | Branch `research/oasis149-canonical-rebuild-20261018`

## SITUAZIONE ESATTA
Il paniere corretto è **original149**, non Top150 né EUR60 né 219. Sorgenti: `evidence_v1/data/original149/universe.csv` e manifest originale con hash dei **149** CSV. 2.366 sedute 2017-02-01 — 2026-07-01, sei macroclassi (25+25+25+25+25+24), 24 osservazioni Volume=0, nessun OHLC invalido fra quelli verificati. È un insieme di ETF USA già esaminato ripetutamente, non un vero universo delistings/PIT e non un'opzione necessariamente negoziabile in EUR. La produzione `etf_trader` non viene modificata.

### G0 qualità — PASS solo per integrità tecnica, NON per investibilità
GitHub Actions `39139072964`. Test quantitativi hash/cronologia e due simulazioni indipendenti. OASIS149 mensile Top2 CAGR +1,10%, MaxDD giornaliero −60,40%; P3 isteresi più crisi +4,77%, MaxDD −63,55%. Pertanto il vecchio OASIS è respinto come portafoglio.

### G1 informazione — FAIL
Cinque modelli cronologici (null, prezzo-momentum, factor residual per classe, interazione con regime, generativo Student-t), 5.120 confronti su 64 date indipendentemente campionate a 21 sedute, label di rendimenti aperto/aperto successivi mai utilizzate prima della maturazione, confronto NEW contro HELD al netto di hurdle convenzionale 30bp:
- H0 NULL Brier .249491, logloss .692147.
- H1 momentum Brier .249523, logloss .692209.
- H2 fattoriale per categoria Brier .249507, logloss .693576, AUC .542.
- H3 gerarchico Brier .254363.
- H4 Student-t Brier .254000.
H2 differenza Brier vs H0 circa −0.000016 (negativa = peggiore), bootstrap CI [−.00736, +.00721], comprende zero. H2 non ha generato **nessuna** proposta di switch che superasse le soglie stabilite. Non confondere AUC marginalmente positiva con probabilità calibrata o alpha.
**VETO** su G1: nessuno dei cinque segnali deve essere promosso all'operatività.

### G2 struttura del capitale — IMPORTANTE MIGLIORAMENTO RETROSPETTIVO, non alpha
Sette strategie con stesso segnale OASIS PRICE, stessi 149 ticker e stesso Open successivo (benchmark Top2 ricostruito con errore massimo 4.4e-16):
- R0 Top2: CAGR 1.10%, daily MaxDD −60.40%, Sharpe .030.
- R1 Top6 qualunque categoria: CAGR 8.52%, MaxDD −39.67%, Sharpe .319.
- **R2 Top1 per ciascuna delle 6 categorie, 1/6 ciascuno: CAGR 7.43%, MaxDD −32.45%, Sharpe .420.**
- R3 Top1 per categoria, inversa volatilità con 25% max ciascuno: CAGR 7.06%, MaxDD −30.16%, Sharpe .481.
- R4 R3 e solo 75% investito: CAGR 5.41%, MaxDD −23.25%, Sharpe .499.
- R5 R3 con Student-t ES dynamic: CAGR 5.89%, MaxDD −29.54%, Sharpe .427; 317 giorni di scambio vs 114 R3: overlay non giustificato.
- R6 Top2 con ES: CAGR 4.16%, MaxDD −34.94%, Sharpe .213; 1.385 giorni di scambio, turnover eccessivo.
Confronto passivo contestuale non cost-matched: SPY buy-hold CAGR 15.25%, MaxDD −32.05%; **60/40 SPY/AGG CAGR 11.39%, MaxDD −23.55%**. Entrambi su quotazioni USD rettificate.
R2 CAGR per epoca: 2017-20 +10.97%; 2021-23 **−0.51%**; 2024-26 +12.02% annualizzato. Il rischio non è stabile nei cambi di regime.
**VETO** su affermazioni di rendimento eccezionale o alpha: solo la riduzione di concentrazione ha forte significato descrittivo.

### G3 rischio specifico / respiro vs crisi — FAIL DI CALIBRAZIONE
Action di G3: `OASIS149_G3_REAL_CRISIS_VS_NORMAL_BREATHING`. 128 previsioni (due portafogli x 64 date mensili), eventi a fine orizzonte: log perdita sotto −8% nei 21 giorni successivi.
R0 Top2: 12 eventi su 64; riferimento maturato Brier .15761, modello gaussiano .14058, Student-t .14450, empirico .15541. Gli algoritmi di rischio non catturano abbastanza eventi con l'allarme soglia 30%: Student-t 0/12.
R2 sei asset class: 4 eventi su 64; riferimento maturato Brier .05947, gaussiano .05914, Student-t .05960, blocchi storici .06072. Con soglia di allerta precongelata P>=30%, nessun modello produce un allarme su queste 4 perdite; gli intervalli bootstrap comprendono zero. Il rischio severo è più raro con diversificazione, ma **nessuno dei rilevatori proposti è sufficientemente calibrato**. Campione di crisi troppo piccolo per apprendere hazard sofisticate dai soli 149 ETF.
Nessuno dei rischi stimati è diventato un segnale di vendita, nessun nuovo backtest del rendimento ha introdotto queste stime.

## IL VERO PROBLEMA
- Non è il numero di layer né la sofisticazione della teoria: dal solo pannello OHLCV non è stato ancora identificato un vantaggio predittivo economico stabile.
- L'errore concettuale iniziale era prendere un ranking debole e aspettarsi che ottimizzazione, isteresi e crisi rendessero forte il suo valore informativo.
- Un filtro di crisi del mercato medio non stima il rischio dei singoli ETF o dell'effettivo portafoglio; ma neppure lo Student-t multivariato prodotto dalle sole code dei prezzi si è dimostrato calibrato.
- Diversificazione per rischio economico class-specific è il miglior contributo misurato: salvaguardia del capitale di ricerca, non una strategia di sovraperformance già risolta.
- La componente probabilistica richiede dati condizionanti ex ante, non altri parametri ritoccati sugli stessi anni.

## Piano concreto per un salto metodologico, ordinato per veto

**P0 / DATA_PROVENANCE.** Identificare tutti i 149 ETF da simbolo e underlying, tipo di replica, azionario/credito/commodity, inception, costi storici, valuta, liquidità effettiva e corporate actions. Ricostruire un universo storico con fondi nati e chiusi durante il periodo; i 149 originali restano un panel diagnostico, non una definizione PIT di mercato investibile. Conservare raw vendor vintage, timestamp di pubblicazione e hash; usare prezzi apertura effettivamente negoziabili e spread conservativi. Per dati macro revisionabili serviranno release vintage (es. storico ALFRED) e verifiche di availability, non dati finale rivisti.

**P1 / FACTOR-SCIENTIST.** Ricercare *informazioni davvero nuove* su eventi macro/di mercato disponibili prima del segnale, per categoria: term structure tassi 2y/10y e curva per bond, spread high-yield e stress creditizio, domanda/offerta commodity e roll yield se disponibili, volatilità implicita/dinamica delle opzioni, liquidità/spread, FX/DXY e relazioni commodity/equity. Non basta scaricare una serie: misurarne lag di pubblicazione, causalità e contributo incrementale alla previsione netta dei sostituti. Valutare prima modelli semplici di confronto rispetto all'incumbent, con shrinkage gerarchico e calibrato Student-t; usare interazioni regimi SOLO quando proper score migliorano il NULL su più epoche. Non riaddestrare pesantemente su 2021–2026 bruciato e rivendicare indipendenza.

**P2 / MICROSTATE-OBSERVER.** Stima causalmente filtrata e separata dello stato di ogni ETF rispetto al suo fattore economico: deriva residua e volatilità condizionata, surprise seriali, rischio di drawdown e hazard di vero cambio, contro naïve EWMA/CUSUM; distinguere shock da normale oscillazione per *calibrazione predittiva* e non ampiezza assoluta del ribasso. Eventi di crisi poco numerosi: modelli fortemente regolarizzati e niente HMM multifattore complessi senza nuove informazioni.

**P3 / PORTFOLIO-RISK.** Considerare sei categorie e cap di esposizione per ETF come parametri di benchmark di rischio, comparandoli a 60/40 SPY-AGG come standard realistico; eliminare allocazioni Top2 ad alta concentrazione. Testare stress con downside covariances, per ETF e di portafoglio, su campioni indipendenti, prima di usarli per tagliare rischio. Overlay Student-t e cash dinamico NON promossi finché non migliora rischio calibrato rispetto a controlli più semplici.

**P4 / IMPULSE-CONTROL.** Solo se P1 passa: no-trade region da posterior `new−held` log-payoff credibile + costi bid/ask/FX reali + durata opportunità + perdite marginali, soglie da tolleranza rischio prefissata e non da tuning ex post. Evitare di vendere su volume mancante o shock non persistente. Dati prezzi futuri non possono entrare nel decision path. Riconoscere rapidamente cadute e riprese SOLTANTO quando esiste una probabilità condizionata realmente migliore del modello nullo.

**P5 / INDEPENDENT-VALIDATOR.** Separate per epoca, veri P&L aperto/aperto, costi bid-ask, real cash EUR, ETF disponibili per data di quotazione, confronti equal-exposure vs 60/40 e paper trading prospective post 2026-07, test multipli corretti. Brier/log score di opportunità e probabilità di tail event devono passare prima di consentire nuove esecuzioni di strategia. In assenza di risultati, dichiarare no-edge e tenere benchmark passivo.

## Squadra per responsabilità
- Coordinatore scientifico con veto su risultati senza PIT, calibrated proper score, drawdown ed esecuzioni.
- Ingegnere dataset as-of e fondi/FX.
- Statistico bayesiano/stati latenti e test calibration.
- Specialista rischio portafoglio, code e ricostruzioni economiche.
- Esperto dinamiche di crisi/riemersione leadership.
- Auditor indipendente di leak, sovraottimizzazione, costosità e placebo passivo.
Queste sono competenze e job deterministici eseguiti/da eseguire, non istanze LLM indipendenti spacciate per collaboratori.

**Decisione:** G0 integrità PASS; G1 informazione FAIL; G2 miglioramento struttura rischio solo storico; G3 capacità allarme FAIL. Nessuna strategia OASIS è stata dimostrata superiore al semplice passivo in rendimento e drawdown insieme sul 149. Documentazione e sorgenti salvati, etf_trader invariato.
