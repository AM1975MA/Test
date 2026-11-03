# OLC42 — Audit critico delle strategie europee, universo EU152 e ricerca di informazione predittiva

**3 novembre 2026 · AM1975MA/Test · Ricerca retrospettiva, non un nuovo sistema di trading**

## Executive decision

Nessun nuovo 50% di CAGR europeo è stato dimostrato. Il riferimento OLC19 sul 2021–2024 è **23,1999% EU165** contro **50,7722% USA149**, per portafogli simulati con la stessa variante `TOP2_CONTEXT_REVALUE / FAST_LOCK3`, costo legacy 0,001. Il **52,3006% USA** appartiene alla diversa variante OLC17 `ALL_PREOPEN_V6` e non va trasferito ad altri esperimenti.

L'audit OLC42 è operativo su due aspetti circoscritti:
1. Una **nuova lista di ricerca EU152** ottenuta da EU165 escludendo 13 ETF distributivi quando un ETF ad accumulazione con lo stesso *indice attualmente dichiarato* è già presente, entrambi superano il filtro del prezzo originale osservato e l'Acc non ha storia inferiore al warm-up. Si mantengono **96 Acc e 56 Dist**. Questa scelta **NON certifica ancora equivalenza storica economica/PIT** né modifica l'universo di produzione.
2. La differenza fra mercati nel premio lordo della Top2 rispetto alla mediana del paniere è spiegabile contabilmente soprattutto dalla maggiore **dispersione delle opportunità** USA, e solo in parte dal diverso vantaggio di ranking standardizzato. Questo è un fatto statistico retrospettivo, non una causa certificata del divario nel CAGR netto dei portafogli.

## 1. Lineage, controlli e limitazioni

- Base universo: OLC39 `EU165_original_universe.csv`, con 165 ticker originali.
- Politica Acc/Dist e candidati: OLC41 (`research/olc41_eu165_acc_census_20261103/results/*`), commit origine `c229aa89f24d97a6ca438803d0b0c805b586da34`. Catalogo ETF secondario corrente 2026, non storico per ogni data.
- Etichette: OLC32 `OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz` dentro `OLC32_RESULTS.zip` congelato, con `label_valid`, `r_o2o_bp`, `auth_rank` e date Open→Open. La riparazione Xetra del 01/06/2020 ha riguardato etichette e NON retroattivamente il NAV OLC19.
- Revisione dei risultati: registro V3 (`V3_EXPERIMENT_REGISTRY.json`, 40 esperimenti) e principali rapporti OLC25, 26, 27, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 41, oltre ai report EU165 dei modelli V2/V3 e al riepilogo NAV OLC06–19.
- Non sono stati scaricati dati aggiornati post-luglio 2026, riprodotti tutti i 500×24 modelli né rieseguiti i backtest OLC19 con portafoglio e stop. Le analisi nuove sono *diagnostiche* sulla serie congelata; non sostituiscono i test precedenti.
- **Leakage/selection bias residui**: universo selezionato con informazioni del 2026; anni 2019–2026 già riutilizzati in molti tentativi; nessuna finestra retrospettiva del progetto può essere dichiarata nuovo holdout vergine. Mancano certificazione total-return EUR, quote `observed` USA originali, corporate action/delisted, PIT indice/share class, costi di negoziazione effettivi.

## 2. Filtro Acc/Dist e risultato EU152

Dal censimento: 165 ETF = 96 Acc + 69 Dist. Fra i Dist, 25 hanno un candidato Acc interno con lo stesso nome indice normalizzato, ma solo **13 coppie** hanno entrambi prezzi originali abbastanza antichi secondo OLC41. Si elimina in **un universo di ricerca separato** la riga Dist e si mantiene una sola volta il ticker Acc già esistente; si ottiene **152 = 96 Acc + 56 Dist**. Fra i 9 Dist effettivamente posseduti storicamente soltanto `IM2A.DE` è in questo gruppo, e l'Acc `EEAA.DE` è già esistente.

La condizione storica del candidato Acc include l'Open originale osservato fin dal 1 febbraio 2019, almeno 500 Open osservati prima del primo segnale del 2021, e almeno 1021/1026 Open osservati durante il 2021–2024. **Sono condizioni sui dati, non garanzie di training sufficiente per qualunque nuovo modello**. Delle 152 righe rimaste **24 non passano** il gate completo: devono essere rese eleggibili dinamicamente in base all'epoca e al lookback/target del modello; non vanno retrodatate né eliminate in modo permanente.

