# LINEAR annuale e mensile: risultati verificati

> Rettifica audit successivo 2021/2023: questo replay conserva Compact/Tail/Macro, ensemble MA3 e gestione rischio/esecuzione canonici, ma non invoca Opportunity (ne il router storico ne il cap Opportunity) o il cap shock opzionale. La precedente descrizione conversazionale di tutti i layer attivi era errata. BASE, annuale e mensile condividono la medesima ricetta di replay; i numeri restano invariati. Vedere `annual_diagnosis/REPORT.md` e `RISK_FINDINGS.md`.

## Decisione

Respingere LINEAR mensile come sostituto dell'annuale: CAGR, MaxDD e Sharpe peggiorano su tutti e tre i download. Conservare l'annuale come riferimento di ricerca LINEAR; nessuna promozione rispetto alla baseline originale o modifica al repository produttivo.

Periodo economico comune: 2017-02-01–2026-07-01, 2366 osservazioni canoniche. Tre revisioni congelate Yahoo dello stesso universo Original149: non sono tre campioni indipendenti.

| Modello | CAGR r1 | CAGR r2 | CAGR r3 | CAGR medio | MaxDD medio | Sharpe medio | Range CAGR (pp) | SD CAGR popolazione (pp) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BASE | 29.753448% | 30.843705% | 34.677079% | 31.758077% | -32.216416% | 1.105346 | 4.923631 | 2.111491 |
| LINEAR annuale | 29.664649% | 32.866464% | 32.421180% | 31.650764% | -28.452546% | 1.083741 | 3.201815 | 1.416112 |
| LINEAR mensile | 25.500920% | 26.598634% | 23.648806% | 25.249453% | -30.331213% | 0.918304 | 2.949828 | 1.217319 |

| Disaccordo tra download | BASE | Annuale | Mensile |
|---|---:|---:|---:|
| Top1 any | 43.026205% | 20.752325% | 18.258664% |
| Top2 ordinato any | 76.584954% | 52.874049% | 53.930685% |
| Top2 non ordinato any | 66.990702% | 41.462384% | 42.392223% |

Mensile meno annuale: CAGR medio -6.401312 punti percentuali; MaxDD medio peggiore di 1.878667 punti; range CAGR ridotto di soli 0.251987 punti. Il gate preregistrato fallisce. L'annuale aveva comunque fallito i precedenti gate assoluti rispetto a BASE: il confronto non autorizza un'adozione operativa.

## Che cosa e stato testato

Walk-forward causale con storico crescente (expanding), non finestra mobile degli ultimi 12 mesi. Annuale: cutoff 1 gennaio. Mensile: cutoff primo giorno del mese. Ogni fit LINEAR riparte da zero; nessun aggiornamento incrementale. Sono stati riusati byte per byte 30 stati di gennaio e calcolati 312 nuovi fit, per 342 stati complessivi. Stesse feature, loss ListNet, decili, L2, solver e regole di preprocessing/split dell'annuale; cambia la frequenza del cutoff. Viene sostituito solo Compact21, con ricalcolo dei discendenti; le altre regole canoniche V2 restano invariate.

Il 10% finale delle date mature viene riservato alla validazione, con purge. Per LINEAR queste osservazioni non entrano nell'ottimizzazione e non segue un refit sull'intero campione. Al cutoff 2026-06-01 l'ultima uscita di etichetta nel subtraining e 2024-01-03, mentre il campione maturo completo arriva a 2026-05-01. L'aggiornamento mensile pertanto non equivale ad apprendere dagli ultimi mesi. Anche l'annuale usa questa regola: il ritardo non dimostra la causa del peggioramento mensile.

BASE usa invece l'intero training maturo. BASE contro LINEAR non isola la sola architettura: cambiano anche campione effettivo, target/loss, regolarizzazione, preprocessing ed ensemble. Il confronto annuale contro mensile resta coerente all'interno della ricetta LINEAR.

LINEAR e un punteggio composto da una somma di feature standardizzate moltiplicate per pesi appresi. I pesi vengono ristimati a ogni cutoff. BASE XGBoost puo rappresentare soglie e interazioni non lineari. I dati disponibili non permettono di attribuire causalmente a questa differenza la maggiore o minore performance.

## Qualita predittiva e interpretazione degli esperti

Con aggregazione uniforme per data (`aggregate_by_date`), annuale verso mensile: percentile Top1 0.515373 verso 0.504999; NDCG5 0.514051 verso 0.516663; RankIC 0.003090 verso 0.003684. Evidenza mista: piccoli guadagni su alcune metriche, peggioramento Top1. Il CAGR del portafoglio completo non misura da solo la qualita del ranking.

Due agenti specialisti, apprendimento e interpretazione economica, hanno esaminato i sorgenti e discusso tra loro in italiano. Concordano sulla preferenza per l'annuale tra queste due implementazioni e sul rifiuto del mensile. Maggiore concordanza Top1 e minore dispersione CAGR non compensano il deterioramento economico; non provano maggiore correttezza predittiva. Non e dimostrato che il peggioramento derivi da overfitting, cambio di regime o ritardo del training. Il risultato non condanna il walk-forward mensile in generale.

Possibile prossimo audit, non eseguito: attribuire il divario mensile-annuale nei rendimenti logaritmici archiviati per mese/anno e accordo/disaccordo delle selezioni, annotando pesi e recenza del subtraining, senza nuovi fit. Una vera finestra mobile di 12 mesi sarebbe un esperimento diverso da preregistrare.

## Grafici e verifiche

`charts/ANNUAL_RETURNS_3_DOWNLOADS.csv`: 90 rendimenti anno-modello-download. `charts/ANNUAL_RETURNS_DISPERSION.csv`: 30 aggregati. Rendimenti netti composti dai log-rendimenti canonici; 2017 e 2026 sono periodi parziali, non annualizzati. Barre medie, punti dei tre download e intervallo min–max: non intervallo di confidenza. La crescita del capitale usa media e min–max delle equity, non il CAGR medio.

- [Run modelli, audit e confronto](https://github.com/AM1975MA/Test/actions/runs/38611937261), commit 8a130e6f735b47d295de9ea38bcbc03ce14cef1e. Fit, audit ed economia completati; stato globale failure solo per serializzazione JSON del grafico, corretta nel run separato senza ripetere i fit.
- [Run grafici corretto, success](https://github.com/AM1975MA/Test/actions/runs/38616382786), commit 9badb332ba2a613291cbfbf650861561d8575909.
- Artefatto modelli 11919650380: ZIP SHA256 `7a6d699cfa68d80c27beed18f3c349641ac73c4dd61a91ac4e0553d4afd4c897`.
- Artefatto confronto 11920785663: ZIP SHA256 `521605154c8a0c99313f9afbbafda49939f2a9b35d8540972d25d3c1b2c9257b`.
- Artefatto grafici 11919447275: ZIP SHA256 `dea35e0e51e50b1eb0a3a52fb053182eceda8987264b1e304b113ac95ff4503e`.
- Audit tutti i 342 stati PASS; massimo gradiente indipendente 9.997627532608091e-8, soglia 1e-7. Sette test dedicati PASS.
- Ricalcolo indipendente locale delle metriche dei sei replay candidato/controllo: massimo errore 2.220446049250313e-16. Novanta rendimenti annuali verificati contro l'artefatto CI alla stessa tolleranza. Nessun nuovo fit nella verifica o nel recupero grafici.

Input congelati conservati. Nessuna modifica al repository produttivo.
