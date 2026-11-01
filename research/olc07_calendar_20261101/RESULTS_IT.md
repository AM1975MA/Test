# OLC-07: il vantaggio del ritardo dipende dalla fase del segnale

1 novembre 2026. Test economici conclusi; ricerca retrospettiva, nessuna promozione e nessuna modifica a main. Il salvataggio integrale storico dei checkpoint su GitHub NON è concluso.

## Contratto e verifica

Fasi predefinite: fine mese P0, cinque sedute locali prima P5, dieci prima P10. Ogni fase rigenera feature, cluster, etichette mature e modelli annuali 2019–2026, con stesse famiglie e iperparametri. Non sono vecchie previsioni semplicemente rietichettate. 240 modelli: 80 controlli P0 e 160 fit alternativi. 48 imputatori non contati come modelli.

P0 riproduce esattamente tutte le27.191 righe di previsione CL01 e12 percorsi OLC06.16oggetti di pannello/calendario identici. L'adattatore delle feature ha corretto solo lo snapshot: il sorgente esponeva soltanto fine mese, rendendo vuoti i pannelli interni al mese. Le formule e i valori originali rimangono identici alle date originali; errori e regressioni conservati.

Target HALF. IMMEDIATE cambia subito, DELAY3 mantiene per due sedute e cambia alla terza, PHASE5 completa in cinque. Budget rischio, indicatori giornalieri e target V6 congelati aP0: non è una ricostruzione completa del V6 per fase. Stesso capitale iniziale1 a febbraio2019; nessun PnL pre-start. Date effettive del successivo Open. Due costi .001/.003 nella convenzione di mezzo turnover legacy, NON automaticamente10/30bp per lato.

## CAGR e MaxDD,2021–2024, costo .001

|Fase del segnale|Esecuzione|CAGR EU|CAGR USA|MaxDD EU|MaxDD USA|
|---|---|---:|---:|---:|---:|
|Fine mese|IMMEDIATE|16,01%|35,52%|-26,43%|-20,15%|
|Fine mese|DELAY3|18,91%|38,72%|-28,60%|-20,15%|
|Fine mese|PHASE5|17,61%|37,97%|-27,23%|-20,19%|
|5sedute prima|IMMEDIATE|8,61%|15,58%|-45,75%|-33,89%|
|5sedute prima|DELAY3|10,06%|13,52%|-43,30%|-34,79%|
|5sedute prima|PHASE5|10,00%|11,52%|-43,44%|-35,20%|
|10sedute prima|IMMEDIATE|7,84%|9,43%|-36,41%|-41,40%|
|10sedute prima|DELAY3|5,01%|13,76%|-38,91%|-41,52%|
|10sedute prima|PHASE5|6,12%|11,54%|-36,83%|-42,47%|

Costi stressati, P5: CAGR EU6,67/8,12/8,07%, USA12,67/10,58/8,71%, ordine IMMEDIATE/DELAY3/PHASE5. P10: EU5,50/2,74/3,83%, USA6,49/10,64/8,51%. Non emerge un beneficio comune di ritardo o gradualità nelle fasi alternative.

Intera finestra febbraio2019–1luglio2026, P5: CAGR EU9,43/8,03/8,68%, USA25,57/28,14/25,04%. P10: EU10,27/9,25/9,51%, USA27,03/29,97/28,58%. P0 resta EU11,55/14,60/13,34%, USA40,85/45,53/46,39%. Sono rendimenti di versioni e finestre dichiarate, non sostituzioni del39,33%storico.

## Interpretazione e prossimo controllo

Il vantaggio del ritardo a fine mese resta osservato e riproducibile. Non si trasferisce però stabilmente: aP5 miglioraEU ma peggioraUSA nel2021–2024; aP10 accade il contrario. Non viene scelto un calendario diverso per mercato.

Cambiare fase cambia insieme informazioni, osservazioni del training, target e proposte; non prova da solo una stagionalità economica di fine mese o che il beneficio originario sia falso. La prova misura sensibilità della catena al calendario, con rischio/V6 congelati. Prima di un modello di urgenza, il controllo informativo utile è incrociare separatamente calendario del training e calendario della previsione, senza usare futuro. Quel confronto e il modello tempo-evento NON sono stati eseguiti in questo lotto.

Incertezza:48mesi2021–2024, blocchi appaiati3/6,6000estrazioni,seed20261101. DELAY3menoIMMEDIATE, blocchi6: P0+2,51pp log/annoEU,+2,32USA; P5+1,35EU,-1,79USA; P10-2,71EU,+3,87USA. Tutti gli intervalli attraversano zero: non è un veto automatico, ma neppure una probabilità di successo. Reimpiego dello storico e dipendenza dei mercati espliciti.

## Controlli conclusi

36portafogli(12controlli+24alternativi),67662intervalli ricostruiti da quantità/cash/Open, errore massimo NAV3,55e-15.1872metriche ricalcolate indipendentemente, errore1,67e-13.96audit annuali con maturazione e chiavi ricostruite.17test nuovi passati nell'ultimo run.8perturbazioni dei dati futuri su ticker/cutoff reali lasciano identiche le feature passate: verifiche a campione, non audit integrale dei refit.4test separati dell'uploader archivistico. Nessun processo di ricerca lasciato in esecuzione.

Revisione dell'autore, non indipendente. Limiti: universo sopravvivente, total-return/distribuzioni non certificati, calendario aggregato osservato non certificato point-in-time, quantità frazionarie, spread e fill legacy allo stessoOpen. Nessuna autorizzazione live implicita.

## GitHub: perimetro reale

I vecchi README dichiaravano parte dei sorgenti ausiliari, modelli, input e ledger negli ZIP della conversazione. Non era corretto dire che tutto fosse già suGitHub.

Ora è verificata la release research-preserved-20261101: ETF_Research_Tracked_Snapshot_20261101.zip,148447790byte,SHA25622675c4c8fcb5fde4da78192db8aa61e008b025294c476b90c2551117e210374;346blob deduplicati da12branch e vendor canonico. È una fotografia del materiale tracciato, non dei checkpoint mancanti.

Recuperati25ZIP locali,1305741864byte,8715membri contando dipendenze ripetute, CRC/SHA256verificati.3archivi coincidono byte-per-byte con file della fotografia; per22la copia integrale non è verificata in quel perimetro.361contenuti distinti di sorgenti/test/documenti non compaiono identici nella fotografia selezionata. Non è una ricerca esaustiva di qualunque ramo/revisione/asset.

Il connettore corrente non espone upload file-locali verso release; il runtime non ha GitHub CLI autenticata. L'uploader versionato richiede --upload, non sovrascrive e controlla gli hash remoti. Non dichiariamo avvenuto un upload da un semplice dry-run.

La cartella GitHub corrente conserva protocollo, decisioni tecniche e questa sintesi. I pacchetti OLC07 consegnati contengono tutti i nuovi script,modelli,pannelli,NAV e test. Il checkpoint richiede i tre parent già consegnati(OLC06,Original39EU,paired-frontier risultati), elencati per hash; non è dichiarato autonomo né automaticamente pubblicato suGitHub. I risultati scaricabili restano distinti dalla persistenza remota.
