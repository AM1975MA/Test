# OLC103 — Stabilità del Top2 come informazione (protocollo prima dei risultati)

**13 novembre 2026 — ricerca retrospettiva, nessun trading live.** Si riutilizza il periodo 2019–prima apertura luglio 2026 già esplorato, dunque **NON** un holdout indipendente. Modelli, primi due ETF del segnale mensile, V6, FAST_LOCK3 e motore nativo congelati nei checkpoint OLC19/67/102. Non cambiare il ranking, né selezionare un nuovo ETF in base alla stabilità. Solo la policy sperimentale di esposizione può essere variata.

## Informazioni causali
S0 = chiusura prima della prima apertura dell'evento k; S1 = chiusura di k; S2 = chiusura di k+1. Il primo ingresso lecito che usa tutti e tre è apertura k+2. Il controllo mantiene i Top2 originali, lo stesso giorno di ingresso k+2 e identiche altre regole.

## Segnale congelato
Calcolare T0, T1, T2 = insiemi di 2 ETF con migliori score contestuali (rango ML originale/aggiornato, OLC102), e `retention=(|T0∩T1|+|T0∩T2|)/4`. `full_stable=1` solo se T1=T0 e T2=T0, indipendentemente dall'ordine. Non richiedere che Top1 e Top2 conservino l'ordine. No identità ticker come feature apprendibile.

## Prima domanda: informazione predittiva
Per ogni evento maturo (escluso l'ultimo): `future_raw` = media dei log ritorni dei due ETF ORIGINALI da Open[k+2] ad Open[next_event]; `future_excess` = `future_raw` meno mediana universo eleggibile del mese, stesso ingresso/uscita. `bad` se future_raw < -5%; obiettivo diagnostico, non stop eseguibile. Nessun risultato usa altre due alternative o un ETF che non fosse nella coppia originale.

Analisi descrittiva con correlazioni Spearman e differenze conditional stable/unstable, bootstrap a blocchi circolari di 6 decisioni, seed 103613, 3000 replicazioni. Non fare selezioni a posteriori per mercato o anno.

Test incrementale *prequential*: per evento j si usa il training j' <= j-2 (esiti pienamente maturi), almeno 24 mesi. Fit train-only mediana, StandardScaler; Ridge alpha=10 su target future_excess limitato **solo nel training** a ±0.25, e LogisticRegression C=0.5 per bad. Baseline con feature ex ante `[score_margin_2_3, mean_top2_score, past_mom21, past_vol63, early_pair_close_return, gross_V6_at_open]`; estensione aggiunge **solo retention**. L'early_pair_close_return è calcolato da C[k+1]/C[k-1] (osservabile prima di k+2); non usare Open[k+2] come predittore. Valutazione non troncata su 64 mesi ca. per mercato: MSE (regressione) e Brier (loss), con differenze appaiate e block bootstrap 6. Requisito per supportare la tesi: miglioramento appaiato stabile in entrambi i mercati e su target rendimento/rischio, da confermare su dati prospettici indipendenti prima di promuovere.

## Seconda domanda: utilità economica contabile nativa
Sempre Top2 T0 originale, identica politica di ingresso k+2, V6 e FAST_LOCK3. Pesi 50/50 oppure MINVAR63 come OLC67, senza fit nuovo. Scelte di esposizione prescritte, non ottimizzate su risultato:
- BASE: gross V6 originale
- ALL75 / ALL50: cap a 0.75 / 0.50 sul gross in tutti i mesi alla terza apertura (controllo semplice riduzione)
- UNSTABLE75 / UNSTABLE50: stesso cap solo se `full_stable=0`
- STABLE75 (placebo direzionale): cap solo se `full_stable=1`
I cap sono applicati da k+2 fino al successivo evento; prima di allora la precedente strategia resta invariata. `gross` pre-esistente più basso resta sempre più basso; ricostruire gli `alt` V6 a parità di regole. Due scenari fee/frizione (0.001/0.001 e 0.003/0.005), entrambi i mercati. Confrontare CAGR/MaxDD native, turnover, stop, esposizione e paired annualized log-return a blocchi di 6 mesi. Nessun nuovo parametro ricercato su questo stesso campione.

## Gate
Verificare parità del controllo BASE alle due scorecard OLC102 `FIXED_DAY2_HALF` / `FIXED_DAY2_MINVAR63`; 180 eventi originali OLC19, sette matrici contabili per baseline OLC19 e V6, assenza di utilizzo di S2 prima di k+2. Non affermare valenza forward o broker execution. Qualunque incongruenza fallisce il test, non produce falsi rendimenti. Risultati esplorativi, nessuna promozione live.
