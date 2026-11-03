# E1 — Ampliamento EU165/USA149: prima verifica storica reale (3 novembre 2026)

**Stato:** GitHub Actions **SUCCESS**, verifica di vintage quote **SUCCESS**, ricerca storica 2021–2024. **Non è una nuova strategia e non è un backtest tradabile**. Universo di produzione e modelli originali invariati.

## Obiettivo
Misurare il massimo *vantaggio ex-post* disponibile aggiungendo **5 ETF UCITS quotati in EUR** a EU165 e **3 ETF statunitensi** a USA149, comparando **48 segnali mensili** da gennaio 2021 a dicembre 2024, date effettive `entry_date/exit_date` identiche all'archivio OLC32, calcolo `r = 10000 × ln(adjusted_Open_exit / adjusted_Open_entry)`. Ogni candidato deve possedere almeno **500 Open storici osservati prima del segnale**, e quotazioni esattamente sulle date di ingresso/uscita. Nessun fill pre-inception; nessuna formazione di modello su nuovi ETF.

## Riproducibilità e archivi

- GitHub Actions del run con audit qualità: https://github.com/AM1975MA/Test/actions/runs/41723201482
- Candidato/source: `run_candidate_oracle.py`; controllo prezzi: `validate_quote_vintage.py`.
- Archivio originale: Library `OLC32_RESULTS.zip` → `OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz`; `baseline_oracle_2021_2024.csv` congelato nel ramo come media Top2 e miglior ETF originale per mercato e mese, 96 righe, sulla popolazione eligible originale.
- Risultati GitHub Actions artifact `sector-opportunity-e1-research`: `candidate_quote_quality.csv`, `candidate_monthly_labels.csv`, `incremental_oracle_primary_monthly.csv`, `incremental_oracle_primary_summary.csv`, `control_quote_vintage_monthly.csv`, `control_quote_vintage_summary.csv`, `manifest.json`.
- Quote nuove scaricate con `yfinance` `auto_adjust=True`, Open 2018-01-02→2025-03-31 (1.841 date EU e 1.821 USA), sulle 48 coppie di date nessun dato mancante, numeri distinti, niente fusione di classi.

## Candidati e qualità

| Mercato | Simbolo / ISIN | Espansione | Esito storia e calendario |
|---|---|---|---|
| EU | G2X.DE / IE00BQQP9F84 | Azioni società minerarie aurifere | 48/48, 500 giorni pre-segnale |
| EU | USPY.DE / IE00BYPLS672 | Cybersecurity | 48/48 |
| EU | CMOD.MI / IE00BD6FTQ80 | Indice commodity diversificate Bloomberg | 48/48 |
| EU | WTIC.DE / IE00BYMLZY74 | Enhanced commodity | 48/48 |
| EU | 2B76.DE / IE00BYZK4552 | Robotica e automazione | 48/48 |
| USA | BOTZ | Robotica | 48/48 |
| USA | LIT | Litio e batterie | 48/48 |
| USA | PAVE | Infrastrutture USA | 48/48 |

