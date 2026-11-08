# OLC72 — Test nativo Return125 *family-aware*, controllo USA ed importanza condizionale approssimata

**8 novembre 2026 · Stato: COMPLETO, CONTROLLI PASSATI, NESSUNA PROMOZIONE**  
Periodi 2019–2026 già ampiamente esplorati: tutti i risultati sono retrospettivi, non prove di alpha fuori campione. OLC19, OLC67 e `main` non modificati.

## Risposta sintetica

L'ipotesi di aumentare la qualità economica del ramo Return125 **senza aggiungere feature o cambiare la FUSION**, ma equilibrando le probabilità di campionamento XGBoost delle 46 famiglie economiche, è stata testata su entrambi i mercati con la ricetta nativa originale e **30 refit annuali** (2021–25, tre seed per mercato/anno). La FUSION originale resta superiore sul MAIN 2021–24. In 2025 il candidato è migliore staticamente, ma quell'anno è già esplorato, e la conclusione non è stabile per tutti gli anni precedenti. Nessun nuovo CAGR viene dichiarato: non è stato autorizzato un replay OLC19 poiché il gate di qualità Top2 è fallito.

## 1. Recupero dei modelli nativi USA e riproducibilità

I modelli USA **originali** si trovano in `parents/fits/USA/BASE/{year}/RETURN_{seed}.ubj` nei due volumi del checkpoint OLC08F; i modelli EU in `fits/EU/R_RSI_DOMAIN/{year}/RETURN_{seed}.ubj` nel pacchetto RSI. Abbiamo verificato che i due insiemi riproducono esattamente `RETURN` e `FUSION` OLC19 su **120 market-month**, 60 per ciascun mercato, per 2021–25. Su **18.216 righe originali** la parità degli score Return è esatta.

In aggiunta, un refit **senza nessuna modifica** di un modello originale seed101 nel 2024, effettuato riproducendo gli input X, XP, le etichette, i gruppi e l'intera ricetta nativa, ha dato **errore massimo prediction = 0.0** sia EU sia USA. Questo rende attribuibile l'esperimento successivo all'unico intervento di campionamento. È stato recuperato il codice storico: non utilizzare la configurazione mostrata da un Booster UBJ *ricaricato* per inferire gli iperparametri di training, perché il caricamento reimposta diversi parametri di training ai default.

### Parametri rimasti immutati

Return XGB `rank:ndcg` con relevance 0..15 costruita per ogni mese con la differenza economica normalizzata `(r - mediana)/(q90 - q10)` e clipping, labels disponibili solo dopo `exit_date_21`, `ndcg_exp_gain=False`, pair method `topk` con 5 coppie, 360 round, max_depth=4, eta=.035, subsample=.85, colsample_bytree=.8, min_child_weight=8, lambda=8, alpha=.1, seed 101/202/303. Tutti i 125 input restano identici, compresi NaN e ordine. Le altre previsioni ET/XGB Hybrid42, memoria e FUSION 0.475/0.525 sono congelate.

**Unica modifica:** in XGBoost DMatrix, per la feature j appartenente alla famiglia f con `k_f` colonne di tipo RAW/PCT/DEV si imposta `feature_weights[j]=1/k_f`, in modo che ciascuna delle 46 famiglie abbia la stessa massa *attesa* nel campionamento dell'80% delle feature per albero. La procedura non costringe il modello a usare le famiglie in modo uniforme: può legittimamente sceglierne alcune più spesso o con gain maggiore.

## 2. Rendimento futuro Top2, test principale 2021–24

| Mercato | FUSION originale 21d | Family-aware 21d | Δ 21d pp | Orig. 42d | Family-aware 42d | Persistenza Orig. → Family |
|---|---:|---:|---:|---:|---:|---:|
| EU | 2.131% | 1.941% | -0.190 | 3.754% | 3.825% | 33.3% → 30.2% |
| USA | 3.501% | 2.867% | -0.634 | 3.899% | 3.130% | 24.0% → 21.9% |

