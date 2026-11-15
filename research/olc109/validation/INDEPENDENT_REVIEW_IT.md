# OLC109 — Revisione indipendente di conti, segnali e fonti

## Esito

**PASS contabile e di conformità ai protocolli per tutti i 200 percorsi: 110 del blocco iniziale, 50 del secondo e 40 del terzo.** La correttezza del calcolo non costituisce validazione economica della strategia.

Il criterio attuale dell'utente è CAGR almeno 30%, con drawdown e Calmar descrittivi. I percorsi che raggiungono questo CAGR sono **0/200**, inclusi **0/40 nello scenario BASE**. Il migliore CAGR è **25.7526% in BASE** e **28.8205% tra tutti gli scenari**. I campi tecnici legacy che includono DD 25% e Calmar 1 vengono riconciliati senza trattarli come criterio corrente di esclusione.

I file di protocollo, il codice finanziario e i dati conservano gli hash registrati prima dei rispettivi run. Le date registrate ordinano ogni congelamento prima della relativa esecuzione e dopo l'osservazione del blocco precedente. I blocchi 2 e 3 sono adattivi dichiarati, non holdout indipendenti. Non sono stati aggiunti ulteriori casi finanziari dall'auditor.

## Cosa è stato ricostruito

- **49.055 ordini**: quantità, prezzi, notionali, costi, disponibilità Open, ordine vendite/acquisti e associazione all'ultima istruzione maturata.
- **16.925 istruzioni**, incluse **1.320 riduzioni**: il revisore deriva anche l'assenza di istruzioni nei giorni senza trigger, non controlla soltanto gli ordini esistenti.
- **3.121 target mensili/iniziali**: ranking, opportunità, pesi e filtri ricostruiti dai dati; i target finali con controllo di volatilità sono verificati sullo stato di conto ricostruito.
- **80 snapshot e 13.528 gruppi distinti**: idoneità storica, mediana del turnover a 63 sessioni includendo gli zeri, osservazione corrente, 126 rendimenti, Pearson, complete-link a 0,85, mediana dei punteggi e rappresentante più scambiato. Le 80 partizioni sono ricostruite in ciascuno dei tre blocchi.
- **11 baseline disponibili di OLC108** identiche nei file finanziari e nei vettori decisionali. Mancano nell'archivio precedente solo i 4 stress passivi; non sono classificati come confronti superati.
- **300 ISIN** e **591.000 righe uniche**: raw Close × Volume ricostruito esattamente dalle copie sorgente, con maschera V3 e verifica degli hash. Il campione comprende tutti i nomi selezionati nei target e 48 nomi deterministici di controllo per blocco.

Il revisore contabile e quello dei segnali non importano engine, core o selettori di produzione. Il clustering usa la stessa libreria standard SciPy per il complete-link, con una matrice Pearson ricostruita separatamente; questa dipendenza comune è esplicita.

## Riconciliazione

| Controllo | Peggiore differenza assoluta |
|---|---:|
| NAV o cassa | EUR 1.33e-10 |
| Costo di un ordine | EUR 1.42e-14 |
| Identità giornaliera P&L meno costi | EUR 2.55e-11 |

CAGR, valore finale, drawdown Close e Open/Close campionato, Calmar, volatilità, peggiori 21 sessioni, costi, giorni operativi, esposizione media e rendimenti annuali sono riconciliati. Le vendite e gli acquisti seguono il budget alla ricchezza Open precedente ai costi, la banda del 3%, il ticket e la scala comune di acquisto necessaria all'autofinanziamento. Nessun riempimento è ammesso senza Open valido.

## Test negativi e causalità

I sei controlli negativi sono stati respinti: quantità errata anche con cassa/NAV coerenti, commissione alterata, target cambiato senza cambiare ordini, esecuzione prima della maturazione, ritardo accorciato e identificativo di un'istruzione superata. Il conto originale non alterato è accettato.

Tre date reali — 28 febbraio 2020, 30 dicembre 2022, 30 dicembre 2024 — sono confrontate con il solo prefisso storico e con 21 sessioni future alterate pesantemente in prezzi, volume e maschere. Tutte le 40 configurazioni mantengono gli stessi 120 vettori target, gruppi e correlazioni precedenti. È un controllo comportamentale separato che importa intenzionalmente i selettori di produzione.

