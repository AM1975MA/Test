# ETF Trainer V2 USA149 vs EU48 — forensic completa, 19 ottobre 2026

## Stato della prova

La spiegazione non è un'unica causa: il motore ETF Trader V2, portato a 48 soli ETF Europe-underlying, non mostra alpha affidabile nel ranking, e i suoi stop calibrati sugli ETF USA peggiorano contemporaneamente CAGR e MaxDD. Una parte del divario pubblicizzato USA/EU dipende invece da una differenza metodologica della stessa simulazione, già quantificata.

- Refit EUR48 eseguito realmente: Titanium e MA3 Hybrid24 originali, 6 annual fit 2021–2026, target maturi.
- Stesso universo 48 ISIN, identiche previsioni 65 mesi, 1374 sedute market Open EU 2021-02-01–2026-07-01. Prezzi Open e Close Yahoo invariati; correzioni tracciate SOLO High/Low per 49 OHLC incoerenti dell'input esecutivo.
- Ripetizione NO REFIT dei risultati V2 originali source-fed entro errore assoluto 1e-12 giorno per giorno nel forensic GitHub Actions [39323294312](https://github.com/AM1975MA/Test/actions/runs/39323294312); confronto 500 Europe source baskets riuscito nella GitHub Action [39324034001](https://github.com/AM1975MA/Test/actions/runs/39324034001).
- Nessuna variazione ai sorgenti del repo AM1975MA/Etf_trader; tutta la ricerca su AM1975MA/Test branch research/etf-v2-eu48-causal-audit-20261019.

## 1. Non sono due risultati omogenei

| Esame | USA149 originale | EU48 portato |
|---|---|---|
| Universi | 149 ETF globale+USA+EM+commodity+fixed income | 48 ISIN di underlying rigorosamente europei |
| Metodologia | Media CAGR di **500 portafogli** casuali ma deterministici, 24 ETF, 4 di ognuna delle 6 categorie, top2 entro ogni basket | **UN portafoglio libero** Top2 fra 48 ETF, nessuna quota per settore |
| Data di partenza | Feb 2017 | Feb 2021 |
| Fine | Lug 2026 | Lug 2026 |
| Fonte forecast e calcolo | Original Titanium, MA3 Hybrid24, DD-first, V6, HighCAGR24, V2 | Refitted F3? **NO**: il vero Titanium, MA3 Hybrid24, DD-first, V6, HighCAGR24, V2, ma import/macro/risk adapter EU dichiarato |
| CAGR V2 | **24.897% storico full 2017–26**; **30.557% DIAGNOSTICO 2023–26** | **1.636% 2021–26** |
| Status investment | FROZEN_CANDIDATE, manca test temporale futuro genuinamente unseen | Ricerca fallita sui 48, non promuovere |

Fonte originale ufficiale: AM1975MA/Etf_trader/docs/ETF_TRAINER_V2.md, results/MA3_HYBRID24_CURRENT_RAW_20260924.json e versions/ETF_TRAINER_V2/VERSION.json vendorizzato.

**Original USA non prova +25pp di alpha**: la media storico 2017–26 dei 500 ETF migliori scelti con conoscenza ex-post fra ogni basket (benchmark impossibile da negoziare) rendeva già **24.129% CAGR**, vicino alla strategia USA Hybrid24 **24.490%**; differenza +0.361 punti. Le categorie incluse, il buon regime e la possibilità di rotazione fra asset ad alta crescita spiegano ampia parte del rendimento assoluto, non una previsione autonoma pari a +25pp di alpha. Il confronto USA non ha tuttora una prova prospettica successiva a Lug2026.

## 2. Controllo diretto del meccanismo di 500 panieri: 48 Europa, stesso training, stessi prezzi, zero tuning

Replicata sul dataset EU48 la **STESSA** costruzione dei 500 panieri 24 ETF 6 x4 della strategia USA, usando le **STESSE IDENTICHE** nuove previsioni europee usate dal test libero, i medesimi controller e le 1374 giornate.

[Action 39324034001](https://github.com/AM1975MA/Test/actions/runs/39324034001), verificata success. Non è la variante richiesta dall'utente, ma un controllo sperimentale per spiegare la differenza metodologica.

| Stessa EU48, modello | 1 portafoglio libero 48 ETF | MEDIA di 500 panieri bilanciati 24 ETF |
|---|---:|---:|
| Hybrid24 | **+1.3602%** | **+5.4626%** |
| **V2** | **+1.6362%** | **+5.5132%** |
| MaxDD del V2 | -37.1934% | -33.6055% di MaxDD medio dei 500 |
| V2 vs Hybrid24 | +0.2761 pp | +0.0505 pp |

Differenza di valutazione V2 bilanciato vs libero **+3.877 punti CAGR**. Panieri bilanciati EU: mediana CAGR V2 +5.281%, 10° percentile -0.275%, 5° percentile -1.157%, peggior fondo -5.829%, best basket +19.178%; 88.6% dei 500 panieri CAGR positivo. **Solo 48.6%** dei 500 ottiene un risultato V2 migliore della propria baseline Hybrid24: quindi V2 NON aggiunge un vantaggio affidabile nel gruppo EU. I 500 panieri condividono moltissimi ETF e date; NON sono 500 esperimenti indipendenti. La media dei CAGR non è il rendimento CAGR di un portafoglio investibile reale che abbia un patrimonio aggregato unico.

**Anche dopo questo controllo, 5.51% EU vs 24.90% US rimane un enorme divario**; cambia anche il periodo osservato. Quindi la metodologia spiega una parte del 1.64%, non l'intera crisi.

## 3. Quanta performance distruggono effettivamente i layer di rischio EU

Audit **stesse medesime previsioni** e stessi pesi del producer, senza fittare nuovi modelli o rivalutare le scelte future. Il controller/risk budget viene rimosso separatamente. La somma delle differenze in CAGR fra portafogli con traiettorie auto-finanziate NON è una scomposizione algebrica perfettamente additiva, perché stop, gross, turnover e compounding interagiscono.

| Configurazione | CAGR netto costed | MaxDD |
|---|---:|---:|
| Top2 libero, senza stop né gross controller | **3.8795%** | -34.9955% |
| Top1 libero, senza stop né gross | **4.4941%** | -35.8817% |
| Top2, solo stop originali | **1.3903%** | -37.1608% |
| Top2, solo DD-first gross controller, NO stop | 3.5965% | -36.3579% |
| Top2, DD-first + stop, senza V6 | 1.3727% | -37.1934% |
| Full Hybrid24 | **1.3602%** | -37.1934% |
| Full ETF TRAINER V2 | **1.6362%** | -37.1934% |
| Full Hybrid24 ma commissioni 0 | 2.6527% | -35.9748% |
| Top2 zero risk/zero stop/zero commissione | 4.9633% | -34.0444% |

**Lo stop originale 5.5% è dannoso nel nostro scenario storico europeo**: CAGR perde circa -2.49pp rispetto allo stesso Top2 senza stop e il DD peggiora di -2.17pp invece di migliorare. DD-first gross da solo sottrae -0.28pp CAGR e peggiora DD -1.36pp; V6 alternate sottrae -0.013pp; le fee dirette sottraggono circa -1.29pp CAGR dalla full Hybrid24. V2 top1 risk-off interviene solo in 3/65 segnali mensili (=41 sedute), beneficiando di +0.276pp rispetto a Hybrid24 ma senza migliorare DD.

### Stop per anno, medesimo Top2 e commissione 10bps

| Intervallo | Top2 senza stop | Con soli stop | Δ ritorno annuo |
|---|---:|---:|---:|
| 2021 Feb–Dic | +4.689% | +6.868% | +2.179 pp |
| 2022 | -7.785% | -10.384% | -2.599 pp |
| 2023 | +27.455% | +27.455% | ~0 pp |
| 2024 | -2.014% | -5.475% | -3.461 pp |
| 2025 | -0.807% | -6.709% | -5.902 pp |
| 2026 Gen–Lug | +2.902% | +0.166% | -2.736 pp |

Stop utile 2021, ma nettamente dannoso 2022/2024/2025/2026; occorre audit di eventi Low, spread e riacquisti prima di concludere che basta disabilitare gli stop. Di 49 OHLC anomalie originali la grande maggioranza era su ticker AS; i file DERIVATI espandono solo l'High/Low envelope e lasciano gli originali disponibili per audit. Non è provato che gli stop perdenti dipendano solo da anomalie vendor.

## 4. Anche il RANKER fallisce il proprio compito europeo

- Ranking mensile vs rendimento del mese successivo, 65 cross-section di 48 ISIN: Spearman medio **+0.048235**, 34/65 mesi positivo. Intervallo di confidenza **exploratory** block-bootstrap 3 mesi circa [-0.008,+0.108], contenente 0.
- Il Top2 selezionato a budget corrente registra, prima delle commissioni, un rendimento log mensile successivo pari alla media cross-section **meno 0.2566 punti percentuali ogni mese**, battendo la media dei 48 in soli **32/65 mesi**. Block-bootstrap 3 mesi circa [-1.277,+0.720] punti/mese: non statisticamente distinguibile da zero.
- Top1 realmente eletto: **60 volte ETF settoriali, 5 volte property, ZERO governativi**. La critica sui sette ETF governativi presenti nell'universo non spiega direttamente il fallimento del V2 (a differenza dell'altro modello F3 che investiva tanto anche nei bond).
- Leader 13 mesi **XS8R.DE, tech Europa**, fondo con buy&hold 2021–26 CAGR circa +1.20%; 9 mesi **EXV5.DE, consumer discretionary Europa**, buy&hold circa zero; 9 mesi **EXV3.DE, tech Europa**, buy&hold +10.3%; 6 mesi **EXV1.DE, banche Europa**, il fondo che ex-post ha reso circa +34.1% CAGR. Non scegliere retroattivamente EXV1 è un'impossibilità metodologica; basta questo profilo per constatare che il ranker non ha saputo indirizzare con stabilità i vincitori.
- Benchmark MSCI Europe IMEU.AS **+12.574%** lordo senza costi in identica finestra EU1374, mentre il Top2 senza alcuna protezione fa +3.88% dopo 10bp. Quindi nemmeno abolendo tutti i risk layer il ranking EU produce una performance economicamente competitiva.

**Identità economiche/fattori**. USA dispone di settori tech globali forti e trend diversi, ETF di altri mercati, real asset, cash ETF Treasury; EU48 solo Europa, con 23 sector ETF in parte sovrapposti e government/property duramente penalizzati 2021–26. Il primo modello MA3 EUR48 nel 2021 vede solo **49 segnali mensili maturi × 48 ETF = 2,352 label**; 48 ETF altamente correlati non equivalgono a 2352 osservazioni statisticamente indipendenti. Il modello USA originale aveva feature/discovery e training vintage disponibili dal 2011 e blend selezionato su 2017–22, quindi esperienza/regime/feature scaling molto diversi. Il port 8→6 cluster, cash BIL/SHV→IBCA/IBCN e fattori SPY/HYG/IEF→IMEU/IHYG/EUNH rompe l'equivalenza economica e potrebbe alterare l'utilità degli stop.

## Limiti di inferenza
- I 48 fondi appartengono a un universo di **sopravvissuti nel 2026** scelto anche ex post per data quality. Non è una ricostruzione PIT del 2017.
- Yahoo adjusted prices revisionati ex post, zero volume vendor non sempre assenza di scambi, High/Low incompleti, nessuna prova bid-ask spread o fill reali.
- Anche il +24.897% USA è uno storico ottenuto dopo screening e sviluppo ripetuti e la V2 è FROZEN_CANDIDATE in attesa di unseen post2026-07; non confondere un forte backtest con alpha prospettica certa.
- Nessuna nuova regola/tuning selezionata ex post per massimizzare EU48: tutte le modifiche sono disattivazioni controfattuali e confronto con il disegno dei 500 basket USA.
- Non sommare il +3.88pp dei 500 basket, il +2.49pp degli stop e l'effetto fee come componenti lineari indipendenti.

## Conclusione e ordine operativo
V2 su EUR48 **non soddisfa i requisiti per produzione**. Il rendimento +1.64% è reale come risultato simulato, non deriva da un refit mancato o da un vincolo fittizio sui settori. L'effetto del trasferimento fuori dal dominio USA è decisamente deludente. L'inversione degli stop è evidente e correggibile solo con futura robustezza; più grave, il ranker non mostra un edge economico nemmeno senza controller. Ordine: A) validare Low/stop/gap e falsi trigger su venue multiple ISIN; B) isolare capacità predittiva su US/EU matched equity-only con stessi periodi e 500×24 e singolo-asset; C) ricostruire regimi europei PIT e ridefinire eventuali feature/target solo su training non-minato; D) test out of sample non aperto, no promotion, repo produzione intatto.

## Evidenze complete
- [Action 39323294312](https://github.com/AM1975MA/Test/actions/runs/39323294312): exact daily parity + ablations. File: isin_first2026/v2_forensic48/results/RESULT.json, ABLATION_SAME_1374_SOURCE_SIMULATOR.csv, DAILY_NAV_ALL_RISK_AND_RANK_ABLATIONS.csv, MONTHLY_SCORE_SKILL_AND_SUBSEQUENT_RETURNS.csv, SOURCE_EU48_MONTHLY_EXECUTION_CALENDAR.csv e SHA256_MANIFEST.txt.
- [Action 39324034001](https://github.com/AM1975MA/Test/actions/runs/39324034001): 500 basket model/risk-style matched comparison. File: isin_first2026/v2_forensic48/matched500_results/RESULT.json, EU48_500_MATCHED_BASKETS_METRICS.csv, SHA256_MANIFEST.txt.
- Frozen source EU48 primary GitHub Action 39320679509 and results in isin_first2026/v2_unrestricted48/results/.
