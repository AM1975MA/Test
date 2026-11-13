# OLC103 — Stabilità del Top2: capacità predittiva residua e gestione del rischio

**13 novembre 2026 · Risultato retrospettivo, solo ricerca. Nessuna promozione del modello o trading live.**

## Sintesi

La stabilità della coppia OLC19 attraverso le due chiusure successive **non fornisce, nella formulazione testata, un beneficio predittivo incrementale verificabile** rispetto a score iniziale, margine di classifica, trend, volatilità, andamento dei due giorni e stato V6. La media dei rendimenti dei mesi stabili è superiore, ma i mesi stabili sono soltanto 11 in Europa e 14 negli Stati Uniti e gli intervalli attraversano lo zero.

Nel replay nativo, senza mai cambiare ETF, l’overlay che limita al 75% l’esposizione effettiva `g` se la coppia diventa instabile riduce MaxDD ma sacrifica CAGR. Un cap permanente al 75% riduce ancor più il drawdown: **non è dimostrato che sia la stabilità a identificare il rischio**, anziché la minore esposizione. Nessuna strategia viene promossa.

## 1. Controlli e dati

- Checkpoint congelati OLC19/OLC67/OLC102, veri ranking contestuali giornalieri da modelli annuali originali. Al segnale iniziale, le 90 coppie EU e le 90 USA coincidono con i file OLC19. Le due chiusure successive sono usate **solo dall’apertura seguente** (terza apertura).
- 89 decisioni mensili mature per mercato, da segnale 31/01/2019 a 29/05/2026. Due eventi UE con maschere incomplete vengono esclusi dai test predittivi: 30/09/2019 e 30/04/2020. Restano nella ricostruzione del conto storico, come negli archivi originali.
- I due ETF, il budget V6 di partenza, le politiche di stop FAST_LOCK3, le date e le politiche di allocazione sono identici per tutti i confronti. Variabile testata: *stabilità delle classifiche*; nei replay di rischio è consentito **solo** ridurre il budget con una regola fissa, non sostituire ticker.
- L’osservabilità originale completa delle quote USA e la reale eseguibilità degli stop non sono certificate. Il campione 2019–luglio 2026 è stato esplorato più volte: **non è un holdout vergine**.

## 2. Stabilità e rendimento successivo della coppia originale

Il segnale `retention` conta, su quattro possibili conferme (due ticker × due chiusure), quante volte i due ETF originari rimangono tra i primi due. La dicotomia `full_stable` vale 1 soltanto se entrambi rimangono Top2 in **entrambe** le sedute.

| Indicatore | Europa | USA |
|---|---:|---:|
| Eventi validi | 87 | 89 |
| Eventi pienamente stabili | 11 | 14 |
| Persistenza media (retention) | +48,3% | +49,2% |
| Log-rendimento medio coppia stabile | +4,23% | +4,06% |
| Log-rendimento medio coppia instabile | +1,13% | +2,12% |
| Differenza stabile – instabile, log-pp | 3,11 | 1,94 |
| IC95% descrittivo differenza, log-pp | [-0,12; +6,21] | [-2,45; +7,07] |
| Correlazione Spearman retention/rendimento | 0,047 | 0,024 |
| Rischio perdita >5%, stabile | +9,1% | +14,3% |
| Rischio perdita >5%, instabile | +17,1% | +14,7% |

I log-rendimenti rappresentano solo i due ETF originali dalla terza apertura all’apertura del segnale mensile successivo. Non sono CAGR del conto e non comprendono stop/costi. Le differenze sono fragili, incluse le differenze di rischio. Il campione stabile europeo non include alcuna osservazione nel 2023 e nel 2025.

## 3. Test di informazione incrementale — prequential, non tuning sul test