**Esito:** fallisce il criterio predefinito di miglioramento Top2 contemporaneo in EU e USA. A 21 sedute, la differenza in EU è -0,190 pp, USA -0,634 pp. Le CI descrittive bootstrap a blocchi sei mesi includono zero per il vantaggio di rendimento, ma il segno medio sfavorevole in entrambi i mercati è sufficiente per respingere il gate preregistrato; la MSE della futura forza relativa non è stata addestrata nuovamente, perché l'obiettivo è il ranking nativo.

## 3. Anni singoli, inclusi 2024 e 2025

| Mercato | Anno | Originale 21d | Family-aware 21d | Δ pp | Originale 42d | Family-aware 42d |
|---|---:|---:|---:|---:|---:|---:|
| EU | 2021 | 1.51% | 1.87% | +0.36 | 3.60% | 3.76% |
| EU | 2022 | 3.01% | 2.66% | -0.35 | 3.45% | 3.78% |
| EU | 2023 | 2.20% | 1.71% | -0.49 | 4.21% | 4.73% |
| EU | 2024 | 1.80% | 1.52% | -0.28 | 3.76% | 3.03% |
| EU | 2025 | 1.50% | 2.29% | +0.78 | 3.48% | 4.04% |
| USA | 2021 | 0.85% | -1.22% | -2.07 | 3.59% | 1.37% |
| USA | 2022 | 4.26% | 5.46% | +1.20 | 3.24% | 4.45% |
| USA | 2023 | 4.03% | 2.67% | -1.37 | 6.34% | 4.42% |
| USA | 2024 | 4.85% | 4.55% | -0.30 | 2.42% | 2.28% |
| USA | 2025 | 2.00% | 3.44% | +1.44 | 5.03% | 5.85% |

Il 2024 è importante: il candidato peggiora il Top2 a 21 sedute in entrambi i mercati. Nel 2025 si osserva un'inversione favorevole, EU 1.50%→2.29%, USA 2.00%→3.44%, ma questo **non è** un holdout mai esaminato. Le previsioni 2025 sono cronologiche, però la scelta dell'ipotesi e decine di esperimenti precedenti hanno già utilizzato lo stesso periodo. Nessuna selection policy 2026 o rendimento 2026 è simulato da OLC72.

## 4. Bilanciamento della massa di campionamento ≠ bilanciamento delle importanze economiche

- **EU:** concentrazione del gain delle cinque famiglie principali: 27.4% originale contro 31.9% candidate; numero efficace per HHI 31.7 → 28.3. Tutte e 46 le famiglie presentano gain positivo nei modelli originali e nuovi.
- **USA:** concentrazione del gain delle cinque famiglie principali: 30.0% originale contro 30.2% candidate; numero efficace per HHI 29.5 → 29.6. Tutte e 46 le famiglie presentano gain positivo nei modelli originali e nuovi.

Questo dimostra che la ridondanza **non si risolve semplicemente equalizzando la probabilità d'accesso agli alberi**. In EU, dopo il campionamento bilanciato, il gain appreso risulta anzi più concentrato. `total_gain` degli split non è importanza causale né garanzia di generalizzazione.

La variante cambia la coppia Top2 nel 2021–24 in 25/48 mesi EU e 30/48 mesi USA: l'intervento non è cosmetico, ma non porta un miglioramento economico stabile.

## 5. Test originale nativo USA + perturbazioni condizionali abbinate

OLC71D aveva perturbato indipendentemente dalle altre feature, per famiglia, modelli originali europei. OLC72 usa i modelli **originali EU e USA** e modifica RAW/PCT/DEV congiuntamente, scegliendo per ogni ETF uno dei cinque donatori più vicini **nella stessa data** rispetto alle altre 45 famiglie RAW (ordinamenti normalizzati per data, missing median-neutral soltanto per il matching; il modello riceve i valori originali del donatore). Due seed fissi; sei famiglie già emerse in OLC71, non scelte sulla base degli outcome di OLC72. 6 famiglie × 2 repliche × 12 mesi × 5 anni × 2 mercati = **1.440** valutazioni mensili. Il bootstrap ricampiona i **48 mesi**, mai le 96 repliche come se fossero indipendenti.

