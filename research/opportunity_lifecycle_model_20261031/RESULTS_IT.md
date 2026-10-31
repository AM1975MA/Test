# OLC-01: il primo modello di rendimento residuo non migliora ancora la strategia

31 ottobre 2026. Lotto concluso; ricerca retrospettiva, nessuna strategia promossa e nessuna modifica a main.

## Risposta

La direzione approvata è stata implementata e provata: 72 modelli annuali, tre segmenti separati di rendimento, decisioni dal portafoglio effettivo e 88 simulazioni persistenti USA149/EU165. La prima implementazione non produce un miglioramento comune. Le stime di rendimento sono meno accurate della media storica nei dodici confronti pre2025 per mercato, famiglia e segmento. Conservare CL01 come generatore delle proposte recupera parte del risultato, ma non rende il filtro trasferibile.

Non si abbandona una strada perché un intervallo comprende zero. Il giudizio riguarda qualità delle previsioni, danno economico e mancata trasferibilità. Non viene dimostrata l'impossibilità generale di un modello della durata; non è attribuito un CAGR al vantaggio statico dei cambi a63sedute del precedente diagnostico.

## Implementazione effettiva

Due famiglie fisse (Ridge e HistGradientBoosting), tre teste (ingresso→21,21→42,42→63 sedute), sei fit annuali2021–2026, due mercati:72modelli salvati. Ogni testa ha una propria maschera di etichette mature prima del primo gennaio; ogni mese ha peso totale1. Ventitré feature: score CL01, variazioni dei punteggi, momentum, volatilità, drawdown passato, medie e ampiezza del mercato. Esperti CL01 congelati, non rifittati in questa campagna.

Ridge: imputazione/normalizzazione solo training, alpha20. HGB:120iterazioni,15foglie, learning_rate.05,min_samples_leaf60,l2=10,early_stoppingFalse,seed101. Nessun tuning dopo i risultati.

Le azioni usano ticker/quantità effettive alla chiusura precedente, non precedenti ticker teorici e non Open/gap/Low del giorno dell'ordine. La stima di utilità è una approssimazione di crescita logaritmica media su21/42/63sedute, con covarianza e costo del cambio. Non è una distribuzione predittiva calibrata né la soluzione del problema dinamico completo.

Prima versione limitata a due ticker principali più V6. Pesi relativi25/50/75%, budget50/100%, HOLD e cash. La sostituzione di un solo slot è parziale sul portafoglio, non un arbitrario trasferimento fra quattro o più ticker. Le protezioni originarie restano; V6 non può riempire il capitale volontariamente lasciato in cash. HOLD evita un nuovo ordine discrezionale, non tutte le operazioni obbligate dai controlli.

Il lotto iniziale ha72percorsi;16successivi, registrati in PROPOSAL_FILTER_DIAGNOSTIC.md dopo i primi risultati, conservano soltanto la proposta CL01 e fanno scegliere al modello tra proposta, vero HOLD e cash. Sono una diagnosi post-risultati, senza nuovi fit o ritocchi dei parametri.

## Confronto2021–2024

Prima decisione dei nuovi modelli: febbraio2021; gennaio conserva il riferimento.2019–2020è avvio comune, non nuova performance dei modelli. Costo0,001sulla misura legacy del turnover, non automaticamente10bp per lato. Tutte le varianti sono ripetute anche a0,003. Stesse protezioni e medesima versione per i due mercati.

| Configurazione | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| CL01 pesi originali |10,56%|-30,02%|42,90%|-21,91%|
| CL01 capitale50/50, confronto principale |15,75%|-26,47%|33,68%|-20,15%|
| HGB nuovo ranking solo21 |0,63%|-25,04%|-4,97%|-41,28%|
| HGB nuovo ranking profilo21/42/63 |4,56%|-21,59%|-0,39%|-49,35%|
| HGB profilo più HOLD/cambio/cash |3,13%|-25,11%|7,01%|-40,91%|
| HGB profilo più azioni parziali |2,99%|-27,96%|-5,19%|-49,69%|
| CL01 propone, HGB breve filtra |14,73%|-22,40%|5,83%|-43,06%|
| CL01 propone, HGB profilo filtra |3,15%|-26,27%|37,87%|-22,36%|

HGB è mostrato per illustrare i passaggi, non per nascondere Ridge. Quest'ultimo è conservato integralmente: Ridge parziale rende-7,79%EU/-20,80%USA, con MaxDD-37,56%/-70,32%. Il vecchio39,33%non è il confronto: appartiene a diversa strategia e finestra. I controlli CL01sono riprodotti esattamente; nessuna curva precedente cancellata.

Le durate fisse non risolvono il problema: bimestrale fase0CAGR16,18%EU/31,25%USA, fase1 11,93%/12,76%. Tutte le fasi2e3mesi restano nel pacchetto, senza scegliere quella favorevole a un solo mercato.

## Qualità delle previsioni, prima di ottimizzare il capitale

Rapporto fra errore quadratico medio del modello e quello della propria media storica di training. Maggiore di1significa peggiore. Sono medie prima per mese, solo esiti maturati prima del2025,46mesi per il primo segmento e45per gli altri.

| Famiglia | Segmento | Rapporto errore EU | Rapporto errore USA |
|---|---|---:|---:|
| Ridge |ingresso–21|1,121|1,039|
| Ridge |21–42|1,083|1,048|
| Ridge |42–63|1,213|1,043|
| HGB |ingresso–21|1,276|1,138|
| HGB |21–42|1,502|1,193|
| HGB |42–63|1,537|1,147|