Fit cronologico indipendente per mercato, esempi di training con eventi fino a `j−2`, almeno 24 precedenti maturi e validi. Due modelli gemelli: **BASE** usa sei informazioni ex ante (score, margine Top2–Top3, mom21, vol63, ritorno delle prime due chiusure e gross preesistente); **BASE + STABILITÀ** aggiunge soltanto `retention`. Ridge α=10 per il rendimento relativo contro la mediana degli ETF osservati e regressione logistica C=0,5 per la probabilità di perdita inferiore a −5%. Imputazione e normalizzazione SOLO sul training. Nessuna selezione di parametri in base agli esiti.

| Mercato / metrica | Solo BASE | BASE + stabilità | Miglioramento (BASE − nuovo) | IC95% miglioramento |
|---|---:|---:|---:|---:|
| EU, MSE rendimento relativo (n=62) | 0,002102 | 0,002113 | -0,000010 | [-0,000083; +0,000072] |
| EU, Brier perdita >5% (n=62) | 0,118444 | 0,121090 | -0,002646 | [-0,004689; -0,000945] |
| USA, MSE rendimento relativo (n=64) | 0,005249 | 0,005369 | -0,000120 | [-0,000269; +0,000002] |
| USA, Brier perdita >5% (n=64) | 0,142237 | 0,148757 | -0,006520 | [-0,013910; -0,000549] |

**Risultato:** i quattro miglioramenti sono **negativi**, quindi la stabilità peggiora la qualità delle previsioni. Gli IC95% Brier descrittivi sono interamente inferiori allo zero, ma il bootstrap a blocchi di sei mesi non corregge i numerosi esperimenti precedenti: non è una prova formale di dannosità universale. Il test esclude comunque la promozione di questa feature sulla base dei dati disponibili.

## 4. Test economico con intero conto nativo

Il Top2 è sempre quello originale, e la terza apertura è comune a tutti. `g` è la variabile di budget rischioso **effettivamente letta** dal motore OLC19; `gross` è un input descrittivo V6 e modificarlo non produceva il cap desiderato. Tale errore di implementazione è stato identificato e documentato in addendum prima delle simulazioni economiche valide. Nessuna modifica alle regole V6/FAST_LOCK3 o ai ticker. Si confrontano BASE, cap a 75%/50% sempre, cap solo quando il Top2 è instabile, e cap 75% applicato ai mesi stabili come controllo direzionale.

### Baseline 50/50; fee 0,001 e stop friction 0,001 — FULL 2019–luglio 2026

| Politica | EU CAGR | EU MaxDD | USA CAGR | USA MaxDD |
|---|---:|---:|---:|---:|
| Controllo: nessun cap | +22,19% | -28,65% | +42,81% | -30,40% |
| Cap 75% se instabile | +18,68% | -23,09% | +35,60% | -24,04% |
| Cap 50% se instabile | +14,74% | -18,02% | +28,94% | -23,00% |
| Cap 75% in tutti i mesi | +17,21% | -21,88% | +34,43% | -23,42% |
| Cap 50% in tutti i mesi | +12,09% | -18,02% | +26,50% | -16,85% |
| Cap 75% se stabile (controllo inverso) | +20,67% | -27,56% | +41,57% | -30,40% |

Il cap ai mesi instabili riduce la crescita e il drawdown. Ma in EU il cap selettivo 75% ha esposizione media effettiva 79,35%, contro 76,84% del cap permanente; negli USA 80,23% contro 76,86%. **Non confrontare quei CAGR come se il rischio investito fosse identico.** Il modello cap sempre ottiene MaxDD più contenuto perché è più prudente. Nessun miglioramento netto di alpha economicamente dimostrato.

### MINVAR63 a terza apertura, stesso rischio e stesso costo

| Politica | EU CAGR | EU MaxDD | USA CAGR | USA MaxDD |
|---|---:|---:|---:|---:|
| Controllo MINVAR63, nessun cap | +22,10% | -26,51% | +42,43% | -27,72% |
| MINVAR63 + cap75 instabile | +18,57% | -21,82% | +35,24% | -23,05% |
| MINVAR63 + cap75 sempre | +16,90% | -20,47% | +33,94% | -21,34% |

