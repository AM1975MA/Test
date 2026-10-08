# L2-M | Volatilità depurata dal momentum: risultati e decisione — 2026-10-08

**COMPLETATO: costruzione feature e audit indipendente PASS; nessun learner selettore addestrato; nessuna promozione.** Source repo **solo AM1975MA/Test** branch `research/target-redesign-level2-v1`; `Etf_trader` invariato. [Protocollo pre-risultati](L2M_VOL_RESIDUAL_PROTOCOL.md) commit `c88847325829fa13a8c872aaff35ee50f97f4796`; [amendment numerico documentato](L2M_NUMERICAL_AMENDMENT.md) commit `601b32572d92a758a717977d52ad2204f71c244b`; [sorgente core matematico](l2m_volatility_core.py). Tutto il sorgente effettivamente eseguito, 14 file di dati, bootstrap e audit è nell'archivio conversazionale `ETF_Trader_L2M_volatilita_ortogonale.zip` (SHA256 `bfcc6fd7864c348c70d893210b435e92a3f02756b60fc6ded81a878815b847e4`, ZIP test PASS).

## Campione, indipendenza e definizioni

Yahoo Repeat2 *stessi CSV congelati* dell'original149, 149 ETF, **113 date mensili** 2017-02–2026-06; 16.837 osservazioni matchate alle labels Open-to-Open 21 sessioni. Dati storici scaricati nel 2026: NON vero archivio point-in-time, Original149 già studiato ripetutamente. Per costruire il modello di *expected vol* si usano tutti i month-end dal 2010, sempre antecedenti alla valutazione annuale. **Nessuna osservazione di ritorno futuro usata nella costruzione delle feature**.

Volatilità grezza: deviazione standard (ddof=0) dei 63 log-rendimenti giornalieri passati. Momentum: log ritorni 21/63/126 sedute con variabili sia segnate sia assolute. `cs_orthog`: proiezione OLS ogni mese e in ciascuna delle 6 macro-categorie di zscore(`log(vol63)`) sulla costante e i sei regressori zscore del momentum, mediante SVD least-squares. ***Per costruzione*** l'errore è ortogonale alla proiezione lineare contemporanea. Non è una dimostrazione di indipendenza non lineare, aumento di alpha o stabilità inter-vintage. La volatilità grezza **va mantenuta nel motore di gestione del rischio**.

Secondo metodo `vol_conditional`: `SimpleImputer(median) -> StandardScaler -> Ridge(alpha=100)` sul percentile intra-categoria della `log(vol63)`, 6 percentili di momentum e categorie, fit annuale su mesi passati; inferenza solo anno futuro. Non è ortogonale automaticamente per data e categoria.

## Risultato qualitativo principale

| Variabile | Rank IC media intraclasse vs rendimento futuro netto 21 sedute | Spearman medio vs score XGB |
|---|---:|---:|
| log-vol63 tradizionale | **−0.00027** | **+0.68133** |
| log-vol63 normalizzata entro categoria | −0.00027 | +0.39425 |
| Volatilità ortogonale `cs_orthog` | **−0.01311** | +0.17094 |
| Volatilità conditional annuale | **−0.01482** | +0.28965 |
| Momentum63 | +0.00670 | +0.30838 |
| Accelerazione 21 vs precedenti 42 | +0.03327 | −0.06259 |
| Trend t-stat 63 | +0.02607 | +0.14785 |
| Quota giorni positivi 63 | +0.02263 | +0.20708 |

L'associazione del raw `vol63` con il rank futuro è prevalentemente **tra categorie** (IC globale +0.04867), non dentro la categoria (−0.00027). La residualizzazione riduce la forte associazione col punteggio originale XGB, ma **non produce da sola un segnale positivo di rendimento**. Piccoli IC negativi non provano che filtrare alta vol residuale migliori il CAGR; sono solo medie retrospettive.

**Blocco bootstrap date (3 mesi, 5000 repliche, CI 95% descrittivi e non corretti per multiplicità):** IC intraclasse `cs_orthog - raw` = −0.01284, CI [−0.04305,+0.01202]; `vol_conditional - raw` = −0.01455, CI [−0.02936,−0.00090]. Estrema cautela: Original149 è un dataset esplorato intensivamente, 113 mesi non 16.837 prove indipendenti; nessuna rilevanza futura dimostrata.

## Audit numerico

- **678** coppie month-end/categoria 2017–2026, e **274** hanno design matrix non a rango pieno (collinearità signed/abs momentum), quindi usare proiezione sul sottospazio SVD a rango effettivo, non coefficienti nominali non identificabili.
- Correlazione lineare max assoluta `cs_orthog` vs ciascuno dei sei momentum standardizzati, per mese e categoria, **2.21e−13** (per costruzione). Non chiamare questo un test predittivo.
- **Importante difetto di generalizzazione dell'alternativa annuale**: correlazione assoluta Pearson residua *media* con singoli momentum per categoria/mese **0.26–0.30**, con massimi fino a ~0.92; `vol_conditional` non soddisfa il vincolo di ortogonalità stretta.
- **Independent audit PASS**: **31** proiezioni rifatte con SVD indipendente (max errore 2.36e−13), **24** misure ricomputate dai Close Yahoo (max errore 1.60e−16), 10 cutoff annuali causalmente antecedenti, nessuna key duplicata.

