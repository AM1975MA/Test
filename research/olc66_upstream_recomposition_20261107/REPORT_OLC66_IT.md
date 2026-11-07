# OLC66 — Selezione a monte, ordine dei layer e ricomposizione della strategia ETF

**7 novembre 2026. Esito: nessuna nuova variante promossa.** Ricerca retrospettiva, non trading. Lo storico 2019–2026 è stato analizzato molte volte: non costituisce una nuova conferma fuori campione.

## Executive summary

OLC66 testa, su dati congelati originali, se una ricerca in due stadi (scoperta Top10 e ordinamento economico Top2) e due modifiche dell'ordine memoria/fusione migliorino la selezione degli ETF. **Nessuna delle sei alternative supera la FUSION originale in Europa e USA simultaneamente**. Non ricerchiamo i pesi che avrebbero massimizzato il CAGR passato. Il test non ha quindi attivato nuovi replay di trading per le varianti OLC66.

Un controllo aggiuntivo degli archivi OLC19 ha evidenziato una distinzione metodologica decisiva: `OLC19 ORIGINAL` usa i Top2 di FUSION, mentre il benchmark storico di **23,20% CAGR EU / 50,77% USA nel 2021–24** proviene dalla selezione **`TOP2_CONTEXT_REVALUE`** con rischio **`FAST_LOCK3`**. Sul perimetro per mese del segnale, la configurazione contestuale cambia 21/48 coppie EU e 23/48 USA. Pertanto non dobbiamo assimilare la qualità del solo FUSION a quella dell'intera strategia.

## 1. Esperimento upstream preregistrato

Protocollo depositato prima di calcolare gli outcome su GitHub, branch `research/olc66-upstream-recomposition-20261107`, commit `0320e451d9b4789b4193a6592e75288d3d3c70dc`. Input verificati tramite SHA256: OLC11 Selezione, OLC14 Fitting, OLC16 Input/Code, OLC19 Risk. Riferimento B0 originale riprodotto con formula OLC63, 180/180 decisioni mensili paritarie con OLC19 ORIGINAL.

Le alternative sono state fissate prima dei risultati: `C1_CLASS` (classificatore originale OLC11), `C2_EARLY_BLEND` (media 50/50 dei percentili di FUSION e CLASS), `R1_NATIVE_TOP10` (logistica economica dentro shortlist originale), `R2_UNION_TOP10` (lo **stesso** modello sulla shortlist allargata al classificatore), `O1_FUSE_THEN_SMOOTH`, `O2_SMOOTH_BOTH_THEN_FUSE`. R1/R2 hanno utilizzato **10 fit annuali** LogisticRegression C=0.1 e StandardScaler train-only, con target di top quintile a 21 sedute, gruppi mensili completi la cui `exit_date_63` precede il gennaio dell'anno di previsione; nessuna identità ticker e nessun valore futuro come feature. L'originale conserva la sua memoria 40/30/30, blend ET60/XGB40, Return 47,5% e modello 52,5%.

**MAIN = gennaio 2021–dicembre 2024:** 48 segnali mensili valutabili per mercato. **LATE = 2025:** 10 mesi EU e 12 USA con etichette complete, solo diagnostica già esplorata. Tutti i valori sotto sono medie di rendimenti statici Open→Open dei due ETF nelle successive 21 sedute, senza costo, stop, V6 o risk budget. **Non sono CAGR.**

| Ranking a monte | EU 21d | USA 21d | Δ EU vs B0 | Δ USA vs B0 |
|---|---:|---:|---:|---:|
| **B0 FUSION originale** | **2,131%** | **3,501%** | — | — |
| C1 Classifier OLC11 | 1,832% | 1,552% | −0,299 pp | −1,949 pp |
| C2 Fusione anticipata | 2,276% | 2,778% | **+0,146 pp** | −0,723 pp |
| R1 Logit entro Top10 | 1,925% | 2,103% | −0,206 pp | −1,398 pp |
| R2 Logit con Top10 ampliato | 1,925% | 1,735% | −0,206 pp | −1,766 pp |
| O1 Fusione → memoria | 2,112% | 3,059% | −0,018 pp | −0,442 pp |
| O2 Memoria due rami → fusione | 2,073% | 2,997% | −0,058 pp | −0,504 pp |

