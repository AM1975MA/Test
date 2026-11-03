# OLC44-A — Primo gate supervisionato causale (3 novembre 2026)

**Esito GitHub Actions: PASS. Decisione: NO PROMOTION. Questo è un *diagnostico economico con AUTH*, non la riproduzione né il riaddestramento nativo completo di OLC19.**

## Conclusione in parole semplici

Il modello impara a muoversi raramente. In Europa indovina due delle sole tre sostituzioni, e il vantaggio lordo annuo simulato della coppia è piccolo; negli USA tutte e tre le sostituzioni peggiorano. Il risultato è coerente con **scarso segnale trasferibile**, NON con un passaggio robusto dal 23% al 50%.

## Input, regole e controllo temporale

- Riferimento frozen: 96 mesi/mercato con top1, top2 e rendimenti futuri dell'analisi **OLC35 AUTH** (48 date × 2 mercati, 2021–2024). Non è il ranking esatto OLC19 FULL e non contiene NAV, stop, V6, costi di ribilanciamento.
- ETF aggiunti: EU `G2X.DE`, `USPY.DE`, `WTIC.DE`, `2B76.DE`; USA `BOTZ`, `LIT`, `PAVE`. `CMOD.MI` escluso per dati High/Low non idonei al motore di stop.
- 4 feature calcolate esclusivamente sul prezzo di chiusura fino alla data del segnale: log momentum a 63 sedute, log momentum a 126, volatilità degli ultimi 63 rendimenti giornalieri, drawdown su 63. Minimo 500 osservazioni realmente esistenti. **Nessuna identità del ticker** come feature.
- Unico modello predefinito: scaler fit su train + Ridge alpha30, uno per mercato. Target `log_forward_new - log_forward_incumbent2`. Dati addestramento solo se `exit_date < signal_date corrente`; verificato nei log.
- Sostituzione di **una sola seconda posizione** se il vantaggio predetto supera lo 0,005 log (50 bp/mese). Finestra di test: gennaio 2022–dicembre 2024, 36 segnali per mercato, con almeno 10 mesi passati maturati. Nessun fitting sul futuro del singolo mese.
- Pesi mensili 50/50 e comparazione lorda `log(.5exp(r1)+.5exp(r2))`; un separato stress applica **20bp per sostituzione**. Non include l'intero ledger OLC19, V6, costi di negoziazione del resto del portafoglio o stop, per cui il CAGR qui non è mai definibile `CAGR OLC19`.

## Risultato economico dello *stesso proxy AUTH* (2022–2024)

| Metrica | EU | USA |
|---|---:|---:|
| Segnali mensili | 36 | 36 |
| Switch | 3 | 3 |
| Switch corretti | 2 | 0 |
| CAGR lordo AUTH Top2 immutato | **28,7117%** | **50,3743%** |
| CAGR lordo con Ridge | **29,4163%** | **44,0939%** |
| CAGR proxy dopo 20bp per switch | **29,1577%** | **43,8060%** |
| Differenziale paired logaritmico medio | **+4,549bp/mese** | **−35,552bp/mese** |
| IC95% bootstrap circolare 6 mesi su differenziale | **[−11,691; +24,261] bp/mese** | **[−82,823; 0,000] bp/mese** |

**Interpretazione:** l'Europa migliora meno di 1pp di CAGR lordo, con un intervallo che comprende danni; il peggioramento USA è importante in termini economici e mostra che i filtri appresi non generalizzano automaticamente. Non sono 36 esperimenti indipendenti; i 36 mesi sono l'unità temporale e l'intero periodo è già stato studiato ripetutamente.

I risultati sono archiviati in `results/olc44_summary.csv`, `results/olc44_annual_proxy.csv`, `results/olc44_prequential_monthly_decisions.csv`, `results/olc44_training_maturity_audit.csv`, `results/candidate_asof_feature_and_forward_audit.csv`, `results/olc44_manifest.json`. Codice `olc44_prequential_gate.py`, protocollo GitHub Actions [run 41732239967](https://github.com/AM1975MA/Test/actions/runs/41732239967).

## Gate di riproduzione nativa OLC19: tuttora non superato

Il checkpoint originale OLC19 riproduce esattamente i rendimenti di esecuzione originale ma ha **score e selezioni congelati per l'universo precedente**. Per 4 nuovi ETF EU e 3 USA servono i 42 input Hybrid, Return125, i fit annuali ET/XGB dei rami di previsione 21/42/63 e tutta la catena di ranking, aggregazione, memoria e V6/stop ricostruita senza cambiare definizione. Il solo fitting Ridge qui non è un sostituto di questa catena.

Il rapporto OLC14 della Library documenta 480 nuovi modelli elementari, 42 input Hybrid, 3 seed e l'uso di artefatti originali di grandi dimensioni: **non è stato ancora eseguito un refit equivalente con strumenti nuovi**. Non usare proxy a 4 feature per certificare il CAGR di OLC19 expanded.

## Decisione per il successivo passo

Nessuna promozione. Prima di un OLC19 nativo ampliato sono necessari test di parità delle feature su **tutti i vecchi ticker** (prima di aggiungere nuovi), distribuzioni adjusted price coerenti, serie per fondi che rispettino i lookback, rifit annuale solo su etichette maturate e parità del motore. Una volta raggiunta parità perfetta di vecchi score/decisioni, l'effetto *solo universo ampliato* sarà attribuibile.

Il presente passo ha falsificato l'ipotesi forte che un semplice supervisore low-dimensional possa produrre immediatamente il salto al 50%; non prova che nessun ML o feature nascosta possa riuscirci.
