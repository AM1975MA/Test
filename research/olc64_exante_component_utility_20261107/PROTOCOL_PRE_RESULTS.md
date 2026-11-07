# OLC64 — L'affidabilità marginale dei componenti è prevedibile *prima* del segnale?

**7 novembre 2026. Preregistrazione diagnostica PRIMA di calcolare le relazioni OLC64.** Nessun learner aggiuntivo, nessun cambio di componenti/pesi/threshold e nessun replay del portafoglio. Tutte le date 2019–2026 sono già state ampiamente analizzate: le risultanze sono solo ipotesi esplorative, non un holdout indipendente.

## Fonte congelata
Utilizzare esclusivamente i risultati mensili OLC63 verificati, con 16 configurazioni fattoriali originali per evento/mercato, più le correlazioni fra punteggi *note al momento del segnale*:
- `OLC63_MONTHLY_FACTORIAL.csv`, SHA256 `f6cf047b543904e425f46b0b8c3c4aac13f81b0aea9040f4fb57f4df93759916`;
- `OLC63_MONTHLY_CORRELATIONS.csv` (ex ante, deriva dai ranking originali congelati);
- `OLC63_MONTHLY_SHAPLEY.csv`, SHA256 `72bb4b75319100428d33acd6a331ecddb45e695caf06270d4281728016619672`, solo per controlli di identità, non per addestramento.

Stessa maschera di date OLC63: EU MAIN 48, USA MAIN 48; EU LATE 10 mesi di 2025 per etichette future mancanti, USA LATE 12. Nessun cambio di supporto per ottenere un risultato più conveniente. Eventuali assenze sono esplicite. Rendimento futuro solo come outcome per diagnostica; non per costruire predittori.

## Due ipotesi fisse, senza ricerca di soglie

**H1: discordanza RETURN vs CURRENT**. Per data/mercato `D_R = 1 − Spearman_rank(RETURN, ORIGINAL_CURRENT)`, calcolato all'ingresso. Target `Y_R = [V(REXM)−V(EXM)] − [V(REXM)−V(RXM)] = V(RXM)−V(EXM)` dove `V` è il rendimento statico futuro Top2. Questo è il differenziale *di utilità marginale* di RETURN rispetto a ET, condizionato agli altri componenti; non è un target di ranking dei singoli ETF. Su 16 maschere `V(RXM)=V(13)`, `V(EXM)=V(14)`.

**H2: discordanza ET vs XGB**. `D_X = 1 − Spearman_rank(ER,XR)`; target `Y_X = V(REXM) − V(REM) = V(15)−V(11)`, utilità marginale di XGB quando altri componenti sono presenti.

Calcolare H1/H2 con rendimenti a 21 e 42 sedute **senza cercare altro**; risposta primaria 21 sedute, 42 solo verifica di orizzonte. Per ciascuno EU e USA:
- Spearman fra D e Y sui 48 mesi MAIN; per coerenza anche Pearson descrittivo.
- CI95% descrittivo con ricampionamento circolare a blocchi di 6 mesi, `B=3000`, seme `64001`; nessuna correzione famiglia, intervalli non inferenziali validati.
- verifica dell'effetto per i quattro anni MAIN e 2025 LATE come diagnostica solo; *nessuna selezione di anno o mercato favorevole*.
- controllo tabelle originali: 16 maschere per mese, nessun training, predittori uguali qualunque sia il futuro, stessa granularità e ordinamento date.

**Gate di passaggio**: solo una relazione con stessa direzione su EU/USA, segnali coerenti nel 2024 e 2025, e CI95% descrittivo che non includa zero può motivare una futura registrazione di un piccolo meta-learner su dati futuri. In mancanza di tali requisiti, **NO GATE, NO PROMOTION**. Il controllo è associativo e non definisce una policy trading. Senza un holdout vergine, anche un gate superato non sarebbe evidenza sufficiente per produzione.