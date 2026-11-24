# Perseo U20 — riproduzione

Due archivi da estrarre nella stessa cartella: PERSEO_U20_CODICE_RISULTATI.zip e PERSEO_U20_STATI_INPUT.zip. Non sovrascrivono U19. Il rapporto è RAPPORTO_PERSEO_U20.md; PERSEO_U20_ANALISI.html è autonomo con grafico incorporato.

## Replay autonomo
Richiede soltanto numpy. Dal contenuto estratto:

    python replay_saved.py

Ricalcola tutti i107conti dalle decisioni congelate, prezzi, maschere, stati e modalità di rischio. Confronta bitwise l'intero ledger. Per un sottoinsieme aggiungere parti del nome account, per esempio:

    python replay_saved.py TRANSFER_LOCAL_TRANSFER_BASE_15 USA_NATIVE_REFERENCE_ISOLATED_15

L'audit contabile indipendente dei107conti è results/INDEPENDENT_LEDGER_AUDIT.csv; quello sui nuovi indicatori è results/QA_FINAL.json. REPLAY_CHECK.json registra il sottoinsieme effettivamente ricalcolato in questa sessione; non pretende che tutti107siano stati nuovamente ricalcolati dalla procedura standalone.

## Ricostruzione completa della campagna
I file run20.py, walkforward20.py, transfer20.py, context20.py, architecture20.py, analyze20.py, report20.py ricostruiscono gli esperimenti in quest'ordine. Richiedono i due archivi U19 estratti in una cartella sorella chiamata perseo_u19_work e le dipendenze REQUIREMENTS.txt. I prezzi, le125/42feature e le previsioni U19 vengono riutilizzati; nessun nuovo modello di ranking è stato addestrato in U20. I modelli originali salvati in U19 non sono necessari per il replay dei conti congelati.

U19 codice/risultati:
https://chatgpt.com/library?file_id=libfile_fde3_f-02a507a3f2148191b0e869e191e834fa_549d1bce98388191a0aeb13709c4eff9&account_id=personal
SHA256 8b5548d2bc52e9fb95f561c1fd7d0b2251974007537a0f6be31e787f7e3e0baf

U19 dati:
https://chatgpt.com/library?file_id=libfile_fde3_f-2233b3f9f4fc8191b432bb56ec5d1a8d_549d1bce98388191a0aeb13709c4eff9&account_id=personal
SHA256 1ec8de3950fe827050f4c22cb3909e6eb75e086beddd831761f2910e449cea91

## Interpretazione e limiti

U20A precede i nuovi risultati sul rischio. U20B/C/D sono estensioni esplicitamente successive. La famiglia dei candidati e la sua selezione annuale sono distinte. Non c'è un holdout storico non esplorato; nessuna promozione live.

Il40,23%USA della nuova architettura è il vecchio selettore nativo preservato. Il44,31%USA con stop isolato è una diversa variante; non viene combinato retrospettivamente con i numeri migliori degli altri panieri.

MONTHLY_FINAL/ANNUAL_FINAL attribuiscono il P&L apertura→apertura alla seduta iniziale; le tabelle di selezione walk-forward usano solo valorizzazioni disponibili prima del cutoff annuale. Non confrontare direttamente mesi di confine con report che usano la data finale dell'intervallo senza riallinearli.

Limiti ereditati: cataloghi non point-in-time, quotazioni rettificate, controlli osservabilità su barre complete, stop sintetici intraday, liquidità/slippage incompleti. Il controllo causale delle nuove formule non elimina questi limiti.

## Correzione interna di implementazione
Prima dell'analisi finale è stato corretto il completamento dei proxy mancanti: la lettura delle coppie mensili usa una copia immutabile degli input, per evitare che l'aggiornamento in avanti della prima coppia cancelli i successivi segnali. Tutti i conti U20C sono stati rigenerati prima dell'audit. Gli indicatori di correlazione usano anche la storia precedente al2020. Le versioni precedenti non sono risultati da interpretare.
