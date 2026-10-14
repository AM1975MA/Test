# Opportunity su LINEAR annuale: risultato verificato

Decisione: non adottare il router; mantenere LINEAR annuale come riferimento. Il cap ha un impatto trascurabile e non risolve 2021/2023. Nessuna promozione in produzione.

Periodo comune 2017-02-01–2026-07-01,2366osservazioni e113periodi completi su114segnali disponibili. Tre download Original149 congelati. Nessun nuovo fit Compact/Tail/Macro/MA3. I fit nuovi riguardano solo Opportunity.

| Variante | CAGR r1 | CAGR r2 | CAGR r3 | CAGR medio | MaxDD medio | Sharpe medio | Range CAGR pp | SD CAGR pp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LINEAR annuale | 29.664649% | 32.866464% | 32.421180% | 31.650764% | -28.452546% | 1.083741 | 3.201815 | 1.416112 |
| + Opportunity cap | 29.664649% | 32.866464% | 32.423181% | 31.651432% | -28.452546% | 1.083762 | 3.201815 | 1.416475 |
| + Router causale | 30.098218% | 33.020224% | 30.588865% | 31.235769% | -27.983363% | 1.072561 | 2.922006 | 1.277600 |

## Anni richiesti

| Anno | LINEAR medio | Cap medio | Router medio | Router r1/r2/r3 |
|---|---:|---:|---:|---|
| 2021 | 1.837272% | 1.837272% | 1.837272% | 7.015447% / -4.859707% / 3.356075% |
| 2023 | 5.476594% | 5.476594% | 0.676948% | 4.532220% / 5.855978% / -8.357352% |

Il router perde 0.414996 punti di CAGR medio, pur migliorando il MaxDD medio di 0.469183 punti. Fallisce il gate preregistrato sul CAGR medio e sulla conservazione del95% del CAGR in ciascun download: il terzo passa da32.421180% a30.588865%. La riduzione del range CAGR totale da3.201815 a2.922006 punti non compensa questi esiti. Il2023 peggiora da5.476594% a0.676948% medio; il2021 resta invariato.

Nel terzo download, il divario logaritmico2023 (-0.169032) si concentra interamente a novembre: il router aumenta il peso su PALL al100% per21giorni, contro il controllo PALL/ARGT. Il risultato2023 passa da+8.519394% a-8.357352%. Questa e una differenza del replay controllato, non una prova di validita futura del modello. Il fatto che r1/r2 migliorino il CAGR totale mentre r3 peggiora e una fragilita da rendere visibile.

Il cap non vincola mai r1/r2 e vincola solo19/2366giorni (0.8030%) in r3. Aumenta il CAGR medio di soli0.000667 punti percentuali, senza modificare il MaxDD. Passa formalmente il filtro numerico preregistrato (compreso miglioramento>1e-10), ma il vantaggio e economicamente trascurabile e non giustifica una promozione. Nessuna soglia e stata cambiata per forzarlo ad agire.

Il DIRECT sempre applicato e soltanto diagnostico, non un candidato aggiuntivo scelto dopo il risultato: CAGR medio31.118157%, inferiore al controllo. Tutti i risultati sono conservati in METRICS.csv e ANNUAL_RETURNS.csv.

## Definizioni e correzioni causali

Cap: funzione Stage19 originale sullo score finale Top1, G2=min(g,opportunity_cap(score)); nessun fit. Router: modelli e miscela Opportunity storici, modifica del peso Top1 dopo confidence, senza cambiare ticker o V6. Escluse esplicitamente due feature derivate da target futuri; shadow ammesso soltanto con exit<=signal e almeno12periodi maturi. Quindi e un router storico corretto e integrato nel motore canonico V2, non una replica byte-identica del vecchio simulatore o del diverso selettore excess-max. Vedere PREREGISTRATION.md.

Top1/Top2 restano uguali per costruzione: disaccordo finale tra download20.752325% Top1 e52.874049% Top2ordinato, identico al controllo. Il test modifica pesi/esposizione, non le selezioni. Le tre revisioni sono correlate, non tre campioni indipendenti. Periodo gia esaminato: nessun risultato costituisce validazione futura indipendente.

## Verifica

[Run38623113443 SUCCESS](https://github.com/AM1975MA/Test/actions/runs/38623113443), commit39e37743c6df316fc6defe4f8f24da5667d0ce83. Tre replay e summary SUCCESS. Cinque test causali PASS su ciascun job. Prima dei nuovi fit, equity/turnover del controllo ricostruiti contro gli archivi verificati entro1e-12. Verifica locale ulteriore: esatta parita E/T con gli archivi originali in tutti i tre download. Input originali e pannelloMA3 autentico controllati tramite hash.

Prefix raw2022-12-30: feature causali e cluster uguali esattamente sulle date comuni;120feature non-forward, esclusioni salvate. TrainingOpportunity strettamente maturo; le decisioni shadow sono state ricalcolate indipendentemente dagli exit timestamp, tutte conformi. Metriche dei12percorsi ricalcolate localmente: errore massimo6.661338147750939e-16 rispetto aCI. Hash ZIP dei tre artefatti verificati prima dell estrazione. Nessun fit durante la verifica locale.

Primo avvio38622838644 fermo prima dei fit per dipendenzaMatplotlib mancante; risolto nel runtime senza cambiare modello, input o soglie. Nessun risultato del primo avvio viene usato.

Evidenza: SUMMARY.json, METRICS.csv, ANNUAL_RETURNS.csv, LOCAL_CHECK.json e ARTIFACTS.json; archivi completi (PATH,decisioni,previsioni,audit) nel run Actions. Tutto esclusivamente AM1975MA/Test; repository produttivo intatto.
