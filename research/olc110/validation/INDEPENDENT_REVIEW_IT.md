# OLC110 — Revisione indipendente di conti, decisioni e causalità

## Esito

**PASS su tutti i 78 percorsi dichiarati**, senza discrepanze finanziarie materiali. Sono comprese tutte le 13 configurazioni e i sei scenari, incluso NEXT_CLOSE. I cinque conti BASE corrispondenti agli scenari precedenti replicano OLC109 senza differenze nelle tabelle giornaliere, negli ordini e negli array delle decisioni. Gli 80 target mensili del selettore originale sono ricostruiti esattamente dalle serie storiche.

Il giudizio riguarda la conformità dell'implementazione al protocollo congelato, la contabilità e le verifiche di causalità eseguite. Non dimostra efficacia economica futura e non certifica i limiti point-in-time delle fonti.

## Evidenza quantitativa

| Verifica | Copertura | Esito |
| --- | ---: | --- |
| Percorsi completi | 78 / 78 | PASS |
| Ordini ridimensionati indipendentemente | 32.533 | Differenza zero in quantità, prezzo, controvalore e costo |
| Istruzioni ricalcolate dai prezzi e dal conto | 20.810 | PASS |
| Selezioni iniziali/programmate ricostruite | 7.848 | PASS |
| Righe giornaliere dello stato dei posti | 183.492 | PASS |
| Maschere delle azioni mirate | 12.962 | PASS |
| Tentativi di esecuzione mirata | 13.020 | PASS |
| Controlli sulle quantità fuori maschera | 27.275.452 | Nessuna modifica |
| Date effettive degli ordini | 32.533 | Nessun anticipo rispetto al segnale e al ritardo |
| Righe annuali | 546 | Tutti gli anni 2020–2026, incluso il 2024 |
| Segmenti descrittivi | 312 | Tutti i quattro segmenti per ogni percorso |
| Repliche BASE OLC109 | 5 / 5 | Differenza massima zero |
| Perturbazioni del futuro | 78 confronti | Tutti invarianti |
| Casi letterali della reference | 10 | PASS |
| Alterazioni materiali deliberate | 10 | Tutte respinte |

La differenza massima di NAV e cash è **EUR 0**. Il residuo massimo dell'identità di autofinanziamento è EUR 1,4552 × 10⁻¹¹; quello dell'attribuzione giornaliera del P&L è EUR 2,5466 × 10⁻¹¹. Sono residui numerici dell'aritmetica in virgola mobile.

Le quantità di controlli sopra sommano i percorsi: non rappresentano eventi di mercato indipendenti né aumentano la dimensione economica del campione.

## Architettura dell'audit

`signal_reference.py` ricostruisce i Close causali riportati, i log-rendimenti, le medie, i massimi precedenti, sigma21, la liquidità mediana a 63 sedute, l'ammissibilità, i percentili e il selettore DEDUP_DUAL_TREND_OPP. La correlazione è calcolata dai 126 rendimenti disponibili alla data del segnale. Il codice dei percentili usa la definizione del rango medio con gestione dei pareggi, separatamente dalla funzione di ranking produttiva.

`policy_reference.py` implementa autonomamente i due posti e gli stati NORMAL/CASH/REBOUND. Ricostruisce la scelta mensile, il mantenimento dello stato per ETF, le uscite, la liquidazione effettiva, la conferma persistente della vacancy, i rientri, il probe dopo l'acquisto e le opportunità FRESH. Non legge i target salvati per decidere il comportamento atteso.

`account_reference.py` mantiene il conto, la coda e l'istruzione pendente. A ogni Close ricava l'azione dalla reference, ne confronta intenzione nominale, maschera, target eseguibile e metadati; alla quotazione successiva ricava vendite, acquisti, costi e finanziamento. Prezzi fuori maschera continuano a valorizzare il patrimonio, ma non autorizzano ordini e non rinviano l'azione mirata. Le quantità fuori maschera devono restare esattamente uguali.

Le tre reference e il runner importano soltanto librerie numeriche/standard e i moduli locali di validazione. Non importano engine, protection, dedup_selectors, cluster_selectors, signals o core di produzione. Il controllo AST e gli hash dei file sono in VALIDATION_CODE_HASHES.json. Le convenzioni numeriche di base sono adattate dalle precedenti reference indipendenti OLC109; non esiste una dipendenza runtime da quel codice.

## Proprietà dello stato effettivamente esercitate

La ricostruzione verifica che un desiderio CASH non equivalga a una vendita completata. Sono state riconosciute 7.384 conferme di vacancy effettiva e 2.766 occasioni di ammissione bloccate da una liquidazione non ancora confermata. Il calendario mensile ha conservato 1.040 stati CASH e 316 stati REBOUND di ETF mantenuti. I nuovi ingressi mensili bloccati dalla protezione sono stati 552.

