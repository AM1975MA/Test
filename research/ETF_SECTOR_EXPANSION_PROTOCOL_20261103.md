# EU165/USA149 — Espansione settoriale controllata (2026-11-03)

**Ricerca, nessuna modifica ai panieri di produzione e nessun nuovo CAGR dimostrato.** L'obiettivo non è aggiungere più nomi, ma aumentare l'opportunità economica realmente distinta e catturabile fuori campione.

## Materiale consultato

- Roster USA149 originale: `etf-trader-v3 corrected/fullstack_legacy/data/ETF_UNIVERSE.csv` (149 usabili; `PIN` marcato non usabile), letto da GitHub.
- Tassonomia EU165 archiviata nella Library `EU165_ECONOMIC_TAXONOMY.csv` (165 righe); OLC42 `OLC42_AUDIT_IT.md` (EU152 preliminare: 96 Acc, 56 Dist, 13 esclusioni solo ricerca).
- Rapporti V3 `EU48_TRUE_CORRECTED_CAPACITY_20261025.md`, `etf149_rank_to_pnl_20261030/README_IT.md` e NAV EU/USA `research/etf_performance_charts_20261102/`.
- Schede e elenchi aggiornati: https://www.justetf.com/en/how-to/invest-in-cyber-security.html ; https://www.justetf.com/en/how-to/invest-in-robotics.html ; https://www.justetf.com/en/how-to/invest-in-water.html ; https://www.justetf.com/en/how-to/invest-in-biotech.html ; https://www.justetf.com/en/how-to/invest-in-clean-energy.html ; https://www.justetf.com/en/how-to/invest-in-semiconductors.html ; https://www.justetf.com/en/how-to/invest-in-uranium.html ; https://www.globalxetfs.com/funds/botz/ ; https://www.globalxetfs.com/funds/lit/ ; https://www.globalxetfs.com/funds/pave .

## Diagnosi strutturale EU165

La tassonomia classifica fra le 165 righe: 32 `EU_COUNTRY_UNRESOLVED`, 25 `EUR_SOVEREIGN_DURATION_UNRESOLVED`, 22 `EU_FACTOR_UNRESOLVED`, 20 `BROAD_EUROPE`, 11 `EU_REIT_PROPERTY`. **Questi 110 record sono categorie grossolane, non 110 duplicati dimostrati**; alcune contengono esposizioni diverse. Lo screening va effettuato su ISIN/fondo/indice e look-through delle partecipazioni.
La tassonomia include già `VVSM.DE` ISIN `IE00BMC38736` con `SEMICONDUCTORS_WORLD`: non inserirne un secondo clone senza dimostrare esposizione distinta. Contiene inoltre `QDVE.DE` (tech USA), `XDWT.DE` (tech mondo) e diversi ETF settoriali Europa. Le nuove opportunità non devono essere limitate alla geografia UE: sono UCITS negoziati in Europa ma possono investire globalmente.

Nel roster USA149 sono **già presenti** `SMH`, `SOXX`, `HACK`, `IBB`, `XBI`, `ITA`, `PPA`, `URA`, `TAN`, `ICLN`, ecc. Raddoppiare questi segmenti per numero aumenta la ridondanza senza garanzia di payoff. Candidati USA più differenzianti: `BOTZ` (robotica, inception 2016-09-12), `LIT` (litio e batterie, inception 2010-07-22) e `PAVE` (infrastrutture US, inception 2017-03-06); **date di inception non equivalgono a quotazioni giornaliere originali complete**.

## Prima shortlist non promossa

Tabella macchina leggibile in `research/ETF_SECTOR_EXPANSION_SCREEN_20261103.csv` con ISIN, classe, fonte e vincoli. Priorità EU: cybersecurity, robotica/automazione, acqua, biotech; valutare energie pulite; uranio e nucleare soltanto dalle rispettive date di ammissibilità, senza retrodatazione. USA: BOTZ, LIT, PAVE prima della duplicazione di temi esistenti.

**La priorità è definita sulla copertura attuale e la disponibilità potenziale dei prodotti, NON sui loro rendimenti 2021–2026.** Gli ISIN `UNKNOWN` per la biotech sono intenzionalmente sospesi finché non verificati. Ogni riga deve essere ricontrollata per ticker/venue, classe, valuta, dividendi, launch/inception, TER e spread; data provider delle quotazioni e una stringa indice corrente non sono prove point-in-time.