Per il blocco 3, si ricostruiscono separatamente i portafogli a 63/126/252 sessioni e i loro pesi di capitale. TILT conserva esattamente unione dei titoli ed esposizione del MIX; il revisore verifica anche la condizione dei tre sleeve pieni, la positività di momentum/accelerazione, il bonus diviso nelle parità e il cap target di 1/3 per gruppo e per coppia correlata sopra 0,85. La correlazione 0,85 è un filtro dentro ogni sleeve; la miscela può contenere una coppia più correlata se il peso totale della coppia resta entro 1/3. I TOP1 intenzionalmente investono fino al 100% in un solo ETF.

## Aggregazione e bootstrap indipendenti

Una verifica separata ricostruisce 16.000 rendimenti mensili e 1.400 rendimenti annuali dai DAILY, inclusi tutti i 200 risultati dell'anno 2024. Riproduce 16 confronti accoppiati e 112 contributi relativi annuali. La massima differenza sui log-rendimenti mensili è 2,54e-15; sui rendimenti annuali è zero.

Il bootstrap usa blocchi mobili circolari di 6 mesi, 10.000 repliche e seed 109 sulle differenze mensili accoppiate. Il revisore ricostruisce le repliche tramite molteplicità dei mesi. Gli intervalli descrivono la media annualizzata dei log-rendimenti relativi, non la differenza dei CAGR in punti percentuali. Tutti i 16 intervalli descrittivi al 95% includono zero; non sono corretti per le prove multiple e non convalidano come holdout le scelte adattive.

DEDUP_DUAL_TREND_OPP rispetto a DUAL21 migliora il CAGR storico di 3,3775 punti percentuali; la stima del rendimento log-relativo annualizzato è 0,027215, con intervallo descrittivo [−0,105784; +0,154132]. TILT rispetto a MIX migliora il CAGR di 0,6853 punti, con intervallo log-relativo [−0,016589; +0,034709]. MIX rispetto a HORIZON252 cambia insieme orizzonti e composizione: il confronto non isola un effetto puro della diversificazione.

Le annualità BASE di DEDUP_DUAL_TREND_OPP e DUAL21 sono rispettivamente +33,9452% e −4,8925% nel 2024; +57,1652% e +46,2702% nel 2025; −15,2983% e −17,7022% nel 2026 fino al 30 ottobre. Le verifiche e tutti i confronti sono in `BOOTSTRAP_ANALYSIS_REVIEW.json`.

## Confronto del filtro a parità di stato contabile

La diagnosi del filtro di trend è verificata su 160 intervalli, 80 BASE e 80 LAG2. Per ogni intervallo, entrambi i rami ripartono dalle unità e dalla cassa effettive di TREND_OPP alla chiusura del segnale. Un ramo mantiene il target effettivo e l'altro rimuove soltanto il filtro aggiuntivo sugli emergenti. I controfattuali non vengono concatenati e non aggiungono nuove strategie complete ai 200 percorsi.

Il revisore riproduce indipendentemente tutti i 320 rami con la propria funzione di dimensionamento degli ordini e i target già verificati, senza importare il simulatore di produzione. La massima differenza di NAV terminale è EUR 7,28e-12, quella dei costi EUR 2,84e-14. I 160 terminali del ramo effettivo coincidono esattamente con i DAILY originali. La maturazione k+1+lag, gli Open validi, i riempimenti parziali e la chiusura alla decisione successiva sono rispettati. Non si osservano riempimenti comuni anteriori alla nuova maturazione; quel ramo resta controllato per lettura del metodo, senza una ricorrenza empirica in questi intervalli.

In ciascuno scenario cambiano 40 target su 80. Nei 40 casi cambiati, BASE presenta 24 vantaggi e 16 svantaggi, media +87,2645 bp e mediana +176,0804 bp; LAG2 presenta 27 vantaggi e 13 svantaggi, media +90,1865 bp e mediana +59,9171 bp. Su tutti gli 80 intervalli, inclusi i 40 pareggi, le medie sono +43,6322 bp e +45,0933 bp e la mediana è zero in entrambi gli scenari. Un vantaggio significa rendimento maggiore del ramo senza filtro, anche se entrambi perdono: non è un conteggio di trade profittevoli.

