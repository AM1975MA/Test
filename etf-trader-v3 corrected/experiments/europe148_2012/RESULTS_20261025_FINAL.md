# V3 Europe148 — 25 ottobre 2026: audit e backtest corretto

**Stato:** ricerca, NON promuovere a produzione. Ogni sorgente originale, le branch US149 e i modelli legacy rimangono invariati. Le modifiche sono nel branch `research/v3-europe148-historical-20261024` e nella cartella `etf-trader-v3 corrected/experiments/europe148_2012`.

## Cosa è stato realmente testato

- **148 ETF europei**, 148 ISIN distinti: 48 precedenti e 100 nuovi OHLCV verificati il 24 ottobre. Sei categorie, prezzi EUR della sede Xetra e calendario EXSA, universo **dinamico** (115 eleggibili a gennaio 2018; 148 a maggio 2026). Non si inventano storici antecedenti la quotazione.
- V3 sorgente nativo **125 feature corrette**, annual retrain strettamente 2012+ con sole etichette maturate prima del 1 gennaio di ogni anno. Nove fitting 2018–2026, 3 seed, XGBoost 360 round, 4 ranker (depth4, leaf15, leaf31, leaf127) e 5 regressori 125/101 feature. Set OOS non filtrato sulla disponibilità futura dell'etichetta.
- **101 mesi** OOS segnale da gennaio 2018 a maggio 2026, esecuzione ai successivi Open EUR, conto unico, detenzione Top1/Top2/Top3/Top5 a pesi uguali, costi 10 bps per lato, NAV giornaliero fino al 1 luglio 2026 (2134 giorni di quotazione).
- Meta-tree: 500 panieri *dipendenti* di 24 ETF bilanciati per le 6 categorie per mese, deduplica coppie top1-vs-alt, 36 configurazioni preesistenti, addestramento trimestrale etichette maturate prima di 60 giorni, selector guard sui 24 mesi precedenti; decisione su portafoglio reale e non CAGR di 500 panieri.

## Errori dimostrati nei sorgenti/dati e correzioni

1. La precedente linea EU48 cosiddetta V3 utilizzava per un test feature V2 legacy (9 differenze nelle downvol e numerose discrepanze). EU148 usa esclusivamente il kernel V3 corretto `etf_trader_v3.source_only.kernel`.
2. **59 quote mancanti il 6 marzo 2026** inducevano le finestre rolling strette a espellere ~59 ETF in marzo-aprile-maggio 2026: eleggibili 146 febbraio, **89 marzo / 89 aprile / 89 maggio**, 148 giugno. Si è applicato il precedente Close già noto **solamente alle feature tecniche del giorno mancante**, non al prezzo eseguibile, all'Open originale o al target. Dopo la correzione: **147 marzo, 148 aprile, 148 maggio**.
3. **Split ETF LU0192223062, 26:1 il 6 luglio 2018**. Prezzo Close 5 luglio 192,59546 EUR; 6 luglio 7,44617. La serie originale generava una **falsa perdita −96,13%**; per il segnale giugno 2018 il target Open-to-Open 21 sedute era **−96,103% falso** anziché **+1,310%**. Il prospetto BNP Paribas conferma l'evento. Il derivato normalizza *tutti* gli Open/High/Low/Close pre-split ÷26, i volumi pre-split ×26; raw provider immutato.
4. Due ulteriori quarantene storiche **precedenti al test**: `LU0292097747` con salto di livello non verificato **+43,55%** il 30 luglio 2015 e volume zero (scartati solo i prezzi antecedenti la discontinuità); `LU0274209237` con una sola quotazione fantasma **+24,43%**, volume zero il 6 novembre 2014 e ritorno il giorno seguente (rimosso solo il giorno non negoziato). Ambedue restano disponibili quando maturi 2018+.
5. Rimosso nel fitting il filtro `.fwd_ret_21.notna()` dal *test* (sarebbe una scelta ex-post su dati futuri); mantenuto esclusivamente per training con etichette maturate. Corretta la dipendenza CI verso artefatti validi. Aggiunto audit operazioni su volumi pari a zero.
6. Audit finale 148 serie derivate 2012–2026: **nessun close-to-close giornaliero oltre ±35%**; si preserva il movimento reale plausibile di +20,33% nel marzo 2020 senza modifiche arbitrarie.

Sorgente split: BNP Paribas Easy prospetto aprile 2020 https://www.ciireland.com/wp-content/uploads/2019/09/BNP-PARIBAS_Prospectus_042020.pdf (sezione classi QD-DIS: split 26 al 06/07/2018).

## Risultati EUR148, CAGR netto e maximum daily-open drawdown

