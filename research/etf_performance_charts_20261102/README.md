# ETF – Curve storiche EU165/USA149 (2 novembre 2026)

**Grafici basati su NAV gia salvati nei checkpoint, senza training/backtest/trading.** Le curve 2019–2026 comprendono il 2019 da febbraio e il 2026 fino al 1 luglio.

## Grafici principali – 2021–2024

![EU 2021–24](charts/EU_rendimento_MAIN.svg)

![USA 2021–24](charts/USA_rendimento_MAIN.svg)

## Periodo completo 2019–luglio 2026

![EU completo](charts/EU_rendimento_FULL.svg)

![USA completo](charts/USA_rendimento_FULL.svg)

## Rendimenti anno per anno

![EU annui](charts/EU_annuali.svg)

![USA annui](charts/USA_annuali.svg)

## Esplorazione completa

[Dashboard interattiva (HTML scaricabile)](dashboard.html) – comprende 1.480 serie NAV mensili (9 lotti × 2 mercati), con selezione di strategia, mercato e periodo. Dopo il download aprire il file HTML nel browser: funziona offline.

In `data/` sono pubblicate tutte le curve NAV a fine mese, una tabella per mercato/lotto, la tabella annuale per **tutte** le varianti, e i metadati SHA256 degli archivi di partenza. In `charts/` sono disponibili anche grafici separati per ciascun lotto.

**52,30% USA**: per OLC17 `TOP2_CONTEXT_REVALUE / ALL_PREOPEN_V6` il checkpoint indica **52,3006% CAGR sul 2021–24**, con fee legacy0,001. È una variante di *sensibilità informativa*, non una strategia live.

**Benchmark nero**: ETF best ex-post, scelto per miglior buy-and-hold Open a entrambe le estremità del periodo fra titoli con quotazioni valide. Intero periodo: **QDVE.DE** in EU165, **SMH** in USA149; 2021–2024: **QDVE.DE** in EU165, **ARGT** in USA149. Benchmark senza costi e selezionato con informazione futura; non è una comparazione operativa né dimostra alpha.

**Avvertenze:** Le strategie hanno politiche di ingresso/protezione diverse (IMMEDIATE/DELAY3/PHASE5/PREOPEN/EOD). La fee legacy0.001 non equivale automaticamente a 10 bp/lato. I dati quote total return, il survivorship, i reali spread e i fill intraday non sono certificati. Verificare differenze solo a parità di configurazione. Le curve 2019–26 e 2021–24 sono ribasate a 100 sull'inizio della finestra mostrata, mentre il CAGR ufficiale dei report può applicare diverse convenzioni di giorni effettivi.

**Provenienza:** archivi originali persistiti nella Library `ETF_Research`, SHA256 in `data/METADATI.json`. Pubblicazione dei soli derivati grafici/serie NAV, non delle matrici di training, modelli, dati grezzi o altri contenuti dei checkpoint.

### OLC06

![OLC06 EU](charts/EU_OLC06.svg)

![OLC06 USA](charts/USA_OLC06.svg)

### OLC08F

![OLC08F EU](charts/EU_OLC08F.svg)

![OLC08F USA](charts/USA_OLC08F.svg)

### OLC09

![OLC09 EU](charts/EU_OLC09.svg)

![OLC09 USA](charts/USA_OLC09.svg)

### OLC12

![OLC12 EU](charts/EU_OLC12.svg)

![OLC12 USA](charts/USA_OLC12.svg)

### OLC14

![OLC14 EU](charts/EU_OLC14.svg)

![OLC14 USA](charts/USA_OLC14.svg)

### OLC15

![OLC15 EU](charts/EU_OLC15.svg)

![OLC15 USA](charts/USA_OLC15.svg)

### OLC17

![OLC17 EU](charts/EU_OLC17.svg)

![OLC17 USA](charts/USA_OLC17.svg)

### OLC18

![OLC18 EU](charts/EU_OLC18.svg)

![OLC18 USA](charts/USA_OLC18.svg)

### OLC19

![OLC19 EU](charts/EU_OLC19.svg)

![OLC19 USA](charts/USA_OLC19.svg)
