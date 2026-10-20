# Preregistrazione: ranking ETF globale vs selezione Top5 a due stadi
Data: 2026-10-20. Ramo `research/original149-two-stage-top5-20261020`. Nessuna modifica alla produzione.

## Obiettivo e falsificazioni
Dai sei modelli XGB125 già congelati (profondità 2–7, run Github Actions 39492170319), esaminare se separare **filtro globale** e **riordinamento della Top5** possa aumentare la redditività su ETF senza addestrare alcuna rete nuova. I modelli sono stati creati tramite walkforward rigoroso; gli score alle date storiche sono OOS del singolo modello. Non usare mai risultati futuri per scegliere candidati.

## Configurazioni predeterminate, NO tuning
Controlli fissi: XGB depth2 (4 foglie max), depth3 (8), depth4 (16), depth5 (32), depth6 (64), depth7 (128). Proposte:

- **STAGE3_20_4**: primi 20 ETF per ranking depth3 (8 foglie); all'interno, primi 5 secondo ranking depth4 (16 foglie).
- **STAGE3_20_7**: primi 20 depth3, poi Top5 ordinata da depth7 (128 foglie).
- **STAGE3_30_7**: primi 30 depth3, poi Top5 depth7.
- **STAGE2_20_7**: primi 20 depth2, poi Top5 depth7.
- **BLEND3_4**: 50/50 *percentili di score per la data* depth3 e depth4, poi Top5.
- **BLEND3_7**: 50/50 percentili depth3 e depth7, poi Top5.

Numero di esperimenti fissato prima di vedere risultati. Non ottimizzare il cutoff scegliendo fra 10, 15, 20, 25, ecc. dopo il test. Le due scelte 20/30 sono ipotesi distinte preregistrate. Non introdurre feature o parametri appresi dai rendimenti OOS.

## Causalità e misure
I sei score per ogni ETF/date sono file archivio `ALL_OOS_SCORES.parquet` di run 39492170319, 476 decisioni 2017–giugno 2026; verifica assoluta stesso roster SHA, 70.924 ETF/date, date e ticker_id, e identità di rendimenti/tutti target. Confronto depth4 con l'originale run XGB125 39479754815, la cui riproduzione è stata già verificata a differenza ZERO. Nessun training/refitting, nessun fit dei pesi o shortlist, nessun lookahead nel punteggio. Per i metodi STAGE ordinare il ranking completo lasciando la shortlist prioritariamente in testa e gli esclusi nell'ordine del primo stadio, per calcolare un RankIC globale comparabile **sapendo che l'ordinamento fuori shortlist non viene investito**. Top5 sempre selezionata dentro shortlist, senza scelte ex-post. Per BLEND usare rank percentile cross-sectional, senza trasformazioni fitted a posteriori.

Portafoglio Original149: Top5 long equal-weight, decisioni ogni cinque sedute, ingresso open(t+1), uscita open(t+6), 20bps costo roundtrip conservativo, NAV giornaliero identico alla funzione `nav_path` originale.

## Audit e decisioni
Per tutti i modelli: RankIC Spearman, Top5 overlap oracle, rendimento medio 5 sedute, CAGR netto, MaxDD, Sharpe, peggior rendimento settimanale, risultati per anno, differenze paired bootstrap 95% a blocchi circolari di 5 settimane, rispetto a depth3 e depth4. Confrontare con depth7 per capire se la shortlist aggiunge davvero valore all'esperto deep. Le differenze di rendimento vanno annotate prima e dopo selezione del modello storico migliore; evitare promozione in assenza di vantaggi convincenti rispetto al **migliore modello singolo** e al benchmark più semplice.

L'intero 2017–2026 è già stato ripetutamente esplorato: questa rimane una verifica esplorativa di ipotesi, NON un holdout prospettico, anche se le predizioni sottostanti erano out-of-sample annuale. Un eventuale vincitore deve essere confermato successivamente su periodi nuovi o universo ETF non ancora studiato. Nessun deploy automatico.
