# OLC100 — Verifica indipendente del segnale e disponibilità degli input

**Data controllo:** 12 novembre 2026. **Stato:** BLOCCATO per il nuovo Top2; validazione storica e download superati. Nessun segnale prospettico, nessun ordine, nessun nuovo CAGR.

## Cosa è stato effettivamente controllato

- Checkpoint OLC19 originale: SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`, valido.
- Pacchetto snapshot 12/11: **316/316 file** verificati sui checksum interni. Contiene **314 ETF** (165 EU e 149 USA), **29.845 barre** archiviate successive al 1° luglio 2026 (15.839 EU; 14.006 USA).
- Ranking: ricostruzione della scelta Top2 applicando ai punteggi OLC16 originali il criterio di ordinamento congelato. **90/90 decisioni EU e 90/90 USA corrispondono esattamente** agli archivi OLC19 per il periodo di ricerca. Verificata anche la formula originale del modello contestuale annuale 2026: **12/12 pesi mensili EU/USA riprodotti**, errore massimo **1,67e-16** rispetto al `PARAMETER_TRACE` congelato.
- Ultimo segnale originale disponibile: **30 giugno 2026** (entry **1° luglio 2026**). Ultimi Top2 originali soltanto come verifica di identità storica: `LBRE.DE / EXV6.DE` EU e `PPLT / PALL` USA. **Non sono raccomandazioni attuali**.
- Modello contestuale annuale OLC16 `2026_TOP2_CONTEXT.json`: presente e conservato. Nel checkpoint esaminato non sono presenti gli artefatti serializzati necessari a generare ex novo i forecast Return125 e i forecast ET/XGB Hybrid42 sulle date di luglio–novembre. I CSV dei rispettivi score si fermano a giugno 2026. Non è possibile produrre un Top2 novembre 2026 genuino senza ripristinare il primo stadio e dimostrare la parità pregressa.

## Errore di perimetro nelle anomalie OHLC: chiarito

Il downloader misura **83** barre di quotazioni anomale nell'intero fetch dal **19 giugno** al 12 novembre 2026, ma salva il panel nuovo solamente dal **2 luglio**. In questo panel sono presenti **79** flag (`71 EU / 8 USA`). Le altre **4** anomalie ricadono nel periodo di sovrapposizione **19 giugno–1° luglio** e non erano persistite nel primo snapshot: BEL.BR (2), ISFA.AS (1), LYXIB.MC (1). I checksum sono validi; non è corruzione del file. È necessario separare i due perimetri nel report e archiviare esplicitamente il fetch di sovrapposizione.

Fra le 79 barre nuove segnalate: **27** presentano una violazione superiore a **10 basis point**; quella massima è **103,87 bp**. Non vengono eliminate, corrette o rese eseguibili dal test; il motore di stop richiede fonti verificate.

## Azione effettuata sul codice

È stata predisposta una correzione nel downloader di ricerca OLC100 che registra separatamente anomalie di *overlap* e *post-anchor*, e conserva l'OHLC originale del tratto di sovrapposizione come file autonomi. **Cinque test locali superati**. I modelli, i parametri del ranker, OLC19, OLC67 e il ramo principale restano invariati.

## GitHub Action ripetuta con la correzione — 12 novembre 2026

- Run **43317078803**: https://github.com/AM1975MA/Test/actions/runs/43317078803. Acquisizione conclusa, artifact diagnostico conservato. Il job ha volutamente restituito `failure` poiché la geometria OHLC di 15 ETF non è convalidata.
- **314/314** ETF riacquisiti, **314 serie post-anchor** e **314 serie overlap** archiviate separatamente; **630/630 SHA256** verificati autonomamente.
- **29.845 barre nuove + 2.677 barre overlap**, 32.522 righe totali nei due pannelli. La riconciliazione **79 post-anchor + 4 overlap = 83** è ora verificata file per file.
- Le quattro barre overlap ora verificabili nei CSV sono: BEL.BR (2026-06-24 e 2026-06-26), ISFA.AS (2026-06-19), LYXIB.MC (2026-06-19).
- In una fonte con High/Low non coerenti con Open/Close, il fill dello stop non è certificabile: **SOURCE_INTEGRITY_PASS_PRICE_GEOMETRY_FAIL**. Nessun Top2, simulazione o ordine è stato emesso.

`OLC100_RECHECK_QA_20261112.json` contiene la riconciliazione ripetuta e gli hash; `OLC100_CAPTURE_RECHECK_20261112.zip` conserva lo snapshot grezzo.

## Esito e condizione per il prossimo segnale

**OLC100 nuovo Top2: NON DISPONIBILE / BLOCCATO.** Non è un esito negativo di rendimento: manca il requisito di generazione autentica dei forecast e la continuazione dello stato di portafoglio V6/FAST_LOCK3. Il calendario del segnale di fine novembre non è ancora maturato al 12 novembre.

Per sbloccare occorrono: modelli upstream originali/contratto di training e feature, parità dei punteggi almeno gennaio–giugno 2026, produzione dei punteggi mensili successivi con soli dati osservati prima del cutoff, validazione quote/maschere e contabilità V6 a stato persistito. Un semplice download di prezzi o un modello surrogato non soddisfa tali prerequisiti.

## File della verifica

- `audit_olc100_readiness.py`: verifica di checksum, universo, 180 selezioni, dataset e blocchi di causalità.
- `OLC100_ASOF_READINESS.json`: risultato strutturato, stato fail-closed.
- `OLC100_SUSPECT_OHLC.csv`: 79 anomalie nelle sole barre persistite post-anchor; controlli di severità.
- `capture_asof.py`, `test_capture.py`: futuro downloader OLC100 con conteggio overlap/post-anchor separato.
