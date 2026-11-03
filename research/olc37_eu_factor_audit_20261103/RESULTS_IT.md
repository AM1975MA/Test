# OLC37 — Audit PIT/TR e screening fattoriale della strategia europea

**3 novembre 2026 — Ricerca EU165, solo diagnostica. Nessun nuovo predittore, nessun trade, `main` e USA149 invariati.**

## Decisione

**Gate A dati: INCOMPLETO / BLOCCANTE per dichiarare alpha o promuovere cambiamenti.** I due checkpoint storici hanno SHA-256 corretti e la contabilità OLC19 è stata riconciliata esattamente, ma restano non certificati le esposizioni storiche point-in-time dei 165 ETF (ISIN/share-class/indice/valuta/hedge), total-return/distribuzioni/corporate actions, reali prezzi d'asta eseguibili, spread e dato delistati. Gli ETF quotati in EUR non hanno necessariamente sottostante europeo e il solo rapporto tra prezzi non misura un premio economico fattorialmente neutrale. Questo è il **risultato operativo**: nessuna nuova strategia può essere validata oggi con pretesa di vera alpha settoriale.

**Risultato sostanziale:** il conto europeo aveva già esposizioni importanti a semiconduttori nel 2022–2024. Il suo limite non è semplicemente l'assenza di un bonus al momentum o del settore tecnologico in shortlist. Occorre distinguere (i) esposizione a fattori che già genera crescita, (ii) tempistica e dimensione delle allocazioni, (iii) premio netto specifico della selezione ETF rispetto a benchmark a pari fattori **prima** di intervenire sul ranking.

## Provenienza e accuratezza contabile

- OLC19 checkpoint `OLC19_Rischio_Rientro_Checkpoint_20261102.zip`: SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`.
- OLC32 `OLC32_RESULTS.zip`: SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d`.
- Congelamento prima delle nuove metriche: `PROTOCOL_PRE_METRICS.md`, commit `65cee88b013110a984057314858e34dfbed45e9b`.
- L'addendum `ACCOUNTING_ALIGNMENT_ADDENDUM.md` è una **correzione di metodo dopo un audit fallito**, registrata prima dei risultati al commit `0d90c6962aa7cd10186b3a7d34680d28a977a91d`. Il NAV del parent alla riga k è valorizzato alla data `dates[k+1]`; allineare naïvement al prezzo sulla riga k avrebbe prodotto falsi risultati.
- Verifica indipendente del codice OLC19 `portfolio_metrics_parent.py`: CAGR EU del conto `TOP2_CONTEXT_REVALUE / FAST_LOCK3 / fee 0.001` 2021–2024 = **23,19991785%**, MaxDD **−28,60841254%**. Scarto ricalcolo CAGR ~2,8×10⁻¹⁷ e rendimento di periodo 0. Questi sono simulati storici, non CAGR live certificati.
- Controlli USA **non eseguiti come nuovo esperimento e non modificati**: OLC17 `ALL_PREOPEN_V6` **52,3006% CAGR**, OLC19 `FAST_LOCK3` **50,7722% CAGR**; differenti esecuzioni, stesso periodo, storici.

## Gate A: verifica di disponibilità delle aperture

Nel pannello UE ci sono **1.898 date** (2019-02-01..2026-07-01) e **167 colonne**, delle quali 165 ETF e due strumenti tecnici. Le chiavi data e ticker sono uniche. Dal 2021 al 2024 ci sono **1.026 date** archiviate; tutti e cinque i proxy hanno aperture realmente osservate nello stesso giorno in **1.021** date. Le altre sono `2021-05-24`, `2021-12-24`, `2021-12-31`, `2024-12-24`, `2024-12-31`: i prezzi numerici non diventano per questo eseguibili.

Nel 2020 il **01/06** ha 11/167 strumenti marcati osservati e il **02/06** ne ha 150/167. L'overlay delle etichette OLC32 ha correttamente rimosso il confine eseguibile fittizio di giugno, ma **non** ha riscritto i NAV OLC19. `LEEU.DE` al 02/05/2024 rimane `observed=False`. L'assenza dei dati di quotazioni USA `observed` non interessa il clone EU ma blocca la certificazione comparabile del sistema multi-mercato.

### Bloccanti dati ancora aperti

