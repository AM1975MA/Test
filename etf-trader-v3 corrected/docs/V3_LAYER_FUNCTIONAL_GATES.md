# V3 Corrected — Contratti di qualità e prove indipendenti per ciascun layer

**Data:** 21 ottobre 2026. **Scope:** ricerca metodologica separata, nessuna modifica alla produzione. **Regola generale:** il CAGR NON è una funzione obiettivo dei layer. Verifica economica globale soltanto al termine del percorso, dopo il congelamento degli output.

## Principio sperimentale

- Una modifica funzionale per volta. Se si modifica la qualità della rappresentazione, non si cambiano contemporaneamente profondità/numero di foglie, funzione di loss, orizzonte, risk overlay, ponderazioni o regime.
- Base dati, basket, etichette, universo e calendario identici per baseline e challenger. Il test 2018–2026 è **storico esplorativo**, già ampiamente esaminato; prima della promozione servono dati temporalmente o documentalmente mai usati per scegliere i candidati.
- Addestramento `walk-forward` con etichette mature e verifica `exit_date < train_cutoff`. OOS e controlli al livello mese; i 500 panieri condividono ETF e NON sono 500 campioni indipendenti.
- Per ogni contender: ipotesi pre-registrata, delta abbinati rispetto al layer congelato, intervalli bootstrap a blocchi 6 mesi, Holm per gli esperimenti simultanei, report per anno, stress per intervalli e audit feature importance/source.
- Conservare codice, SHA, score completi, prediction dates, iperparametri, failure, esperimenti rifiutati; **non promuovere un layer solo perché funziona in un anno o migliora un unico indice**.

## L00 — Validità dei dati e delle feature

**Compito:** produrre indicatori matematicamente definiti, osservabili al tempo del segnale e sufficientemente informativi senza falsificare le osservazioni.

Metriche primarie: quota di feature disponibili per età ETF e regime temporale, assenza di leakage, accuratezza delle formule su serie sintetiche con oracle, consistenza OHLC entro tolleranza, duplicazioni esatte e collisioni MAD, riproducibilità cross-sectional. Metriche secondarie: stabilità della distribuzione, tasso di saturazione/clipping e ridondanza non voluta. **Non confondere la quantità di feature con informazione realmente distinta.**

