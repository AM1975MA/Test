# OLC27 — Classificatore della coda dei leader: risultati economici e validazione

**2 novembre 2026. Esito: NEGATIVO; nessuna promozione della strategia.** Protocollo registrato prima degli esiti al commit `b50e756831cd7b237083fabe0fe2c901ddf8597d`, controllo pre-outcome `4306b6c4d790cc0dd759c1169938c06924f67eba`. Parent economico OLC20 AUTH, nessuna modifica a `main` e nessuna operazione di trading.

## Idea e differenza rispetto a OLC25/OLC26

OLC25 ha mostrato che aggiungere direttamente la forza storica al FUSION danneggia i due portafogli. OLC26 ha scoperto informazione di ranking a lungo orizzonte ma nessuna monetizzazione del Top2. OLC27 prova un esperimento *diverso e circoscritto*: stimare l'appartenenza al decile di rendimento relativo futuro a 126 sedute, con LogisticRegression molto regolarizzata, usando il punteggio AUTH e cinque trasformazioni del momentum già congelate. L'eventuale azione è **una sola sostituzione** entro i primi cinque ETF dell'AUTH, consentita solo se miglioramento di probabilità predetta >=0,05 e distacco nel ranking AUTH <=0,05.

Tre ricette autentiche: `AUTH_ONLY` (solo FUSION, controllo), `LONG_POOL` (pooled EU/USA), `LONG_STRAT` (stessa architettura, fitting distinto EU/USA). Tre controlli `LONG_POOL_NULL27001..27003` con le etichette future rimescolate esclusivamente entro stessa data/mercato, NON strategie candidabili. Nessun parametro o soglia è stato adattato agli esiti. I modelli annuali usano soltanto etichette con maturazione a 126 sedute **strettamente anteriore** al 1° gennaio dell'anno. Il 2021 ricade su AUTH.

## Confronti economici completi — periodo principale 2021–2024

**HALF, FAST_LOCK3, costo legacy 0,001**. CAGR e MaxDD in %:

| Variante | CAGR EU165 | CAGR USA149 | Delta EU (pp) | Delta USA (pp) | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|---:|---:|
| AUTH | **23,200** | **50,772** | — | — | −28,608 | −20,226 |
| AUTH_ONLY | 23,200 | 50,772 | 0,000 | 0,000 | −28,608 | −20,226 |
| LONG_POOL | 20,992 | 45,195 | **−2,208** | **−5,577** | −28,506 | −20,226 |
| LONG_STRAT | 22,804 | 45,584 | **−0,396** | **−5,188** | **−24,046** | −20,226 |

Nessuna variante aumenta il CAGR contemporaneamente in Europa e USA; `AUTH_ONLY` produce selezioni, rendimenti e curve identici e non è alpha.

**Sensibilità al rischio e ai costi:**

| Condizione | AUTH EU / USA | POOL EU / USA | STRAT EU / USA |
|---|---|---|---|
| FAST_LOCK3 fee 0,003, CAGR | 19,884 / 42,733 | 17,730 / 37,262 | 19,466 / 37,816 |
| ALARM fee 0,001, CAGR | 22,087 / 45,507 | 19,899 / 39,823 | 21,681 / 42,089 |
| ALARM fee 0,003, CAGR | 19,712 / 41,870 | 17,561 / 36,402 | 19,281 / 38,696 |
| FULL 2019-febbraio–2026-luglio FAST_LOCK3 fee 0,001, CAGR | 19,764 / 39,484 | 17,895 / 33,678 | 20,341 / 36,873 |

La STRAT migliora il CAGR EU nella finestra **FULL** di circa +0,577 pp ma peggiora il CAGR USA di −2,611 pp: non è una prova comune e non è una nuova strategia promossa. Nel 2020 tutti i candidati sono identici ad AUTH per fallback; non è una prova di capacità di gestire il crash.

## Qualità delle probabilità e selezione Top2

Sui soli segnali 2022–2024 con target futuro disponibile, **medesime righe valide per ciascun confronto**:

| Universo | Metrica | Logistic AUTH_ONLY | LONG_POOL | LONG_STRAT |
|---|---|---:|---:|---:|
| EU165 (4.945 righe) | ROC AUC | **0,6417** | 0,6385 | 0,6113 |
| EU165 | Brier (minore è meglio) | **0,08852** | 0,08913 | 0,09034 |
| USA149 (5.364 righe) | ROC AUC | **0,7195** | 0,7132 | 0,7189 |
| USA149 | Brier | **0,08603** | 0,08676 | 0,08642 |

Il blocco di momentum non migliora la calibrazione Brier né, sulle stesse righe, la discriminazione ROC AUC contro il controllo che conosce soltanto FUSION. I valori sono storici e le finestre di target a 126 giorni si sovrappongono: le righe non costituiscono 10.000 prove indipendenti.

Sui Top2 delle 46 date EU e 48 USA con target futuro noto nel 2021–2024, la frazione di selezionati che a sei mesi risulteranno nel decile migliore è: EU AUTH 28,26%, POOL 28,26%, STRAT 29,35%; USA AUTH 28,13%, POOL 29,17%, STRAT 30,21%. La piccola crescita di questa **metrica ex post non negoziabile** non si traduce in crescita del NAV.

## Perché fallisce: diagnostica dell'orizzonte e delle decisioni

Nell'intervallo 2021–2024, POOL modifica 7 coppie EU e 9 USA; STRAT modifica 8 EU e 9 USA. Tutte le decisioni modificate dall'adapter coincidono *esattamente* con il log di sostituzione, e restano nel Top5 AUTH.

Confrontando il ticker entrante con quello escluso dall'algoritmo, su **esattamente una finestra Open di ingresso→Open dell'ingresso successivo** (lordo, senza stop/costi), emerge:

| Ricetta | Universo | Eventi con prezzi eleggibili | Differenziale O2O medio entrante−uscente | % eventi in cui entrante batte uscente |
|---|---|---:|---:|---:|
| POOL | EU | 7/7 | −1,92 pp | 42,9% |
| POOL | USA | 9/9 | −4,61 pp | 22,2% |
| STRAT | EU | 8/8 | −0,16 pp | 50,0% |
| STRAT | USA | 9/9 | −3,43 pp | 33,3% |

La classifica futura a 126 giorni del ticker entrante è invece **in media migliore** di quella dell'uscente, sia in EU sia negli USA. Questo è il disallineamento osservato: una preferenza direzionale a sei mesi non garantisce maggiore rendimento nel mese di possesso immediato. Gli importi O2O non sono una decomposizione additiva del NAV: protezioni, V6, fee e cambi di posizione alterano i percorsi successivi.

Tra i cinque ticker che AUTH giudicava migliori, la correlazione media per singola data fra **probabilità prevista** e rendimento del prossimo mese Open→Open è bassa: EU POOL 0,109 / STRAT 0,070 (AUTH 0,061 sulle stesse 33 date); USA POOL 0,039 / STRAT −0,014 (AUTH 0,136 sulle medesime 36 date). Eppure il **vero** rango futuro a 126 sedute, noto solo ex post, ha una correlazione positiva con il mese Open→Open, EU 0,446 e USA 0,306 nelle date eleggibili. Ciò non dimostra che il target lungo sia intrinsecamente errato: il modello non riesce a stimarne abbastanza bene la **coda Top5** e le poche sostituzioni sono economicamente dannose sul mese corrente.

## Costi, rischio, controlli negativi e incertezza

La STRAT migliora il MaxDD europeo 2021–2024 da −28,61 a −24,05%, ma a costo di crescita leggermente inferiore e di una marcata perdita negli USA. Il costo legacy 0,001/0,003 è la convenzione sul mezzo-turnover, **non** automaticamente 10/30 punti base per lato. In nessun contratto/costo si registra un miglioramento di CAGR comune a EU/USA.

I tre controlli negativi di training rimescolato (non scelti come candidate strategy) battono **tutti e tre** il CAGR POOL autentico sia in Europa sia negli USA nel periodo primario FAST_LOCK3 fee 0,001; uno dei tre raggiunge CAGR 25,10% EU, ma resta sotto AUTH negli USA. Tre controlli non sono un test statistico calibrato. Il risultato è comunque un avvertimento contro la pretesa di alpha informativo dell'overlay.

