# ETF Trader V3 corrected — Root-cause analysis EUR48 ranker e decision tree, 24 ottobre 2026

**Verdetto:** problema reale nel trasferimento della capacità del ranker dai 149 ETF statunitensi ai soli 48 ETF europei, più un'allocazione Top2 con ramo di confidenza inerte e un layer di rischio assente dal replay standalone. Nessun cambio al modello operativo. Campione storico già esplorato, non un holdout.

## Riferimenti verificati

- [Sei fit annuali OOS, stesso codice e stessi parametri tranne limite foglie](https://github.com/AM1975MA/Test/actions/runs/40111997235) — 6 job PASS 2021–2026; ogni modello a 127 foglie replica il punteggio archivato originale con errori al massimo nell'ordine di 10^-8 e identico Top1 in tutti i 65 mesi.
- [Backtest ablation economica completa 15/31/63/127 + exact V2 reference](https://github.com/AM1975MA/Test/actions/runs/40112390505) — PASS, 1374 giornate, 65 segnali, identico 48-ETF EUR universe, 125 feature, 3 seed, 360 boosting rounds, annual mature-only train 2017+, next-open, 10 bps one-way su notional scambiato.
- [Replay reale decision tree con 500 panieri europei solo per formazione e selezione, EUR48 unrestricted per esecuzione](https://github.com/AM1975MA/Test/actions/runs/40092281559) — PASS; Top2 allocazione 75/25.
- [Replay originale del V3 127 con confronto reale V2 depth4](https://github.com/AM1975MA/Test/actions/runs/40087054494) — PASS.
- [V3 native allocator 8 curve NAV e controllo V2 esatto](https://github.com/AM1975MA/Test/tree/main/etf-trader-v3%20corrected/experiments/europe48_transfer/results/native_alloc_20261024/tables).

## 1. Rendimento e drawdown, Top1 EUR48 netto 10 bps

| Primo stadio | CAGR 2021-02..2026-07 | maxDD daily open | terminal equity EUR1 |
|---|---:|---:|---:|
| V2 Compact125, XGB depth 4 (360 round, 3 seed) | +4.7279% | -25.8932% | 1.2839 |
| V3 lossguide, MAXLEAF 15 | **+12.3922%** | **-24.2234%** | 1.881 |
| V3 lossguide, MAXLEAF 31 | **+15.3540%** | -26.7879% | 2.166 |
| V3 lossguide, MAXLEAF 63 | +5.0424% | -32.0272% | 1.305 |
| V3 lossguide, MAXLEAF 127 | **-0.2257%** | **-41.1836%** | 0.98785 |
| V3 127 + nested selective decision tree | +4.7060% | -41.1836% | 1.2825 |

Il modello a 127 può usare fino a 127 foglie con max_depth=0/grow_policy=lossguide. È molto più espressivo di max_depth=4 e, soprattutto, l'addestramento europeo iniziale contiene circa 2.3k righe contro una quantità sensibilmente maggiore nel precedente universo USA149. Il miglioramento a foglie inferiori è consistente con **eccesso di capacità e overfitting relativo al dominio europeo**, ma non isola una prova formale di overfitting (servono train-vs-test learning curves e conferma indipendente).

Nessuna valutazione autorizza a scegliere 31 soltanto in base al CAGR dello stesso periodo già studiato. 15/31 sono candidati di ricerca; non diventano iperparametri ufficiali.

## 2. Robustezza della comparazione di capacità (solo diagnostica)

| Ranker | Top1 winner capture (65 mesi, dei 48) | Top3 capture | Mean selected forward21D excess vs 48 mean | Selection <= -10% forward |
|---|---:|---:|---:|---:|
| V2 depth4 | 3.08% (2/65) | 7.69% (5/65) | +0.2008% | 0/65 |
| V3 leaf 15 | 4.62% (3/65) | 7.69% (5/65) | +0.7236% | 0/65 |
| V3 leaf 31 | 3.08% (2/65) | 10.77% (7/65) | +0.8828% | 1/65 |
| V3 leaf 63 | 3.08% (2/65) | 6.15% (4/65) | +0.1572% | 1/65 |
| V3 leaf 127 | 3.08% (2/65) | 6.15% (4/65) | **-0.3451%** | 2/65 |

Le hit-rate Top1/Top3 sono di scarsa precisione statistica con soli 65 mesi (caso random Top1 1/48=2.08% e Top3 3/48=6.25%). Il ranking a 127 ha mean Spearman +0.0389, maggiore del V2 +0.0251; questo non garantisce capacità di scegliere proprio il singolo ETF col miglior payoff.

Controllo paired month net log-growth a blocchi da sei mesi (3000 bootstrap; non corretto per multi-test):
- foglie 15 vs 127: +0.9911 punti percentuali logaritmici/mese, CI95 [0.0684, 2.0443] pp.
- foglie 31 vs 127: +1.2076 pp, CI95 [0.4265,1.9681] pp.
- foglie 31 vs depth4 V2: +0.8043 pp, CI95 [0.0921,1.5012] pp.
- foglie 31 vs foglie 15: +0.2165 pp, CI95 [-0.4648,+1.0091] pp: **non distinguiamo 15 da 31 con sicurezza**.
- campione ampiamente investigato prima di questo test: questi CI sono di ricerca, non inferenza corretta per il model search.

La variante 31 ha battuto la versione 127 nei rendimenti annuali nel 2021, 2022, 2023, 2024, 2025; nel 2026 i due hanno scelto le stesse posizioni (pari risultato). Si tratta di una robustezza descrittiva, non di una prova indipendente.

## 3. Errori/limiti confermati nel trasferimento US→EU

**Dead logic: confidenza Top2 percentile.** In `v3_europe48_meta_economics.py`:
`w1=1 if full_rank_gap>=.12 else .75`. Ma `full_rank_gap` è la distanza tra le prime due posizioni *percentili globali* su 48 ETF, esattamente 1/48 = 0.020833333 in TUTTI i 65 mesi, secondo la tabella loggata `EU48_V3_MONTHLY_NESTED_TREE.csv`. La soglia 0.12 è quindi matematicamente irraggiungibile e `TOP2` è sempre 75/25. Nel protocollo dei 500 panieri US di 24 ETF il gap dei migliori DUE ALL'INTERNO del paniere può essere più ampio perché il rango è riferito a 149 ETF, quindi non è la medesima grandezza. Questo non incide sul Top1, ma costituisce un bug funzionale nella logica adattiva dell'allocazione Top2 europea e rende il confronto con V2 equal-weight Top2 (50/50) non strettamente comparabile.

**Assenza del controllo di rischio completo.** `costed_path` usa un account EUR investito al 100% in 1–5 ETF, con soli ribilanciamenti mensili e 10bp. Non include layer `Stage19`, stop o defensive risk-off. Il max DD −41.1836% avviene precisamente da **2022-04-21 a 2022-10-13**; al tempo il selector V3 non ha ancora 24 mesi OOS già maturati, quindi è sempre CORRECTED e non può effettuare sostituzioni. I primi meta interventi sono del 2023. Il DD identico per le due strategie non è misterioso: sono letteralmente la stessa curva prima del 2023.

**Informazione effettiva per il meta-tree.** I 500 panieri sono sovrapposti. Nel run EU48 i pair-event unici di ogni mese vanno da 3 a 105, mediana 29, media 33.69, 22/65 mesi con meno di 20 eventi. Il regressore albero conserva solo il primo contesto per ciascuna coppia e usa campioni limitati per addestrare 36 strategie di 1–3 profondità, min_samples_leaf 100/300. Non è un dataset composto da 500 segnali indipendenti.

**Universo e input.** Solo 48 fondi che erano negoziabili nel 2026, ricostruiti storicamente 2017–2026: selezione ex-post potenzialmente soggetta a survivorship bias. OHLC da più vendor, alcuni High/Low incoerenti riparati nel derivato ma originali Open/Close invariati; la prova resta di ricerca, non esecuzione broker-grade. Almeno 6 macrocategorie comprendono azioni settoriali, paesi, factor, bond sovrani EUR e immobiliare: in 2022 la diversificazione fra queste classi non garantiva protezione.

## 4. Test di software integrity verificati

- Parità EU48 di 48 ticker × 65 mesi, prezzo target EUR 21 next observed sessions next open, labels senza contaminazione di training annuale.
- 127 foglie replica perfettamente il ranker originale su tutti i sei refit, scarto raw prediction max circa 10^-8 e Top1 invariato.
- V2 depth4 original source-only 125F benchmark replica CAGR 4.72791493406% con differenza numerica inferiore a 1e-10.
- Replay su 1374 osservazioni EUR open e costi in notional, non emergono nella NAV salti singoli oltre 10% al giorno; il drawdown 2022 è una perdita cumulativa.
- Data lineage SPY USA ritardato al precedente US market close prima dell'apertura UE, verificato nel source `strict_build_spy`; quindi non è evidenza di indisponibilità temporale o lookahead di SPY.
- Confronto pienamente autonomo *modello di ranking*, non l'intera V2 Stage19 o V3 fullstack.

## 5. Decisione

1. **Congelare e non promuovere** il ranker 127 su Euro48.
2. Considerare leaf15/leaf31 come ipotesi *pre-registrate* per un futuro test davvero successivo, non scegliere il 31 perché ha CAGR più alto sullo stesso storico; l'incertezza sul distacco 15 vs 31 include zero.
3. Correggere con un'apposita ablation la regola Top2 di confidenza, usando margine degli score raw standardizzati o probabilità decisionale calibrata cronologicamente. Non modificare la strategia finché non ci sono verifiche.
4. Validare un portafoglio unico con logiche di rischio chiaramente comparabili: V2 Stage19 vs V3 fullstack Stage19; selezionare la stessa allocazione e stesso fee model.
5. Confermare su periodi nuovi e ISIN pre-esistenti alla data di formazione, e con quote corrette e stabili di broker/provider.

**Nessun modello operativo modificato. Risultati e ablation conservati nella cartella V3 della branch di ricerca.**


## Addendum verificato il 25 ottobre 2026: `VERO` feature kernel V3 e capacità 15/31/63/127

Il test precedente con 15/31 foglie e feature legacy NON era una V3 corrected autentica. Abbiamo rifatto i sei fit annuali 2021–2026 sul **kernel V3 corretto originale**, lasciando immutati 48 ISIN, prior-close USA, 125 feature, seed, 360 round, regole cronologiche e 10 bps one-way sul portafoglio EUR unica NAV.

- [Report genuino kernel corrected con costi, rischio e bootstrap](EU48_TRUE_CORRECTED_CAPACITY_20261025.md).
- [7 archivi con 6 OOS annuali e confronto economico completo](results/true_corrected_leaf_capacity_20261025/).
- [Sei fit riusciti](https://github.com/AM1975MA/Test/actions/runs/40189199418), [replay economico riuscito](https://github.com/AM1975MA/Test/actions/runs/40189614773).

CAGR Top1 del ranker realmente corretto: **leaf15 +1,40%, leaf31 +8,39%, leaf63 +5,00%, leaf127 +3,85%**; V2 depth4 originale **+4,73%**. Top2 equal-weight leaf31 +6,27% vs V2 +3,73%, Top5 leaf31 +7,19% vs V2 +4,96%. Tuttavia **MaxDD Top1 leaf31 −34,61% vs V2 −25,89%**, ancora peggiore, e il vantaggio del leaf31 presenta IC95% paired a blocchi mensili comprendenti zero sia rispetto al leaf127 corretto sia rispetto al V2. La selected excess forward21D del leaf31 è solo +0,35% sulla media dei 48, e il Top1 sceglie il vincitore assoluto soltanto **2/65** mesi.

**Decisione invariata: non promuovere leaf31 o altri modelli dalla sola prova sul calendario storico già studiato.** La correzione del codice feature è essenziale e separata dall'iperparametro max_leaves; rischio e selezione EU48 restano problemi aperti. Il test è standalone, **non** il full Stage19.