La procedura riduce distorsioni di un cambio arbitrario delle rappresentazioni ma NON è un vero conditional-knockoff generativo: possono comunque essere introdotti vettori fuori distribuzione. La differenza tra rendimento Top2 originale e matching **non è un contributo causale**.

### Differenziale Top2 21 sedute originale meno matching (2021–24)

| Mercato | Famiglia | Δ originale−matched, pp | IC 95% a blocchi, pp |
|---|---|---:|---:|
| EU | `acc_mom_21_63` | +0.200 | [-0.069; +0.524] |
| EU | `acc_mom_5_21` | -0.074 | [-0.350; +0.287] |
| EU | `beta_mkt126` | -0.075 | [-0.399; +0.172] |
| EU | `mom5` | +0.087 | [-0.421; +0.677] |
| EU | `vol21` | +0.162 | [-0.112; +0.569] |
| EU | `vol63` | +0.064 | [-0.219; +0.324] |
| USA | `acc_mom_21_63` | +0.131 | [-0.302; +0.561] |
| USA | `acc_mom_5_21` | +0.109 | [-0.618; +1.101] |
| USA | `beta_mkt126` | +0.243 | [-0.144; +0.690] |
| USA | `mom5` | +0.112 | [-0.219; +0.434] |
| USA | `vol21` | +0.209 | [-0.185; +0.704] |
| USA | `vol63` | -0.393 | [-1.176; +0.048] |

**Tutte le CI al 95% contengono zero.** Alcuni risultati di OLC71D in EU si ridimensionano quando si rispetta la somiglianza con il resto delle feature, es. `acc_mom_21_63` da +0,45 a circa +0,20 pp; per altre famiglie il segno cambia. Non esiste un insieme di famiglie emerso con importanza condizionale positiva e stabile e replicata in EU/USA. Le sei famiglie erano state selezionate alla luce degli esiti EU OLC71D, quindi non sono ipotesi indipendenti.

## 6. Decisione e ricerca successiva

- Nessuna nuova strategia promossa. **OLC19** resta baseline operativa congelata; **OLC67** resta un candidato di ricerca da verificare prospetticamente.
- Dalle 125 feature provengono segnali realmente usati, ma un equalizzatore semplice del campionamento non dimostra rendimento incrementale robusto. È invece plausibile che alcune **interazioni fra famiglie** e la loro **validità temporale** siano la parte delicata della generalizzazione.
- Per ulteriori esperimenti, prima di aggiungere un learner, verificare quali interazioni *tra famiglie* conservano valore predittivo su finestre non utilizzate dalla ricerca e con distanze temporali; ma lo storico 2019–26 è già stato fortemente esplorato, quindi il risultato resterebbe esplorativo.
- Se la variante non supera la gate sul Top2, non si deve calcolare un CAGR inventato: servirebbe il vero replay `TOP2_CONTEXT_REVALUE → V6 → FAST_LOCK3` con costi e stato di rischio, eseguibile soltanto dopo aver superato il filtro.
- Dati OHLC non ricertificati per adjustment/total return, universe point-in-time e delisting, originale maschera osservazioni USA, bid/ask/stop reali; riproducibilità computazionale non equivale a operatività verificata.

## 7. Riproducibilità e controllo indipendente

- Hash delle cinque sorgenti immutabili controllati contro protocollo.
- 120 market-month e 18.216 righe Return/FUSION originali riprodotte esattamente per 2021–25, entrambi i mercati.
- 2024 native XGBoost seed101 riaddestrato senza modifica: **zero differenze** dall'originale USA e EU.
- 30 nuovi booster family-aware salvati, ricaricati per controlli indipendenti su 2021/2024/2025, 240 coppie Top2 verificate e payoff confrontati con OLC72_MONTHLY.
- 1.440 perturbazioni abbinate, doppia verifica di Top2/changement e CI bootstrap a 48 eventi per mercato.
- Fonte: checkpoint OLC08F, RSI e OLC19 già nella Library; non sono duplicati nel nuovo ZIP da decine di MB.
- GitHub branch `research/olc72-return125-family-aware-20261108`, pre-registrazione prima dei 30 fit e delle perturbazioni, protocollo commit `3d9b9aef78cfaafa2d295270a4bf0ed6def0e153`.