1. Anagrafica economica **PIT** per tutti gli ETF selezionabili: ISIN, indice, settore, Paese, valuta di negoziazione e di sottostante, share class, hedging e switch storici.
2. Prezzi tradabili e rendimenti total-return in EUR, dividendi, corporate actions e delisting, calendari per singola quotazione; maschere di quote originali USA e EU.
3. Audit degli ordini con informazione disponibile prima dell'asta, commissioni vere, spread, quantità, slippage e first-executable price.

Questi dati non sono stati inventati o sostituiti con holdings attuali. Lo screening seguente **non supera Gate A**.

## Gate B: cinque fattori quotati in euro, modello di stile retrospettivo

Proxy fissati prima degli esiti: `EXSA.DE` (STOXX Europe 600), `SXR8.DE` (S&P 500), `SXRV.DE` (Nasdaq-100), `QDVE.DE` (S&P 500 IT), `EXX1.DE` (banche eurozona). Le loro identità e indici sono tratti dalle schede emittenti o di mercato conservate in `FACTOR_PROXY_CATALOG.csv`. Le informazioni di catalogo consultate nel 2026 **non** certificano le holdings 2019–2024. `EXSA/EXX1` sono a distribuzione, perciò il rapporto fra i loro Open non è total-return.

Per ogni anno 2021–2024 sono stati usati esclusivamente **252 intervalli di rendimento dei proxy osservati antecedenti** al primo Open dell'anno. L'ottimizzazione ha solo lo scopo di riprodurre lo *stile dei rendimenti precedenti* del conto, con pesi non negativi, somma <=100%, niente leva, e cassa residua a zero interessi. Il clone è poi mantenuto durante l'anno con i pesi che derivano dal movimento dei prezzi e ribilanciato all'Open iniziale dell'anno successivo. È uno **screening statistico**, non una replica certificata delle vere esposizioni del conto e non una scelta per massimizzare il rendimento.

**Finestra comune osservata:** 2021-01-04 → 2024-12-30, 1.021 aperture e 1.020 intervalli. Non coincide esattamente con la finestra dichiarata dallo scorecard ufficiale e ha una diversa metrica annualizzata. Gli Open sono nella valuta di negoziazione EUR, senza riconciliazione distribuzioni/total-return.

| Curva storica matched | CAGR prezzo/NAV ann. | Volatilità ann. | MaxDD |
|---|---:|---:|---:|
| OLC19 EU (NAV originale netto, allineato) | **23,29%** | **22,63%** | **−28,61%** |
| Clone fattoriale long-only (costi illustrativi) | 14,45% | 16,02% | −22,48% |
| EXSA Europa broad (solo Open) | 8,44% | 14,11% | −20,49% |
| SXR8 S&P 500 EUR (solo Open) | 17,97% | 14,87% | −17,08% |
| QDVE tecnologia USA EUR (solo Open) | 24,80% | 22,79% | −26,47% |

**NON SI PUÒ CONCLUDERE CHE LA DIFFERENZA +8,84 pp di CAGR OLC19−clone sia alpha.** Il clone ha volatilità inferiore di 6,61 punti, ha nel 2021 circa il 49,3% in liquidità per effetto del training sul 2020, e non comprende la componente semiconduttori (`VVSM.DE`), che il conto detiene per ampie percentuali nel 2022–2024. Il rischio **non è abbinato**, mancano esposizioni economiche, il clone non utilizza la stessa disciplina dinamica di stop e il trattamento dei dividendi non è omogeneo. Anche QDVE è un benchmark individuato da una storia già esplorata: non dimostra una strategia alternativa ex ante.

Le 5 proxy spiegano solo una parte del profilo in-sample e sono collineari (SXR8, SXRV e QDVE si sovrappongono). Coefficienti annuali e contabilità giorno per giorno in `EU_STYLE_TRAIN_BY_YEAR.csv`, `EU_FACTOR_CLONE_DAILY.csv` e `EU_STYLE_REBALANCES.csv`. L'audit ricostruisce indipendentemente il clone in quantità di quote e cassa, con scarto massimo ~5.1e-10 sugli indici.

## Dato nuovo utile: ciò che il portafoglio aveva realmente già comprato

Usando `primary_units × Open / NAV` allineato alla seduta corrente (solo ETF **principali**, non componente difensiva), i pesi medi su aperture osservate comuni sono:

| Anno | VVSM.DE, semiconduttori | QDVE.DE, IT USA | Combinati |
|---|---:|---:|---:|
| 2021 | 0,00% | 0,00% | 0,00% |
| 2022 | **22,56%** | 0,00% | **22,56%** |
| 2023 | **21,12%** | 0,00% | **21,12%** |
| 2024 | **29,67%** | **24,29%** | **53,96%** |

