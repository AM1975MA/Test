# Piano: paper_ltr_v1/LISTNET_NEXT_TESTS.md

Autorizzazione utente 12 ottobre2026: «ok allora procedi con la linea concordata».
Repository esclusivo AM1975MA/Test; worktree paper-ltr-test;
branch research/paper-ltr-feasibility-20261012; PR72 già dedicata alla ricerca.
Input e sorgenti canoniche congelati, sources/ solo lettura, produttivo escluso.

## Stato di partenza

BASE e ListNet100 completati e conservati, nessun nuovo fit dei controlli.
Fit originale run38179662587; replay38180179897. I numeri originali sono
la baseline del nuovo confronto. La diagnosi dei90 fit è già stata eseguita.

## Compiti e ownership

1. ML: learner/run/tests in paper_ltr_v2, Budget300 e controllo lineare.
2. Statistica: audit/summarize/PREREGISTRATION/tests, KL e gate convenzionali.
3. Finanza: replay/summarize_replay/tests, provenienza e calendari.
4. Coordinatore: workflow, integrazione, review, Actions, risultati e PR.

## Decisioni vincolanti

- Prima audit senza nuovi fit, poi Budget300; lineare in fase separata.
- Nessuna modifica a portafoglio, costi, esecuzione, feature o storico.
- Gate fallito non autorizza aumenti di budget o nuove combinazioni.
- Il replay economico resta diagnostico anche se la qualità fallisce:
  l'utente ha richiesto esplicitamente il CAGR, nessuna promozione automatica.
- Riusare i checkpoint fermati per patience solo dopo certificazione di identità.
- Preregistrare solver lineare, arresto numerico e budget prima dell'esecuzione.
- Non chiamare il periodo2017–2026 holdout vergine.

## Avanzamento

- Audit implementativo: implementato; 23 test v2 e 16 test v1 verificati.
- Preregistrazione: scritta prima dei fit; pubblicazione e ripresa 14 ottobre2026.
- Budget300: non avviato.
- Lineare: non avviato.
- Replay e decisione: non avviati.

## Ripresa del 14 ottobre2026

- Commit e373189 pubblicato; run38562284435: audit90 checkpoint passato,
  nuovi fit0, poi confronto raw→TI esatto fallito prima dei fit.
- Audit conservato11892402901, SHA JSON
  e4f57018d56ee22f7ede4a302e80d4900bde981369debaa541da0e5eb6a76509.
- Diagnosi38563762311: stesso host r3, profilo storicoAVX512 esatto;
  profilo fit conAVX512 disabilitato non esatto. Vedi amendment separato.
- Certificazione38564721801: acquisizione hostcompatibile al secondo tentativo;
  confronto esatto sui tre download in esecuzione, nessun fit.
- Workflow modelli riusa audit90 verificato per hash e attende certificazione
  storica prima di avviare i fit. Gate esatto e ricette restano invariati.