## Diagnostica della forma e del rischio di coda

Si divide descrittivamente la forma in "regolare" se ultimi 63 giorni: quota positivi ≥50%, e quota massimo salto giornaliero sotto la mediana della categoria. All'interno di ciascun settore/mese, la volatilità residua è alta vs bassa rispetto alla mediana. Nei gruppi *regolari* l'incidenza di outcome nel decile peggiore passa da **8.39% (vol residua bassa)** a **13.21% (alta)**; in gruppi *non regolari* da **7.29%** a **11.27%**. Le medie dei rendimenti forward 21d (non CAGR) sono rispettivamente regular **+0.431% vs +0.246%**, irregular **+0.666% vs +0.675%**. Diagnosi descrittiva esplorativa, non guida operativa o prova di significatività.

**Variazione temporale dei legami con la forma:** IC acceleration2017–2021 circa −0.002, 2022–2026 +0.072; trend t-stat +0.038 vs +0.013. Non codificare uno switch di regime da questi due segmenti dopo averli esaminati.

## Valutazione per competenza — criteri indipendenti, non agenti autonomi

- **Machine learning:** preservare la scelta di opportunità estreme, non cambiare con un ranker "più stabile" che abbatta alpha. `cs_orthog` è ortogonale linearmente ma rimane potenzialmente dipendente nonlinearmente; Compact21 e MA3 contengono già momenta/efficienza/accelerazione, quindi successiva *ablation controllata* deve dimostrare informazione incrementale, evitando feature duplicate e fit su futuro.
- **Econofisica:** curvatura, costanza direzionale, salti, regime high-dispersion, skew/tail downside e vol-of-vol, non soltanto sigma. La maggiore frequenza dei peggiori risultati con alta vol residua suggerisce una possibile funzione di *tail risk*, non automaticamente di comprare il titolo a volatilità bassa.
- **Statistica:** 113 periodi condivisi e stessa storia Yahoo; bootstrap per date, non righe/ticker; regressori collineari gestiti matematicamente, no tuning sul campione bruciato; differenza residual vs raw in generale **non dimostra** miglioramento futuro.
- **Risk management:** mantenere raw vol/downvol come indicatori di rischio e per sizing; giudizio finale soltanto sull'intera V2 e sulle stesse esecuzioni, valorizzazioni, gap, costi, turnover, drawdown **giornaliero**. Non sostituire V2 con un Top1 proxy.

## Baseline economica completa e gate mancante

`compact21_stability_v1/results/FULL_REPLAY.json`, BASE V2 full sui 3 Yahoo revisited, **già calcolato precedentemente**:

| Versione | CAGR | MaxDD | Sharpe | turnover annuo |
|---|---:|---:|---:|---:|
| Repeat1 | **29.753%** | −34.862% | 1.046 | 12.944× |
| Repeat2 | **30.844%** | −25.690% | 1.087 | 12.960× |
| Repeat3 | **34.677%** | −36.098% | 1.183 | 13.231× |

**Il Golden Annual V2 43.146% / DD ~−25.04% resta un risultato storico da riconciliare per artifact, codice, dati ed engine**, non ricalcolato in L2-M. Nessun modello che utilizza le nuove variabili L2-M è stato immesso nell'intera V2, dunque **non esistono nuovi CAGR, DD giornalieri o costi da riportare**. Sono prerequisiti per giudicare un challenger prima della produzione.

**Prossimo gate sensato:** recupero end-to-end bit/fingerprint-comparabile Golden 43% e spiegazione delle differenze rispetto ai 29.8–34.7; quindi **un solo challenger** che aggiunga residual-vol/shape come segnale di *rischio condizionale*, non volatilità bassa come veto, lasciando invariati ranking V2, MA3, HighCAGR24, V6 e accounting. Confronto paired same-data su rischio rendimento completo e stabilità; senza prospective data rimane ricerca.

## Artefatti

Full reproducibility ZIP `ETF_Trader_L2M_volatilita_ortogonale.zip` allegato in conversazione: `l2m_run.py`, `l2m_independent_audit.py`, `RESIDUAL_VOL_PANEL.csv.gz` (16.837 righe), `MONTHLY_DIAGNOSTICS.csv`, `CROSS_SECTION_ORTHOG_AUDIT.csv`, `FACTOR_CORRELATION_AUDIT.csv`, `ANNUAL_PAST_ONLY_FIT_AUDIT.csv`, `BLOCK_BOOTSTRAP_IC.csv`, `SHAPE_RESIDUAL_STRESS.csv`, manifests, risultati, log (14 files), SHA256 `bfcc6fd7864c348c70d893210b435e92a3f02756b60fc6ded81a878815b847e4`. Raw Yahoo e original XGB labels restano congelati nei precedenti artifacts, non duplicati nel pacchetto.
