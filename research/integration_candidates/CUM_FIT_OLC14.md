# CUM_FIT OLC14 — candidata prioritaria di integrazione

Registrazione: 2 novembre 2026, su richiesta dell'utente. Stato: **CANDIDATA_PRIORITARIA_NON_PROMOSSA**. Nessuna modifica a main, nessun ordine, nessuna sostituzione implicita della baseline.

## Identità congelata

Repository: AM1975MA/Test. Esperimento padre: research/olc14-fitted-ranking-20261101, commit `6fcc215eeaa9834f5bcf8581e1fa6549a403f5b2`. Fonti: `research/olc14_fitted_ranking_20261101/RESULTS_IT.md`, `src/chrono_fit.py`, `src/ranking_core.py`, sorgenti e archivi indicati nel report OLC14. Questa scheda ricopia risultati documentati del padre; non sono nuovi test.

## Configurazione da preservare

Tre teste cumulative C21/C42/C63 stimano separatamente i percentili dei rendimenti dall'ingresso alle tre scadenze, elevati a 1,5. Stessi 42 input Hybrid e due famiglie ET/XGB; media dei tre seed 101/211/307 sulle previsioni grezze, poi score di testa .6*percentile(ET)+.4*percentile(XGB).

La combinazione usa S=sum(beta_h*z_h**alpha), beta>=0, somma beta=1. Pesi stimati ogni primo gennaio 2021–2026 usando previsioni storiche fuori campione ed esiti di gruppo interamente maturi; curvatura alpha e penalità scelte nella validazione temporale interna. Il 2019–2020 usa il controllo fisso, non costituisce successo del fitting. Una sola formula annuale condivisa USA/Europa; non è una stima separata per continente. I beta sono pesi dei segnali, non percentuali di capitale né durate di possesso.

Il criterio del fitting è il vantaggio relativo U delle opportunità, non il CAGR. U=(L0_21+q*L21_42+q^2*L42_63)/(1+q+q^2), q=2^(-21/42). Scale dei punteggi allineate senza esiti futuri; memoria e fusione Return invarianti. Il classificatore OLC11 non viene implicitamente aggiunto a questa candidata.

## Evidenza da preservare insieme ai limiti

2021–2024, IMMEDIATE, nominale 50/50, costo legacy .001 sul mezzo turnover L1:

| Configurazione | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| ORIGINAL | 20,03% | -23,25% | 39,92% | -27,00% |
| CUM_FIXED | 22,11% | -25,79% | 30,83% | -20,15% |
| CUM_FIT | 22,75% | -30,82% | 39,01% | -19,18% |

Febbraio 2019–1 luglio 2026, stessa modalità:

| Configurazione | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| ORIGINAL | 14,94% | -33,68% | 38,13% | -30,69% |
| CUM_FIXED | 17,82% | -32,09% | 36,40% | -25,53% |
| CUM_FIT | 18,10% | -32,09% | 42,08% | -25,53% |

Motivo della conservazione: crescita e drawdown completi favorevoli nei due universi; nel periodo principale crescita americana vicina all'originale con drawdown ridotto. Il costo di rischio europeo nel periodo principale resta materiale. Non scegliere soltanto la finestra favorevole.

La metrica diretta del ranking corrente non migliora nei due mercati. Dopo memoria/fusione il contributo cambia: la complementarità può avere valore ma va dimostrata rispetto a controlli abbinati. Con input sistemici ritardati di una seduta, il confronto principale IMMEDIATE peggiora entrambi secondo il report padre. Flussi ausiliari di rischio/V6 congelati: attribuzione condizionata, non ricostruzione completa del V6. Universi correlati, storia già riutilizzata, total-return/FX/distribuzioni/delistati non certificati, costi/spread e fill same-open legacy restano limiti.

## Prossima domanda autorizzata

Verificare se uno stato di mercato disponibile alla decisione spieghi e preveda il contributo incrementale di CUM_FIT, e se possa guidare la scelta/combinazione delle formule. Non interpretare la semplice variazione dei sei fit annuali come prova di dipendenza dai regimi.

Conservare come controlli ORIGINAL, CUM_FIXED e CUM_FIT; ogni nuovo passo su entrambi gli universi, criterio nativo prima del conto, nessun veto automatico se l'intervallo comprende zero. Una promozione richiede nuova evidenza, non questa registrazione.

## Stato della conservazione

Questa scheda è un file Git tracciato. I binari parent rimangono negli archivi OLC14 già documentati in Library; non vengono dichiarati caricati nelle release GitHub da questa registrazione. Nessun nuovo modello o portafoglio è stato eseguito in questa fase.
