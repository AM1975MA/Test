# OLC38 — Verifica dei fattori europei e della leadership effettivamente prevedibile

**3 novembre 2026 · EU165 soltanto · Esito: nessuna strategia promossa · USA e `main` congelati.**

## Sintesi per la decisione

Le tre prove preregistrate (commit `3a335ab57bd38543a41c826806b7632cd4ec010b`) hanno chiarito parte della struttura europea, **senza trovare un metodo affidabile di miglioramento del portafoglio**. L'aggiunta dei fattori semiconduttori, auto e viaggi rende il clone statistico più correlato al conto Meteorite EU, ma non lo rende comparabile a parità di rischio. La selezione automatica dei due fattori più forti nei 126 giorni precedenti è **peggiore** di un portafoglio equiponderato sul successivo intervallo mensile effettivo. Le attività per una mappa storica PIT/total-return dei 165 ETF restano il vero prerequisito di un'attribuzione di alpha.

Tutti i confronti descritti di seguito sono su **Open prezzi EUR** e NAV simulati archiviati; non sono rendimenti total-return verificati né transazioni effettivamente certificabili. Sono svolti sul 2021–2024 già intensamente esplorato, NON su un holdout nuovo.

## F0/F1 — Ampliare i fattori spiega meglio il rischio, ma non permette di rivendicare alpha

I cinque ETF-strumento originali di OLC37 (EXSA, SXR8, SXRV, QDVE, EXX1) sono confrontati con un set ampliato che include EXV5 auto, EXV9 turismo/tempo libero e VVSM semiconduttori. Il set ampliato ha 7 ETF nel fit 2021, quando VVSM non ha abbastanza storia, e 8 dal 2022. Ogni gennaio la stima conosce **soltanto 252 intervalli anteriori**, ha pesi non negativi e somma <=1, usa liquidità residua e paga una commissione ipotetica fissa su mezzo turnover. Non si sceglie il fit che produce il rendimento futuro più alto.

Periodo comune **4 gennaio 2021 – 30 dicembre 2024**, 1.021 Open osservati, 1.020 intervalli.

| Indicatore | OLC19 Meteorite EU storico | Clone 5 fattori OLC37 | Clone 7/8 fattori OLC38 |
|---|---:|---:|---:|
| CAGR su 252 intervalli | **23,29%** | 14,45% | 13,26% |
| Volatilità annua | **22,63%** | 16,02% | 18,05% |
| MaxDD | −28,61% | −22,48% | −25,13% |
| Correlazione giornaliera con Meteorite | 1,000 | 0,670 | **0,708** |
| Errore RMS giornaliero contro Meteorite | — | 105,96 bp | **101,56 bp** |

Fra 2022 e 2024, su uguali intervalli osservati, la correlazione passa da circa 0,666 a 0,712 e l'errore RMS scende da circa 109,96 a 104,73 bp. Il set allargato **migliora il tracking out-of-time**, come previsto per una descrizione di stili più ampia; non migliora il CAGR. **Non si può sottrarre il 13,26% dal 23,29% e chiamare quei 10,04 punti 'alpha'.** Il clone ha volatilità molto più bassa, componenti mancanti, nessuna equivalenza certa delle distribuzioni, nessun matching degli stop o dell'esposizione complessiva. Il risultato non ha superato Gate A di qualità dati.

La presenza del settore VVSM migliora il fitting dopo la sua disponibilità effettiva. Nel 2023 il clone ampliato assegna circa 32,4% a VVSM e nel 2024 circa 30,2%, ma tali valori sono coefficienti di replica di *rendimenti passati*, non holdings certificate né consigli di acquisto.

## F2 — Che cosa deteneva concretamente il sistema europeo

Dalle **quantità realmente registrate** da OLC19 al prezzo Open archiviato, la somma dei pesi degli otto strumenti nominati e il resto delle posizioni primarie sono:

| Anno | Posizioni primarie totali / NAV | Otto ETF nominati / NAV | Altri ETF primari / NAV |
|---|---:|---:|---:|
| 2021 | 98,85% | **45,99%** | 52,86% |
| 2022 | 86,51% | **37,77%** | 48,73% |
| 2023 | 99,97% | **29,35%** | 70,62% |
| 2024 | 94,17% | **62,56%** | 31,61% |

La quota non mappata **non** significa assenza di tecnologia/USA/banche: potrebbe avere la stessa esposizione tramite altri ETF. Non si sommano queste quote alle componenti difensive per identificare un portafoglio completo. Nel 2024, le quote di **VVSM.DE + QDVE.DE rappresentano circa 53,93% del NAV** in media sulle date archiviate. La selezione tecnologica già avveniva, perciò non serve un nuovo 'bonus tech' senza verificare se il timing o il dimensionamento siano davvero prevedibili.

Le quote valutarie e le distribuzioni non sono state rielaborate; poche posizioni hanno un Open registrato non osservato, e sono segnalate nel CSV `F2_NAMED_HOLDINGS_BY_YEAR.csv`. Le percentuali sono contabili da dati sorgenti storici e non costituiscono una ricostruzione di negoziabilità intraday.

## F3 — Test del prossimo mese di trading: la leadership a 126 giorni non basta