| Ranker | Top1 CAGR | Top2 CAGR | Top3 CAGR | Top5 CAGR | Top5 MaxDD |
|---|---:|---:|---:|---:|---:|
| V2LIKE_DEPTH4 | −1,85% | −3,92% | +1,52% | +4,09% | −42,39% |
| V3_LEAF15 | +0,94% | +0,10% | +0,17% | +3,96% | −44,77% |
| V3_LEAF31 | +1,47% | +0,11% | +2,61% | +1,67% | −45,82% |
| V3_LEAF127 | +3,27% | +4,01% | +4,75% | **+5,88%** | **−44,87%** |

**Benchmark di contesto su identico intervallo:** acquisto/mantenimento `DE0002635307` (EXSA, indice europeo) +8,84% CAGR / −35,22% maxDD, 10 bps entrata e uscita. Il ranker non genera valore rispetto al benchmark.

**Separazione esatta turnover e costi:** V3_LEAF127 Top5 ha 156,22 notionali movimentati (sommati sui 101 ribilanciamenti); CAGR **+7,86% senza commissioni** contro **+5,88% netto**, ~**−1,99 punti CAGR**. Inoltre **19 ordini di ribilanciamento coincidono con volume riportato zero**: l'eseguibilità non è provata senza un vero book e spread; 10bps non include slippage realistico.

## Predictive skill EU148 full-universe, 101 mesi

| Ranker | Vincitore esatto Top1 | Vincitore incluso Top3 | Spearman medio | Eccesso 21D medio Top1 vs ETF eleggibili |
|---|---:|---:|---:|---:|
| V2LIKE_DEPTH4 | 4/101 | 7/101 | −0,0312 | −0,271 punti % |
| V3_LEAF15 | 1/101 | 5/101 | −0,0353 | −0,031 punti % |
| V3_LEAF31 | 2/101 | 6/101 | −0,0196 | +0,057 punti % |
| V3_LEAF127 | 3/101 | 7/101 | **−0,0096** | **+0,054 punti %** |

Il 127 foglie non presenta correlazione positiva stabile sul rendimento futuro. Bootstrap 3 mesi, 10.000 replicazioni per 127 foglie: **Spearman IC 95% [−0,0565,+0,0373]**; differenziale Top1 21D vs media eleggibile **[−0,895,+1,019] punti percentuali**. Entrambi comprendono zero, e le configurazioni sono già state valutate su questo storico: non è un holdout veramente nuovo.

## Meta-decision-tree EU148

| Modello Top1 | CAGR netto | MaxDD |
|---|---:|---:|
| V3_LEAF31 semplice | +1,47% | −48,20% |
| V3_LEAF31 + albero 36 famiglie e nested selector | **+0,73%** | **−48,20%** |

L'albero viene scelto in 42/101 mesi ma sostituisce concretamente il Top1 solo in 11; eccesso incrementale medio **−0,087 punti % per segnale**. Esempio negativo ottobre 2020: selezione alternativa **−25,71 punti % a 21D** rispetto all'originale. Media Top1 excess diminuisce +0,057 → −0,029 punti %. **Respinto.** I panieri dipendenti non sono 500 portafogli indipendenti né 500 nuovi mesi.

## Diagnosi e cosa NON è lecito concludere

- **Dimostrato:** la vecchia esecuzione europea era contaminata da pipeline V2, dato mancante massivo, split e altre due anomalie storiche. Dopo la rettifica e riaddestramento completo, l'EU148 continua a sottoperformare; pertanto non basta riparare dati o ottimizzare layer/risk.
- **Dimostrato:** la capacità del ranker di ordinare gli ETF su mercato EU è debole (correlazione rank-rendimento prossima a zero) e il turnover erode ~2pp di CAGR.
- **Non dimostrato:** che il mercato europeo debba offrire lo stesso CAGR degli USA. Confrontare gli aggregati 500 panieri da 24 ETF o le configurazioni USA 2022–2026 con un *unico* conto EU148 su 2018–2026 non è metodologicamente equivalente. Servirebbe parità stretta di coorte, periodo, calendario, orizzonte target, valuta, kernel, costi e rischio.
- **Limiti:** snapshot dell'universo noto 2026 (survivorship bias), storico vendor non point-in-time, assenza book bid-ask/slippage, possibili vecchi aggiustamenti dividend/corporate action, ETF con volume zero, scelta foglie/alberi già influenzata da OOS precedente. **Non promuovere a trading reale.**

## Artefatti riproducibili

- Derivati OHLCV rettificati e audit: GitHub Actions https://github.com/AM1975MA/Test/actions/runs/40218758892.
- Pannello 125F / universo cronologico: https://github.com/AM1975MA/Test/actions/runs/40218835822.
- Fitting nove anni (tutti PASS): https://github.com/AM1975MA/Test/actions/runs/40219002667.
- Backtest economico 101 mesi, CSV scorecard, 2134 NAV giornalieri, ticket, skill e manifest: https://github.com/AM1975MA/Test/actions/runs/40219900158.
- Meta-tree 36, basket deduplicati, log e NAV economico: https://github.com/AM1975MA/Test/actions/runs/40219904186.