Bootstrap descrittivo appaiato sui 48 mesi 2021–2024, 5.000 ricampionamenti circolari a blocchi di sei mesi, differenziale annuo di log-return candidato−AUTH:

| Variante | EU differenza [IC95%] pp | USA differenza [IC95%] pp |
|---|---|---|
| POOL | −1,84 [−5,11; +0,86] | −3,76 [−11,04; +3,15] |
| STRAT | −0,33 [−4,04; +3,40] | −3,49 [−11,75; +4,27] |

Gli IC comprendono zero: **non** è un veto automatico, né una probabilità posteriore che la strategia funzioni. Non correggono la ricerca multipla storica. I CAGR negativi del lotto, le verifiche economiche e i placebo giustificano il mancato avanzamento, senza attribuire falsamente certezza a un campione ridotto.

## Integrità e limiti

- **7 procedure**, di cui 1 controllo AUTH, 3 modelli autentici (1 controllo AUTH_ONLY +2 con momentum) e 3 placebo, **56 conti** su 2 mercati ×2 rischio ×2 costo, **36 fit annuali non-AUTH**.
- **8 conti AUTH identici elemento per elemento a OLC20**, con V6 candidate-specific ricostruito senza sovrapposizioni.
- 6 test locali passati, inclusi perturbazione delle etichette future senza effetto sui fit precedenti, parità di decisioni con i log, vincolo Top5 e riproducibilità dei seed.
- Ricalcolo indipendente di 32 CAGR principali da CSV di rendimenti giornalieri con errore massimo circa **2,44×10^-15**; i placebo hanno audit del ledger ma non CSV giornalieri persistiti.
- Prezzi preparati, maschera originale osservata assente negli USA, possibili lacune di total-return/FX/delisting, spread/quantità minime e fill intraday non certificati; fonte EU richiede observed=True per i confronti O2O diagnostici.
- QDVE.DE era il miglior ticker selezionato **ex post** e non è stato usato in nessun target, filtro, feature o selezione di modello.
- Il campione 2021–2024 è stato già esplorato intensivamente. Un nuovo fit più complesso sulla stessa finestra aumenterebbe il rischio di selezione retrospettiva.

## Decisione e direzione della ricerca

**OLC27 respinto.** Il risultato più utile non è un vincitore, ma una diagnosi replicata: i segnali lunghi sono insufficienti a migliorare i Top2, e l'evento di leadership a sei mesi non ottimizza automaticamente il rendimento del **prossimo periodo Open→Open**, che determina la contabilità del portafoglio. Evitare altri tuning a posteriori di `C`, gap di probabilità, gap di punteggio o shortlist sulla stessa storia.

Il prossimo controllo dovrebbe essere un confronto **allineato al payoff e al timing reali** (ad esempio completando OLC24 con target economico Open→Open e audit di maturazione), con attenzione alla discrepanza di regime e alla reale disponibilità di quote, e infine una finestra realmente prospettica. Un altro classificatore senza una nuova evidenza non è automaticamente un progresso.

## File verificabili

Nel pacchetto risultati: sorgenti `src/run_olc27.py`, `src/verify_olc27.py`, `src/diagnose_horizons.py`, test `tests/test_tail.py`, `VERIFICATION.json`, metriche `results/PRIMARY_MATCHED.csv`, `TAIL_PROBABILITY_QUALITY.csv`, `TOP2_DIAGNOSTICS.csv`, `PAIRED_BOOTSTRAP.csv`, `INDEPENDENT_CAGR_CHECK.csv`, `SWAP_OPEN_TO_OPEN_DIAGNOSTIC.csv`, `TOP5_126VSO2O_MONTHLY.csv`, tutte le scorecard e curve autentiche. Non comprende tutti i file parent OLC20/OLC26; i percorsi upstream e gli hash sono documentati nel repository GitHub e nella Library persistita.
