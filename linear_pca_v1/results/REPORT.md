# LINEAR annuale PCA95: risultato verificato, variante respinta

Decisione: mantenere LINEAR annuale originale come riferimento di ricerca; respingere questa PCA95. Ridurre la dimensionalita non migliora automaticamente previsione o stabilita. Nessuna promozione in produzione.

30fit completi (10anni x3download); in ogni fold restano43componenti ortogonali su125, con95.0200-95.1479%varianza conservata. Unica soglia95% fissata prima dei risultati, nessun whitening. Stesso training/split/purge, nessun full-training refit, stesso ListNet/L2/solver, portafoglio/rischio/costi/esecuzione. Opportunity escluso.

| Configurazione | CAGR r1 | CAGR r2 | CAGR r3 | CAGR medio | MaxDD medio | Sharpe medio | Span CAGR pp | SD CAGR pp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LINEAR annuale125 | 29.664649% | 32.866464% | 32.421180% | 31.650764% | -28.452546% | 1.083741 | 3.201815 | 1.416112 |
| PCA95/43componenti | 22.926474% | 18.798357% | 18.164166% | 19.962999% | -29.891994% | 0.753440 | 4.762309 | 2.111428 |

| Disaccordo tra download | LINEAR annuale | PCA95 |
|---|---:|---:|
| Top1 any | 20.752325% | 26.754015% |
| Top2 ordinato any | 52.874049% | 46.534235% |
| Top2 non ordinato any | 41.462384% | 33.939138% |

| Anno | LINEAR medio | PCA95 medio |
|---|---:|---:|
| 2021 | 1.837272% | -1.817015% |
| 2023 | 5.476594% | -7.547513% |

PCA95 peggiora CAGR in ciascun download; CAGR medio -11.687766pp. Il drawdown medio peggiora di1.439448pp; in r2 peggiora oltre il limite2pp. Span eSD del CAGR aumentano. Top2 diventa piu concorde, ma Top1 meno concorde: non e una stabilizzazione complessiva utile. Gate economico preregistrato FAIL (CAGRmedio,ognidownload,Sharpe,DDindividuale,span,Top1). Entrambi i controlli di qualita relativa95% passano, ma la qualita assoluta resta debole: non sufficienti per adottare.

## Qualita e interpretazione

Percentile Top1 perdata:0.515373->0.500386; NDCG5:0.514051->0.507671; RankIC:0.003089->-0.015555. Sono metriche standalone di Compact21, non il rendimento del portafoglio completo. Preservare95%varianza degli input non significa preservare95%informazione predittiva. Il risultato e compatibile con l esclusione di direzioni utili, ma non dimostra quali siano ne che ogni riduzione dimensionale fallisca.

La base risulta molto simile fra download nelle coordinate standardizzate (distanza normalizzata fra proiettori media0.000399,max0.000515), e k=43 sempre. Questo non impedisce instabilita delle decisioni finali; numerazione/segni delle componenti non equivalgono a stabilita economica. Ogni download ha il proprio scaler: la distanza non misura direttamente uno spazio comune di prezzi grezzi.

Il controllo con tutte125direzioni usa i coefficienti annuali gia archiviati: errore massimo degli score2.1538326677728037e-14, normaL2 invariata entro1e-10. Nessun riaddestramento del controllo completo. Conferma la distinzione fra rotazione equivalente e vera restrizione del sottospazio.

## Verifica e provenienza

[Run38968119427 SUCCESS](https://github.com/AM1975MA/Test/actions/runs/38968119427), commit2dfa69f59bb168d5f02f6da031a47f9eb4668d37.27test PASS (4PCA,23regressione). Audit30modelli ricostruisce preprocessing/PCA solo da subtraining e verifica soglia,ortogonalita,proiettori,coefficienti,inferenza e gradientePC indipendente. Massimo residuoPC9.94425947363397e-8, soglia1e-7. L algoritmo PCA di ricostruzione riusa la stessa funzione, mentre gradiente/inferenza hanno controlli separati: non si presenta come certificazione con un algoritmo PCA indipendente.

ZIP modelli e confronto verificatiSHA256 prima dell estrazione (ARTIFACTS.json). Verifica locale:30hash checkpoint e ortogonalita/coefficienti/sogliaPASS;6percorsi candidato/BASEcontrollo ricalcolati con formula separata, massimo errore2.220446049250313e-16. Tutti gli array dei3controlli corrispondono agli archivi precedenti entro1e-12. Nessun nuovo fit nella verifica locale.

Periodo2017-02-01--2026-07-01,2366osservazioni,113periodi completi/114segnali disponibili. I rendimenti2017e2026 sono parziali, non annualizzati nelle tabelle annuali. Tre revisioni correlate dello stesso mercato, periodo gia ripetutamente esaminato, nessuna validazione futura indipendente. Fonti e archivi originali conservati. Solo AM1975MA/Test; produzione intatta.

## Prossima idea richiesta dall utente: solo pianificazione

Bozza separata `raw_patterns_v1/EXPERIMENT_DESIGN.md`: OHLCV normalizzati senza indicatori tecnici, finestre21/63/126sedute, controllo lineare sugli stessi input e piccolaMLP condivisa traETF. Dense non previene overfitting; pilot temporale pre2017,capacita limitata e regolarizzazione da fissare prima del periodo gia osservato. Non concatenare finestre sovrapposte duplicando dati. Target resta21sedute. Nessun fit di questa linea e stato avviato. Il budget completo con3seed sarebbe270fitMLP+90lineari, quindi prima va misurato il costo di un pilot e congelato il protocollo.
