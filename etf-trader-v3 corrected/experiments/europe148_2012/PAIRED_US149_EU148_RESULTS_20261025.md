# USA149 vs Europa148 — verifica rigorosa V3 127 foglie, 25 ottobre 2026

**STATO: RICERCA. NON PRONTO ALLA PRODUZIONE.** Esperimento completo realmente eseguito su GitHub Actions, sorgenti V3 originali non modificati, branch di ricerca dedicato. Confronti deterministici fra i due mercati, non confronto scorretto fra una V2 US149 storica ottimizzata e un account EU148 nativo.

## Tracciabilità esecuzioni e artefatti

- Controlli senza ML (momentum deterministico, benchmark passivi, singolo conto EUR): https://github.com/AM1975MA/Test/actions/runs/40226379195
- Pannelli **125 feature V3 originali corrette**, entrambi sul calendario di sessioni comuni: https://github.com/AM1975MA/Test/actions/runs/40226846660
- **18 fitting annuali**: 9 US149 + 9 EU148, tutti terminati con successo: https://github.com/AM1975MA/Test/actions/runs/40227138117
- NAV economici Top1/Top3/Top5, 2076 osservazioni giornaliere per strategia, trade ledger, audit e skill: https://github.com/AM1975MA/Test/actions/runs/40227417589
- File di ricerca: paired_us149_eu148_controls.py, build_paired_v3_panels.py, fit_paired_v3_127_annual.py, evaluate_paired_v3_127_economics.py, corrispondenti workflow .github/workflows/v3-us149-eu148-paired-*.yml, tutti in questa branch.

## Contratto metodologico realmente verificato

- Coorti originali: **149 ETF USA** (149/149 eleggibili primo mese gennaio 2018), **148 ISIN ETF Xetra EUROPA**, dei quali 115 eleggibili a gennaio 2018 e 148 a maggio 2026. La coorte europea NON include prezzi anteriori alla propria data di quotazione. Selezione azionaria limitata a 75 USA e 89 iniziali–112 finali EU; stili e pesi di categoria **non identici**, quindi il confronto azionario è un controllo di sensibilità, NON universi perfettamente abbinati.
- Ultima seduta comune dei mercati di ogni mese, **101 segnali gennaio 2018–maggio 2026**. Trading prima seduta congiunta successiva all'Open, **1 febbraio 2018–1 luglio 2026**, **2076 mark**. Regole identiche di decisione/esecuzione, costruzione NAV e costi.
- Conto unico reale, peso uguale sui migliori Top1/Top3/Top5, senza leva, commissioni/slippage modello **10bps per lato sul nozionale effettivamente movimentato**. Nessuna selezione basata su rendimenti futuri. Quotazioni prive di Open non eseguibili; per posizioni già detenute un Open assente bloccherebbe il test, anziché fingere una vendita.
- Prezzi USD originari per calcolo feature US; **USD convertiti EUR usando EURUSD già noto al precedente close USA** per NAV/operazioni. EU quotata EUR. Questo fixing differito è un *proxy*, non lo spread FX realmente eseguibile; costo cambio non incluso.
- **V3 native source-only 125 feature** su calendario di entrambi i mercati con comune target successivi **21 sessioni congiunte**. L'intersezione dei calendari differisce intenzionalmente dai 21 giorni della singola borsa precedentemente usati. Le 59 quote europee mancanti il 6 marzo 2026 sono ripristinate col Close precedente **soltanto per feature**, non prezzi eseguibili o target. Corporate action 26:1 e 2 anomalie già sanate nei derivati precedenti. US mantiene SPY come fattore, EU mediana cross-section: **fattore non identico** ma kernel identico, nel rispetto del confronto dei mercati.
- Training dal 2012 di sole etichette 21-sessioni maturate entro il 1° gennaio dell'anno di predizione; **9 fitting 2018–2026**, 360 iterazioni, 3 seed 101/202/303, XGBRanker 127 foglie, 125 feature. Nessun filtro sulla futura etichetta nel set di test. Primo stage soltanto, **senza** meta-tree, overlay di rischio, Stage19 o ulteriori layer.
- I controlli senza ML utilizzano momentum trailing 21/63/126/252 comuni e gli stessi costi/simulazione; le scelte di lookback vanno considerate test multipli, non iperparametri selezionati prospetticamente. Il risultato principale V3 127 era prefissato prima di questo run.

## Benchmark e controllo senza machine learning: CAGR netto EUR / MaxDD

