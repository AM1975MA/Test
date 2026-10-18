# OASIS149 — G4 nuova informazione macro, protocollo PREREGISTRATO
Data: 2026-10-18. Branch isolato: `research/oasis149-macro-asof-g4-20261018`.
Stesso universo **esatto 149 ticker originali**; `evidence_v1/data/original149/universe.csv` verificato per hash in `oasis149/results/MANIFEST_149.json`. Finestre di previsione non sovrapposte di 21 sedute, valutazione 2021–2026, 30bp di costo convenzionale della sostituzione, confronto candidato contro l'ETF posseduto sul roster OASIS149 P3 (usato solo per definire incumbent as-of). Questi test NON riutilizzano l'universo dei 150, non selezionano tickers in funzione dei rendimenti e non effettuano trade.

## Domanda scientifica e FALSIFICABILITÀ
Una informazione ECONOMICAMENTE DISTINTA dal prezzo delle 149 quote (volatilità implicita di mercato, curva dei tassi, credito) migliora la previsione probabilistica del vantaggio relativo netto fra ETF, anziché imitare una correlazione momentanea?

4 osservabili giornalieri pubblici, scaricati e hashati:
- `VIXCLS` — proxy volatilità implicita azionaria USA, livelli 15/25 come normali scale NO soglie operative;
- `DGS2` — Treasury USA 2 anni (percentuale);
- `DGS10` — Treasury USA 10 anni (percentuale);
- `BAMLH0A0HYM2` — credit spread ICE BofA high yield option-adjusted (percentuale).
Fonte `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`. G4 usa **observation_date <= signal_close_date − 7 giorni CALENDARIO** per evitare chiusure e tempi di pubblicazione, con backward-only asof join massimo 14 ulteriori giorni per mancanti. Questa misura non garantisce che dati revisionati siano storicamente identici: le serie FRED scaricate oggi sono il *vintage di oggi*, non osservazioni PIT certificate. Nessuna pretesa di alpha autentico. G4 scatta lo stop se una serie manca e NON sostituisce quote ETF / valori futuri. Snapshot scaricato con SHA e data di retrieval, no sorgenti sintetiche.

## Tre modelli a confronto, SENZA sweep iperparametri
- H0 NULL: probabilità online di vittoria netta del challenger, esattamente il precedente `H0_PRIOR` G1; label future maturate strettamente prima del segnale.
- H2 PRICE_GROUP: il medesimo modello di prezzo già respinto (`H2_GROUP_RESIDUAL`), stesse 13 caratteristiche su coppie e `LogisticRegression(C=0.15, solver='liblinear')`, scaler fit su training data.
- H5 MACRO_CONDITIONAL: H2 price group features + 4 fattori economici as-of standardizzati entro training: livello log(1+VIX), curva 10−2, 10y, livello HY spread; + 4 modifiche a 21 **giorni di calendario** (macro time axis; sole osservazioni già disponibili) + macro stress x 6 differenze dummy di asset class: `log(1+VIX) * (I(asset_i in group) − I(asset_j in group))` e `credit spread * difference group`; macro terms centered and scaled train-only, `C=0.08`, shrinkage L2; NO griglia.
- H6 MACRO_COMPACT: H2 + SOLO 4 livelli macro (più parsimonioso); `C=0.08`. Diagnostico predefinito, non selezionato ex post.
H5 è l'ipotesi PRIMARIA rispetto a H2 e H0; H6 è ablation. Non usare G1 preesistente H3/H4 per selezionare parametri. Stessa generazione catalogo 8 challenger e 64 probe, 5.120 confronti previsti su 64 ancore.

## Allineamento etichette e fitting
Come G1 originale: t = segnale al Close, entry prossimo Open, outcome dopo 21 Open osservati; train SOLO righe con fine outcome OPEN < signal.Close di data corrente. Ritraining a ogni data valutata. Peso per anchor = 1/numero confronti di quell'anchor (normalizzato) così migliaia di coppie non diventano N indipendente. Nessuna statistica globale di scaler sul periodo futuro, NO forward fill oltre la finestra prevista. Le caratteristiche macro vengono calcolate sul quadro scaricato, ritardate **prima** dell'unione, senza modificare le label.

## GATE precommittato
Test primario solo task challenger (1024 coppie / 64 ancore), out-of-development 2021-2026:
- H5 Brier e logloss **inferiori** sia a H0 sia a H2;
- riduzione Brier H5 vs H0 **positiva con CI bootstrap 95% per blocchi di tre ancore da 21 sedute**;
- Brier H5 < H0 **in entrambe** 2021–23 e 2024–26;
- stesse condizioni di data as-of e p calibrata. Se gate fallisce, non costruire alcuna strategia G4; non riaddestrare su tutto il basket o ottimizzare C/soglie.
- Report completezza dati macro, n delle date as-of, conteggio mancante e data effettivamente più recente di ogni feature. CI con 1500 repliche e seed 20261018.
- Report p>0.65 e vantaggio >=10 punti rispetto NULL come **shadow opportunities** solo diagnostiche, mai reinvestite in backtest; misurare rendimento netto ex post e denominatore.
- Gruppi 6, epoche 2021–23 e 2024–26, n posizioni/eventi prima/dopo.
- Nessuna interpolazione di shock come dati futuri; nessun rendimento ex post usato per etichette di gruppo.

## PIT e decisione
Questa è un'esplorazione *revision-risk* su un dataset originale già bruciato. Un esito positivo **NON** autorizza operatività. Per parlare di PIT servono ALFRED vintages/realtime_start e timestamp disponibilità, o una fonte immutabile archivio CBOE/UST/ICE; alcuni record ICE possono avere restrizioni. In assenza: marcatura `UNVERIFIED_REALTIME_VINTAGE` e veto sul trading. ALFRED documenta revisioni e vintages (https://alfred.stlouisfed.org/help/downloaddata). I prezzi Yahoo 149 hanno risistemazioni storiche e non rappresentano quote bid/ask con eseguibilità comprovata.

## Persistenza
Salvare source CSV 4 serie, manifest sha, report merge as-of, PREDICTIONS_FULL con every prequel probability and labels, proper scores, CI per anchor, warnings e la decisione del coordinatore in `oasis149/macro_g4/results/`. Separare commit prima dell'esecuzione (il presente documento) dai risultati. Non toccare produzione `etf_trader`.
