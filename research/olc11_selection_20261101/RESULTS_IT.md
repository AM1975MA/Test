# OLC11 — obiettivo selettivo e disponibilità delle etichette relative

1 novembre 2026. Lotto concluso; integrazione di ricerca, nessuna promozione su main. 240nuovi modelli annuali,4refit originali di controllo,zero nuovi portafogli e nessun nuovo CAGR.

## Contratto

Stessi42inputHybrid ordinati, stesse famiglie/budget, anni2019–2026, seed101/211/307 fissati prima dei risultati. NativeY=.45rank21^1.5+.35rank42^1.5+.20rank63^1.5: forza relativa futura, non rendimento o probabilità di guadagno. Return125RSI resta congelato.

Cinque learner per anno/mercato/seed: regressoriET/XGB, classificatoriET/XGB del quintile superiore diY, rankerXGB con NDCG/guadagni lineari e rilevanza round(15Y). Nessuna ricerca di iperparametri. Le scale delle funzioni obiettivo cambiano: stessi coefficienti di regolarizzazione non certificano identica complessità effettiva. I classificatori non hanno class weighting né oversampling.

Tutti i nuovi bracci usano gruppi mensili completamente osservati, la cui ultima uscita63 precede il cutoff annuale. La restrizione modifica il trainingEU, quindi il confronto primario è con regressori RIADDESTRATI SULLE STESSE RIGHE, non direttamente con il vecchio modello. Il controllo originale archiviato resta distinto. I quattro refit2022 riproducono esattamente i forecast originali. Nessuna assenza di label futura rimuove una previsione corrente.

## Miglioramento del layer isolato

Segnali2021–2024 con esiti63maturi prima del2025,44mesiEU/45USA, media delle previsioni grezze dei tre seed, uguale peso per mese:

|Metrica nativa|EU XGB regressore|EU XGB classificatore|USA regressore|USA classificatore|
|---|---:|---:|---:|---:|
|NDCG@2|0,4730|0,5235|0,4562|0,4929|
|Quota Top2 nel miglior20%diY|32,95%|37,50%|35,56%|38,89%|
|Quota Top2 nel peggior20%diY|22,73%|22,73%|28,89%|18,89%|
|Rammarico sul target|0,5061|0,4689|0,5282|0,4841|

L'NDCG migliora in tutti6confronti mercato×seed. La precisioneTop2 migliora in5su6: seed101EUlievemente sfavorevole. Nessun seed selezionato come vincitore. Il ranker standalone non supera il regressore abbinato nei due universi sulle metriche principali: NDCG circa0,447EU/0,434USA. Gli altri esiti sono conservati, non si proclama superiore una famiglia dal nome dell'obiettivo.

Payoff statico Top2meno media dell'universo, punti percentuali PER ORIZZONTE (non CAGR, non cumulabili, senza costi/stop/rotazioni):

|Orizzonte|EU reg|EU class|USA reg|USA class|
|---|---:|---:|---:|---:|
|21sedute|−0,03|+0,63|+0,73|+1,86|
|42sedute|+0,32|+1,82|+0,60|+2,97|
|63sedute|+1,55|+3,11|+0,07|+3,26|

Sono46mesi a21sedute in entrambi;44EU/45USA a63. BrierXGBCLASS: EU0,158480 controprior0,160842; USA0,157368 contro0,160804. Logloss migliora anch'esso. Sono previsioni dell'evento relativo, non probabilità di guadagno e non calibrazione certificata in ogni sottogruppo.

## Il beneficio non sopravvive automaticamente alla composizione

NDCG@2prima della fusione, dopo ranking percentile.6ET+.4XGB: EUcontrollo0,5089 contro0,4624 sostituendo soloXGB col classificatore; USA0,4660 contro0,4757. Nella fusione finale conReturn e lag: EU0,5411 contro0,5391; USA0,5283 contro0,4667. PrecisioneTop2finaleUSA41,11%contro35,56%.