Nota: questo controllo MINVAR63 ricalcola i pesi alla **terza apertura**; non coincide automaticamente con il candidato OLC67 ufficiale, che usa la convenzione originale dei pesi al segnale e il timing DELAY3 nativo. Il confronto within-table rimane contabile e a tempistiche uguali.

### Costi più elevati: fee 0,003, stop friction 0,005 (50/50)

| Politica | CAGR EU | CAGR USA |
|---|---:|---:|
| Controllo | +17,69% | +31,59% |
| Cap75 instabile | +14,11% | +25,71% |
| Cap75 sempre | +12,71% | +24,84% |

Il risultato qualitativo non cambia aumentando i costi: il cap riduce il rendimento medio del conto, oltre al drawdown. Gli intervalli appaiati per il cap75 instabile sul differenziale di log-rendimento annualizzato rispetto alla baseline sono:

- **EU:** -2,96% log annuo, IC95% [-6,10; +0,31] log punti; descrittivo, non corretto per più test.
- **USA:** -5,16% log annuo, IC95% [-9,40; -0,98] log punti; descrittivo, non corretto per più test.

![NAV Europa](results/OLC103_NAV_EU.png)

![NAV USA](results/OLC103_NAV_USA.png)

## 5. QA indipendente e limiti

- **48 replay nativi**, entrambi i mercati × due allocazioni × sei politiche × due costi, con controllo della parità del braccio originale OLC19 e V6 e dei controlli OLC102 FIXED_DAY2. Nessun cambio d’identità dei Top2 selezionati.
- Ricalcolo indipendente dalla NAV salvata: errore massimo CAGR `1.39e-16` e MaxDD `2.78e-16`. Il QA verifica anche che gli score delle due sedute successive non siano usati prima dell’apertura successiva.
- I due eventi europei con prezzi non osservati sono esclusi dalla competenza predittiva ma rimangono nel replay contabile: il replay è fedele al checkpoint, **non una certificazione delle sue quotazioni originarie**. Gli USA non possiedono la maschera genuina completa dei prezzi osservati.
- L’ingresso alla terza apertura è il medesimo per tutti i contrasti. Le stime di rischio usano barre OHLC storiche e ipotesi di prezzo eseguibile; niente ordini broker o risultati live. L’effetto di interventi sullo stesso motore a prezzi esogeni è causale **solo dentro il simulatore**.
- I dati economici sono retrospettivi e oggetto di molteplici iterazioni OLC01–102; gli intervalli bootstrap sono descrittivi e non garantiscono replicabilità futura.

## 6. Decisione

**Non promuovere la stabilità del Top2 né come feature predittiva aggiuntiva né come trigger di esposizione.** La stabilità completa è troppo rara e il test prequential peggiora l’errore su entrambi i mercati; gli overlay di rischio riducono l’esposizione, ma non hanno dimostrato alpha incrementale rispetto a un semplice cap non condizionato. Conservare OLC19 come baseline, OLC67 come candidato originale già congelato, senza modificarne ranking, allocazione, timing o FAST_LOCK3. Qualsiasi nuovo uso della persistenza richiede previsioni registrate prima degli outcome su dati veramente successivi al freeze e uno stato contabile eseguibile certificato.

## 7. Riproduzione e file

Dipendenze: checkpoint OLC19, sorgenti OLC102 e file EU/USA `DAILY_CONTEXTUAL_RANK.pkl`; vanno risolti in una directory locale prima di eseguire. `run_olc103.py` e `verify_olc103.py` sono script documentali ancora con i path di lavoro originali; il pacchetto include snapshot dei rank, dati delle decisioni, predizioni out-of-training, NAV nativa, contatori, serie mensili, due protocolli addendum, SHA256 e figure.