**Blocco qualità importante:** due ETF che oggi dichiarano lo stesso indice non sono automaticamente la *stessa classe*, né hanno identico TER, tracking error, valuta di negoziazione, esposizione valutaria, hedge, corporate action o distribuzione passata. Tutte le 13 esclusioni sono quindi segnate `RESEARCH_ONLY`, non `PIT_VERIFIED`; eventuale restauro/porting produttivo richiede prove di issuer/venue per la singola data.

### Test di sola esclusione, senza rifit (OLC32, 2021–2024)

| Controllo | Risultato |
|---|---:|
| Segnali mensili | 48 |
| Top2 diversa eliminando i 13 Dist | **2/48** |
| Top5 diversa | **5/48** |
| Proxy Top2 50/50, lordo, CAGR semplice 12/48 | **30,01% originale; 30,25% filtrato** |
| Differenza media di rendimento lordo | **+1,52 bp/mese**, tutta in due decisioni |
| 2025–2026: decisioni Top2 modificate | **0** |

Le modifiche sono 2023-09-29 (`EEAA.DE;IM2A.DE`→`EEAA.DE;ZPRP.DE`, +29,51 bp nel proxy 50/50) e 2024-06-28 (`VVSM.DE;IM2A.DE`→`VVSM.DE;EXH8.DE`, +43,60 bp). **Non è un backtest EU152**: non sono stati ricalcolati i 500 panieri, i modelli, gli score, l'esecuzione D+1, i costi o V6/FAST_LOCK3. Tutti gli score derivano dall'originale EU165. La sovrapposizione informativa nel training precedente rimane, anche se si filtra il Top2.

### Divergenza dei rendimenti delle coppie di medesimo indice nominale

Per le 13 coppie con date Open→Open osservate coincidenti nel 2021–2024, il differenziale assoluto medio tra ritorni mensili dei due ticker è **15,17 bp**, e solo **2/13 coppie** hanno meno di 5 bp/mese di differenza assoluta media. La coppia `EXXX.DE/XB4A.DE` arriva a 52,68 bp/mese di differenza assoluta media e un mese a 179 bp; `IM2A.DE/EEAA.DE` ha 13,51 bp/mese di differenza assoluta media. Non è un premio sistematico Acc: la media *firmata* cambia segno secondo la coppia. Non è provato che ogni discrepanza dipenda da distribuzioni: potrebbero concorrere differente fondo, sede, valuta, indice/gestione, rettifiche o altri effetti. **Non fondere né sostituire le serie storiche dei prezzi.**

## 3. Informazione effettiva nel cross-section EU contro USA

Etichette originali Open→Open, stesso intervallo e 48 mesi per mercato, `auth_rank` calcolato senza osservare l'esito futuro. Si considera il rendimento logaritmico medio lordo dei due primi AUTH, confrontato con la mediana dei titoli validi del rispettivo mese.

| Media mensile 2021–2024 | EU165 | USA149 |
|---|---:|---:|
| Rendimento lordo Top2, log-bp | 213,355 | 303,828 |
| Mediana lordo, log-bp | 69,725 | 33,252 |
| **Vantaggio Top2 − mediana**, log-bp | **143,630** | **270,577** |
| Dispersione cross-sectional, deviazione standard popolazione, bp | 290,409 | 455,785 |
| Vantaggio normalizzato per SD *della mediana*, medio mensile | 0,407 | 0,521 |
| Mesi Top2 superiore a mediana | 31/48 | 31/48 |
| Spearman medio globale FUSION vs futuro ritorno (diagnostica) | +0,007 | +0,006 |

Si noti che OLC35 riportava *un diverso z-score* calcolato sul premio sopra la **media** del paniere (EU ~0,437, USA ~0,523), non sulla mediana. I valori 0,407/0,521 qui derivano dal nostro z-score sulla **mediana**: nessuna discrepanza metodologica.

**Scomposizione algebrica esatta del divario USA−EU = +126,946 bp/mese** nel premio Top2−mediana:

- **+76,767 bp/mese**, differente livello medio della dispersione opportunità (60,5%).
- **+42,359 bp/mese**, differente vantaggio normalizzato (33,4%).
- **+7,821 bp/mese**, diversa covarianza mensile dispersione×vantaggio normalizzato (6,2%).