Per C2 l'intervallo descrittivo bootstrap a blocchi di 6 mesi sul Δ21 EU è circa [−0,275; +0,505] punti; quello USA [−1,533; +0,040]. Escludendo a turno un anno del 2021–24, C2 resta negativo negli USA in tutte e quattro le prove. I risultati del 2025 non cambiano la decisione: non è un nuovo OOS.

### Ricerca delle opportunità e precisione della shortlist

La Top10 del classificatore aggiunge in media appena **1,125 candidati EU** e **1,688 USA** per mese alla shortlist originale. Dei **96 futuri ETF Top2** (due per 48 mesi), l'unione contiene **36 invece di 35 EU** e **36 invece di 29 USA**. L'oracolo *ex post* dentro la shortlist aumenta soltanto da 6,244% a 6,344% EU e da 11,255% a 12,620% USA nel rendimento statico mensile a 21 sedute. Questi oracoli conoscono il futuro e non sono investibili. Il Logit R2 non sfrutta l'opportunità: rende quanto R1 in EU e meno in USA. Aggiungere candidati molto simili non risolve né scoperta né ranking.

**Decisione OLC66 upstream:** nessuna promozione; non applicare il classificatore isolato OLC11 né spostare memoria dopo il FUSION, né aggiungere il ranker R1/R2 alla strategia corrente.

## 2. Ruolo effettivo della rivalutazione contestuale (controllo nativo OLC19)

L'OLC19 originale conserva per ogni mese tre stadi distinti: (a) costruzione della FUSION e proposta dei Top2, (b) eventuale rivalutazione contestuale della coppia (`TOP2_CONTEXT_REVALUE`), (c) esecuzione e gestione rischio (`FAST_LOCK3`, `BASE`, `ALARM`, `FAST_NOLOCK`). Non si possono sommare differenze di rendimento dei tre stadi come se fossero indipendenti.

Sono state lette e riconciliate **720 selezioni native** per quattro varianti di selezione × due mercati × 90 segnali. Tutte le **180 coppie OLC19 ORIGINAL** corrispondono alla ricostruzione della FUSION; sul supporto comune 2021–2024, la rivalutazione contestuale cambia **21/48 coppie EU** e **23/48 USA**.

| Rendimento statico medio per finestra | EU ORIGINAL | EU CONTESTO | USA ORIGINAL | USA CONTESTO |
|---|---:|---:|---:|---:|
| 21 sedute, 2021–2024 | 2,131% | 2,167% | 3,501% | 4,196% |
| 42 sedute, 2021–2024 | 3,754% | 3,222% | 3,899% | 4,665% |

La rivalutazione contestuale è favorevole negli USA su entrambi gli orizzonti; in Europa è quasi neutra a 21 sedute e sfavorevole a 42. Anche qui non si tratta di trading NAV né di verifica di nuovi fill.

## 3. Dove collocare i layer di gestione rischio: backtest nativi OLC19 già archiviati

I valori seguenti **provengono dalle scorecard autentiche del checkpoint OLC19**, riprese e controllate, e NON sono stati ricalcolati su ciascuno dei candidati upstream OLC66. Sono confronti a selezione contestuale identica e con fee legacy `.001`.

| Contratto contabile | EU CAGR 2021–24 | USA CAGR 2021–24 | EU CAGR FULL 2019–lug26 | USA CAGR FULL 2019–lug26 | USA FULL MaxDD |
|---|---:|---:|---:|---:|---:|
| BASE | 22,23% | 50,55% | 19,7% | **43,6%** | −32,0% |
| ALARM | 22,09% | 45,51% | 18,6% | 39,6% | −34,2% |
| FAST_NOLOCK | **23,23%** | 47,49% | 18,8% | 34,9% | −27,4% |
| FAST_LOCK3 | 23,20% | **50,77%** | **19,8%** | 39,5% | **−26,1%** |

Nel segmento di crisi 2020, il MaxDD di FAST_LOCK3 è circa **−15,4% EU / −17,5% USA**, rispetto a **−25,1% EU / −25,7% USA** di BASE. Nel 2025, invece, BASE supera FAST_LOCK3 nel rendimento storico in entrambi i mercati. La differenza di rischio è economicamente significativa, quindi il modello più redditizio nel FULL **non è automaticamente il migliore** per un investitore con vincolo di drawdown. Le scorecard mantengono le convenzioni originali del motore e non sono certificazione dei prezzi d'esecuzione.

