# OLC41 — Censimento completo Acc/Dist EU165, con vincolo di storicità

**3 novembre 2026.** Solo EU165. **Nessuna conversione applicata**; USA, `main` e le configurazioni originali rimangono invariati.

## Risultati verificati del censimento
- **165/165** ticker europei censiti; **96 Acc**, **69 Dist** nelle informazioni di prodotto correnti. **153** identità ricavate provvisoriamente da un catalogo europeo a ticker base; **12** ulteriori identità riconciliate attraverso ISIN e fonti esterne per borsa. Per 153 non si dichiara una conferma issuer/venue individuale, e nessuna è una mappa constituent-level storica PIT.
- Dai ledger autentici 2021–2024: **27 ETF detenuti**, di cui **9 Dist**, coerenti con il precedente audit.
- Storicità del prezzo originale: **141/165** con almeno 500 Open positivi osservati prima del segnale **29 gennaio 2021** e almeno 1021 su 1026 date del periodo 2021–2024, con Open osservato al primo giorno 2019-02-01. **24** non superano questo filtro **di dati**, non necessariamente prova di lancio tardivo. La finestra pre-primo-segnale differisce dal 1 gennaio 2021; il dato di 500 giorni deve essere calcolato a 2021-01-29 per non escludere artificialmente i 502 Open Xetra disponibili.
- Nel catalogo attuale, **25/69** Dist hanno almeno un Acc *già presente in EU165* con nome indice normalizzato identico; **17/69** hanno un candidato Acc che supera il filtro di prezzo; soltanto **13/69** hanno anche l'ETF originale con sufficiente storia. Gli altri 12 sono **8** con soli Acc interni troppo recenti e **4** con storia originale incompleta. Gli altri **44/69** non hanno un candidato Acc *interno* dello stesso indice. Questo NON esclude soluzioni Acc esterne, che richiedono Open originali della corretta borsa e non possono essere autorizzate dal catalogo 2026.
- **Nessuna delle 13 coppie è automaticamente applicabile:** la destinazione Acc è già una riga dell'universo, e la sostituzione uno-a-uno introdurrebbe un doppione. Per evitare doppioni serve una scelta esplicita di cardinalità e un *nuovo* ricalcolo del ranking; non esiste un CAGR deducibile da questa mappa.
- Nei **9 Dist realmente detenuti**, l'unico candidato con stesso indice nominale e sufficiente storico prezzi già in EU165 rimane **IM2A.DE → EEAA.DE**. Anche questo è un ETF distinto e già incluso nell'universo, **non una classe Acc dimostrata identica PIT**.

## Fattori di rischio del catalogo
Il catalogo `albertored/etfdb` è una fonte **secondaria fotografata al 2026**, non una certificazione dell'ISIN e dell'indice alla data di ogni segnale storico. Contiene trasformazioni e nomi di share class attuali, che possono differire dal 2019–2024 (un esempio è un ticker la cui descrizione attuale risale al 2024 ma che compariva nel backtest storico). Il fatto che due ETF abbiano oggi lo stesso nome di indice non certifica un'identica storia di benchmark, replica, currency hedge, distribuzioni, TER o tracking error. Alcune denominazioni sono cambiate a seguito di fusioni tra emittenti.

Il filtro dello storico accetta esclusivamente `observed=True` e `O>0` su prezzi EU originali, non Open riempiti o sintetici. Il criterio 1021/1026 rappresenta il massimo delle sedute Xetra osservate nel periodo; per sedi con calendari differenti è prudenzialmente severo, e va aggiornato con il calendario ufficiale della sede prima di un'eventuale migrazione.

**Non applicare retroattivamente** l'ISIN moderno alle serie di prezzi vecchie senza una *corporate action / share class lineage* confermata. Serve inoltre verificare il trattamento dei dividendi: il prezzo Open non è automaticamente total-return.

## Decisione
**STOP migrazione automatica.** Mantieni le **69** righe Dist originali per ora, marcando `UNCHANGED_PENDING_VERIFICATION`. Non togliere 13 righe per proclamare un nuovo EU152, non inserire 13 Acc duplicati e non ridurre la finestra storica. Gli USA restano esclusi da qualsiasi modifica.

I prossimi dati necessari per la reale sostituzione sono: mappatura ticker–ISIN per venue e data, storico di prezzo negoziabile non riempito per i candidati Acc esterni, storico del benchmark e classe dal prospetto, distribuzioni/total-return, quantità ordini e costi. Solo dopo, su un ramo distinto, si potrà valutare un universo europeo deduplicato e rifare integralmente il backtest *senza chiamarlo stesso algoritmo*.

## File
- `results/EU165_DISTRIBUTION_POLICY_CENSUS.csv`: tutte le 165 righe; identità, politica, storia Open e evidenza.
- `results/EU69_DIST_CANDIDATE_AUDIT.csv`: tutte le 69 righe Dist; Acc interni, quantità candidati, problemi di storia e duplicazione, Acc esterni non verificati.
- `results/EU165_ORIGINAL_PRICE_MASK_AUDIT.csv` e `results/EU27_ACTUAL_HELD.csv`: ripristino controlli indipendenti dagli strumenti e dall'audit precedente.
- `results/OLC41_SUMMARY.json`, `SOURCE_MANIFEST.json`: somme, chiavi e provenienza; protocollo preregistrato al commit `ef1da10`.

**Nessun nuovo training, nessun backtest, nessun codice di produzione modificato.**
