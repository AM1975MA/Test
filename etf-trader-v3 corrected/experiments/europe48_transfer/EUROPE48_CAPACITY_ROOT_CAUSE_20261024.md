# EU48 V3 — audit causale codice, selezione Top1 e sovradattamento, 24 ottobre 2026

**Status:** analisi sorgenti completata e diagnosi 2022 riprodotta con cinque diverse capacità XGBoost. Nessuna modifica al codice operativo V2/V3, nessuna promozione di un nuovo numero di foglie.

## Sintomo verificato su identica contabilità in EUR

Benchmark EU48 certificato a un solo conto, 48 ISIN strettamente europei, prezzi adjusted Open in EUR, 65 segnali gennaio 2021–maggio 2026, ingressi next-open, 10 bp one-way, 1.374 sedute 2021-02-01–2026-07-01.

| Strategia separata da Stage19 | CAGR | MaxDD |
|---|---:|---:|
| Compact125 / precedente ranker depth4 | +4.7279% | -25.8932% |
| V3 127-leaf ranker, senza meta | -0.2257% | -41.1836% |
| V3 ranker + NESTED_24_TOP1_GUARD | +4.7060% | -41.1836% |

La V2 Stage19 completa (-0.1549% CAGR) NON costituisce un confronto omogeneo per la presenza degli ulteriori layer. Il ranking standalone, invece, usa identici prezzi, universo, costi, orizzonte ed allocazione e riproduce il predecessore entro 1e-10: perdita relativa reale.

## I due errori di selezione principali nel drawdown

Il MaxDD V3 Top1 si realizza il **13 ottobre 2022**. Il conto V3 sceglie:
- **31 maggio 2022, ZPRP.DE** (FTSE EPRA Real Estate Europe ex-UK), rendimento netto del mese di detenzione **-18.545%**; l'originale preferiva **XS7R.DE** (target forward 21 sedute -8.787%).
- **31 agosto 2022, IQQP.DE** (iShares European Property), rendimento netto del mese di detenzione **-15.346%**; l'originale preferiva **EXH5.DE** (target forward 21 sedute -4.557%).

Questi due investimenti immobiliari concentrano una parte rilevante dell'errore di scelta; le due sole perdite composte equivalgono a circa -31.0% del capitale attraversato da entrambe. **Non è stato simulato alcun risk overlay** e in entrambi i mesi la policy `NESTED_24_TOP1_GUARD` era inattiva (nessuna configurazione meta ancora scelta). Perciò il MaxDD del modello con/senza decision tree è IDENTICO.

## Review del sorgente: cosa cambia, e cosa NO

1. `v3_europe48_heads.py`: `params = dict(k.COMPACT_PARAMS, max_depth=0, grow_policy="lossguide", max_leaves=127)`. Rispetto a `k.COMPACT_PARAMS` originale (`max_depth=4`), questa sostituzione abilita profondità non limitata e fino a 127 foglie. **360 boosting round, 3 seed e 125 feature rimangono identici.**
2. Stesso `k.add_labels(..., Open, ...) `: outcome 21 sedute da successiva apertura a uscita after 21 sessions, e `target_rank_21` per data. Criterio corretto dal più basso al più alto; non è emersa inversione dei label.
3. Verificata identità di `signal_date, ticker, fwd_ret_21` fra output V3 e Compact125 su tutti i 65 mesi. Il nuovo esperimento 2022 confronta anche punteggi rigenerati: **zero variazioni Top1** contro i file originali depth4 e 127-leaf; raw MAE circa 4.5e-17 (vecchio) e 2.3e-9 (V3).
4. Quotazioni EU realmente Open EUR con SPY americano solo come fattore esplicativo *precedente* all'apertura europea. Il replay economico V2 precedente è riprodotto numericamente. Non sono emersi indizi di uno sfasamento future labels o di un bug nei trade cost.
5. `v3_europe48_meta_economics.py`: il meta-tree costruisce 500 panieri molto sovrapposti e deduplica le coppie ETF al training; richiede **almeno 24 mesi meta OOS** e altri 60 giorni di maturazione. Non può intervenire prima del 2023. Tale scelta protegge la causalità ma lascia scoperto esattamente il 2022.
6. I panieri con solo 48 ETF non generano 500 decisioni indipendenti: nel primo fit meta utile del 2023, 25 date contengono solo 621 eventi coppia/data deduplicati, circa 25 per mese. Questo limita notevolmente la capacità di apprendere con alberi profondi.

## Test sperimentale diagnostico 2022: variare solo capacità XGB

