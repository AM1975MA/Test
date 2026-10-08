# L2-M — Volatilità ortogonale al momentum e audit della forma del trend

**Protocollo fissato il 2026-10-08 prima del primo calcolo L2-M.** SOLO repo `AM1975MA/Test`, branch `research/target-redesign-level2-v1`; `Etf_trader` invariato. Non si cercano iperparametri, pesi o soglie che massimizzino CAGR. Campione Original149 già esplorato => diagnostica, NON holdout.

## Ipotesi dell'utente
La volatilità non deve fungere da surrogato del momentum. Conserviamo separatamente: (a) momentum/direzione su 21/63/126 sedute; (b) variabilità assoluta per rischio e dimensionamento; (c) volatilità relativa/residuale che rimane dopo aver rimosso in modo causale le componenti spiegate da momentum positivo/negativo e sua ampiezza. La costanza e la forma del movimento sono descrittori **distinti da un semplice rapporto momentum/volatilità**.

## Metodo fisso e due diagnostiche complementari
Prezzi adjusted Close dall'archivio Yahoo Repeat2 `11272972639`, 149 ETF Original149, tutte le date month-end SPY dal 2010, features solo osservate al signal time. Valutazione matched e label 21 sedute maturata: 113 date Feb2017–Jun2026 e 16,837 (data,ETF) congelate in L2-L/L2-D. Tag categorie 2026: attenzione al survivorship. Nessun accesso a rendimenti futuri durante preparazione/features.

Feature predefinite: `mom21, mom63, mom126` = somma log return giorni precedenti, `vol63` = std campionaria ddof0 dei 63 log return; volatilità residualizzata sui **sei** regressori `signed_mom21, signed_mom63, signed_mom126, |mom21|, |mom63|, |mom126|`, per categoria e mese. Evitare `vol/mom` perché diverge con momentum vicino a zero.

Metodo principale `VOL_ORTHOG_CS`: per ogni data *e categoria* standardizzare dentro il gruppo **log(vol63)** e i 6 regressori (z-scores mean0, std1) e calcolare il residuo OLS con intercetta, senza usare il target futuro. Usare `np.linalg.lstsq` con tolleranza numerica predefinita; per gruppo <10 osservazioni finite / rank insufficiente, fail-closed. Questa costruzione è **ortogonale PER DEFINIZIONE** soltanto alle sei colonne sui dati contemporanei; non costituisce prova di indipendenza statistica o forza predittiva.

Metodo secondario `VOL_CONDITIONAL_OOS`: per ogni 1 gennaio anni 2017–2026, fare fit su soli month-end precedenti con storia 126-sessioni valida dal 2010; target = percentile intragruppo di log(vol63), regressori = percentili intra-categoria signed e absolute momentum (6), one-hot categorie incluse. `SimpleImputer(median)->StandardScaler->Ridge(alpha=100)`, fit soltanto sulle date passate, senza etichette future; predire l'anno di valutazione, residualizzare `vol_conditional=y - yhat`. È un controllo della decorrelazione effettivamente fuori periodo: non aspettarsi residui a correlazione zero.

## Controlli e interpretabili
- Reconciliare tutte le chiavi L2-D/L2-L, 149×113, 0 duplicati, input SHA.
- `VOL_ORTHOG_CS`: max |correlazione Pearson| intra-data/categoria con 6 regressori <1e-10; testare ridge rank condizione OLS, numero ETF validi e dispersione residua. Dichiarare la proprietà tautologica di costruzione.
- `VOL_CONDITIONAL_OOS`: Spearman medio e massimo e legame residuo con fattori signed/abs; nessun fitting sul futuro e audit date train max < cutoff.
- Predizione SOLO DIAGNOSTICA: IC intra-categoria mensile verso rendimento Open→Open netto 21 sedute, più differenze fra 2017–21 e 2022–26; valutare `vol_raw`, `vol_orthog`, `vol_conditional`, momentum 63, `trend_t_63`, accelerazione e la differenza di performance fra alta e bassa volatilità residua all'interno di trend regolari/irregolari (gruppi predefiniti). Non creare nuove regole investibili.
- Score esistente XGB e feature base: misura Spearman di vol osservata/residuale rispetto a score XGB; non aspettarti decorrelazione dal punteggio XGB, che incorpora molti segnali.
- Paired **monthly** moving block bootstrap 3 date, 5000 draws seeded, difference IC orthog vs raw within-category e conditional vs raw; CI descrittivi, ripetuti test Original149 => nessuna evidenza conclusiva di alpha.
- Econofisica: statistiche di `trend_t`, `single_jump_share`, accelerazione, volatilità residuale per macro-categoria e high/low SPY-vol precedente; rischio di tails. Nessun regime-switch adattato sulla storia.
- ML: rappresentazione ortogonalizzata, collinearità numerica, train-only feature transforms e ridondanza con 125 Compact21+42 MA3 features; nessun fit del modello selettore oggi.
- Portfolio/risk: preservare raw vol/downvol per Stop/MA3; nessun proxy Top1 come giudice del CAGR. Gate non assolto: recupero Parquet/config e replay golden V2 43.146% con identici dati/code/engine, verifica CAGR, daily-DD, trading costs e tre vintage. È un lavoro distinto dal calcolo L2-M. Nessun successo su ranking autorizza la sostituzione della V2.

In caso di coefficenti non identificabili, sample eligibility scarso o contrasto nullo, riportare fallimento e non ottimizzare al volo. Consegnare Python riproducibile, panel, metriche/QA, report e decisione.