Sono state identificate 2.740 prime esecuzioni effettive di probe. Le 1.497 promozioni a NORMAL rispettano una chiusura strettamente successiva al primo acquisto; 1.755 occasioni di conferma prematura sono state soppresse. I cambiamenti desiderati avvenuti con libro occupato hanno prodotto 882 soppressioni di azioni inframensili, preservando il recupero della differenza residua quando il libro si libera.

Le opportunità FRESH entrano a metà posto: 1.265 ammissioni ricostruite. Sono stati verificati 1.695 confronti di correlazione, con 617 esclusioni per correlazione e 340 esclusioni di ETF già detenuti o assegnati. Il caso limite in cui l'ETF base è passato all'altro posto non si manifesta come nuova ammissione FRESH nei dati osservati; è coperto dai casi sintetici separati, insieme alla priorità mensile del proprietario attivo.

## Prezzi, ritardi e NEXT_CLOSE

Ogni ordine usa la quotazione accettata alla data effettiva. L'indice di esecuzione deve essere almeno `signal_idx + 1 + lag`; la maturazione segue l'istruzione più recente divenuta eleggibile. Le vendite precedono gli acquisti, ogni ordine paga il costo dichiarato e l'acquisto aggregato non eccede il cash disponibile dopo vendite e commissioni.

Nei cinque scenari OPEN il prezzo è l'Open osservato e accettato. In NEXT_CLOSE il prezzo è invece il Close osservato e accettato. La sequenza denominata nav_open in questo scenario è verificata come patrimonio al Close prima dei costi. Il drawdown campionato è quindi fra Close prima/dopo i costi; non misura un percorso intraday.

## Causalità dei prefissi

Il test comportamentale separato `check_prefix_causality.py` importa intenzionalmente la produzione per sfidarla; non è usato come oracolo della ricostruzione indipendente. Per ciascuna data 30 dicembre 2021, 30 dicembre 2024 e 30 giugno 2026 altera drasticamente prezzi, maschere di osservazione e liquidità strettamente successivi alla data. Confronta istruzioni, conti delle decisioni, ordini eseguiti, NAV/cash giornalieri e tracce degli stati fino alla data, inclusa la decisione del Close.

Tutti i 13 bracci sono controllati sia con Open e due sedute extra di ritardo sia con NEXT_CLOSE: **78 coppie di confronti**, tutte identiche. Si tratta di verifiche finite, non di una dimostrazione formale per ogni possibile input.

## Precisione, prove negative e limiti

Dopo il controllo indipendente del dimensionamento, il conto registra le esatte quantità e i controvalori serializzati degli ordini; le commissioni e la valorizzazione sono ricalcolate. Questa scelta conserva gli zeri e i residui numerici del libro congelato, senza assumere corretti target o stati salvati. Una catena aritmetica completamente separata aveva prodotto 5,68 × 10⁻¹⁴ unità residue invece di zero: la diagnosi e la ragione della convenzione sono documentate in AUDITOR_PRECISION_NOTE.md e NUMERICAL_RESIDUE_DIAGNOSTIC.json. Nessun finanziario è stato modificato per questo motivo.

Le dieci prove negative alterano soltanto copie in memoria: target nominale, target eseguibile, maschera, stato del posto, prima esecuzione del probe, stato del libro, quantità, commissione, data anticipata e cash. Ogni alterazione materiale è respinta. I risultati congelati non sono modificati.

L'audit non certifica survivorship, vintage degli aggiustamenti, disponibilità point-in-time del catalogo o qualità originaria dei prezzi. Non certifica liquidabilità effettiva, slippage realizzato, capienza o esecuzione sul mercato. Le verifiche sulle fonti e sulla partecipazione sono curate separatamente in validation/source_execution/. Nessun risultato va presentato come holdout incontaminato, dato che il periodo e le strategie precedenti sono già stati osservati.

## Riproduzione

Dalla directory OLC110, con le dipendenze numpy, pandas e threadpoolctl disponibili:

```bash
python validation/run_independent_audit.py .
python validation/check_prefix_causality.py
python validation/check_tamper_rejections.py
python validation/check_aggregate_tables.py
python -m unittest discover -s validation -p 'test_independent_reference.py' -v
```

L'esecuzione richiede i prezzi, la liquidità e tutti i risultati congelati presenti. Il runner verifica gli hash del protocollo, della produzione e degli input prima della ricostruzione. I prospetti principali sono INDEPENDENT_QA.json, INDEPENDENT_RECONSTRUCTIONS.csv, INDEPENDENT_ANNUAL_RETURNS.csv, HOLDINGS_PNL_ATTRIBUTION.csv, BASELINE_REPLICATION.csv, PREFIX_CAUSALITY.json, TAMPER_REJECTIONS.json e AGGREGATE_TABLE_QA.json.
