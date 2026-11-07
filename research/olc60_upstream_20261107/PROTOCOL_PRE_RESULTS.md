# OLC60 — Esperimento preliminare nativo a monte (registrazione prima degli esiti)
Data: 2026-11-07. Solo laboratorio. OLC19/main invariati.

Domanda: il training **diretto sulle 42 feature pre-selezione** può distinguere un ETF con leadership economica persistente a 21 e 42 sedute meglio dell'obiettivo esclusivamente a 21 sedute, e meglio della selezione originale del medesimo layer?

Sorgenti immutabili: archivi OLC14 Heads (input annuali originali: X, XP, train_keys, predict_keys, 42 feature) + OLC14 Results (label group-ranked 21/42/63 e score ORIGINAL_CURRENT/ORIGINAL_FUSION). Nessuna nuova fonte o universo, nessun dato di prezzo intraday. Confronto EU/USA separato; 2021-2024 MAIN, 2025 diagnostico; 2026 solo se label disponibili. Periodi storici già iper-esplorati: *non* holdout indipendente.

**Un solo esperimento a due target, stesso modello e preprocessing**: imputazione mediana solo train, StandardScaler train-only, LogisticRegression(L2, C=0.1, solver=lbfgs, max_iter=350, tol=0.001), per mercato/anno fit expanding su righe del checkpoint con exit_date_63 strettamente < 1 gennaio dell'anno. Seed non utilizzato (solutore deterministico), nessun identificativo ticker come input.

- NEAR target: rank relativo del rendimento a 21 sedute >=0.8 (leader a 1 mese).
- PERSIST target: rank relativo >=0.8 **sia** a 21 **sia** a 42 sedute (leader che permane su due orizzonti). Target della persistenza definiti ex post; solo label mature nei fit.
- B0: punteggi originali OLC14 `ORIGINAL_CURRENT`, **prima** dello smoothing/fusione; originale `ORIGINAL_FUSION` solo controllo descrittivo, NON viene cambiato.

Metriche prefissate: su stesse date/ETF e senza label future nel selettore, Top2 hit rate di target NEAR e PERSIST, Top2 media fwd21 e fwd42, frazione rendimenti negativi, selezioni Top2 mese su mese persistenti, probabilità discriminante ROC-AUC e logloss/Brier soltanto per i due modelli con probabilità, Top2 oracle regret ex post (non trading). Ogni mercato e MAIN/LATE separati; 6-month block bootstrap su differenza monthly hit (paired) descrittiva. **Gate**: richiedere progressi contemporanei in EU/USA su target PERSIST, senza perdere significativamente payoff fwd21, per considerare un eventuale replay nativo più avanti; in assenza, non promuovere né ritarare dopo i risultati. Niente CAGR di trading in questo test; l'attuale motore con stop e V6 non è stato modificato.

Controlli: SHA256 dei due ZIP, parità cardinalità e date, convergenza delle stime, cutoff maturità 63 giorni, dati mancanti non convertiti a zero, nessun riordinamento/ranking secondo label futura, serie e KPI integrali congelati. Limiti: total-return/FX, survivorship, raw quote provenance (USA), 2020 calendario, 2025 già studiato.

**Correzione di QA (prima della consegna):** rilevati pareggi esatti nel Top2 OLC14. Tutte le selezioni sono valorizzate con gli stessi pesi frazionari canonici `topk_weights` di OLC14, senza tie-break alfabetico. La modifica non altera alcun modello o parametro e ha la sola finalità di ripristinare l'identità col test originale.