Il fondo VVSM replica un indice di semiconduttori e QDVE un indice di tecnologia USA secondo le attuali schede degli emittenti; la percentuale è una **esposizione a due ETF** e non un calcolo look-through di società/settori. Nel 2021 altre posizioni principali erano `EXV9.DE` (Travel & Leisure, ~21,2% NAV medio) e `EXV5.DE` (Automobiles & Parts, ~17,0%), a conferma del fatto che il portafoglio ruotava già fra fondi settoriali. Le descrizioni degli indici seguìti sono documentate con fonti pubbliche, ma le composizioni puntuali storiche restano da autenticare.

**Interpretazione:** il sistema già acquisiva esposizione a leadership economiche; non è corretto assumere che la principale correzione consista nell'aggiungere momentum semestrale. Il problema riguarda il *dimensionamento causale del premio direzionale per settore* e il rischio di correlazione/concentrazione, che qui NON abbiamo ancora dimostrato prevedibili.

## Riconoscibilità del leader fra 5 fattori: segnale debolissimo

Al segnale mensile, prendendo la migliore delle cinque proxy su 126 sedute storiche, nei successivi 126 intervalli osservati:

- **Stesso leader: 10/48 date = 20,83%** (nel caso ingenuo di 5 alternative equiprobabili sarebbe 20%, ma non è un test statistico valido perché le proxy sono correlate).
- Correlazione media di Spearman fra ranghi passati e futuri delle 5 proxy = **+0,0125**.
- Rendimento medio futuro a 126 sedute del leader passato = **+6,51%** contro **+8,64%** della media semplice delle cinque proxy, differenza **−2,13 punti percentuali**.

Le finestre di 126 sedute si sovrappongono e lo storico è stato ampiamente riutilizzato. La misura è **descrittiva, senza costi né vincoli di portafoglio**; non dimostra un risultato economico negoziabile. In questa definizione semplice la leadership passata non è sufficiente per scegliere il fattore vincente futuro.

## Criterio di arresto e decisione finale

**STOP a nuovi ranker, coefficienti di momentum e modelli HOLD/SWITCH sullo stesso storico.** Manteniamo intatti USA e il motore OLC19 europeo. I nuovi tentativi sulle performance sono subordinati a due fatti documentati:

- Disponibilità di universo storico/PIT, total-return EUR e verifica delle quotazioni, dei costi e dell'esecuzione (Gate A); oppure dichiarare esplicitamente che il lavoro è soltanto sperimentale non investibile.
- Costruzione di una tassonomia economica verificabile e di un benchmark *matched per fattori e rischio* che includa anche semiconduttori, banche, tecnologia, FX e residui difensivi, **senza ripesare retrospettivamente il modello sull'esito vincente**. Poi testare se esiste davvero un *premio direzionale netto* oltre il fattore semplice, su nuovi dati non esplorati prima di toccare i capitali.

Il lavoro utile successivo **non** è OLC38 con un nuovo classificatore: è chiudere il Gate A partendo dagli ISIN/indice/valuta/settore dei nomi effettivamente acquistati e dai prezzi full total-return, poi rieseguire il controllo a pari esposizione. Nessuna quantità di nuove feature compensa un contratto d'esecuzione o un confronto non omogeneo.

## Output verificabili

- `src/run_olc37.py`, `src/verify_olc37.py`, `src/analyze_holdings.py`, `src/factor_periods.py`, `src/plot_olc37.py`.
- Audit, source manifest, catalogo proxy, pesi annuali, NAV comparabili, ribilanciamenti, esposizioni effettive, diagnostica leadership, risultati di parità e relativi PNG.
- Input congelati OLC19/OLC32 sono archivi originali conservati nella Library utente e **non ricopiati in GitHub** (165MB + 10MB); la riproduzione deve usare gli stessi SHA.

### Limiti delle fonti esterne

Tutti gli strumenti elencati sopra risultano fondi a gestione passiva, con schede emittenti pubbliche, ma l'identità attuale del fondo e del benchmark è un dato di catalogo, non una certificazione delle sue partecipazioni giornaliere PIT negli anni esaminati. Consultare gli URL in `FACTOR_PROXY_CATALOG.csv`; per `VVSM.DE` l'ETF iShares *non* è il referente, è VanEck Semiconductor UCITS ETF con ISIN IE00BMC38736.
