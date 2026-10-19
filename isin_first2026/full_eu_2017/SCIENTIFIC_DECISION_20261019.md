# Paniere ETF Europe-only per test 2017–luglio 2026 — decisione 2026-10-19

## Stato e tracciabilità
- Workflow validato con success: https://github.com/AM1975MA/Test/actions/runs/39311893077.
- Full fresh originals EURO60: https://github.com/AM1975MA/Test/actions/runs/39310277517, 60/60 Yahoo EUR, OHLC raw, adjusted, dividend events, source manifest. Gli originali EUR60 sono **44 ISIN differenti**, non 60 fondi.
- Extra 16 quotazioni bond: https://github.com/AM1975MA/Test/actions/runs/39311335847, 15/16 Yahoo, **7 ISIN diversi** (4 titoli di Stato euro area, 3 euro corporate anche emittenti extra-UE). Etichettati separatamente.
- Settoriali: già archiviati in europe_sector2026/results e alternatives/results e aliases/results; quote Yahoo EUR e ISIN ufficiali Xetra validati nell'archivio preesistente.
- Dataset finale e SHA-256: isin_first2026/full_eu_2017/results/; protocollo prima dei risultati in PREREGISTERED.md.

## Warm-up e data quality, verificati nel dataset generato
Per i **60 ticker originali** sono state acquisite serie da 2004-01-01 quando disponibili fino al 2026-10-19. **60/60** hanno almeno 252 osservazioni giornaliere *prima del 31 gennaio 2017*. Nel solo **2016** i 60 ticker hanno in media **250,38** giornate, minimo **166**, quindi alcuni richiedono anche sedute del 2015 per costruire feature a 252 sessioni; nessun prezzo 2015 è stato fabbricato per colmare il warmup. Per la prima finestra F3 basata su 19+6 feature e le regressioni beta a 126 sedute, il campione ammesso ha warmup sufficiente. Il numero delle sessioni vere pre2017, non solo la stringa della prima data quotata, è incluso in ogni riga di audit.

Fondo **diverso** = ISIN diverso, non venue ticker diverso. Validazione di identità con checksum, anagrafica ufficiale Xetra 19/10/2026 e sorgenti emittenti; 2026 snapshot non equivale ad anagrafica fondi sopravvissuti/quotati nel 2017. Expost time window data-quality filtering è esplicitamente dichiarato e NON ha status PIT.

## Cohort STRICT EUROPE 2017–2026 effettivamente costruito
**48 ISIN unici**, 48 singole quotazioni storiche EUR originali/adjusted archiviate e file wide con Open/Close/Volume per periodo 2016-01-01 → 2026-07-01. **12 ISIN aggiuntivi** rispetto ai 44 ISIN EUR60: non tutti i fondi originali EUR60 superano il filtro prudenziale di qualità. 134 copie di serie esaminate, **114** ticker distinti scaricati, **82** ISIN di candidati Europe-underlying, **48** ammessi.

| Gruppo coerente di attività europee | 48 ETF ISIN unici |
|---|---:|
| Azionario ampio Europa | 4 |
| Azionario singoli mercati europei | 4 |
| Azionario fattoriale e small caps | 4 |
| Azionario settoriale / sotto-settoriale | **23** |
| Immobiliare quotato europeo | 6 |
| Obbligazioni governative area euro | **7** |
| **Totale** | **48** |

Tutti gli **11 macrosettori** rappresentati:
Communication Services 1; Consumer Discretionary 3; Consumer Staples 2; Energy 1; Financials 5; Healthcare 2; Industrials 1; Information Technology 2; Materials 4; Real Estate 3; Utilities 1. Nota: 11 settori non sono 11 esposizioni economicamente indipendenti; SToxx ICB e MSCI GICS potrebbero non coincidere. Gli immobiliari sono già compresi nei 6 REIT/fondi property e i 3 etichettati REAL_ESTATE nel conteggio per settore si riferiscono solo alla colonna sector_11.

Il paniere separato NON STRETTAMENTE EUROPE-ONLY comprende ulteriori **3 ISIN di euro corporate**: IEAC.AS (ISIN IE00B3F81R35, corporate IG), SE15.MI (IE00B4L60045, corporate breve) e IHYG.MI (IE00B66F4759, high yield). Le obbligazioni sono denominate in euro ma gli emittenti possono essere anche statunitensi/globali: non confluiranno nella versione rigorosa UE.

