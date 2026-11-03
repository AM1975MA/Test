# OLC45-B — Opportunità aggiuntiva di ETC su argento fisico e gas naturale (3 novembre 2026)

**Risultato quantitativo reale: controllo Open→Open E1 sulle stesse 48 date del 2021–2024, NON un CAGR di strategia e NON un test del motore OLC19.**

## Risultato e decisione in parole semplici

Dopo aver aggiunto i quattro ETF europei verificati in OLC45, l'inserimento *puramente teorico* di due **ETC** sulle singole commodity avrebbe creato nuove opportunità in **16 mesi su 48**: gas naturale 13, argento fisico 3. Il vantaggio massimo ex-post aumenta di **+319,55 log-bp/mese**, il miglior portafoglio ideale Top2 di **+206,49 log-bp/mese**. Per confronto, i quattro ETF OLC45 aggiungono +91,76 log-bp/mese all'oracolo Top1.

Questi sono **limiti superiori ex-post**: un modello non poteva conoscere in anticipo i mesi migliori. L'incremento è concentrato nel 2021–2022, quando il mercato energetico aveva condizioni peculiari. Perciò questo screening non giustifica alcuna promozione, trade, né la promessa di un CAGR EU al 50%.

## Specifica dei prodotti e fonti primarie

| Categoria | Ticker preferito | ISIN reale | Natura | Fonte emittente |
|---|---|---|---|---|
| Argento fisico | PHAG.MI (VZLC.DE senza prezzi Yahoo) | **JE00B1VS3333** | ETC su metallo fisico allocato | https://www.wisdomtree.com/it/products/commodities/wisdomtree-physical-silver |
| Gas naturale Henry Hub | NGAS.MI (OD7L.DE senza prezzi Yahoo) | **JE00BN7KB334** | ETC collateralizzato su indice futures e swap | https://www.wisdomtree.com/it/products/commodities/wisdomtree-natural-gas |

**Non sono fondi UCITS.** Sono strumenti di debito ETC, con rischi di liquidità, controparte e/o commodity, rollover dei futures, valuta e collateralizzazione. Alcuni codici Xetra restano correttamente marcati come *non verificati nella fonte prezzi*; non si è spacciato l'ISIN per una quotazione effettiva. Le quotazioni di Milano in EUR sono verificabili sulle schede ufficiali dell'emittente. Inoltre il fondo gas attuale è rappresentato con ISIN JE00BN7KB334, non con i codici legacy riportati da fonti non aggiornate.

Borsa Italiana descrive la differenza ETC e fondi UCITS: https://www.borsaitaliana.it/etc-etn/formazione/cosaunetc/cosaunetc.en.htm ; ESMA:https://www.esma.europa.eu/sites/default/files/2025-06/ESMA34-2087785638-1548_Final_report_on_the_Technical_Advice_on_the_review_of_the_UCITS_EAD.pdf .

## Dati e verifiche
- Dataset originale: `OLC32/E1 baseline_oracle_2021_2024.csv` per 48 date, e prezzi osservati E1 dei quattro ETF EU; stessi segnali ed entry/exit esatti.
- Fonte prezzi nuovi: Yahoo via yfinance, `auto_adjust=True`, da gennaio 2017 a febbraio 2025; **48 mesi con entrambe le quote esatte di apertura**, almeno 500 sedute originali disponibili per ogni segnale.
- Dedup per ISIN: non si contano Xetra/Milano come due strumenti differenti.
- `PHAG.MI`: 2.064 daily bars, **107 incoerenze OHLC**, nessuna variazione close-to-close log oltre log(1.6) nel controllo automatico.
- `NGAS.MI`: 2.064 daily bars, **81 incoerenze OHLC**, nessuna variazione close-to-close log oltre log(1.6).
- `VZLC.DE`, `OD7L.DE`: **nessuna serie Yahoo disponibile** in questo run; esclusi senza tentare una serie sintetica.
- 188 errori OHLC su 4.128 barre in totale (**4,55%**): **non usare i valori Low/High di questa fonte per stop OLC19, PnL intraday o valutazioni di eseguibilità**. La validità delle aperture storiche non è certificata soltanto perché il provider restituisce un prezzo.
- Correlazione dei rendimenti mensili Open→Open silver-gas nel periodo −0,181 (descrittiva, non correlazione futura o garanzia di diversificazione).
- L'indice gas su futures può avere *roll yield* molto diverso dal prezzo spot o da altri ETF US: non equiparare al benchmark `UNG` né assumere parità di rischio.

## Misure incrementali **dopo** i quattro ETF già selezionati

| Periodo | Mesi nuovo leader ETC | Incremento Top1 log-bp/mese | Incremento Top2 log-bp/mese |
|---|---:|---:|---:|
| 2021 | 5 | 470,66 | 263,83 |
| 2022 | 6 | 611,30 | 385,65 |
| 2023 | 1 | 0,87 | 49,17 |
| 2024 | 4 | 195,38 | 127,30 |
| **2021–2024** | **16/48** | **319,55** | **206,49** |

Date di massima opportunità teorica: 2022-03-31 +2451,85 log-bp, 2021-12-31 +2136,04, 2021-08-31 +2111,76; tutte attribuite al gas. Questi sono scarti rispetto al *miglior ETF futuro del mese* già nel paniere ampliato, non benefici catturabili ex-ante.

## Posizione scientifica

Lo screening delle commodity rivela una **lacuna di universo**, non prova una **lacuna di informazione predittiva**. L'oracolo combinato vecchio EU +4 UCITS +2 ETC reduce il divario rispetto all'oracolo USA quando entrambi includono gli ETF già aggiunti, ma nessuna riduzione dell'oracolo implica una riduzione proporzionale del CAGR reale.

Il passo di ricerca successivo non è un ulteriore test del miglior rendimento ex-post: è (1) verificare storici coerenti e corporate action su una fonte differente per ETC; (2) dichiarare se il mandato ammette ETC e quale limite di peso/stop; (3) ricostruire una versione della pipeline predittiva con ranking e risk budget *nativi* su queste esposizioni, con score salvati prima delle relative etichette. **Non includere ETC nel paniere EU UCITS prima di tali controlli.**

### Riproducibilità

- Codice: `research/olc45_opportunity_20261103/olc45b_etc_probe.py`.
- Output: `results_ETC/olc45b_etc_monthly.csv`, `results_ETC/olc45b_etc_summary.csv`, `results_ETC/etc_quote_quality.csv`, `results_ETC/etc_cross_correlations.json`, `results_ETC/manifest.json`.
- [GitHub Actions completata](https://github.com/AM1975MA/Test/actions/runs/41733421970). Input E1 congelato con prezzi nel run 41724810594.