Benchmark acquisto e mantenimento, dall'Open 1 febbraio 2018 all'Open 1 luglio 2026:
- SPY USA convertito EUR: **CAGR +15,16%; MaxDD -31,46%**.
- EXSA Europa EUR: **CAGR +8,84%; MaxDD -35,22%**.

| Controllo fisso | USA149 CAGR | EU148 CAGR |
|---|---:|---:|
| Momentum 252d Top1 | +20,35% | -0,89% |
| Momentum 252d Top3 | +21,07% | +3,87% |
| Momentum 252d Top5 | **+21,24%** | **+6,37%** |
| Momentum 252d Top5, selezione solo equity | **+21,72%** | **+9,02%** |
| Momentum 21d Top5, selezione solo equity | +14,50% | +12,10% |

Un divario di opportunità si manifesta anche SENZA decision tree: 252d Top5 full +14,87 punti CAGR USA–EU. Non implica alcuna garanzia di vantaggio sistematico: il passato comprende forti trend settoriali USA e il momento 252d NON è un test ML. Benchmark SPY/EXSA non sono perfetti per fondi multiasset.

## Modello identico: V3 native ranker 127 foglie, netti EUR

| Metodo / misura | USA149 full | EU148 full | USA75 equity | EU89-112 equity |
|---|---:|---:|---:|---:|
| Top1 CAGR | +5,08% | +2,14% | +13,46% | +8,64% |
| Top3 CAGR | +9,72% | +1,78% | +12,76% | +8,59% |
| **Top5 CAGR** | **+13,86%** | **+3,91%** | **+11,81%** | **+10,96%** |
| Top5 MaxDD | -41,31% | -46,97% | -39,08% | -44,47% |
| Top5 nozionale annuo riaggiustato totale, somma normalizzata | 153,07 | 150,78 | 147,24 | 140,21 |
| Top5 ordini su volume vendor riportato zero | 0 | 4 | 0 | 5 |

Nota: le 4 e 5 operazioni europee a volume reported zero impediscono di attestare effettiva eseguibilità con book reale. Ulteriori spread reali peggiorerebbero i risultati; l'esperimento non incorpora costi FX né imposte. Nel benchmark passivo si applicano 10bps anche all'uscita finale, mentre il V3 conserva NAV all'ultimo Open, una differenza di costo terminale minima ma da rendere esplicita.

Il Top5 US full **non supera il suo SPY**: +13,86 contro +15,16, **-1,30 punti CAGR**. Il Top5 EU full **non supera EXSA**: +3,91 contro +8,84, **-4,94 punti CAGR**. La composizione equity-only produce in EU +10,96% vs EXSA +8,84%, ma questo confronto esplorativo non equivale ad alpha validato.

**Distanza relativa V3 Top5 USA–EU:** full 13,86−3,91 = **+9,95 punti CAGR**; scegliendo SOLO equity senza rifare il training 11,81−10,96 = **+0,85 punti**. Con restrizione azionaria il divario storico si riduce di circa 91,5%. All'interno del mercato europeo, equity-only migliora 3,91 → 10,96%, **+7,05 punti**. Questo è l'indizio economico più consistente sul collo di bottiglia: ammissibilità/categorie e passaggio cross-asset. Non è ancora prova causale univoca: restringere asset class cambia rischi, beta, opportunità e size universo.

## Ranking skill: 101 mesi, rendimenti forward21 sulle stesse 21 sessioni comuni

| Misura | US149 full | EU148 full | US equity | EU equity |
|---|---:|---:|---:|---:|
| IC Spearman medio | +0,0343 | +0,0036 | +0,0138 | -0,0037 |
| Vincitore esatto nella Top1 | 5/101 | 4/101 | 5/101 | 5/101 |
| Vincitore nella Top3 | 12/101 | 8/101 | 15/101 | 12/101 |
| Top1 excess medio vs universo, forward21 | +0,812pp | +0,173pp | +0,435pp | +0,497pp |

Skill positiva debole, con ICEU ~zero. Non usare grandi CAGR di singole strategie momentum come surrogato della capacità predittiva del V3. Un ranker realmente robusto dovrebbe mantenere eccesso di rendimento netto a rischio comparabile su mercati e periodi mai utilizzati per selezione.

## Attribuzione settoriale grezza EU Top5

Sui **505 slot ETF-mese** EU FULL Top5:
- **313 slot settoriali equity (61,98%)**
- 50 slot country equity
- 18 slot equity factor
- **81 slot property (16,04%)**
- **43 slot obbligazionari sovereign EUR (8,51%)**
- 0 slot broad equity.