## Prossimo gate scientifico, senza scegliere iperparametri sullo stesso OOS

1. Ricostruire benchmark USA149 ed EU148 **sulla stessa finestra, costo, valuta e single-account**, e ripetere con universi matched per categoria e disponibilità 2018; misurare alpha excess vs rispettivi indici.
2. Isolare kernel / feature target vs dato reale usando baseline momentum predeterminate; analizzare distribuzione feature e calibrazione per cluster, missingness, instabilità 2018–2026, gap di proxy mercato SPY vs mediana EU.
3. Riesaminare orizzonte target esatto 21 sedute vs durata economica fra due segnali; eseguire test di skill sul rendimento fino al successivo ribilanciamento, e test closed-form senza ML.
4. Solo se la prima fase dimostra skill OOS positiva e robusta, riattivare meta-tree e livelli di allocazione/risk su holdout non usato per tuning. Non confondere la performance media di 500 panieri con portafoglio realmente implementabile.


## Verifiche supplementari completate nella stessa sessione

### Frozen tree anche sul vero ranker V3 a 127 foglie

Il primo controllo tree era su 31 foglie, configurazione già testata su EU48. È stata replicata l'identica metodologia su **127 foglie**, che era il miglior first-stage EU148:

| Base | CAGR Top1 netto | Top2 | Top3 | Top5 | MaxDD Top1 |
|---|---:|---:|---:|---:|---:|
| V3 127 senza albero | +3,27% | +4,01% | +4,75% | +5,88% | −46,53% |
| V3 127 + albero nested | **+2,44%** | +3,91% | +4,75% | +5,88% | −46,53% |

L'albero a 127 foglie viene scelto 27 mesi, ma modifica concretamente Top1 solo **5 mesi su 101**. Il contributo 21D medio di questi interventi, diluito sui 101 segnali, è **−0,0641 punti percentuali**. Anche a 127 foglie il layer meta-tree è **respinto** per mancanza di alpha incrementale. Azione riproducibile: https://github.com/AM1975MA/Test/actions/runs/40221385515.

### Ablation causa potenziale di mismatch SPY USA contro mediana ETF EU

Il kernel di produzione sceglie SPY come proxy se disponibile, altrimenti la mediana trasversale di tutti gli ETF. Per EU148 questa mediana comprende azioni, settoriali, real estate e bond. Esperimento controllato: sostituire **solo nel kernel delle feature** il fattore con `DE0002635307` (ampio indice azionario europeo EXSA), rinominato temporaneamente SPY per il calcolo delle feature e ripristinato all'ISIN reale prima di target, pannello e training. **Nessun ETF aggiunto, nessun cambiamento a split, date, fwd labels, featurizzazione restante, hyperparametri, costi, simulazione**. Nove nuovi refit anno-per-anno PASS.

Correlazione giornaliera osservata, 2018–maggio 2026, fra i rendimenti del proxy originale (mediana EU148) e EXSA: **0,9843** su **2133 sedute**. Quindi i due fattori sono già molto simili.

| Ranker / portafoglio | CAGR mediana EU | CAGR fattore EXSA | Δ punti CAGR |
|---|---:|---:|---:|
| V3 15 foglie Top1 | +0,94% | +5,89% | +4,94 |
| V3 31 foglie Top1 | +1,47% | −4,53% | −6,00 |
| V3 127 foglie Top1 | +3,27% | −1,45% | −4,72 |
| **V3 127 foglie Top3** | **+4,75%** | **+7,90%** | **+3,15** |
| V3 127 foglie Top5 | +5,88% | +5,11% | −0,76 |

**Competenza del ranker V3 127:** Spearman originale **−0,00960**, con EXSA **−0,00892** (nessun miglioramento significativo); eccesso forward21 Top1 originale **+0,054 punti %**, con EXSA **−0,271 punti %**. La configurazione EXSA Top3 è un miglioramento storico isolato, **non robusto attraverso Top1/Top5** e **comunque sotto** il benchmark EXSA buy&hold +8,84% CAGR e con drawdown molto peggiore (Top3 EXSA −46,15%, benchmark −35,22%). Non va promossa in base al picco Top3 sullo stesso OOS già esaminato.

Artefatti: pannello EXSA https://github.com/AM1975MA/Test/actions/runs/40220816710; fitting anni 2018–2026 https://github.com/AM1975MA/Test/actions/runs/40220925576; scorecard EUR https://github.com/AM1975MA/Test/actions/runs/40221553338.

**Conclusione aggiuntiva:** la definizione del proxy di mercato **non spiega da sola** il divario con gli USA. Il modello appare sensibile a piccole variazioni della costruzione delle feature e manca un vantaggio cross-sectional stabile. Il 127 foglie Top3 con fattore EXSA è una scoperta esplorativa, non un criterio valido per procedere a produzione.