## Test di valore incrementale — ordine congelato

**E0 — data & eligibility**: partire da EU152 `RESEARCH_ONLY`, conservare EU165 legacy invariato. Prezzi per 2015–2026 quando disponibili, OPEN/CLOSE osservati originariamente, adjusted prices, evento distribuzione, valuta negoziazione e regime FX, numero di giorni mancanti, first observed open. Warm-up per ogni feature e train pooled annuale applicati separatamente; non imporre artificialmente uno storico individuale di 5 anni quando il modello pooled richiede soltanto 252 giorni di feature. No forward fill prima dell'inception; nessuna serie sintetica degli ETF nuovi.

**E1 — opportunity bound**: per mese `t` con stesso calendario e costi contabili, best ex-post `old`, `old+new eligible`, migliori Top2/Top5 diagnostici e mediana. `oracle_gain_t = max_{i in eligible_new+old} r_{i,t+1} - max_{i in eligible_old} r_{i,t+1}`; prezzo di esecuzione successivo identico. Oracle è un tetto descrittivo ex-post, non un rendimento eseguibile. Misurare quota mesi in cui un nuovo ETF è in Top1/Top3 e sua *unique opportunity*, poi confrontare con modelli precongelati.

**E2 — signal transfer**: score V2/OLC19 congelato; nuovi ticker ricevono score tramite stesso modello solo se dispone delle feature valide e nessuna nuova informazione. Se modello dipende dall'intera distribuzione cross-section o dal numero di candidati, ricalcolare coerentemente su *tutti* i ticker anziché appendere score incompatibili. Differenze osservate in rank e scelta attribuite all'universo, non a un training aggiuntivo.

**E3 — matched replay**: replay portafoglio unico EU e USA, base e expanded, medesimo motore di esecuzione, commissioni, spread, turnover e controlli risk/regime. Scelte test principali: (A) originale; (B) +1 ETF per nuovo tema; (C) +2 soltanto se economicamente non fungibili. Predefinire date e universi per evitare cherry-picking. Non mescolare passaggio da EU165 a EU152 con effetto dei nuovi ETF: ablation separata.
 
**E4 — decorrelazione e ritorno marginale**: per ogni ETF candidato fare rolling correlation/residualization rispetto al gruppo già presente; percentuale di forward best mensili nuovi e delta capture della stessa strategia. Misurare incrementi di `effective number of independent bets`, non solo numero di strumenti e proporzione di temi.

**E5 — validazione temporale**: expanding walk forward, embargo >= label horizon e nested selection, criterio primario fuori campione con test paired a blocchi di date. 2019–2026 già esplorato: nuove prove su quel periodo sono diagnostiche, non conferme indipendenti. Da quel punto congelare forecast per dati successivi prima della maturazione delle label.

## Pass/fail gates

1. Nuovo ETF senza duplicate economic exposure o con comprovato residuale informativo.
2. Storia originale osservata sufficiente al warm-up alla specifica data; classe Acc preferita soltanto se copre la finestra, Dist con total-return verificato altrimenti.
3. I nuovi ETF aumentano almeno una metrica di *opportunity* anche nei sottoperiodi predefiniti senza dominanza di un solo mese.
4. Vantaggio net after costs e drawdown non peggiorato indiscriminatamente nel matched replay, con verifiche per regime e controllo test multipli.
5. Nessun nuovo modello promosso soltanto per avere un CAGR più vicino a 50%.

## Limite dell'esecuzione in questa sessione

Questo è uno **screen di strumenti con report registrato**, non un aggiornamento dei panieri in input né un backtest espanso. Le matrici OHLCV e le predizioni OLC19/EU165 archiviate nella Library non risultano nel ramo `main` GitHub sotto forma di input completi eseguibili; il CSV/il rapporto evitano di inventare prezzi o nuove metriche di performance. Il prossimo test da correre quando sono disponibili i prezzi è E1 opportunity oracle — lo stesso diagnostico che determina se l'espansione apre opportunità inaccessibili al paniere attuale.