## US149 mapping, limite di equiparazione
Original 149 ETFs: 25 US Broad/Style, 25 US Sector/Theme, 25 global/developed/country, 24 emerging, 25 duration/credit/cash, 25 real assets/commodities.
Europe-only 48 captures approx analogous **broad/country/style**, **11 equity sectors**, **EUR sovereign duration**, **European REITs**, but intentionally NOT 24 Emerging Markets (America latina, Asia, Arabia ecc.), commodity fisiche globali, US sovereign debt, high-yield issuer globali, né fattori tecnologici puri globali (SOXX/SMH semiconductors, ITA aerospace e difesa USA, biotech US). L'impossibilità di parità 149×6 sotto il vincolo EU riguarda la DIFFERENZA strutturale economica, non mancanza di yfinance. Registrato US149_EUROPE_SECTOR_PROXY_CROSSWALK.csv (25 ticker USA C02 -> sottosettori/proxy UE): un 25:25 elenco per proxy genera ESPOSIZIONI DUPLICATE, quindi **non replicare ticker separati usando lo stesso ISIN**.

Il dataset viene prima di qualsiasi retraining; nessun nuovo F3/H1/H3 modello, R_H, etf_trader o backtest è stato eseguito in questo step. I risultati del vecchio EUR60 non sono confrontabili direttamente con il nuovo 48 su date/holding diversi; per questo servono ricostruire, refittare e medesima contabilità degli ordini. Non usare gli importi annualizzati precedenti come risultati del nuovo paniere.

## Sicurezza scientifica
- Filtri di qualità: almeno 252 sedute prima 31/01/2017; almeno 2250 barre feb17-lug26; EUR; OHLC valido/volume non negativo; max 1% barre con envelope OHLC incoerente; max 10% vendor Volume 0 e max12% barre piatte. A <=2% vendor zero volume <=3% flat, altrimenti B; non viene mascherato prezzo/sintetizzato OHLC per errore di fonte; le anomalie persistono nel raw e in audit. **A/B non è prova di esecuzione reale allo Open**, né spread/volume effettivo. Snapshot attuali possono avere revisioni per dividendi e cambi classi. L'ammissione su qualità misurata ex post è utile per la ricerca, NON è universe membership PIT e introduce un bias da selezione sul campione.
- Classe Amundi CAC40 ESG C40.PA ed EPRE.MI lanciate 2018 con preistoria Yahoo dal 2008–2009: **escluse** dal 2017 per rischio errata identità del fondo in passato. Alternative lanciate nel 2024 escluse dal roster 2017. Nessun prezzo fabbricato prima della data di quotazione documentata.
- In produzione o seria validazione futura: universo point-in-time tramite FIRDS/issuer, corporate actions, reale volume/spread, lag EUR/US factor timing, train-test purged walk forward, test out of sample intoccato, e confronto 48 vs 149 non in regime region/economic equivalent ma con limiti esposti.

## File utilizzabili
- results/STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv: anagrafica deduplicata e qualità 48 fondi.
- results/isin_daily_ohlcv_eur/<ISIN>.csv: quote per giorno (date, ISIN, ticker, venue, OHLC adjusted, Volume).
- results/WIDE_DAILY_OPEN_2016_2026.csv: Open aggiustato per ISIN.
- results/WIDE_DAILY_CLOSE_2016_2026.csv: Close aggiustato per ISIN.
- results/WIDE_DAILY_VOLUME_2016_2026.csv: Volume Yahoo per ISIN.
- results/ALL_EUROPE_ISIN_QUOTES_SOURCE_QUALITY.csv: audit 134 quote/provenance e motivi esclusioni.
- results/SEPARATE_EUR_DENOMINATED_GLOBAL_ISSUER_CREDIT.csv: 3 corporate non ammissibili al strict-Europe.
- results/RESULT.json: numeri, scope, warning.
- results/SHA256_MANIFEST.txt: impronte verificabili.
- US149_EUROPE_SECTOR_PROXY_CROSSWALK.csv: 25 US sector/themes verso gli ETF europei con etichetta SECTOR_CLOSE o BROAD_PROXY.
