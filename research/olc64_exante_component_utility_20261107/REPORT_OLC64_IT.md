# OLC64 — Verifica della prevedibilità ex ante dell'utilità dei componenti

**Data:** 7 novembre 2026. **Esito: NEGATIVO, NO GATE / NO PROMOTION.** Nessuna modifica a OLC19, nessun training o modifica di pesi, nessun acquisto di dati. Protocollo congelato su GitHub prima della prima lettura delle associazioni OLC64.

## Sintesi operativa

L'analisi OLC63 mostra che RETURN, Extra Trees, XGBoost e memoria hanno contributi diversi fra Europa e USA, anche nei diversi anni. OLC64 verifica se quella variabilità sia **prevedibile alla data del segnale** da due indicatori estremamente semplici e congelati: quanto divergono RETURN e CURRENT, e quanto divergono ET e XGB. Il controllo fallisce: **le correlazioni 2021–2024 sono prossime allo zero, cambiano segno fra mercati e non sono stabili anno per anno**. Non introdurre quindi una fusione dinamica guidata da tali disaccordi.

## Dati e unità

- OLC63 identico, 16 coalizioni × 118 mesi/mercati valutabili (EU 58, USA 60); due orizzonti 21 e 42 sedute.
- MAIN: gennaio 2021–dicembre 2024, **48 mesi per mercato**. LATE: 2025, **10 EU / 12 USA**; aprile/maggio EU esclusi per un'etichetta futuro mancante. Il 2025 non è un holdout vergine.
- Due predittori disponibili a t: `D_R = 1-Spearman(RETURN,CURRENT)` e `D_X = 1-Spearman(ET,XGB)` sui ranghi degli ETF eleggibili.
- Target solo per valutazione post evento, mai usati nel segnale:
  - H1: `Y_R = V(RXM)-V(EXM) = V(mask 13)-V(mask 14)`, differenza del contributo marginale di RETURN rispetto a ET a parità degli altri componenti, misurata in pp a 21/42 sedute.
  - H2: `Y_X = V(REXM)-V(REM) = V(mask 15)-V(mask 11)`, utilità marginale di XGB con RETURN, ET e memoria attivi, in pp a 21/42 sedute.
- Spearman per 48 osservazioni mensili su 21 sedute e 42 sedute. IC bootstrap circolare di 6 mesi, 3000 repliche, descrittivo e non corretto per le molte ipotesi storiche.

## Risultati primari, 21 sedute, 2021–2024

| Ipotesi | EU Spearman [IC95%] | USA Spearman [IC95%] |
|---|---|---|
| H1 — discordanza RETURN/CURRENT → vantaggio relativo di RETURN | **+0,137** [−0,169; +0,387] | **−0,062** [−0,342; +0,216] |
| H2 — discordanza ET/XGB → contributo XGB | **−0,094** [−0,364; +0,183] | **+0,022** [−0,235; +0,265] |

Tutti e quattro i CI attraversano zero. Nessun effetto stabile sia EU sia USA. Pearson corrispondenti: EU H1 +0,192 / H2 −0,135; USA H1 −0,023 / H2 −0,031. Non interpretare i coefficenti Pearson come probabilità o differenze di CAGR.

## Sensibilità all'orizzonte e all'anno

A 42 sedute MAIN: H1 EU −0,079/USA −0,082; H2 EU −0,160/USA +0,082. Gli intervalli bootstrap includono zero anche qui. Le correlazioni annuali MAIN a 21 sedute oscillano:

| 2021–2024 | EU H1 | USA H1 | EU H2 | USA H2 |
|---|---:|---:|---:|---:|
| 2021 | +0,315 | +0,007 | −0,133 | +0,347 |
| 2022 | +0,091 | −0,364 | −0,056 | +0,117 |
| 2023 | −0,308 | +0,011 | +0,358 | −0,141 |
| 2024 | +0,179 | +0,084 | −0,291 | −0,055 |

2025 descrittivo (non nuovo OOS), 21 sedute: H1 EU +0,309, USA −0,306; H2 EU −0,512, USA +0,283, con poche date e molte utilità esattamente nulle nel caso H2. Non vi è un effetto comune ai mercati. Evitare di usare l'eventuale rapporto negativo 2025 come nuova regola di trading dopo averlo osservato.

## Significato per la progettazione

Le differenze di valore marginale dei componenti viste in OLC63 **non sono sufficientemente anticipabili da una semplice misura di disaccordo fra ranghi**. Quindi un gate tipo «aumenta RETURN se è divergente» o «aumenta XGB quando ET/XGB sono discordanti» non ha supporto. Il risultato non prova che tutti i segnali di affidabilità del componente siano inefficaci: circoscrive il fallimento a H1/H2 e all'universo storico già ampiamente esplorato.

Prossima priorità, senza cambiare nulla nel modello: eseguire una diagnosi **decisionale e controfattuale dei Top2**: quali opportunità perse erano nel Top5/Top10, quale è il costo economico di una posizione 1/2 sbagliata, quando i due candidati sono equivalenti economicamente e quando pochi casi estremi spiegano l'apparente superiorità della fusione. Separare la diagnosi della scelta del candidato dalla volatilità dei rendimenti/stop ed evitare nuovi tentativi di fitting indiscriminati sulle stesse etichette.

## Riproducibilità / qualità

- Sorgenti OLC63 immutati; SHA256 dei CSV verificati; calendario e supporto immutati.
- `run_olc64.py`: 472 osservazioni diagnostiche (118 market-month ×2 orizzonti ×2 ipotesi); 16 associazioni riassuntive, 32 controlli annuali; bootstrap a blocchi preregistrato.
- `verify_olc64_independent.py`: verifica delle 472 uguaglianze contro le 16 coalizioni, scostamento massimo 7,11e−15 pp; ricostruzione indipendente Spearman come correlazione Pearson dei ranghi, scostamento massimo 6,94e−17. Stato **PASS**.
- Risultati e codice archiviati. Nessuna esecuzione sul portafoglio e nessuna modifica a `main`.