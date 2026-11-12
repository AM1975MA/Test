# OLC100 — Verifica indipendente del segnale e disponibilità degli input

**Data controllo:** 12 novembre 2026. **Stato:** BLOCCATO per il nuovo Top2; validazione storica e download superati. Nessun segnale prospettico, nessun ordine, nessun nuovo CAGR.

## Cosa è stato effettivamente controllato

- Checkpoint OLC19 originale: SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`, valido.
- Pacchetto snapshot 12/11: **316/316 file** verificati sui checksum interni. Contiene **314 ETF** (165 EU e 149 USA), **29.845 barre** archiviate successive al 1° luglio 2026 (15.839 EU; 14.006 USA).
- Ranking: ricostruzione della scelta Top2 applicando ai punteggi OLC16 originali il criterio di ordinamento congelato. **90/90 decisioni EU e 90/90 USA corrispondono esattamente** agli archivi OLC19 per il periodo di ricerca.
- Ultimo segnale originale disponibile: **30 giugno 2026** (entry **1° luglio 2026**). Ultimi Top2 originali soltanto come verifica di identità storica: `LBRE.DE / EXV6.DE` EU e `PPLT / PALL` USA. **Non sono raccomandazioni attuali**.
- Modello contestuale annuale OLC16 `2026_TOP2_CONTEXT.json`: presente e conservato. Nel checkpoint esaminato non sono presenti gli artefatti serializzati necessari a generare ex novo i forecast Return125 e i forecast ET/XGB Hybrid42 sulle date di luglio–novembre. I CSV dei rispettivi score si fermano a giugno 2026. Non è possibile produrre un Top2 novembre 2026 genuino senza ripristinare il primo stadio e dimostrare la parità pregressa.

## Errore di perimetro nelle anomalie OHLC: chiarito

Il downloader misura **83** barre di quotazioni anomale nell'intero fetch dal **19 giugno** al 12 novembre 2026, ma salva il panel nuovo solamente dal **2 luglio**. In questo panel sono presenti **79** flag (`71 EU / 8 USA`). Le altre **4** anomalie ricadono nel periodo di sovrapposizione **19 giugno–1° luglio** e non erano persistite nel primo snapshot: BEL.BR (2), ISFA.AS (1), LYXIB.MC (1). I checksum sono validi; non è corruzione del file. È necessario separare i due perimetri nel report e archiviare esplicitamente il fetch di sovrapposizione.

Fra le 79 barre nuove segnalate: **27** presentano una violazione superiore a **10 basis point**; quella massima è **103,87 bp**. Non vengono eliminate, corrette o rese eseguibili dal test; il motore di stop richiede fonti verificate.

## Azione effettuata sul codice

È stata predisposta una correzione nel downloader di ricerca OLC100 che registra separatamente anomalie di *overlap* e *post-anchor*, e conserva l'OHLC originale del tratto di sovrapposizione come file autonomi. **Cinque test locali superati**. I modelli, i parametri del ranker, OLC19, OLC67 e il ramo principale restano invariati.

## Esito e condizione per il prossimo segnale

**OLC100 nuovo Top2: NON DISPONIBILE / BLOCCATO.** Non è un esito negativo di rendimento: manca il requisito di generazione autentica dei forecast e la continuazione dello stato di portafoglio V6/FAST_LOCK3. Il calendario del segnale di fine novembre non è ancora maturato al 12 novembre.

Per sbloccare occorrono: modelli upstream originali/contratto di training e feature, parità dei punteggi almeno gennaio–giugno 2026, produzione dei punteggi mensili successivi con soli dati osservati prima del cutoff, validazione quote/maschere e contabilità V6 a stato persistito. Un semplice download di prezzi o un modello surrogato non soddisfa tali prerequisiti.

## File della verifica

- `audit_olc100_readiness.py`: verifica di checksum, universo, 180 selezioni, dataset e blocchi di causalità.
- `OLC100_ASOF_READINESS.json`: risultato strutturato, stato fail-closed.
- `OLC100_SUSPECT_OHLC.csv`: 79 anomalie nelle sole barre persistite post-anchor; controlli di severità.
- `capture_asof.py`, `test_capture.py`: futuro downloader OLC100 con conteggio overlap/post-anchor separato.