La selezione isolata migliore NON autorizza a sostituire direttamente lo score nella strategia. Regressione, probabilità dell'evento e rango sono canali diversi. Il classificatore resta un nuovo specialista candidato; il regressore resta riferimento per stimareY. Non vengono ritarati i pesi dopo gli esiti.

## Correzione temporale dimostrata

La regola originaria verificava l'uscita del singoloETF, ma il suo percentile futuro dipende anche dai rendimenti degli altriETF dello stesso gruppo. SuEUsono stati trovati18casi realmente dipendenti da esiti ancora ignoti al cutoff:

|Fit|Data segnale|Righe ammesse troppo presto|Peer ancora ignoti|
|---|---|---:|---:|
|2019|2018-09-28|5|128|
|2025|2024-09-30|6|146|
|2026|2025-09-30|7|157|

Ricostruito esattamente il target originale; alterati soltanto rendimenti63dei peer con uscita successiva al cutoff. Tutti18target delle righe ammesse cambiano, pur lasciando invariati input e rendimento già noto dell'ETF stesso. Non sono stati trovati casi analoghi negliUSA nel perimetro esaminato.

Il criterio per intero gruppo maturo era già preregistrato e impedisce questi casi. Esclude anche gruppi storici incompleti: non tutte le righe rimosse sono leakage. Nel periodo principale2021–2024 la differenza di campione è soprattutto il gruppo incompleto giugno2014. Il miglioramento del controlloEU non viene quindi attribuito interamente alla correzione temporale.

Non viene stimato l'effetto di questi18casi sul vecchio39,33%o su altriCAGR; servirebbe un replay completo separato. Gli archivi storici restano intatti, ma maturazione riga-per-riga non è più considerata sufficiente per questo target relativo.

## Incertezza e limiti

Nel2025EUsolo5mesi hanno tutte le label63mature entro fineanno: classificatore nel quintile peggiore70%degli slot contro60%regressore. GliUSA hanno9mesi;2026parziale soltanto2per mercato. Nell'intera finestra attiva la selezione alta migliora in entrambi ma la frequenza europea dei peggiori aumenta leggermente. Non si nascondono questi esiti.

Bootstrap appaiato44mesi comuni nella griglia48mesi2021–2024,6000repliche,blocchi3/6,seed20261101. DeltaNDCGXGBclass-reg,blocchi6: EU+0,0505 IC95%[−0,0469;+0,1489]; USA+0,0376[−0,0326;+0,1214]. Intervalli simultanei della famiglia più ampi. La tabellaUSAusa45mesi mentre il pairing44; differenza esplicita. Lo zero non è veto automatico; stabilità al ricampionamento non è probabilità posteriore. Storia già ricercata e mercati con sottostanti condivisi.

## Verifiche e persistenza

Tutti240modelli riaperti, forecast identici;16gruppi annuali ricostruiti indipendentemente;28728metriche mensili target e28064valori di riepilogo verificati, errore massimo4,44e−16.10perturbazioni di input futuri preservano previsioni passate;14verifiche conservano Return e supporto corrente.15test nuovi e26ereditatiOLC10passati nelle rispettive suite, non dichiarata verde l'intera suite storica. Autorevisione, non revisore indipendente.

Un errore di serializzazione numpy nell'audit è stato corretto con test rosso/verde e non cambia risultati/modelli. Rimangono prezzi total-return, survivorship, duplicati economici, spread e filllegacy non certificati. Zerooperazioni live.

Il branch contiene tutti11moduli sorgente usati,2filetest, parametri e sintesi. I checkpoint completi includono matrici annuali preparate, modelli, label e output; non sono un nuovo archivio rawOHLCuniversale. Sono nellaLibrarypersistente con hash registrati, NON automaticamente assetGitHub. Per rigenerare i pannelli dal raw servono i parent; per riaddestrare/valutare il lotto bastano gli input inclusi. Main invariato.
