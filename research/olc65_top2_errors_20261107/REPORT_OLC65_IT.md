# OLC65 — Diagnosi degli errori di scoperta, ordinamento e persistenza Top2

**Data:** 7 novembre 2026  
**Stato:** RICERCA / NESSUNA PROMOZIONE. Non è stato modificato OLC19 né il ramo `main`, non sono stati addestrati nuovi modelli e non è stato eseguito alcun nuovo backtest di trading.  
**Ipotesi guida:** prima di sostituire la fusione originale, capire quale parte del processo di selezione genera gli errori più importanti.

## Risultato decisivo

I due tipi di errore sono entrambi materialmente presenti, ma **la maggiore parte del divario teorico di rendimento rispetto ai due migliori ETF futuri è recuperabile, a posteriori, riorganizzando candidati che la fusione aveva già incluso nel proprio Top10**: **60,53% Europa; 56,69% USA**, 2021–2024. Questo *non* significa che quel valore possa essere previsto o monetizzato. Tra le opportunità Top2 future *non* incluse nel Top10 della fusione, inoltre, soltanto **11 su 61 EU** e **27 su 67 USA** compaiono nel Top10 di almeno uno dei componenti originari: la fusione non è l'unica causa degli errori, esistono problemi a monte della selezione dei candidati.

La debole persistenza dei Top2 selezionati è più spesso dovuta a **mancata leadership iniziale** che alla perdita di una leadership già raggiunta: il 57,3% delle posizioni EU e il 59,4% USA non entra nel miglior quintile già a 21 sedute; la quota che ci entra a 21 ma non a 42 è rispettivamente 9,4% e 16,7%.

## Input, supporto e riconciliazioni

- Universi **EU165** e **USA149** originali, medesimi score, calendari e supporto dell'engine OLC19.
- MAIN **48 segnali mensili per mercato, gennaio 2021–dicembre 2024**, 96 *slot* Top2-oracle per mercato; LATE **2025** solo diagnostico: 10 mesi EU (aprile e maggio 2025 esclusi per etichette future incomplete) e 12 mesi USA.
- FUSION originale `0,475*RETURN + 0,525*SMOOTH`, dove `CURRENT=0,6*rank(ET)+0,4*rank(XGB)` e la memoria temporale SMOOTH resta quella nativa, con normalizzazione originale sui mancanti.
- I tre ZIP originari OLC14/16/19, il pannello OLC61 e il ricostruttore OLC63 sono SHA256-verificati; **180/180 decisioni originali OLC19** coincidono, errore massimo sugli score `2,22e−16`, confronto indipendente coi rendimenti di OLC63 errore massimo `<1e−16`.
- **118 market-month validi**, **472 eventi Oracle Top2** (21 e 42 sedute) ricostruiti indipendentemente; **17.769** ETF-month completi. Nessun futuro entra nel ranking in data t. Indipendent QA `PASS`.

## 1. Dove si perde il margine economico teorico?

Per ogni market-month calcolo, sui rendimenti futuri Open→Open, la coppia effettiva della FUSION, la *migliore coppia ex post* fra gli ETF del suo Top10 e la *migliore coppia ex post* fra tutti gli eleggibili. La differenza è sempre non negativa e si separa esattamente in **ordering gap + discovery gap**. Sono *upper bound con conoscenza del futuro*, non alpha realizzabile e non differenze di CAGR.

| Orizzonte 21 sedute, media 2021–2024 | EU | USA |
|---|---:|---:|
| Top2 realmente selezionati dalla FUSION | +2,131% | +3,501% |
| Oracle migliore coppia *dentro* il Top10 | +6,244% | +11,255% |
| Oracle migliore coppia nell'intero universo | +8,926% | +17,179% |
| **Ordering gap (nel Top10)** | **4,113 punti percentuali** | **7,754 pp** |
| **Discovery gap (fuori Top10)** | **2,682 pp** | **5,924 pp** |
| Ordering / total gap | **60,53%** | **56,69%** |

Anche a 42 sedute l'ordering gap supera il discovery gap nell'aggregato: EU **5,455 vs 4,311 pp**, USA **11,455 vs 8,382 pp**. Il gap teorico complessivo non è un obiettivo additivo da minimizzare indiscriminatamente: l'oracolo conosce il futuro e i rendimenti sono estremamente variabili tra ETF.

