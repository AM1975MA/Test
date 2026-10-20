# ETF Trader V2 — prova controllata Stage19: Compact21 XGBoost 127 foglie
**21 ottobre 2026 · ricerca completa · nessuna modifica al repo operativo `Etf_trader`**

## Verdetto
Il **BASE V2 autentico** sui 149 ETF liberi batte la sostituzione isolata del componente Compact21 con XGBRanker 127 foglie sulle **tre vintage originali**, quando tutto il resto dello Stage19 viene mantenuto invariato.

| Vintage OHLCV | BASE CAGR | BASE + Compact127 CAGR | Δ CAGR (pp) | BASE MaxDD | Compact127 MaxDD | Δ MaxDD (pp) |
|---|---:|---:|---:|---:|---:|---:|
| r1 | 29,7534% | 26,9566% | -2,7968 | -34,8621% | -34,8867% | -0,0246 |
| r2 | 30,8437% | 23,2308% | -7,6129 | -25,6896% | -31,5452% | -5,8556 |
| r3 | 34,6771% | 24,9469% | -9,7301 | -36,0975% | -33,8470% | +2,2505 |
| **Media 3 vintage correlate** | **31,7581%** | **25,0448%** | **-6,7133** | **-32,2164%** | **-33,4263%** | **-1,2099** |

Media Sharpe BASE ~1,1053; Compact127 ~0,9008. Le tre vintage sono tre revisioni dei prezzi dello *stesso* universo storico, **non** tre esperimenti indipendenti.

## Certificazione rigorosa

- Input: **le tre vintage dei 149 ETF ORIGINALI**, archivio GitHub Actions [37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), non un nuovo download.
- Score annuale di controllo, ensemble MA3, tutti gli altri esperti, tail, macro e Stage19 dallo stesso cache `learner-full-BASE-r1/r2/r3` della run [37195399755](https://github.com/AM1975MA/Test/actions/runs/37195399755).
- Il BASE originale è stato **rieseguito prima dell’intervento** e il programma ha verificato parità giorno per giorno dei vettori NPZ (NAV, turnover, top1/top2, margini e alternative V6) verso le curve originali con tolleranza assoluta 1e-12, oltre all'uguaglianza esatta delle selezioni giornaliere.
- Il BASE vintage 1 della cache è **byte-identico** al percorso della verifica originale `v2replay-ECON_TOP5_RERANK-r1/baseline_control/FULL_UNIVERSE_PATH.npz`, SHA256 `71832165ab3d9234dc6a7ebef22782b2030566a4be75a553d7382f8b76c18b`.
- Le previsioni in input sono unicamente modificate nella colonna annuale **`compact21`**; tutte le altre colonne di previsione rimangono bit-identiche, e nell'ensemble MA3 cambia esclusivamente la colonna derivata `BASE`. Conservati fonte del codice e formule di `models.variants`, score Tail, macro, ExtraTrees MA3, XGB MA3.
- 10 fit annuali per vintage (2017–2026), 125 feature, 360 alberi, seed 101/202/303, `rank:pairwise`, `grow_policy=lossguide`, `max_depth=0`, `max_leaves=127`; gli altri iperparametri Compact21 sono quelli originali. Ogni anno usa solo etichette con data di uscita anteriore al cutoff del fit.
- Nessun cambiamento a **selettore V6**, **DD-first**, **High-CAGR24**, stop **5,5%**, esecuzione giornaliera, costi 0,1%, universo 149, calendario 2017-02-01..2026-07-01. L'esposizione sistemica media passa per lo stesso controllore e rimane 0,9837637363 in ciascun ramo.
- Numero di sedute per vintage: **2366**, da 1 febbraio 2017 a 1 luglio 2026; nessun anno di cash fittizio.

## Evidenza aggiuntiva

**Differenze delle scelte:** in media il Top-1 giornaliero cambia nel 43,22% delle sedute; il Top-2 nel 64,37%. Quindi l’intervento modifica sostanzialmente le rotazioni dei leader.

**Costo operativo:** turnover annualizzato medio BASE 13,0452, candidato 13,5165 (incremento ~0,4713 volte il capitale), corrispondente al massimo a un ordine di grandezza di **0,05 punti percentuali annui** di costo in più con fee 10bp. Questo non spiega un calo CAGR di 6,71 pp.

**Diagnosi anno per anno**, differenza dei CAGR per singolo anno, mediata sulle vintage:
| Anno | CAGR BASE | CAGR con 127 | Δ pp |
|---|---:|---:|---:|
| 2017 | 26,94% | 16,36% | -10,58 |
| 2018 | 10,65% | 7,77% | -2,88 |
| 2019 | 43,87% | 61,36% | +17,50 |
| 2020 | 29,87% | 39,69% | +9,82 |
| 2021 | 3,11% | -5,76% | -8,87 |
| 2022 | 41,89% | 19,34% | -22,56 |
| 2023 | 29,53% | 22,33% | -7,20 |
| 2024 | 78,82% | 64,55% | -14,27 |
| 2025 | 24,04% | 0,19% | -23,85 |
| 2026* | 60,64% | 75,51% | +14,87 |

*2026 è parziale fino al 1 luglio: sono CAGR annualizzati su metà anno e non rendimenti di tutto il 2026. Il confronto annuale è puramente diagnostico, in-sample di ricerca dopo molte revisioni.*

I miglioramenti 2019/2020 (e nel parziale 2026) non compensano i peggioramenti 2022/2025. La teoria dei regimi differenti è **un’ipotesi testabile**, non un’autorizzazione a scegliere retrospettivamente il ranker vincente per ciascun anno.

## Inferenza/statistica

La differenza media del **log-rendimento annualizzato appaiato** del Compact127 rispetto al BASE è **-5,2242 pp log/anno**. Bootstrap circolare a blocchi da 21 sedute, 6000 repliche, aggregando prima le tre vintage per ciascuna data comune: **IC esplorativo 95% [-13,80; +2,80] pp log/anno**. L’intervallo comprende zero. La superiorità del BASE è netta come osservazione dei tre replay ma non può essere proclamata prova statisticamente definitiva di vantaggio futuro.

## Decisione di ricerca

1. **Preservare il vero BASE Stage19 come riferimento attivo**; il Compact127 è un challenger non promosso.
2. Non ricominciare a ottimizzare TopK, rischio o pesi guardando il 31,76% per “recuperare” artificialmente la performance.
3. Indagare separatamente le decisioni su cui il Compact127 diverge, specialmente 2022/2025, confrontando target a 21 giorni con il target storico multi-orizzonte e analizzando *quali errori di ranking creano perdite economiche*. Nessuna modifica alla pipeline produttiva senza preregistrazione e dati veramente successivi alla ricerca.
4. Qualunque futuro test di feature/ranker mantiene Stage19 autentico ed esegue prima la parità giornaliera del BASE per la **medesima vintage OHLCV**.

## Codice, tracce e prove
- Run SUCCESS (tre vintage + consolidamento): https://github.com/AM1975MA/Test/actions/runs/39511256677
- Branch ricerca: `research/stage19-compact127-one-layer-swap-20261021`.
- Eseguibile: `stage19_compact127_swap/run.py`; aggregazione: `stage19_compact127_swap/aggregate.py`.
- Artifacts: `stage19-compact127-isolated-r1`, `-r2`, `-r3`, `stage19-compact127-isolated-final`.
- Il repository produttivo `AM1975MA/Etf_trader` non è stato modificato.
