# Attribuzione descrittiva dei percorsi archiviati

Analisi dei sei percorsi esistenti BASE e BUDGET300, download r1/r2/r3. Nessun fit, download prezzi o backtest eseguito. `attribute_existing_paths.py` riusa le validazioni di `summarize_replay.py`; produce `ATTRIBUTION.json` e CSV giornalieri, mensili e per tuple di selezioni. Input identificati con SHA256 nel JSON. Esecuzione dal repository con il Python locale già indicato, passando il percorso dello script.

Calendario identico: **2366 sedute, 2017-02-01–2026-07-01**, nessuna esclusione. Schema NPZ: dates, equity, turnover, d1, d2, weight1, margin, alt_idx; CSV leader: date, top1, top2. Le metriche ricalcolate dall'equity coincidono con i RESULT archiviati entro 1e−12. Non viene ricomputata la strategia.

Timing verificato leggendo `vendor/p45/v2_stage19_kernel.py:160–215` e il salvataggio nel confronto canonico: E[k] marca al successivo open O[k+1], dopo esecuzione dei target d1/d2[k] a O[k] e stop durante k. I CSV leader derivano dagli stessi indici: nessun ulteriore lag. La data etichetta l'inizio dell'intervallo, non la valorizzazione finale. L'ultima riga ripete il mark terminale, ha rendimento zero e indici −1 (il ticker CSV finale è spurio): conservarla mantiene il calendario canonico, senza contributo economico. Verificata la corrispondenza indice–ticker nei sei percorsi.

Per ogni giorno si calcola `log(equity_t/equity_precedente)`, con patrimonio iniziale 1. Il gap BASE−300 si somma esattamente nel tempo; partizioni mensili e per selezioni riconciliano entro 1e−12. Il rapporto finale dei patrimoni riconcilia con l'esponenziale del gap. Le percentuali seguenti riguardano il **gap logaritmico**, non punti percentuali di CAGR.

| Download | CAGR BASE | CAGR300 | Gap logwealth | Top1 diversi | Coppia ordinata diversa |
|---|---:|---:|---:|---:|---:|
| r1 |29.75%|22.34%|0.552247|59.26%|84.23%|
| r2 |30.84%|20.29%|0.789204|56.80%|84.95%|
| r3 |34.68%|21.64%|0.956230|55.45%|84.62%|

Due mesi incidono in tutte le acquisizioni:

- **Febbraio 2024**: gap +0.204013/+0.204096/+0.140367. BASE seleziona HACK–IGV nei primi due download, HACK–XLK nel terzo; 300 seleziona UNG–DBO.
- **Dicembre 2025**: +0.147704/+0.195855/+0.206658. BASE: ARGT–PPLT, PPLT–ARGT, PPLT–KRE; 300: USO–BNO in tutti e tre.
- **Ottobre 2025** compensa in direzione opposta: circa −0.162 in ogni download.

I cinque mesi con gap positivo maggiore sommano 0.697657/0.755452/0.716861: **126.33%/95.72%/74.97% del gap netto**, ma soltanto 31.62%/33.40%/29.71% della massa mensile positiva. Superare il 100% indica compensazioni negative; non significa che cinque mesi costituiscano tutto il fenomeno.

Le maggiori singole sedute positive sono 2026-01-29 per r1 (+0.099628; BASE KRE–GLD, 300 GLD–PPLT) e r2 (+0.077897; BASE GLD–KBE, 300 GLD–PPLT); 2022-08-05 per r3 (+0.063755; BASE XBI–FDN, 300 USL–UNG).

Tra download, il disaccordo Top1 su almeno una acquisizione scende da **43.03% BASE a 23.12%300**; coppia ordinata da 76.58% a 51.56%. La maggiore stabilità non preserva il rendimento.

Un controllo decisivo: BASE r3−r1 guadagna 0.349678 logwealth; **0.334508 (95.66%)** si accumula sulle 802 sedute con identica coppia ordinata. Cambiare leader non è quindi una spiegazione sufficiente della dispersione. Anche a selezioni uguali possono differire pesi, input di rendimento e altri stati: questa analisi non ne identifica la causa.

Di quelle 802 sedute, le **572 con weight1 diverso** contribuiscono +0.334059; le 230 con coppia, peso e alternate-index uguali soltanto +0.000449. È una localizzazione osservazionale forte, non un controfattuale sul peso. La componente esplicita costo rebalance, somma di `log(1−0.001*turnover)`, vale −0.002700 nel confronto BASE r3−r1; BASE−300 r1/r2/r3: −0.003321/+0.002244/−0.004068. Non comprende fee degli stop, slippage né effetti indiretti dei costi sugli stati. Gross effettivo, quantità detenute, fill degli stop e rendimenti individuali non sono salvati nel NPZ: la scomposizione causale completa richiederebbe ulteriori artefatti o nuova simulazione, esclusa qui.

Esiste già un controfattuale più informativo: `forensics_v1/results/EXECUTION_ABLATION.json`, run **37149788452**, congela insieme d1/d2/weight1/alt_idx di r2 e li esegue sui tre raw. Lo span CAGR scende da **4.92363133 pp** nativi a **0.00002197899 pp**, identico con rischio r2 congelato o rischio destinazione. Non è stato rieseguito. È coerente con un'origine upstream della dispersione BASE, piuttosto che prezzi/esecuzione downstream; congelando congiuntamente più decisioni **non isola l'effetto del peso**. Non estende automaticamente la conclusione al divario BASE–300. Hash dell'artefatto incluso nello script di attribuzione.

L'attribuzione ai ticker è una partizione per **tuple osservate di selezioni**, non P&L individuale né causalità. Mancano qui rendimenti giornalieri per costituente; feature parquet non lette, ambiente locale senza pyarrow. Non si deducono effetti del solver, revisioni prezzi o segnali specifici. Confronto con audit solver: il problema numerico sintetico non attribuisce il CAGR reale. Sedute mensili correlate, tre acquisizioni dello stesso mercato: questa è diagnostica retrospettiva, **non test statistico né autorizzazione alla promozione**.