Il confronto è descrittivamente stabile per annualità: ordering maggiore di discovery **4/4 anni EU e 3/4 anni USA**. In un bootstrap circolare a blocchi di sei mesi (5.000 repliche, **analisi post-risultato**, intervallo descrittivo condizionato): quota del gap 21d attribuita a ordering EU **[54,58%; 66,98%]**, USA **[51,28%; 62,16%]**. Il gap totale non è dominato da tre singoli mesi: i tre mesi con gap maggiore rappresentano **13,45% EU** e **12,96% USA** del gap cumulato 2021–2024.

## 2. Quanti leader futuri intercettiamo davvero?

Un evento è uno dei **due** ETF che avranno il massimo rendimento futuro reale a 21 sedute in ciascuno dei 48 segnali/mercato. Quindi sono 96 eventi per mercato. La classificazione è esclusiva:

| Collocazione a t dei futuri Top2 a 21 giorni | EU su 96 | USA su 96 |
|---|---:|---:|
| Già nei Top2 originali | 10 (10,4%) | 9 (9,4%) |
| Nel Top10 ma non Top2 — **ORDERING** | 25 (26,0%) | 20 (20,8%) |
| Fuori Top10 — **DISCOVERY** | 61 (63,5%) | 67 (69,8%) |

La copertura Top10 dei *due futuri migliori* è EU **36,5%**, USA **30,2%**. Il tasso di coincidenza esatta con i due futuri migliori è molto basso, ma questa è una misura severa su ordini estremi, con rumore elevato: non significa che i Top2 attuali non abbiano qualità relativa, come dimostra la loro performance storica contro la media dell'universo.

Sui casi DISCOVERY, il rango mediano FUSION è **38 EU** e **30 USA**. In EU **20/61** opportunità sono oltre il rango 50; negli USA **17/67**. Non sono soltanto candidati 11°–12° appena fuori dalla shortlist.

## 3. Gli specialisti avevano già segnalato i leader mancanti?

Tra i futuri migliori a 21 sedute che non erano entrati nel Top10 FUSION:

| Visibilità ex ante nel Top10 singolo componente | EU su 61 mancati | USA su 67 mancati |
|---|---:|---:|
| RETURN | 2 | **19** |
| ET | 6 | 5 |
| XGB | 3 | 5 |
| CURRENT ET/XGB | 4 | 2 |
| SMOOTH con memoria | 7 | 3 |
| **Almeno un componente** | **11 (18,0%)** | **27 (40,3%)** |
| **Nessuno dei cinque** | **50 (82,0%)** | **40 (59,7%)** |

I componenti non sono indipendenti: perciò non si sommano le singole righe. Dire che il leader è *invisibile nel Top10* NON significa che le 42 feature originarie non contengano alcuna informazione predittiva, ma soltanto che i cinque score già addestrati non lo riconoscono tra i primi dieci. È un indizio di problema **di rappresentazione/apprendimento upstream**, non soltanto di pesatura nella fusione.

Le ablazioni del singolo componente, mantenendo fissi gli altri e i pesi originali, riportano alcuni mancati leader nel Top10 (ad es. rimozione RETURN: 7/61 EU; rimozione ET: 9/67 USA). Tali rientri sono sensitività del ranking e NON contributi causali o una ricetta operativa per cambiare pesi.

## 4. Persistenza dei Top2 scelti

Per ogni ETF selezionato dalla fusione originale, il label di leadership è l'appartenenza al **miglior 20% del mercato per rendimento relativo futuro**.

| Fenotipo posizione Top2, 2021–2024 | EU | USA |
|---|---:|---:|
| Leader sia a 21 sia a 42 sedute | 33,33% | 23,96% |
| Leader a 21 ma non a 42 | 9,38% | 16,67% |
| **Non nel quintile migliore già a 21 sedute** | **57,29%** | **59,38%** |
| Seconda finestra 21→42 sotto la mediana cross-sectional | 39,58% | 59,38% |

Il label a 42 sedute è cumulativo, mentre l'ultima riga considera esplicitamente il **periodo disgiunto 21→42**. Sono due modi diversi di definire "persistenza" e non vanno confusi. La misura si riferisce a qualità relativa, non a P&L negativo: un ETF può salire senza entrare nel quintile migliore. **La priorità rimane la qualità della selezione iniziale.**

## 5. Possiamo diagnosticare gli errori prima della decisione?