Identità impiegata per mercato: `E[adv] = E[z] × E[SD] + Cov(z,SD)`. La differenza simmetrica tra i due mercati è ripartita nei tre termini sopra; non attribuisce causalmente alpha né spiega matematicamente la differenza tra CAGR netti con stop. La SD è un **esito futuro**, non una feature nota alla data: non va usata nel trading senza previsione ex-ante.

Differenza per anno nel premio Top2−mediana in bp/mese: 2021 EU 93,3 vs USA 184,7; 2022 EU 173,9 vs USA 401,3; **2023 EU 250,0 vs USA 191,3**; 2024 **EU 57,3 vs USA 305,0**. La fragilità europea **non è uniforme**: il 2023 è favorevole all'Europa, mentre il 2024 è il maggiore collo di bottiglia. Il 2024 è già noto e non può essere usato per selezionare ex post un nuovo modello vincente. Il bootstrap circolare a blocchi di sei mesi sul premio USA−EU dà un intervallo descrittivo di **−40,54 a +318,08 bp/mese**: attraversa zero e non corregge i molti tentativi precedenti.

La correlazione di Spearman globale vicino a zero in entrambi i mercati, a fronte di premio positivo Top2−mediana, mostra perché **una metrica di ranking sull'intero universo** non equivale a capacità di scegliere economicamente bene la **coda Top2**. Non prova che i Top2 siano prevedibili con una variante migliore.

## 4. Ipotesi minimale nuova, testata e NON promossa

Obiettivo diagnosticare se l'**opportunità economica** (dispersione dei rendimenti futuri cross-sectional) sia stimabile da una sola feature non ridondante di prezzo: dispersione fra ETF dei ritorni passati a 63 giorni (`ret_63`), calcolata solo da feature con `feature_available_asof`. Target: SD del rendimento futuro Open→Open del mese. Baseline: mediana espandente delle SD mensili già maturate. Challenger: Ridge a una feature, `alpha=10`, StandardScaler sul train, rifitting espandente mensile con `exit_date < signal_date`. Niente selezione di ETF, stop né sizing, quindi **non è una nuova strategia**.

| 48 previsioni EU 2021–2024 | Baseline | Ridge 1 feature |
|---|---:|---:|
| RMSE della futura dispersione (bp) | **79,64** | 77,41 |
| MAE (bp) | **58,78** | 64,28 |

Correlazione Pearson grezza segnale→dispersione futura +0,249, Spearman +0,142. Il beneficio puntuale sul RMSE è marginale e contraddetto dal MAE; il bootstrap a sei mesi sulla differenza MSE baseline−Ridge dà un intervallo 95% descrittivo circa **[−2.012; +2.762] bp²**, quindi nessuna evidenza robusta di utilità incrementale. Nel 2022 migliora la MSE, nel 2023 e 2024 peggiora. **Esito: NO PROMOTION**.

## 5. Revisione critica delle famiglie già tentate

| Famiglia | Evidenza conservata | Decisione critica |
|---|---|---|
| V2/V3 originali e proxy | I proxy parziali EU165 non equivalgono ai nativi 125-feature/500 panieri; port nativo EU48 richiedeva kernel corretto e diete features | Non confrontare modelli con differenze di contratto, feature o execution |
| Momentum e persistenza OLC25 | Mix 126/252/3-segnali peggiorano entrambi i portafogli rispetto AUTH | Non ripetere bonus di momentum sull'ultimo ranking |
| Target leader a 6 mesi OLC26–27 | Migliora IC cross-section 126d in EU ma peggiora o non muove la Top2; OLC27 cambia Top2 e perde rendimento mese successivo | Target e orizzonte di possesso non allineati |
| KAMA/area/slope OLC29–30 | L'ingresso iniziale anticipato in un best ticker ex post non si traduce in persistenza e NAV migliore | Nessuna promozione di filtri trend universali |
| Core dominante OLC36 | 41/48 sostituzioni; proxy 50/50 EU 27,93% AUTH → 8,24% DOM_CORE | **Rifiutare** la regola di core persistente già provata |
| Raw magnitude OLC31 | Ridge + raw score peggiora MSE/MAE in EU e USA | Il ranking grezzo non è stima calibrata del ritorno |
| Target economico OLC32 | Ridge/HGB con 16 feature addizionali non battono FUSION-only e peggiorano Top5 sign | Evitare altro ML tabellare sullo stesso materiale informativo |
| VIX OLC34 | Classificatore Brier peggiore del null; pochi switch | Fonte esterna ≠ edge se non predice il payoff corretto |
| Fattori OLC37–38 | Clone meno rischioso/risk-unmatched, manca semiconduttori e PIT look-through; leader a 126d non basta | Calibrare esposizioni vere prima di dichiarare alpha fattoriale |
| Metodologia OLC35 e OLC41 | Gap top5 vs futuro best simile per mercato; catalogo 2026 e vecchi dataset non PIT | Dedup e fattori economici prima di nuove combinazioni |

