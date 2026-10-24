# Root-cause review V3 Europa48: configurazione, training, target e simulazione (24 ottobre 2026)

**Esito:** difetto dimostrato nella condizione di allocazione Top2; mismatch fra target forward21D e periodo effettivo mensile; problema significativo e riproducibile di complessità del ranker `max_leaves=127` sull'universo EU48; debolezza strutturale del meta-tree per campione effettivo ridotto. NON abbiamo trovato una manipolazione dei dati o un lookahead nei fitting annuali. Nessuna modifica a V2, kernel o produzione.

## Prove originali e nuove

- Benchmark ufficiale EU48 V2 125F e V3 127 + Tree: [run 40092281559](https://github.com/AM1975MA/Test/actions/runs/40092281559), [report matched EUR](EUROPE48_V3_NATIVE_ALLOCATIONS_20261024.md).
- Sei fit annuali originali, 3 seed, 125F e 127 foglie: [run 40086216896](https://github.com/AM1975MA/Test/actions/runs/40086216896).
- **Nuova verifica controllata 15/31/63/127 foglie**: [run 40112204947](https://github.com/AM1975MA/Test/actions/runs/40112204947), **6 job PASS** 2021–2026; fit `127` riprodotto sui file immutati prima del confronto dei challengers.
- **Nuovo replay realistico costed EUR Top1 con controllo degli originali al livello 1e-10**: [run 40112595040](https://github.com/AM1975MA/Test/actions/runs/40112595040), **PASS**; nessun altro parametro cambia.
- Sorgenti nuovi: `diagnose_leaf_capacity.py` e `leaf_capacity_real_portfolio.py`.

## Risultato principale: real EUR Top1 costed, 65 signal, 1374 sedute

Identico dataset di 48 ISIN Europe only, 1 conto single-unrestricted, feature 125, addestramento annuale 2017+, target etichettati prima dell'anno di test, 360 round, 3 seed 101/202/303, entrata `Open` successiva e 0,1% per lato su notional scambiato. Non vengono apportati interventi ulteriori del decision tree ai modelli nuovi 15/31/63.

| Ranker | CAGR | MaxDD | Sharpe log annualizzato | Gross turnover, conto totale |
|---|---:|---:|---:|---:|
| V2 Compact125 depth4 originale | +4,7279% | -25,8932% | +0,2346 | 139,34 |
| V3 127, senza tree | **-0,2257%** | **-41,1836%** | -0,0105 | 120,61 |
| V3 127 + decision tree originale | +4,7060% | -41,1836% | +0,2371 | 128,54 |
| V3 **15 foglie** | **+12,3922%** | **-24,2234%** | +0,6113 | 169,82 |
| V3 **31 foglie** | **+15,3540%** | **-26,7879%** | +0,7174 | **194,93** |
| V3 63 foglie | +5,0424% | -32,0272% | +0,2409 | 140,75 |

**CAGR storico 15/31 non promuovibile**: l'universo EU48 e i mesi 2021–26 sono stati oggetto di ricerche precedenti e la campagna è un'ablation ex post su quattro leaf capacity. La differenza economica NON costituisce una stima OOS indipendente della performance prevista su altri anni. Il modello a 31 foglie ha molto più turnover: slippage, spread, liquidità e market impact vanno quantificati.

### Year-to-year: la differenza comincia nel 2022

| Anno (2021 e 2026 parziali) | V2 Compact125 | V3 127 | V3 15 | V3 31 |
|---|---:|---:|---:|---:|
| 2021 | +4,82% | +11,46% | +16,62% | +23,70% |
| 2022 | +5,84% | **-19,06%** | **+8,38%** | +4,45% |
| 2023 | +3,58% | +5,68% | +30,26% | +24,50% |
| 2024 | +1,83% | -0,25% | -0,91% | +14,23% |
| 2025 | -2,97% | -3,68% | +8,71% | +10,63% |
| 2026 fino al 1 luglio | +13,07% | +7,85% | +6,09% | +6,53% |

Le scelte 127 provocano grandi perdite nel 2022, e il tree originale non interviene quell'anno. Due operazioni concrete: maggio signal ZPRP.DE **-18,55%** e agosto signal IQQP.DE **-15,35%** nel replay economico (periodi di detenzione fino al prossimo rebalance). Il drawdown -41,18% fra 21 aprile e 13 ottobre 2022 si verifica prima che l'albero inizi a selezionare alternative.

## Primo stadio: ordinamento generale conservato, Top1 distrutto

Confronto dei punteggi **originali** V2 depth4 contro V3 127 su 65 mesi (importante: correlazione fra modelli, NON correlazione con rendimenti):
- Spearman medio fra le due classifiche: **0,8483**; stesso Top1 soltanto **37/65 mesi**.
- 2022: Spearman 0,8674 ma identico Top1 soltanto **6/12**. Comparando *ritorni forward 21 sedute degli ETF effettivamente selezionati*: aprile 2022 EXH8.DE (V2) vs DXSK.DE (V3), V3 peggiore di 10,37 punti; maggio XS7R.DE vs ZPRP.DE, -7,55 punti; agosto EXH5.DE vs IQQP.DE, **-13,49 punti**.
- Sui 65 mesi unrestricted la capacità ranker puro selected excess vs media EU48 scende **+0,2008% V2 → -0,3451% V3 127** per 21 sedute. Percentuale di mesi con ranker ETF vincitore 2/65, vicina alla base random 1/48.

### Ablation per 125 feature / 360 rounds invariati

| Max foglie | Selected excess Top1/21D sui 65 mesi | True top1 winner hit |
|---|---:|---:|
| 15 | **+0,7236%** | 3/65 |
| 31 | **+0,8827%** | 2/65 |
| 63 | +0,1568% | 2/65 |
| 127 | **-0,3451%** | 2/65 |

Del 2022 solo: selected excess medio V3 15 +3,0505%; 31 +2,3972%; 63 +2,1353%; 127 +0,1809%. Differenze paired 65 mesi vs 127:
- 15 foglie: **+1,069 pp/21D**, bootstrap 3-calendar-month circular 95% circa **[+0,072,+2,140] pp**;
- 31 foglie: **+1,228 pp/21D**, CI **[+0,334,+2,189] pp**;
- 63 foglie: +0,502 pp/21D, CI [-0,324,+1,412] pp.

Sono intervalli esplorativi e *non* corretti per la selezione di configurazione, universi già studiati e confronti multipli. Dimostrano che il comportamento è sensibile alla capacità del modello, non identificano automaticamente il leaf ottimale. Il V2 originale `max_depth=4` non coincide matematicamente con `max_leaves=15` loss-guided, ma abbiamo mantenuto tutti gli altri parametri V3 costanti per il confronto causale di capacità.

## BUG CERTO: la regola Top2 non è condizionale sull'universo pieno

Sorgente `v3_europe48_meta_economics.py`: `full_rank_gap = v["rank"][full_order[0]] - v["rank"][full_order[1]]`. `v["rank"]` è `pandas.Series.rank(pct=True)` nel mondo esatto di 48 ETF; il gap fra primo e secondo di 48 è matematicamente SEMPRE `1/48 = 0,020833333`, salvo punteggi perfettamente in pareggio (che NON abbiamo). La regola `TOP2: if full_rank_gap>=0.12 then 100% Top1 else 75% Top1 +25% Top2` non accede MAI al ramo 100%. Il CSV di 65 mesi conferma min=max=0,0208333, **0/65** soglie superate.

Questa è una configurazione logicamente difettosa, non un comportamento di mercato. Dunque le metriche Top2 EUR pubblicate sono per **allocazione 75/25 fissa**, anche se il rapporto la chiama condizionale. Non colpisce il Top1 da 100% e **non spiega il problema principale Top1**, ma richiede correzione *ex ante*. Nel backtest USA149 la stessa forma di gap è usata su panieri 24-of-149: lì i Top1/Top2 del paniere NON sono necessariamente adiacenti nel rank percentile di tutti i 149 ETF, dunque la condizione potrebbe attivarsi.

**Fix di disegno**: definire segnale di confidenza con `(raw_model_score_top1 - raw_model_score_top2)/(IQR(raw_model_scores_over_48)+epsilon)`, o margine diretto di expected utility, con threshold definito su passato non ancora usato e non su quantili di ranghi ordinali consecutivi. Non modificare produzione senza replay pre-registrato.

## MISMATCH CERTIFICATO: addestramento per forward-21D, trading mensile per la prossima apertura

Il codice sorgente `k.add_labels` definisce un target `Open_{next+21 sessions}/Open_{next}-1`. Il generatore di portafogli `isin_first2026.predict48.tournament.monthly_data` e `costed_path` mantengono invece ogni ETF fino alla prima apertura successiva al *seguente* ultimo giorno di mese. Questo produce holding periods di **16–23 sedute**; solo **17/65** trade blocks sono *esattamente* 21 sedute, **48/65** differiscono dall'orizzonte usato dal ranker.

Il problema esiste sia nel vecchio 125F sia nel nuovo 127, quindi **non può spiegare da solo il deterioramento specifico del V3**; tuttavia può rendere le scelte dei Top1 estremi molto sensibili a pochi giorni. Una corretta pipeline di ricerca dovrà fornire etichette allineate ai reali intervalli del portafoglio e tenere 21D come report diagnostico separato, poi ripetere training e confronto senza usare le stesse prove per selezionare iperparametri.

## META-TREE: popolazione campione ridotta e covariate dipendenti dal paniere

`train_month` deduplica per `(ETF_base, ETF_alt)` ma le 14 feature includono la differenza con il secondo e terzo del paniere e `std(rank[top3])`. La stessa coppia ripetuta in panieri diversi ha dunque feature diverse, e il programma conserva solo il **primo** contesto incontrato. L'inferenza sul portafoglio **unrestricted48** invece ha un contesto diverso dai panieri balanced24.

Le prove mostrano da 621 coppie-distinte/mese aggregato su 25 mesi (circa **25 esempi/mese**) fino a 1.935 su 62 mesi: 500 basket non sono 500 eventi indipendenti. Con `min_samples_leaf=300`, molti modelli hanno solo **1 split, 3 nodi**, o poche biforcazioni. La selezione meta non inizia prima del 2023-04 per embargo e 24 mesi; nel 2022 il tree rimane dunque completamente inattivo e il MaxDD Top1 è identico al ranker 127.

Questa architettura ha **cambio di distribuzione train/inference**, non una violazione dimostrata del target-maturity embargo. Per correggere il difetto senza introdurre selezione ex-post, usare feature invarianti per coppia o mantenere i contesti originali con peso inverso per duplicazione e pre-registrare decision tree/risk. I test USA149 hanno già mostrato che una correzione matematicamente più elegante non basta da sola a produrre alpha.

## Altri limiti e interpretazione

- Il pre-market US SPY è costruito usando la **precedente** chiusura americana all'apertura europea: non abbiamo trovato un'evidenza di leakage temporale nella costruzione originale; lo stesso metodo era usato per il baseline.
- Etichette, ticker e 48 legal ISIN/65 date coincidono numericamente con il precedente 125F, e il nuovo fit 127 ricrea i punteggi archiviati. Il replay dei CAGR V2, V3 127 e Tree matcha entro 1e-10. Non c'è evidenza in questa revisione di un semplice bug nella formula CAGR che giustifichi risultati scadenti.
- Il V2 Stage19 completo (CAGR -0,1549%) e V3 standalone non sono comparabili direttamente: il vecchio Stage19 aveva overlay di rischio, bucket cash USA FX-converted e altre allocazioni, mentre i nuovi test isolano ranker e/o tree.
- L'universo EU48 è selezionato in fotografia 2026 e le serie Yahoo sono state backadjusted. Il survivorship bias può rendere eccessivamente ottimistici tutti i risultati; pertanto **+15,35% non è una previsione realistica certificata per investimenti**.
- Fee unidirezionale fissa 10bps, slippage e spread eseguibili reali non modellati. L'uso di 31 foglie incrementa il gross turnover a 194,93 da 120,61: rischio di sovrastimare il vantaggio economico.

## Prossimi passi e decisione

**Non modificare la V3 prodotta.** Questo esperimento diagnostica con certezza la sensibilità alla capacità: 127 foglie nel contesto EU48 è *molto meno adatto* di 15/31 nel calendario osservato, ma non prova che una scelta futura di 15/31 massimizzi il rendimento. Non continuare ad ottimizzare foglie sullo stesso periodo 2021–26.

Priorità successive:
1. Correggere la metrica di confidenza/allocazione Top2 (gap di punteggi grezzi normalizzati, non gap percentile dei primi due globali).
2. Allineare label future all'holding period economico scelto, con vero as-of train e cost audit.
3. Valutare un ranker con controllo di complessità **legato alla numerosità e alla diversità effettiva del training**, preregistrando i parametri e facendo validazione temporale ancora non utilizzata; mantenere il fallback vecchio 125F come controllo.
4. Riprogettare meta tree a osservazioni di coppie uniche con contesti invarianti o pesi `1/k` e confrontare *sullo stesso universo* l'incremento del suo compito specifico, non soltanto il CAGR.
5. Stress test costi / liquidity, benchmarking equal-weight, confronto risk-layer a regole identiche, dataset PIT/survivor-free e altri periodi per promuovere un modello.

Nessuna promozione per ora. **Root cause principale plausibile e quantitativamente verificata: eccesso di capacità del primo ranker a 127 foglie che destabilizza il Top1 su EU48, aggravato da pochi ETF scartati male durante il drawdown 2022.**
