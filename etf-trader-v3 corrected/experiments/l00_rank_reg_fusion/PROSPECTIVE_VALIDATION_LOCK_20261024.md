# V3 — Protocollo bloccato per validazione prospettica (24 ottobre 2026)

**Data del lock:** 2026-10-24. Questa pagina NON afferma l'esistenza di un nuovo holdout. Lo snapshot OHLCV congelato nel repository arriva soltanto al 1 luglio 2026 e l'ultimo segnale con un vero target OOS delle strategie CORRECTED125 e regressori congelati risale a maggio 2026. La valutazione dei nove nuovi studi è 2018–2026 sul calendario già utilizzato. I dati successivi non sono stati incorporati in questa campagna.

## Modelli congelati al lock

- Modello di riferimento **CORRECTED125 + NESTED_24_TOP1_GUARD**. Nessuna variazione, no retraining ad hoc del meta, Top3 originale invariato.
- Challenger A **UTILITY_DT14_L1.5**, DecisionTree hurdle a 14 feature, penalità perdite 1.5 e cost proxy +20 bps.
- Challenger B **UTILITY_RF_REGIME_L1**, Random Forest hurdle con 27 feature tutte disponibili as-of, penalità perdite 1, cost proxy 20 bps.
- Challenger C **UTILITY_HGB_REGIME_L1.5** come controllo di riduzione della coda.
- Tutti i parametri bloccati nei sorgenti con SHA e commit. Non cercare nuove profondità, numerosità delle foreste, soglie o pesi utilizzando i risultati del nuovo periodo.

## Nuova fonte esterna e controllo di replicabilità

1. Acquisire un set di 149 file raw aggiornato, conservando i file originali e il loro checksum, le date richieste, l'istante di scaricamento, il provider e il metodo di rettifica corporate actions. **Niente backfill silenzioso** delle righe storiche congelate.
2. Ricalcolare le feature first-stage alla data di segnale soltanto usando prezzi allora già osservabili. Calcolare le predizioni nuove mantenendo i modelli originali annuali e il loro protocollo di training fino al 2025. Verificare per prima cosa la corrispondenza delle predizioni rigenerate di gennaio–maggio 2026 contro il controllo OOS congelato. Se manca la parità, non presentare il segmento nuovo come prosecuzione omogenea.
3. Solo se la continuità è confermata, registrare l'estensione temporale da giugno 2026 in poi, distinguendo una *valutazione retrospettiva non utilizzata* da una vera *validazione prospettica*, che comincia con i segnali prodotti e archiviati dopo questo lock e con esiti maturati successivamente.
4. Ogni previsione deve essere prodotta e congelata **prima** che siano disponibili i rendimenti futuri usati come label. Conservare manifest hash del panel, membership di tutti i panieri, fitting audit, seed, identificativi job, timestamp UTC, versioni pacchetti, policy allocator e risultati.
5. Riaddestrare il meta-modello secondo il protocollo esistente, con target di 21 sedute maturati da almeno 60 giorni e refit trimestrale, senza feature future.
6. Per la prova di utilità primaria, valutare il confronto con la policy di riferimento sui panieri e **sugli eventi ETF-coppia/data deduplicati** e fare bootstrap su blocchi temporali. Controllare downside a -10%, Top1 hit, selected excess, numero e precisione delle sostituzioni, mix settoriale e turnover.
7. Riprodurre il next-open replay con costi 10, 25 e 50 bps, identico riferimento di dimensione del portafoglio e medesime regole di liquidità/rischio, senza scegliere il miglior modello dal CAGR. La NAV media di 500 panieri non è un unico portafoglio immediatamente negoziabile.
8. Un eventuale segmento di soltanto 3–5 mesi (ad esempio giugno–agosto 2026) serve esclusivamente come smoke test; non può convalidare un alpha stabile. La promozione richiede evidenza su un periodo significativamente più lungo o universi indipendenti, senza interventi manuali adattivi.

## Decisione corrente

**NON PROMUOVERE UTILITY_RF_REGIME_L1**: sul periodo fino a dicembre 2025 perde 1,13 punti di CAGR Top2 rispetto all'incumbent nel test dal febbraio 2022; il guadagno misurato dopo dipende dall'inclusione del 2026, con una precisione Top1 inferiore. La variante DT14-L1.5 migliora Top1, ma non presenta utilità economica e downside superiori in maniera robusta.

Il checkpoint unico resta `CORRECTED125 + NESTED_24_TOP1_GUARD`. Tutti i nuovi modelli sono challenger congelati di ricerca; produzione V2 e V3 invariata.
