# Frontiera USA / Europa: 1.440 replay e ricostruzione dei segnali

31 ottobre 2026. Ricerca retrospettiva; nessuna modifica a main o alla strategia operativa. Il protocollo c56f23e08870060f434b80875050fc9906d1e574 precede i risultati. Questo lotto è concluso; non si presume che processi locali continuino autonomamente.

## Risultato principale

La nuova catena CL01 produce previsioni per90mesi su90 in entrambi gli universi. Hybrid europeo ha almeno143forecast correnti per mese, Return144; gli USA149. Il precedente restringimento a5–6candidati non compare nella nuova ricostruzione. Sono stati riaddestrati tutti e due i componenti Hybrid, non soltanto Return.

La copertura non garantisce rendimento maggiore. Il solo nuovo Return con Hybrid storico porta il CAGR europeo al24,29%, ma riduce quello americano al32,89%. Rifacendo anche Hybrid e tutti i mesi, otteniamo6,17% EU e39,73% USA. Il24,29% NON è una soluzione con l'intera catena ricostruita: conserva Hybrid storico e i suoi buchi. Le sostituzioni di singoli flussi sono controprove esplicite, non versioni confuse sotto lo stesso nome.

La fusione percentile25/75 recupera crescita e drawdown rispetto alla nuova CL01 sull'intera storia, ma perde molto rendimento americano nel periodo pre2025. La nuova difesa sistemica con rientro rapido riduce il crollo2020 con un costo di crescita molto inferiore ai rimedi precedenti, ma non migliora ogni sottoperiodo. Nessuna variante è stata promossa e nessuna è esclusa solo perché un intervallo comprende zero.

## Perimetro effettivamente eseguito

- 912replay sui forecast nativi, incluse due regole di copertura, controlli ripetuti e varianti che negli USA coincidono.
- 488replay sui forecast ricostruiti, incluse sostituzioni isolate Return/Hybrid.
- 40sensibilità al ritardo di una seduta del trigger sistemico.
- 80nuovi modelli annuali principali:48Return XGBoost,16Hybrid ExtraTrees,16Hybrid XGBoost. Altri16oggetti sono imputatori di training. Le calibrazioni mensili aggiuntive non sono contate fra gli80.
- 11selettori;4regole di costruzione;6difese; pesi originali o50/50; due livelli di costo. Il fattoriale costruzione/difesa completo è applicato al selettore originale e CAL2; non è una ricerca cartesiana di tutti gli iperparametri.

Le famiglie includono modello isolato, fusione originale e percentile,25/75 e75/25, supplemento momentum, calibrazione cronologica Ridge a2e5variabili, finestra36mesi, peso esperti da esiti maturati, controllo correlazione, persistenza delle selezioni, shock sistemico con rientro50/75/100%, regime lento e cap di volatilità. Ogni configurazione è provata in entrambi i mercati. Non sono1.440campioni indipendenti e non abbiamo esaurito tutte le strategie possibili o rieseguito ogni vecchio branch.

## Verifiche

22test ereditati e10nuovi test superati. 24controlli temporali sui dati: date delle feature, maturazione annuale, perturbazioni dei prezzi futuri su8ticker per mercato, e parità dei cluster fino al2020 ricostruendo soltanto quel prefisso. I controlli a campione non sono descritti come audit completo di tutti i dati.

Quattro riferimenti nativi riprodotti esattamente, erroreNAV0.0. Tutte le1.440curve ricostruite indipendentemente dalla somma dei PnL giornalieri;37.440valori CAGR/MaxDD ricalcolati. Errori massimi3,11e-15 sul CAGR,5,00e-16 sul drawdown,8,55e-15 sull'identità contabile. Questi test verificano il contratto del simulatore, NON esecuzioni reali, dividendi o sopravvivenza dell'universo.

I file di verifica completi, hash di ogni percorso e modello, forecast, input preparati, modelli e ledger sono nei pacchetti consegnati. SUMMARY.json conserva gli aggregati verificati; i sorgenti principali sono in src/ e tests/.

## Ricostruzione CL01: cosa cambia e cosa no

Feature sulle sedute osservate di ciascun ETF, snapshot alla data decisionale mensile con ultima osservazione nota non più vecchia di5giorni. Nessun backfill precedente alla quotazione e nessun prezzo trascinato diventa eseguibile. I NaN delle formule restano NaN. Si rigenerano ranking trasversali, cluster persistenti, label e modelli, con etichette maturate prima del1gennaio dell'anno di previsione.