Tutte le differenze usano lo stesso NAV iniziale effettivo come denominatore. Media e mediana non sono CAGR, contributi annuali additivi o risultati di una nuova strategia composta. Il candidato e la diagnosi sono stati scelti dopo i risultati; l'esito resta descrittivo. Evidenza completa: `MATCHED_STATE_REVIEW.json`.

## Precisione numerica del revisore

La lettura CSV usa `float_precision='round_trip'`. Un test documenta perché il parser predefinito perde un residuo di 1,82e-12 unità il 12 dicembre 2022 e ricostruisce zero sessioni differite anziché una. Con la lettura esatta si riconcilia il contatore senza modificare alcun risultato finanziario. Il conteggio delle sessioni differite dovute solo a residui numerici nei 200 conti è **1**. La soglia di posizione economica resta 1e-10 unità. Vedere `AUDITOR_PRECISION_NOTE.md` e `CSV_PRECISION_REGRESSION.json`.

## Limiti pratici emersi

Tra tutti gli scenari, **1.316/49.055 ordini** superano il 10% del controvalore giornaliero registrato; **107** superano l'intero controvalore. Nei soli casi BASE sono rispettivamente **240/9.806** e **12**. I percorsi/scenari non sono osservazioni indipendenti e questi conteggi non sono frequenze prospettiche.

Il rapporto massimo è **27.01×**: `HORIZON252__LAG1`, 2020-11-03, LU0259322260, ordine EUR 3.068,64 rispetto a EUR 113,60 registrati. La mediana del turnover a 63 sessioni non vincola il volume del giorno di esecuzione. Il volume di una singola sede può non rappresentare la liquidità totale dell'ETF, ma queste osservazioni impediscono di certificare l'ipotesi di riempimento all'Open con impatto fisso di 15 bp. Nessun denominatore di turnover degli ordini è nullo.

L'audit descrittivo copre tutti i 339.800 stati di chiusura, inclusa l'ultima sessione, e 750.564 marcature di posizioni. L'età massima di un Close detenuto è 5 giorni di calendario; le sessioni di conto con età superiore a 5 giorni sono 0. Ciò non certifica la negoziabilità contemporanea.

Le guardie TREND_REDUCE sono effettivamente sell-only. Poiché congelano anche il peso delle posizioni superstiti e l'esecuzione forzata supera la banda del 3%, possono vendere una piccola parte di un titolo superstite se il suo peso relativo sale tra segnale ed esecuzione. Non equivale a vendere esclusivamente i nomi che hanno attivato l'uscita.

Restano i limiti già dichiarati: catalogo attuale e survivorship; maschera Open che usa retrospettivamente il volume positivo della giornata completata; vintage dei fattori di aggiustamento non certificato; interesse sulla cassa nullo; imposte escluse; unità economiche frazionarie; drawdown campionato Open/Close. Nessuna verifica rende questi dati un universo storico perfettamente point-in-time o converte un test adattivo in una conferma fuori campione.

## Riproduzione

```bash
python validation/run_independent_audit.py
python validation/run_independent_audit.py --results-directory results_stage2 --output-directory validation/stage2
python validation/run_independent_audit.py --results-directory results_stage3 --output-directory validation/stage3
python validation/check_tamper_rejections.py
python validation/check_csv_precision_regression.py
python validation/check_prefix_causality.py
python validation/check_held_price_age.py
python validation/check_analysis_bootstrap.py
python validation/check_matched_state_review.py
python validation/build_audit_report.py
```

Fonti primarie dell'audit: `INDEPENDENT_QA.json`, `stage2/INDEPENDENT_QA.json`, `stage3/INDEPENDENT_QA.json`, le rispettive `INDEPENDENT_RECONSTRUCTIONS.csv`, `INDEPENDENT_GROUP_CONDITIONS.csv.gz`, `LIQUIDITY_SOURCE_CHECKS.csv`, `TRADE_PARTICIPATION.csv.gz`, `HELD_PRICE_AGE_ALL_CLOSES.csv`, `BASELINE_REPLICATION.csv`, `PREFIX_CAUSALITY.json`, `TAMPER_CONTROLS.json`, `CSV_PRECISION_REGRESSION.json` e i tre manifest di esecuzione.