La ricerca successiva dovrebbe **smettere di ottimizzare l'ennesima funzione di score sullo stesso 2021–2024**. Un risultato 40–50% ottenuto ora modificando molti coefficienti sul medesimo campione sarebbe un forte candidato a selezione retrospettiva, non a salto verificato.

## 6. Roadmap focalizzata sul salto di qualità, ordine di priorità

**Gate A — dati certi prima della ricerca su alpha.** Mappare ISIN/ticker/sede/indice/classe *point-in-time*, inclusi cambi di indice/merger; ottenere serie prezzi tradabili realmente osservate, dividend total-return in EUR con regole coerenti, delistati e corporate actions. Verificare calendario venue, possibilità di esecuzione preopen, commissioni, spread/slippage e stato del mercato USA alla decisione europea. Nessuna retrofusione della serie Dist dentro la serie Acc.

**Gate B — togliere il peso informativo artificiale degli indici duplicati.** Generare panieri 500×24 su gruppi economici PIT e roster eleggibili: monitorare esposizioni effettive per settore, area, fattore, valuta sottostante e hedging, non soltanto sei categorie nominali o il ticker di quotazione. Stabilire che i **96 Acc + 56 Dist** non significano 152 scommesse indipendenti.

**Gate C — separare tre problemi diversi.** (i) Previsione *causale* della dispersione/opportunità fra fattori al prossimo periodo di esecuzione; (ii) selezione *relativa e residuale* di ETF dentro fattori comparabili, con target 21/42/63 che coincida con il periodo effettivo di possesso; (iii) dimensionamento coerente e risk budget, confronto con lo stay-current a costi veri. Il motore esistente AUTH/OLC19 è il baseline; ML solo metagovernor dopo evidenza positiva sui gate precedenti. Non fare un ranking diretto a 6 mesi e usare il suo segnale per il mese immediato senza verificare il disallineamento.

**Gate D — ricerca scientificamente falsificabile.** Congelare un unico candidato e un protocollo di target/split/pricing prima di osservare i nuovi dati, con cutoff di maturazione, walk-forward, cluster/bootstrap per mese, benchmark factor/risk-matched, controlli placebo, stabilità fra regimi e conti nettamente riconciliati. Gli anni fino a luglio 2026 sono ampiamente esplorati; raccogliere dati successivi senza adattare il modello al campione di valutazione. Richiedere un aumento di rendimento netto persistente senza drawdown ingestibile: l'obiettivo 50% è aspirazionale, **non un benchmark da forzare**.

## Output prodotti

- `EU152_RESEARCH_UNIVERSE_NOT_PROMOTED.csv` e `EU13_DIST_EXCLUDED_RESEARCH_ONLY.csv`: pubblicati sul ramo GitHub di ricerca OLC42 con script di rigenerazione e verifica GitHub Actions.
- `eu_dedup_pit_preliminary.csv`: audit per mese Top2 originale/filtrato OLC32.
- `acc_dist_same_index_spreads.csv`, `acc_dist_same_index_monthly_spreads.csv`: differenziali osservati Dist/Acc a parità date.
- `OLC42_EU_US_MONTHLY.csv`, `OLC42_EU_US_BY_YEAR.csv`, `OLC42_EDGE_DECOMPOSITION.csv`, `OLC42_PAIRED_EDGE_BOOTSTRAP.csv`: ricostruzioni quantitative e decomposizione.
- `OLC42_PREQUENTIAL_DISPERSION.csv`, `OLC42_PREQUENTIAL_DISPERSION_SUMMARY.csv`: unico test informativo ex-ante di opportunità, non operativo.
- `diagnose_dedup.py`, `paired_etf_spreads.py`, `olc42_opportunity_decomposition.py`, `olc42_prequential_dispersion.py`: sorgenti e verifica di input necessari nei commenti.
- `figures/01–04`: grafici diagnostici, NON NAV investibili.

**Stato finale:** dati e laboratorio europeo migliorati, nuovo ranker non promosso, nuovi backtest nativi non eseguiti, `main`, `Etf_trader`, OLC19 e USA149 invariati.