Non cambia soltanto dicembre: cambiano il conteggio delle sedute native, l'allineamento del benchmark per beta, l'eleggibilità dei cluster senza requisito di quotazione futura e le label su aperture osservate. Gli orizzonti rimangono sul calendario comune locale e la prima apertura successiva è ammessa entro5giorni. Le formule125rimangono legacy, inclusa la vecchia semantica downvol: non viene silenziosamente sostituito un kernel corrected125. Le categorie dei bond servono al clustering, non a chiamare un ETF obbligazionario cash.

I controlli separati sostituiscono solo Return, solo Hybrid, entrambi sulle vecchie date, poi entrambi con tutti90mesi. Il motore/rischio resta congelato. Gli innesti isolano il flusso di forecast, ma non tutta la causa interna al training. Non è corretto chiamare il calo18,26→6,17 l'effetto del solo calendario.

## Confronto comune febbraio2019–1luglio2026

Pesi originali, costi originali. USA revisione1; NON la media storica39,33% sul2017–2026. I nuovi innesti ripartono da capitale1a febbraio2019; il riferimento USA43,28% differisce lievemente dal43,27% di un conto iniziato nel2017e ritagliato. Nessun vecchio risultato è cancellato.

| Configurazione | EU CAGR | EU MaxDD | USA CAGR | USA MaxDD |
|---|---:|---:|---:|---:|
| Riferimento nativo |18,26%|-35,95%|43,28%|-30,13%|
| Solo nuovo Return, Hybrid storico |24,29%|-30,14%|32,89%|-32,49%|
| Solo nuovo Hybrid, Return storico |9,27%|-35,96%|43,26%|-29,78%|
| Entrambi rifatti, vecchie date |6,34%|-36,49%|39,73%|-29,00%|
| CL01: entrambi rifatti,90mesi |6,17%|-36,79%|39,73%|-29,00%|
| CL01: fusione percentile25/75 |11,91%|-32,92%|42,42%|-28,51%|
| CL01: capitale50/50 |11,40%|-34,34%|40,61%|-26,89%|

## Stesso confronto prima del2025

| Configurazione | EU CAGR | EU MaxDD | USA CAGR | USA MaxDD |
|---|---:|---:|---:|---:|
| Riferimento nativo |8,27%|-35,95%|39,21%|-30,13%|
| Solo nuovo Return, Hybrid storico |11,69%|-30,14%|28,20%|-27,42%|
| Solo nuovo Hybrid, Return storico |5,20%|-35,96%|41,63%|-29,78%|
| CL01 completa |4,74%|-36,79%|41,09%|-29,00%|
| CL01: fusione percentile25/75 |7,73%|-32,92%|32,60%|-28,51%|
| CL01: capitale50/50 |9,56%|-34,34%|35,37%|-26,89%|

La combinazione25/75 non viene promossa dal risultato integrale: pre2025 aiuta l'Europa ma penalizza gli USA. La calibrazione rolling36sui vecchi forecast mostra un'altra mancata trasferibilità: sull'intera finestra EU19,78% contro18,26%, ma USA15,03% contro43,27%. Le alternative restano nell'evidenza, non vengono cancellate.

## Nuova difesa sistemica con rientro rapido

Si attiva soltanto se il mercato mediano perde almeno5%in5sedute E almeno60%dei titoli è negativo sulle5sedute. Budget rischioso50%; rientro75%quando5sedute diventano positive,100%con recupero anche dellaMA20. Usa chiusure precedenti; non chiama crisi sistemica il solo ribasso del leader. Il cap include V6.

Pre2025, contro CL01 senza cap aggiuntivo:

| Mercato | CAGR base | CAGR difesa | MaxDD base | MaxDD difesa |
|---|---:|---:|---:|---:|
| EU |4,74%|4,77%|-36,79%|-32,36%|
| USA |41,09%|40,99%|-29,00%|-27,52%|

Febbraio–marzo2020: perdita EU da22,96%a14,48%; USA da5,26%a5,38%. Questi sono rendimenti della finestra, NON CAGR annualizzati. Nel2020 intero EU da-20,15%a-17,76%; USA da+53,10%a+52,90%. Il rimedio è meno distruttivo del vecchio rientro rigido, ma non elimina le perdite.

