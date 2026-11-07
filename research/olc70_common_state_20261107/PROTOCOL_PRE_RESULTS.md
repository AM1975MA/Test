# OLC70 — Controfattuali allo stesso stato, previsione economica e backtest nativo

**Data: 7 novembre 2026. Protocollo congelato PRIMA di osservare gli esiti OLC70.**
RESEARCH ONLY; nessun cambiamento a main, OLC19 o esecuzione reale. Lo storico 2019–2026 è stato ripetutamente esplorato: non esiste un holdout vergine e OLC70 non può validare alpha fuori campione.

## Ipotesi e necessaria correzione rispetto a OLC69
I target OLC69 erano differenziali di *portafogli indipendenti*, con holdings/stop-lock/cash differenti. OLC70 valuta nello stesso evento ciascuna scelta da **identico stato contabile pre-trade**. Quattro rami A = HALF+IMMEDIATE, B = MINVAR63+IMMEDIATE, C = HALF+DELAY3, D = MINVAR63+DELAY3. FAST_LOCK3 e V6 invariati. Eventi mensili e coppie ETF originali TOP2_CONTEXT_REVALUE, simulatore OLC19 nativo, fee=.001 primaria e stop friction=.001.

## Contratto engine causale
- Ricostruire lo stato integrale: quantità ETF, strumenti difensivi, free cash, cooldown, lock/pending reentry, ultimo proposal e target eseguito, ordini ancora da applicare e scheduler del ritardo.
- Ricalcolare la policy di controllo A dal giorno iniziale; salvare uno snapshot pre-evento per ogni apertura mensile, non lo stato dopo la decisione.
- Dal medesimo snapshot alla data t eseguire 4 branches **solo fino alla prossima apertura mensile** e misurare log(NAV_next_open/NAV_event_open), con stop e V6 nativi. Differenziali B/C/D meno A in logbp.
- Indici e quote aperte alla prossima apertura soltanto per il target *futuro*, mai feature disponibili al tempo t; non trattare ciò come una decisione.
- Verificare il replay spezzato sulla stessa policy, tutti e 7 gli array del motore identici al nativo per A e D, e uguaglianza dei NAV a parità di stato. Vietato scegliere il miglior ramo ex-post come strategia.
- Uno snapshot da stato A rende le label **off-policy** per un futuro conto adattivo; segnalarlo esplicitamente e verificare se/quanto lo stato adattivo si discosta.

## Modello OLC70 prequential
Per isolare l'effetto della **correzione delle etichette**, mantenere ESATTAMENTE le quattro feature e lo stimatore OLC69, senza nuova ricerca: universe_breadth_63, pair_avg_mom63, pair_prior_mom_weighted_tilt, pair_corr63, StandardScaler train-only + Ridge(alpha=25), tre regressioni B/C/D vs A, una per mercato; min 24 osservazioni mature. Feature as-of prima del trade (OLC68, snapshot congelato). Allena al mese t soltanto etichette sino al mese t−2 o anteriori. Se non trainabile scegliere A. Ramo scelto = argmax fra A=0 e le tre previsioni, con vantaggio stimato >5 logbp mensili per non scegliere A. Ties privilegiano A/B/C/D.
Eseguire le scelte in UN unico conto OLC19 con target e ritardo specifici per evento e stati di rischio continui; non concatenare replay mensili. Replay fee=.001 e stress fee=.003 mantenendo scelte invariate.

## Confronto e gate
Stessi periodi OLC19: MAIN 2021–2024, FULL Feb2019–apertura 1 Lug2026, 2024, 2025, 2026 parziale e crisi 2020. Riportare CAGR (252 giorni), MaxDD, rendimenti annuali e differenze rispetto a OLC19 A e OLC67 D *da risultati eseguiti*. Confrontare la skill di previsione al semplice mean-only train-only: RMSE e correlazione mensile su dati maturi. Quantificare divergenza delle etichette common-state vs OLC69 e il ruolo dei lock. Il gate per considerare OLC70 candidato paper (mai live) è FULL CAGR >= OLC19 in ENTRAMBI i mercati, MAIN CAGR >= OLC19 in entrambi, FULL MaxDD non peggiorato oltre 3pp; nessuna ottimizzazione post-esito. Se fallisce, respingere; mantenere OLC19/OLC67 research reference.

## Integrità
File input OLC67 SHA256 dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4, OLC68 presignal SHA256 b7911d1346f6d78a19513547fd4b91b8a68a1806b2332f3a95815fcaf2caf330. Quote OHLC, stop-fill e USA original-observed mask non broker-verified; nessun dato esterno, nessun forward-trading. Nessun aggiustamento dopo la lettura degli outcome.