Fonti delle sedi/ISIN: [G2X](https://www.justetf.com/en-de/etf-profile.html?isin=IE00BQQP9F84), [USPY](https://www.justetf.com/en-it/etf-profile.html?isin=IE00BYPLS672), [CMOD Borsa Italiana](https://www.borsaitaliana.it/borsa/etf/scheda/IE00BD6FTQ80-ETFP.html?lang=it), [WTIC emittente](https://www.wisdomtree.com/it/products/commodities/wisdomtree-enhanced-commodity-ucits-etf-usd-acc), [2B76 emittente](https://www.ishares.com/de/privatanleger/de/produkte/284219/ishares-automation-robotics-ucits-etf?siteEntryPassthrough=true).
**Attenzione:** i ticker provvisori `CMOD.DE` e `WCOA.DE` dell'esperimento iniziale erano mappature di sede *errate*: sono stati corretti **prima** della versione riportata. I dati risultati qui usano esclusivamente CMOD.MI e WTIC.DE; due ticker per lo stesso ISIN non vengono duplicati.

## Risultati effettivamente calcolati: incremento dell'oracolo, NON CAGR

| Calcolo, media sui 48 mesi | EU165 + 5 | USA149 + 3 |
|---|---:|---:|
| Mesi nuovo ETF > best originale | **12/48** | **2/48** |
| Miglior ETF originale, media logbp mese | 946.44 | 1706.87 |
| Miglior ETF con nuovi, media logbp mese | 1040.27 | 1725.69 |
| **Incremento Top1 ex-post medio (log-bp/mese)** | **+93.8314** | **+18.8139** |
| **Incremento Top2 ex-post medio (log-bp/mese)** | **+84.3834** | **+13.8593** |

Il divario tra massimi mensili ex-post USA ed EU passa **da 760.44 a 685.42 log-bp/mese** quando entrambi gli universi vengono ampliati: riduzione **75.02bp, circa 9.9% del gap dell'oracolo originale**. NON significa riduzione analoga del gap di CAGR netto o una previsione del ritorno sfruttabile.

### Concentrazione per anno e nuovo vincitore

- EU incremento Top1 ex-post medio per mese: **2021 0.00bp**, **2022 +194.96bp**, **2023 +44.83bp**, **2024 +135.54bp**. Il miglioramento non è uniforme; pochi mesi dominano.
- Il nuovo vincitore assoluto è `G2X.DE` in **8 mesi** (totale contributi 3402.05 logbp sui 48 mesi), `USPY.DE` in **3 mesi** (611.08), `CMOD.MI` in **1 mese** (490.77); `WTIC.DE` e `2B76.DE` non vincono mai il primo posto ex-post ma possono incidere sulla Top2. Sui 48 mesi, G2X apporta **circa il 75.5% dell'incremento totale dell'oracolo Top1**, non 75.5% del rendimento investibile.
- USA: `LIT` unico nuovo primo assoluto in **2 mesi**; `BOTZ` e `PAVE` mai.

### Diversificazione reale, non conteggio ticker

Correlazione Pearson dei rendimenti log mensili dei nuovi EU sui 48 mesi:
- `CMOD.MI` versus `WTIC.DE`: **+0.961**: molto simili; non rappresentano due scommesse indipendenti. Preferire una quota per esposizione, selezionata per accessibilità, costo e liquidità verificata, evitando ponderazione duplicata nel ranking.
- `USPY.DE` vs `2B76.DE`: **+0.762**: parziale sovrapposizione tecnologia globale, non copie perfette.
- `G2X.DE` vs `CMOD.MI`: **+0.048**: informazioni in larga misura differenti in questo periodo. Correlazione storica non garantisce indipendenza futura.
- Nell'universo USA, la maggior parte degli asset reali principali esiste già (`UNG, URA, GLD, GDX, GDXJ,` etc.). La mancanza europea è più strutturale che di semplice cardinalità.

## Controllo quote tra vintage — risultati indipendenti

Si sono riscaricati gli adjusted Open per 4 ETF **già presenti nell'archivio originale**, allineati a 48 date × 4 = **192** coppie, e confrontati i rendimenti O2O logbp con la colonna originale congelata OLC32:
- `QDVE.DE`: media scarto assoluto **2.61e-8bp**, massimo **1.23e-7bp**.
- `VVSM.DE`: media **8.91e-8bp**, massimo **4.53e-7bp**.
- `SMH`: media **0.000557bp**, massimo **0.002383bp**.
- `UNG`: media **1.71e-7bp**, massimo **4.89e-7bp**.
- **192/192 matched**, **0 scarti >50bp**. Coerente con la corretta formula e calendarizzazione delle fonti. Non certifica la trattabilità della quotazione, il pricing spread, la fiscalità o l'equivalenza ex-ante fra ETF.

## Giudizio e prossimi passaggi scientifici

1. L'estensione EU offre nuove opportunità storiche misurabili, ma solo una piccola parte del *massimo* gap di opportunità USA si chiude con questi fondi. Non è prova né previsione di un CAGR EU vicino al 50%.
2. `G2X.DE` (minatori d'oro) è il candidato esplicativo più influente per *opportunità ex-post*, non automaticamente il migliore in un ranking previsionale o di volatilità.
3. Gli ETF su commodity diversificate `CMOD.MI` e `WTIC.DE` sono esposizioni a futures/diversified index, **non** repliche equivalenti di `UNG` sul gas naturale. Considerare ETC/ETN su singole commodity richiederebbe una nuova policy di rischio/struttura, separata dall'universo UCITS.
4. Lo step successivo indispensabile è ricostruire **score comparabili as-of dei nuovi ETF** con i migliori modelli precongelati, quindi eseguire portafoglio singolo original-vs-expanded (E1 e full OLC19), costi, turnover, risk overlays, applicazione della dedup EU152 **separata**, e test cronologico senza scegliere l'ETF vincente guardando il futuro. Fare tre bracci: originale, nuovi temi non duplicati, nuovi temi completi.
5. 2021–24 e 2019–26 sono stati usati ripetutamente dal progetto: **questo test ex-post non è nuova validazione fuori campione**. Imporre congelamento prospettico delle predizioni prima dell'etichetta, identity point-in-time, spread/fill e block-bootstrap temporale prima di qualsiasi approvazione operativa.

**Non è stata modificata alcuna strategia di produzione, il paniere EU165 originale o USA149, né il repository `Etf_trader`.**