Sull'intero periodo EU il MaxDD passa invece da-36,79%a-36,92%; USA mantiene il beneficio. Quindi nessuna garanzia generalizzata. Aggiungendo persistenza della graduatoria pre2025 EU7,20%/MaxDD-33,85%, USA40,13%/-27,52%: un compromesso da conservare, non una vittoria automatica.

## Fine2021–2023: miglioramento locale non è vittoria globale

Rendimenti cumulati novembre2021–dicembre2023:

| Variante | EU rendimento | EU MaxDD | USA rendimento | USA MaxDD |
|---|---:|---:|---:|---:|
| Riferimento nativo |+10,66%|-28,66%|+99,26%|-24,05%|
| CL01 completa |+44,45%|-28,91%|+82,10%|-21,91%|
| CL01 con difesa rapida |+43,68%|-28,66%|+81,56%|-23,25%|
| CL01 persistenza+difesa |+48,45%|-25,95%|+75,69%|-21,49%|

La rigenerazione cambia favorevolmente l'episodio europeo che aveva motivato la ricerca, ma non conserva quell'effetto in tutta la storia. Nessuna regola viene ritarata scegliendo gli anni che la favoriscono.

## Perché il ranking globale non basta

Nel controllo pre2025 a candidati identici, il nuovo Hybrid EU ha rankIC medio0,081 contro0,043 del vecchio; l'excess return mensile dei Top2 scende però da circa1,00%a0,65%. Vecchio/nuovo ranking Hybrid correlano0,46EU contro0,91USA. Migliorare l'ordinamento generale non garantisce le migliori due decisioni. Sono61mesi EU e72USA; alcune label dei segnali di dicembre maturano a gennaio. Non sono rendimenti di portafoglio netti né prove di causa unica.

## Incertezza e decisione

Bootstrap mensile appaiato, stessi blocchi campionati nei due mercati,3/6mesi,10.000estrazioni seed20261031. Fractions positive sono stabilità al ricampionamento, NON posteriori o probabilità di successo futuro. Il riferimento e il periodo sono sempre espliciti. Nessun automatismo basato sull'inclusione dello zero.

R25 meno CL01, blocchi6mesi, differenziale logaritmico annuo:
- pre2025: USA-6,20pp, IC[-15,66;+2,85]; EU+2,86pp, IC[-2,34;+8,16].
- storia mensile completa fino a giugno2026: USA+1,90pp, IC[-9,88;+15,51]; EU+5,35pp, IC[+0,19;+10,46].

Il criterio descrittivo congelato di crescita migliore nel mercato peggiore a costo stressato, senza peggiorare il drawdown di nessuno, non individua una dominanza pre2025. Questo non elimina i compromessi rischio/rendimento: difesa rapida, persistenza, R25 e sostituzioneReturn restano piste distinte. I molti tentativi e il riuso della storia non vengono annullati dal doppio universo o dal bootstrap.

## Timing delle protezioni e limiti

40sensibilità ritardano di una seduta soltanto gap/breadth del trigger originale. Il riferimento EU nativo passa18,26→22,26%; USA43,27→41,82%. CL01 passa EU6,17→12,26%, USA39,73→38,26%. Non è un costo fisso: cambia il percorso. Il ritardo non viene scelto perché migliora EU e non certifica un fill live. La vecchia assunzione di osservare il gap e negoziare allo stesso Open resta un limite di ricerca.

Restano non certificati total-return/dividendi, corporate action, fondi delistati, spread, volume eseguibile e sincronizzazione intraday. Le89/90mensilità storiche già studiate non sono holdout vergini. Gli anni2025e2026sono diagnostica; il2026termina il1luglio e il suo CAGR non è rendimento dell'anno intero. cost=.001/.003 è applicato al turnover legacy, NON automaticamente10/30bp per lato. Per i confronti temporali si conserva l'etichetta decisionale del motore, con capitale valorizzato all'Open successivo e ultima osservazione piatta.

## Conservazione

Sorgenti, protocollo, sintesi e principali verificatori sono nel branch di ricerca. I pacchetti della conversazione conservano inoltre forecast, audit, tutti1.440NAV/ledger,80modelli e pannelli di training, con hash. Grandi input/binari NON sono implicitamente dichiarati caricati suGitHub. Servono i due checkpoint precedenti per riprodurre i raw; restore_dependencies.py ne controllaSHA256. Non è stato modificato main né eseguita alcuna operazione di trading.
