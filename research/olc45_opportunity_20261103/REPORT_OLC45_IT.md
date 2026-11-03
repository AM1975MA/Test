# OLC45 — Quali esposizioni aggiungono opportunità davvero nuove? (3 novembre 2026)

**Esecuzione GitHub Actions: PASS. Solo opportunità EX-POST, non rendimento investibile né CAGR di strategia. Nessun cambiamento alla produzione.**

## Conclusione, in parole semplici

Nell'Europa le nuove opportunità sono molto concentrate: **minatori d'oro ≈76,6%**, cybersecurity ≈13,5%, commodity diversificate ≈9,6%, robotica ≈0,4% del miglioramento del *massimo rendimento mensile teorico*. Quindi aumentare indiscriminatamente il numero di ticker non equivale ad aumentare diversificazione economica: qui ha aiutato soprattutto portare una categoria di aziende assente o sottorappresentata.

La distribuzione è attribuita senza doppio conteggio mediante Shapley esatto delle aggiunte su **tutte** le permutazioni di 4 ETF EU e 3 USA. Non è una probabilità di previsione, non suggerisce di comprare oggi i vincitori storici.

## Base e test

- Riferimento `OLC32/E1`: 48 mesi con segnale 2021–2024, esecuzione identica next-open→next-open e miglior rendimento futuro originale congelato.
- ETF EU ammessi a prezzo Open storico e controllo intraday del motore: `G2X.DE`, `USPY.DE`, `WTIC.DE`, `2B76.DE`.
- USA: `BOTZ`, `LIT`, `PAVE`.
- `CMOD.MI` volutamente escluso dal gruppo ammissibile per **539/2400 barre con OHLC incoerenti**, malgrado l'E1 Open-only fosse utilizzabile. Il rapporto E1 con cinque fondi ha quindi misure leggermente diverse.
- Per ogni mese la funzione valore `max(old_top1,new candidates)` e la media dei migliori due; la seconda migliore originale viene recuperata come `2×mean_top2-old_top1`. Si confronta il valore di ciascun sottoinsieme di candidati e si sommano i margini medi per tutte le permutazioni, con check `sum(Shapley)=incremento oracle totale` data per data.
- L'oracolo osserva il futuro SOLO per capire l'ampiezza delle opportunità, mai per generare un trade. I prezzi sono snapshot adjusted Open del 2026, non storico broker/PIT certificato.

## Tabella dei risultati

| Misura 2021–2024 | EU165 + 4 | USA149 + 3 |
|---|---:|---:|
| Mesi testati | 48 | 48 |
| Mesi con nuovo leader ex-post | **12** | **2** |
| Incremento medio di miglior ETF ex-post (log-bp/mese) | **+91,764** | **+18,814** |
| Incremento medio della migliore coppia ex-post (log-bp/mese) | **+74,012** | **+13,859** |

Questi numeri non possono essere annualizzati in un CAGR di trading perché il miglior ETF viene definito solo DOPO la fine di ogni mese.

### Contributo Shapley (Top1: somma di incremento storico su 48 mesi)

| Mercato | ETF e settore | Contributo log-bp complessivo | Quota dell'incremento del mercato |
|---|---|---:|---:|
| EU | **G2X.DE — azioni minatori d'oro** | **3371,883** | **76,55%** |
| EU | USPY.DE — cybersecurity | 593,255 | 13,47% |
| EU | WTIC.DE — commodity diversificate | 421,718 | 9,57% |
| EU | 2B76.DE — robotica | 17,830 | 0,40% |
| USA | LIT — litio e batterie | 903,070 | 100% |
| USA | BOTZ — robotica | 0 | 0% |
| USA | PAVE — infrastrutture USA | 0 | 0% |

Fonte quantitativa: [GitHub Actions OLC45](https://github.com/AM1975MA/Test/actions/runs/41732588738), `results/olc45_theme_shapley_priority.csv`; `results/olc45_expost_oracle_monthly.csv`; `results/olc45_overlap_correlations.csv`; fonte input E1 frozen. Anche quando una categoria ha Shapley zero può contribuire a un portafoglio diversificato: significa solo che **non aumenta il massimo dei due migliori ex-post nel periodo esaminato**.

## Interpretazione economica e prossimo screening: ETF ≠ ETC

`G2X.DE` è un ETF UCITS azionario su società che estraggono oro e argento, **non** detiene oro fisico. Le aziende minerarie risentono anche di margini, costi, gestione, leva operativa e sentiment azionario. Fonte [VanEck Gold Miners UCITS](https://www.justetf.com/en-de/etf-profile.html?isin=IE00BQQP9F84), ISIN IE00BQQP9F84, lancio 25 marzo 2015.

L'estensione naturale del nostro universo economico è testare in una **coorte separata di ricerca** alcuni ETC/ETN europei già esistenti prima del 2019, quali:
- **Silver fisico** WisdomTree Physical Silver, ISIN **JE00B1VS3333** (attenzione: inizia con JE, non IE), ad es. `VZLC.DE` Xetra EUR, `PHAG.MI` Italia EUR. È **ETC**, strumento di debito collateralizzato, non ETF UCITS compliant, lancio 2007. [Emittente](https://www.wisdomtree.com/it/products/commodities/wisdomtree-physical-silver).
- **Gas naturale** WisdomTree Natural Gas, ISIN **JE00BN7KB334**, ETC basato su future e swap collateralizzati, lancio 2006 (dati attuali non certificano continuità della stessa linea ISIN in tutte le epoche). [Emittente](https://www.wisdomtree.com/it/products/commodities/wisdomtree-natural-gas).
- La definizione della struttura ETC e differenze dal requisito UCITS è illustrata anche da [Borsa Italiana](https://www.borsaitaliana.it/etc-etn/formazione/cosaunetc/cosaunetc.en.htm) e [ESMA Technical Advice UCITS eligible assets](https://www.esma.europa.eu/sites/default/files/2025-06/ESMA34-2087785638-1548_Final_report_on_the_Technical_Advice_on_the_review_of_the_UCITS_EAD.pdf).

Questi strumenti NON devono entrare nel paniere UCITS fino alla verifica di: struttura di credito/collaterale, eventuale tracking futures/roll yield, rischi controparte, valuta quotazione, storico prezzi osservati e affidabilità intraday, costo/volume negoziabile, compatibilità delle regole di stop e adeguata copertura risk-off. Un ETC gas futuro **non è economicamente uguale** a un ETF su produttori di gas né a una commodity diversificata.

## Decisione e limiti

La conclusione supportata è che **l'universo EU ha avuto 12 mesi di opportunità teoriche aggiuntive** grazie a 4 ETF, ma **la maggior parte è un solo tema**. È razionale studiare ulteriori esposizioni reali poco correlate, non moltiplicare cloni di cybersecurity e robotica.

Non è stato aggiunto un nuovo rendimento predittivo. L'anno 2021–2024 è iper-esplorato e i nuovi candidati sono scelti dopo i dati; Shapley misura un'opportunità ex-post, non un rischio futuro prevedibile. Ogni passo successivo richiede price/feature point-in-time, allocazione costed, stessa execution e validazione indipendente.