Quindi **124/505 = 24,55% delle posizioni nominali** erano in ETF immobiliari o sovrani EUR. La variante equity-only Top5, con stesso ranker e date, seleziona 410 slot settoriali equity, 70 country e 25 factor. Questi conteggi sono **slot nominali, non contributi causali al profitto/perdita del conto**. L'esclusione di property/bond elimina anche esposizioni difensive che potrebbero tornare utili in altri regimi.

## Incertezza campionaria: bootstrap cronologico a blocchi

Stime da **101 rendimenti log mensili abbinati** sugli identici Open di ribilanciamento/uscita. **20.000 replicazioni** moving-block bootstrap circolare, blocchi contigui di 3, 6 e 12 mesi, riuso degli stessi indici per le due strategie in confronto. Percentili al 2,5 e 97,5% sul DIFFERENZIALE DI CAGR annualizzato, non bootstrap i.i.d. di 500 panieri dipendenti. I risultati sotto usano il blocco **6 mesi**, seed 20261025:

| Differenziale Top5 CAGR in punti percentuali | Osservato | IC bootstrap 95% |
|---|---:|---:|
| EU equity-only – EU full | **+7,05pp** | **[+2,70; +12,28]pp** |
| US full – US equity | +2,05pp | [-10,04; +15,81]pp |
| EU equity-only – EXSA | +2,12pp | [-4,96; +10,08]pp |
| US full – SPY | -1,30pp | [-14,98; +14,44]pp |
| US full – EU full | +9,95pp | [-2,79; +23,60]pp |
| Differenza fra effetti restrizione equity nei due mercati | +9,10pp | [-4,05; +23,97]pp |

La miglioria EU equity-only è statisticamente ben separata da zero **in-sample** anche coi blocchi 3 e 12 mesi, ma la restrizione è stata identificata *dopo aver guardato questo stesso OOS*, e l'intervallo NON corregge per la ricerca di ipotesi/strategia. Il vero test è un holdout successivo realmente inutilizzato; non chiamarla scoperta definitiva. Il differenziale USA–EU full e il delta rispetto a benchmark non sono robustamente distinti da zero nell'IC 95% a blocchi 6m.

Per completezza, **differenza fra gli IC di Spearman medi US FULL meno EU FULL +0,0306**, IC95% bootstrap a blocchi 6m **[-0,0360; +0,0973]**. L'asserzione che il ranker abbia vera skill nettamente migliore sugli USA **non è statisticamente dimostrata** sui 101 mesi.

## Cosa spiega e cosa resta irrisolto

**Diagnosi supportata dai test**: le differenze di opportunità del mercato sono visibili anche con momentum senza ML; la scelta cross-asset del V3 EU full è storicamente penalizzante; la variante limitata alle sole azioni recupera gran parte del gap di CAGR rispetto al sottouniverso US. Il full V3 di entrambi i mercati ha alpha passivo netto non convincente. I meta-tree aggiuntivi già testati EU non hanno migliorato i risultati; pertanto non sono stati forzatamente aggiunti a questi run di primo stadio.

**Non provato**: la regola azionario-only vincerà in futuro, il divario è interamente dovuto a settori/beta, o il V3 ha vantaggio sistematico negli USA. La performance USA V2 originale ~31,76% appartiene a differente architettura/periodo/portafoglio; non è stata né replicata né falsificata da questo specifico test V3 127.

**Limiti e rischi residui**: universo selezionato nel 2026 (survivorship bias), dati OHLCV vendor non point-in-time, 5 operazioni equity EUR a volume reported zero, nessun book/slippage effettivo, FX as-of proxy non eseguibile, dividendi/azioni societarie storiche da auditare ulteriormente, apertura USA ed Europa in orari fisici diversi, sovrapposizione target 21-sessioni e mesi reali non perfettamente equivalenti, universo azionario USA vs EU non settorialmente abbinato, rischio valutario su US, scelta alpha equity post-hoc. Nessuna promozione in produzione.

**Prossimi gate obbligatori**: (1) controfattuale sui segnali full EUR a categoria congelata ex ante, con stesso beta/risk budget e penalizzazione spread/volumi, per separare errori cross-asset da esposizione azionaria; (2) benchmark fattoriali matched EUR/USD hedged e cambiamento universo 2026 survivorship; (3) nessuna nuova ottimizzazione fuori da finestra OOS già sfruttata, ma test su dati temporalmente vergini. Poi, soltanto con skill robusta, riprendere meta-layer e risk stage.