Per ciascuna delle 48 date del segnale EU da gennaio 2021 a dicembre 2024 sono stati ordinati i **fattori realmente disponibili alla data del segnale** per rendimento sui precedenti 126 Open osservati. I due fattori primi in classifica occupano ciascuno 50% del capitale nel successivo Open OLC32, e vengono detenuti sino all'Open di uscita archivato; costo ipotetico `0.001 × mezzo-turnover` sui pesi effettivamente risultanti. Confronto predeterminato: equiponderazione fra gli stessi 7/8 fattori all'epoca disponibili, con la stessa regola di costi. Una regola causale di *benchmark*, non un componente di Meteorite.

**48/48 intervalli** sono valutabili con entrambe le aperture osservate per tutte le proxy selezionabili. I segnali non usano la futura maschera observed per scegliere. *NB: 2021 VVSM entra nel test solo dopo 126 sedute di storia*, senza backfill.

| Metrica proxy 2021–2024 | Due fattori momentum126 | Equiponderato fattori |
|---|---:|---:|
| CAGR 12 mesi | **12,29%** | **17,44%** |
| MaxDD mensile | **−36,31%** | **−22,57%** |
| Volatilità annualizzata da mesi | 21,86% | 16,68% |

La **differenza media paired Top2−EW è −37,33 punti base mensili**; bootstrap circolare in blocchi di 6 mesi, 4.000 estrazioni, seme 38001, intervallo descrittivo 95% **[−125,11; +43,20] bp/mese**. Il limite inferiore non è positivo e la media è negativa: *gate preregistrato FALLITO*. La scelta Top2 del passato coincide con 26 delle 96 posizioni tra le future Top2 (27,1%) e la correlazione media di Spearman entro il paniere fra punteggi passati e ritorni del prossimo mese è **−0,0045**.

Differenza media per anno, in bp/mese: **2021 −97,40; 2022 −35,53; 2023 −36,79; 2024 +20,38**. Il solo 2024 favorevole è una diagnosi ex-post, **non** autorizza un cambio di regime usando la conoscenza del risultato. Le date 2025–2026 sono archiviate come diagnostica e non utilizzate per scegliere una soglia o promuovere la regola.

Questi CAGR sono di **due nuovi portafogli-proxy mensili senza V6 o stop**, non del motore di Meteorite. Non sono economicamente comparabili col 23,20% originale di OLC19 e non sostituiscono il suo NAV; l'8-fattori non è un portafoglio fattoriale completamente certificato.

## Audit e blocchi rimasti

- Originali OLC19 e OLC32 controllati su SHA256; snapshot EU ridotto conserva esattamente i 5 membri necessari e ne dichiara i digest. Il codice può ricostruire lo stesso risultato dall'archivio intero o dal compatto.
- Verifica indipendente: clone 5 fattori OLC37 replicato (NAV finale <1e−9 indice di differenza), **515 label ETF–mese** controllate contro OLC32 (errore massimo 4,6e−13 bp), NAV e costi ricostruiti su 66 decisioni, 4.000 bootstrap, test di alterazione dei prezzi futuri che non cambia i segnali passati. F1 usa sempre training con data finale antecedente al 1° gennaio dell'anno valutato.
- **Gate A = FAIL:** esposizioni storiche point-in-time della totalità dei 165 ETF, TR/corporate actions/FX/hedging, prezzi d'asta bid/ask, spread reali e delisting non certificati; maschera originale delle quote USA mancante (USA non usato per OLC38). Le informazioni su indice/ISIN oggi disponibili **non** equivalgono a composizioni storiche PIT.
- I due motori USA sono originali e separati: OLC17 `ALL_PREOPEN_V6` 52,3006%, OLC19 `FAST_LOCK3` 50,7722% CAGR storico 2021–24. Nessun file di USA o `main` modificato; nessuna posizione o ordine eseguito.

## Decisione e seguito corretto

**Stop a ulteriori ottimizzazioni di soglie e momentum sullo stesso storico.** F1 spiega un po' meglio le oscillazioni, F2 identifica esposizioni già presenti, F3 falsifica la scorciatoia 'basta comprare i settori più forti negli ultimi sei mesi'. Nessuna strategia EU viene promossa, nessun intervento USA è autorizzato.

Il prossimo requisito non è l'ennesimo backtest su 2021–24: è produrre una **mappa PIT delle esposizioni economiche degli ETF realmente selezionati**, includendo l'indice replicato, currency/hedging, distribuzioni e data di validità, e poi costruire *un benchmark a esposizione, rischio ed esecuzione matched*. Solo quando un rendimento direzionale incrementale è osservabile in dati nuovi ha senso rivalutare il selettore EU.

## Riproduzione e repository

Preregistrazione [OLC38 commit `3a335ab`](https://github.com/AM1975MA/Test/commit/3a335ab57bd38543a41c826806b7632cd4ec010b), branch `research/olc38-eu-factor-tests-20261103`, `main` invariato. Vedere `README_REPRODUCE.md` per gli hash degli input e il comando offline. Risultati, figura, codice e audit nel pacchetto ZIP. Non è stata usata alcuna fonte storica di holdings esterne non certificata.