Tutti i dodici rapporti superano1. I rankIC medi HGB europei sono circa-0,035/0,000/-0,045. Nessuna di queste statistiche dimostra assenza universale di informazione, ma questa implementazione non ha prodotto il vantaggio economico richiesto. La media storica è un controllo predittivo, non una strategia con rendimento garantito. Top2 e profilo sono verificati anche su supporto comune delle label.

## Decisioni che perdono opportunità

Controllo: HGB profilo che filtra soltanto proposte CL01. Il riferimento è disponibile ex ante, non il migliore ETF futuro.

| Mercato / mese decisionale | Azione | CL01 | Filtro |
|---|---|---:|---:|
| EU febbraio2021 |CASH|+19,77%|-0,10%|
| EU giugno2023 |CASH|+8,30%|-0,10%|
| EU dicembre2023 |CASH|+10,05%|-0,10%|
| EU giugno2024 |CASH|+8,82%|-0,10%|
| USA settembre2024 |CASH|+19,58%|+0,33%|
| USA novembre2024 |HOLD|+2,29%|-9,41%|

Al31maggio2023il portafoglioEUdetiene EXV3.DE/EL4C.DE, al30novembre2023VVSM.DE/EXV4.DE: il filtro sceglie cash in entrambi. Al31ottobre2024il portafoglioUSA mantiene PALL/KWEB e perde9,41%nel mese seguente contro+2,29%CL01. I registri includono anche le decisioni favorevoli. La tabella illustra il meccanismo, non assegna causalità generale a sei episodi scelti.

Le aggregazioni mantengono l'etichetta decisionale legacy: E[k]è capitale al successivoOpen. Non sono una contabilità di esecuzione alla chiusura di fine mese. Emergere sia uscite premature sia mantenimenti sbagliati esclude la scorciatoia di imporre maggiore durata a tutte le posizioni.

Nel2025, già esplorato, HGB breve rende-5,06%EU ma+89,72%USA: non viene scelto dal solo risultato americano. CL01half rende+25,59%/+49,45%. Il filtroprofilo su CL01nel2025rende+37,02%/+41,45%, ma nel2026parziale+14,08%/-18,18%. Sono rendimenti effettivi del periodo;2026termina al1luglio.

## Incertezza

Confronti appaiati su48mesi2021–2024, stessi blocchiUSA/EU3o6mesi,10000estrazioni,seed20261031. Ottanta righe di contrasti principali; frazioni favorevoli sono supporto al ricampionamento, NON posteriori o probabilità di profitto futuro.

Filtro HGB profilo su CL01menoCL01half, costo0,001e blocchi6mesi: EU-11,73punti logaritmici annualizzati, intervallo[-23,59;-0,91]; USA+3,07, intervallo[-27,78;+32,66]. Il solo zero non decide; il danno europeo, la scarsa previsione e la mancata trasferibilità impediscono l'adozione.

## Verifiche e limiti

Quattro baselineCL01originale/halfUSA/EU con erroreNAV0.0. Ottantotto percorsi ricostruiti indipendentemente da posizioni dopo stop e Open successivi: errore massimo3,55e-15. Ricalcolati3696valori CAGR/MaxDD/rendimento: errore massimo5,51e-14. Ottanta percorsi con controllore mantengono avvio identico fino a febbraio2021. Verificati hash e maschere mature di72modelli;8refit su dati reali con perturbazione di etichette/feature future restituiscono previsioni identiche;6prove su politiche reali non cambiano passato dopo alterazione dei futuri input.

19test nuovi passati;8diagnostici precedenti e10frontiera passati nel proprio ambito. Il tentativo di raccolta ricorsiva di tutte le copie storiche ripristinate genera431errori di import/nomi duplicati: non è dichiarata verde l'intera suite del repository. Nomi e traceback sono nel pacchetto. Revisione finale dell'autore, non indipendente.

Un bug verificato rendeva inefficace una scelta esplicita di ridimensionamento se il peso nominale rimaneva uguale nonostante il drift. Corretto con un flag di ordine discrezionale dopo test fallito; tutti88percorsi rieseguiti dopo la modifica. Non è stata fatta ritaratura economica.

Restano limiti su survivorship, total-return/dividendi, spread, liquidità e assunzione legacy gap/fill allo stessoOpen. L'utilità è un surrogato di secondo ordine, non un modello completo di tutte le future transizioni di rischio. Non sono state stimate probabilità calibrate di continuazione o di coda. Non sono state introdotte feature apprese di età della posizione. Non si certifica l'impossibilità della direzione generale lifecycle.

## Decisione e conservazione

Nessuna politica OLC-01adottata. Ora il motore confronta azioni con incumbents reali e conserva i loro effetti; manca ancora informazione affidabile sul rendimento residuo. La prossima ipotesi utile è distinguere direttamente il vantaggio di una propostaCL01 rispetto alla posizione e all'esposizione realmente detenute, anziché sottrarre previsioni assolute stimate sull'intero universo. Quella nuova ipotesi non è stata eseguita qui; deve rispettare proposte fuori campione, campioni non selezionati ex post e doppio universo. Non si risolve il problema aggiungendo una soglia favorevole al grafico.

Repository: protocollo/addendum, nucleo eseguibile di training/azioni/replay e risultati essenziali. Pacchetti conversazione: tutti i sorgenti, test, verificatori,72modelli, forecast,88NAV/ledger, decisioni e hash; checkpoint con input preparati. La copiaGitHubnon va descritta come caricamento dei grandi modelli o dell'intero materiale dei pacchetti. Main e produzione invariati.