Una modifica *dell'ordine dei layer* può alterare per definizione stop, esposizione e protezioni, e non è stata provata dal semplice test di selezione. Le combinazioni di politiche non rieseguite non hanno quindi CAGR rivendicabile.

## 4. Ricomposizione della migliore architettura **supportata**

La scelta sostenuta dalla totalità degli esperimenti OLC11–65 e dalla nuova prova OLC66 non è una nuova architettura con CAGR più alto. È una **baseline congelata e riproducibile**:

1. Input/feature originali e train annuale causale, senza inserire nei learner etichette ancora immature; controllare identità ticker, disponibilità e mercato.
2. Previsioni dei rami ET/XGB e Return originali; percentili cross-sectional, con ET/XGB 60/40 nel punteggio `CURRENT`.
3. Smussamento del SOLO ramo modellistico `CURRENT` con memoria 40/30/30 e potenza 1,1; il ramo Return rimane indipendente.
4. FUSION: 47,5% Return e 52,5% del ramo modellistico smussato, producendo il ranking originario.
5. `TOP2_CONTEXT_REVALUE` **dopo** la fusione: conservare separatamente la trasformazione contestuale invece di attribuire il suo miglioramento agli head di previsione.
6. V6/overlay di rischio ed esecuzione `FAST_LOCK3` con lo stesso contratto originale di stop e costi; preferibile quando il contenimento del drawdown è un vincolo rilevante. `BASE` resta un benchmark importante perché mostra maggiore CAGR USA FULL ma drawdown peggiore.

Questa è **la miglior strategia oggi difendibile in termini di evidenza e controllo del rischio**, non la massimizzazione retrospettiva del CAGR né una prova di superiorità statistica fuori campione.

## 5. Perché non scegliamo una ricombinazione vincente a posteriori

- Sei varianti upstream OLC66, più decine di OLC11–65, sono state esaminate sugli stessi 2019–2026: selezionare un vincitore per anno o mercato gonfia la performance apparente.
- Nessuna modifica preregistrata supera insieme la FUSION sul 21d di EU e USA; non esiste un gate sufficiente per un nuovo replay contabile candidato.
- Il 2025, che favorisce alcune nuove varianti, **non è vergine** e non può sostituire il periodo MAIN o essere usato per scegliere retrospettivamente la variante.
- Il risultato non prova che la fusione sia universalmente ottimale. Indica che gli strumenti testati non hanno dimostrato un miglioramento robusto rispetto a un sistema multi-specialista già efficace.
- I dati non certificano universi point-in-time completi, storico adjusted/total return omogeneo, maschera delle quotazioni originali USA e prezzi di stop/bid-ask reali. Sono limiti sul rilievo economico dell'intera serie, non una ragione per introdurre un altro layer.

**Decisione:** nessuna promozione, nessun cambiamento a 0main o OLC19; conservare FUSION → CONTESTO → V6/FAST_LOCK3 come riferimento e utilizzare l'audit OLC65 per progettare, separatamente, un test prospettico della qualità delle opportunità scoperte e del ranking delle posizioni di testa.

## 6. Output e verifiche

- Verifiche parità score e 180/180 decisioni OLC19 ORIGINAL, rendimenti congelati OLC63 (118 eventi); test indipendente 826 selezioni candidato/mese superati.
- 10 fit annuali cronologici, cutoffs per label con maturità rigorosa. Le varianti C1/C2/R1/R2 e O1/O2 sono documentate nel protocollo preregistrato.
- `OLC66_SUMMARY.csv`, `OLC66_MONTHLY.csv`, `OLC66_LOYO.csv`, `OLC66_BLOCK6_BOOTSTRAP.csv`, `OLC66_POOL_SUPPORT.csv`, `OLC66_CONTEXT_RISK_CHOICES.csv`, `OLC66_NATIVE_CONTEXT_STATIC_COMPARISON.csv`, `OLC66_OLC19_ARCHIVED_SCORECARDS.csv`, `OLC66_QA.json`, `OLC66_INDEPENDENT_QA.json`, `OLC66_NATIVE_RECOMPOSITION_QA.json` e gli altri output nel bundle.
- `engine_rerun = false` per le 6 varianti OLC66; il confronto rischio è una rilettura di backtest OLC19 **già eseguiti**, non una nuova simulazione di combinazioni ottimizzate.