Sono state valutate quattro metriche ex ante già determinate nel protocollo: margine score fra posizioni 2–3, margine 10–11, discordanza RETURN/CURRENT e discordanza ET/XGB. La correlazione Spearman mensile con i gap futuri è principalmente debole e non trasferibile fra i mercati.

Esempio più evidente, discordanza RETURN/CURRENT vs gap DISCOVERY a 21 sedute:

- **EU:** Spearman **−0,305**, CI95% descrittivo blocchi 6 mesi **[−0,495; −0,098]**.
- **USA:** Spearman **+0,254**, CI95% **[−0,041; +0,529]**.

Il segno cambia e i test sono numerosi, sullo stesso storico già ripetutamente analizzato. **Non introdurre un gate a soglia**, né interpretare l'intervallo EU non attraversante zero come validazione, vista la molteplicità delle ipotesi. Il controllo produce una diagnosi, non una nuova previsione affidabile.

## 6. Il 2025 è un controllo descrittivo, non un holdout

EU 10 mesi valutabili: media Top2 21d **+0,36%**, gap ordering **5,13 pp**, discovery **4,15 pp**. USA 12 mesi: media Top2 **+2,00%**, ordering **14,56 pp**, discovery **3,48 pp**. L'importanza relativa delle due componenti cambia nel tempo, in particolare nel 2025 USA. Le date sono state ripetutamente esaminate nei precedenti OLC: **non usare questi dati per scegliere un peso nuovo**.

## Decisione e successiva linea di ricerca

**OLC65 completato, diagnostica validata, nessuna strategia promossa.** I risultati supportano una separazione *concettuale* di due problemi upstream:

1. **Discoverability:** circa 60–82% dei futuri leader completamente mancati non compare nel Top10 di nessuno degli score originari. Per studiarli serve verificare quali pattern nelle 42 feature e nelle relazioni cross-sectional erano disponibili *a t*, senza privilegiare a posteriori specifici ETF.
2. **Ranking economico dei candidati:** il Top10 nasconde, ex post, la quota più grande del gap teorico. Occorre una funzione di apprendimento e una rappresentazione che misurino direttamente l'affidabilità delle opportunità di testa, invece di aggiungere una correzione sullo score già fuso.

**OLC66 proposto, non eseguito qui:** audit della separabilità *out-of-time* dei casi DISCOVERY e ORDERING, con gruppi interi maturati al cutoff e baseline richiamata esattamente; poi eventualmente un'architettura upstream con due obiettivi congiunti (qualità della shortlist e priorità Top2) validata su date realmente nuove. Non scegliere metodi, pesi o iperparametri in base alle performance 2019–2026. Nessuna modifica alla strategia prima di quel passaggio.

## Limitazioni materiali e tracciabilità

- Gli *oracoli* selezionano con conoscenza del futuro; i divari non sono alpha realizzabile. Nessun costo/stop/reinvestimento/gestione del rischio e **nessun CAGR** nuovo.
- Il campione è stato ampiamente ricercato: bootstrap e stabilità annuale NON ristabiliscono l'indipendenza fuori campione. Nessuna correzione per tutta la ricerca multipla OLC.
- Etichette 21/42 sovrapposte, dati prezzi adjusted e convenzioni multi-borsa, potenziale survivorship/universo storico non-PIT, USA priva di maschera prezzi originariamente osservati, Europa con alcune date non osservate, quote/spread/fill non certificati. Nessun nuovo download dati.
- Output principali: `OLC65_MONTHLY_GAPS.csv`, `OLC65_ORACLE_TOP2_CLASSIFICATION.csv`, `OLC65_SELECTED_PERSISTENCE.csv`, `OLC65_EXPERT_VISIBILITY.csv`, `OLC65_EXANTE_ASSOCIATIONS.csv`, `OLC65_FROZEN_SCORE_AND_OUTCOMES.csv.gz`, file annuali/QA/robustezza.
- Programmi: `run_olc65.py`, `verify_olc65_independent.py`, `analyze_robustness.py`; il ricostruttore originale OLC63 viene copiato byte-identico e verificato. SHA256 sorgenti e checkpoint salvati nel QA.
- Protocollo registrato su GitHub **prima** del run OLC65: branch `research/olc65-top2-error-taxonomy-20261107`, primo commit `1c115c71315f0af45eae6ed96e371877c93fbdda`.