[Workflow riuscito e log integrali](https://github.com/AM1975MA/Test/actions/runs/40111851199);
[artifact 12 file](https://github.com/AM1975MA/Test/actions/runs/40111851199/artifacts/12566957443).

Training 58 mesi (2017–2021), **2.784 righe** ma soltanto 58 segnali temporali. Inferenza OOS 12 mesi (2022), 576 scelte ETF. 3 seed, 360 rounds, 125 feature, target e prezze/costi identici. La ricostruzione dei due modelli già certificati ha PASSATO la verifica del Top1 di ogni mese.

| Capacità consentita | Foglie realmente utilizzate per albero (ultime 60 iterazioni) | Spearman TRAIN | Spearman OOS 2022 | Rendimento netto conto Top1 sui 12 segnali 2022 |
|---|---:|---:|---:|---:|
| XGB depth 4 originale (max 16) | 11.97 | .9577 | .0909 | **+24.134%** |
| loss-guide 15 foglie | 15.00 | .9644 | .0661 | +30.432% |
| loss-guide 31 foglie | 31.00 | .9679 | .0867 | +18.223% |
| loss-guide 63 foglie | 55.92 | .9684 | .0753 | +9.824% |
| **V3 loss-guide 127 foglie** | **56.05** | **.9686** | **.0795** | **-10.019%** |

**Definizione del ritorno economico nell'ultima colonna:** si usano esattamente i 12 segnali emessi nel 2022, si acquistano gli ETF alla successiva apertura e si disinveste alla successiva rotazione mensile; il capitale parte dalla prima apertura di febbraio 2022 ed esce all'inizio 2023. È un CAGR annualizzato `costed_path` di questa specifica finestra, **non** il ritorno nel 2022 solare. Nessuna variante è stata selezionata in base al risultato di questo audit ex-post.

Il modello depth4 trova il vero vincitore in **34/58 date TRAIN, solo 1/12 OOS**. Il 127-leaf ne trova **53/58 TRAIN, ancora 1/12 OOS**. Train molto forte con Top1 invariato sul test e performance pesantemente degradate: **forte evidenza di sovradattamento della selezione estrema Top1 nell'anno critico**. Il 127-leaf usa circa 60 foglie (non 127 effettive), 5× il numero originale.

La Spearman aggregata non è monotona rispetto al ritorno Top1: il rischio è soprattutto scegliere ETF fortemente in perdita pur migliorando i ranking medi. L'albero aumenta il fitting degli eventi di training senza rilevabile beneficio nel vero ranking dei vincitori 2022.

## Interpretazione, limiti e prossimi controlli

- Questa è una spiegazione **fondata su codice + diagnostica ricostruita**, NON una prova di un bug di segno, prezzo, USD/EUR o mancato embargo. Non significa che tutti i titoli immobiliari fossero a priori prevedibilmente perdenti.
- L'uso della capacità 127 ottimizzata sull'USA149 su 48 EU con soli 58 mesi 2022 fornisce un'ipotesi causale concreta di **modello sovradimensionato rispetto al dataset/regimi e perdita di generalizzazione**.
- Il 2022 è stato individuato a posteriori perché peggiorava il sistema. Gli ottimi risultati di depth4/15 in questa finestra **NON sono un nuovo holdout**, non autorizzano la promozione di 15 foglie e possono essere fortuna di questo regime.
- Risk layer assente e decision tree inattivo nel 2022 spiegano perché maxdd resta -41.18%. Le opportunità statistiche EU48 non sono quelle USA149: Top1 migliore fra 48 scelte 2/65 mesi (vs random atteso 1.35/65); persino il vecchio depth4 ha limitata competenza Top1.
- Per trarre una conclusione sull'intero mercato europeo, pre-registrare un unico confronto su tutti i 65 mesi `depth4 / 15 / 31 / 63 / 127` con 3 seed e stessa contabilità, e verificare ogni anno, drawdown, top1, tail-loss; **non scegliere il numero di foglie dal CAGR storico**. Poi isolare il risk layer con regole identiche per V2 e V3.
- I risultati USA149 precedenti erano in parte su media NAV di **500 panieri**, mentre l'Europa riporta un unico conto su 48 ETF. Anche questa diversa unità statistica impedisce il confronto semplicistico dei CAGR.

**Decisione attuale:** conservare i modelli originari, nessun cambiamento operativo. Il problema significativo è insufficiente generalizzazione, specialmente Top1, della capacità V3 su EU48, aggravata da rischio di concentrazione e warm-up meta. Prima di aumentare ulteriormente il numero foglie occorre una selezione capacity-aware e un controllo separato del rischio.