Audit certificato [39652313100](https://github.com/AM1975MA/Test/actions/runs/39652313100): 203 output, 15 gruppi duplicati **solo Tail**, 10 combinazioni data/feature con MAD=0 (9 `drawdown21_dev`, 1 `drawdown63_dev`), 497 celle con volume zero (nessun volume negativo accettato dal caricatore), 893 flags di roundoff floating-point di entità irrilevante e **zero violazioni OHLC sopra la tolleranza 1e−8 usata dal loader**. La colonna `Close*Volume` rimane un proxy del dollar turnover, poiché i prezzi sono rettificati.

**Decisione L00-L01:** congelare per gli esperimenti L01 lo schema `CORRECTED125`. Non rimuovere ancora i 15 alias Tail: saranno studiati separatamente nel loro layer. Nessuna superiorità rispetto a `LEGACY` è implicita nel congelamento: qui si congela la validità delle formule, non il ranking.

## L01 — Ranking dei 149 ETF / vincitori

**Compito:** ordinare correttamente opportunità con target forward di 21 sedute, con enfasi sul primo e sui primi tre.

Metriche **primarie**: Top-3 dei migliori ETF nei panieri canonici; `nDCG@3` per paniere usando come rilevanza il rango dei ritorni futuri (così non dipende da outlier monetari); regret del primo selezionato. Metriche **secondarie**: Top-1, IC di Spearman per mese, mean reciprocal rank, rango futuro medio del selezionato, stabilità per anno/seed. Non CAGR.

Primo esperimento già predefinito, con **125 feature corrette intoccabili** e 360 round/3 seed:
1. `CORRECTED` baseline XGBRanker 127 foglie, `rank:pairwise` (OOS del test verificato 39515716383);
2. `L01_PAIR63` modifica **solo capacità** (63 foglie, stessa loss);
3. `L01_NDCG127` modifica **solo loss** (`rank:ndcg` con gain lineare e pair top-3, sempre 127 foglie).

La configurazione non può promuoversi per sola nDCG se peggiorano in modo consistente Top-3 e regret; la scelta sarà esplicitamente multi-obiettivo, motivata e sottoposta a conferma.

## L02 — Tail, eventi estremi e asimmetria

**Compito:** valorizzare le rare opportunità fortemente positive e prevenire selezioni con grande perdita, senza riscrivere il ranking centrale congelato.

Test separati: `top-decile winner recall`, `top-k miss rate` dei vincitori estremi, `downside false-selection rate`, regret nel peggior decile, PR-AUC per eventi rari (soglia derivata solo dal train), stabilità e calibrazione per età ETF e regime. Baseline ranker L01 congelata; Tail off vs on, loss invariata fra prove dello stesso sotto-esperimento.

**Priorità tecnica nota:** 15 gruppi di input Tail sono duplicati esatti. Test `TAIL_FULL60` contro `TAIL_DEDUP45` con identici algoritmi, training e seed. Eventuali risultati positivi non autorizzano modifiche simultanee al ranker.

## L03 — Regime di mercato / RMT / Macro

**Compito:** stimare ex ante se le condizioni del mercato cambiano la probabilità che un esperto sia affidabile.

Metriche: `Brier score`, log-loss, AUC/PR-AUC secondo prevalenza, stabilità temporale e precisione di transizione, calibrazione nel tempo. Se si valuta l'effetto della selezione esperti, il gate deve usare SOLO feature disponibili alla data e performance degli esperti **già maturate** prima del training. Confronto con `always-on`, `market-only` e modelli senza regime. Non utilizzare l'anno in cui F3/H1 è risultato migliore come etichetta di futuro disponibile al segnale.

## L04 — Fusione dei modelli / score finale

**Compito:** combinare componenti che apportano informazione incrementale invece di duplicarsi.

Metriche: ΔTop-3, ΔnDCG@3, Δregret rispetto al migliore esperto singolo **congelato**, correlazione degli errori, risposta in drawdown/stress e sensibilità ai pesi. Le ponderazioni devono essere apprese su OOF storici maturati, mai sul futuro finale.

## L05 — Allocazione e costruzione del paniere

**Compito:** convertire correttamente i punteggi in decisioni senza introdurre arbitrariamente rischio/concentrazione.

Metriche: cattura opportunità attesa a parità di budget, contributo marginale di Top-1 vs Top-3, stabilità pesi, concentrazione, turnover necessario, stima commissioni e coerenza delle esecuzioni next-open. Il rendimento totale è diagnostico e non parametro da massimizzare in questo gate. Nessuna funzione di rischio variata insieme alla policy di selezione.

## L06 — Rischio, falsi allarmi e resilienza

**Compito:** prevenire perdita estrema *quando* esiste rischio prevedibile, senza azzerare sistematicamente buoni segnali.

Metriche primarie: expected shortfall/CVaR (tail left), drawdown condizionale e tempo di recupero, sensitivity/recall su grandi perdite, false alarm rate e giornate di esposizione conservate, missed-opportunity rate. Applicare decisioni esclusivamente su dati disponibili prima dell'operazione. Esecuzione e ranking L01–L05 congelati.

## L07 — Validazione sistema completo

Solo dopo i precedenti gate: replay end-to-end con costi, vincoli di calendario, sensibilità a spread/slippage e periodo realmente non sfruttato nel tuning. Qui si potranno osservare anche CAGR/Sharpe, **come conseguenza delle competenze dimostrate dai layer**, senza usarli per modificarli retrospettivamente.

## Registro ed evidenza di rilascio

Un gate è `PASS` solo quando input/oracle, training, metriche e controlli si completano e la differenza supera il criterio definito; `REJECTED` quando peggiora; `INCONCLUSIVE` se intervalli o periodi non sono sufficienti. Una versione matematica corretta può essere `QUALITY_PASS` pur non essendo `PREDICTIVE_PASS`. La produzione V2 e i suoi score originali restano invariati.
