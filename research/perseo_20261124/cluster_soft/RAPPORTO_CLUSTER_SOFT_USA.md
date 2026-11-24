# Perseo — il contributo del cluster al ranker USA

24 novembre 2026. **Manteniamo il ranking originale di U27.** Il bonus dei cluster storici USA riduce il CAGR in tutte e otto le varianti con bonus e in ognuno dei quattro scenari di costi e ritardo. Il segnale che osservavamo sul rendimento medio del cluster non si è tradotto in migliori sostituzioni dei singoli ETF.

## Come è stato eseguito

Base U27 CORR70 con i 149 ticker USA. Lo score ticker è il flusso originale OLC104 `TOP2_CONTEXT_REVALUE_FUSION`. A peso cluster zero riproduce la stessa coppia ordinata di U27 in tutti i 57 mesi. Ai ranghi ticker si somma il rango centrato del cluster Ridge moltiplicato per il coefficiente prefissato. Tutti i 149 ticker risultano presenti su ogni data e restano eleggibili. I due ticker selezionati mantengono peso 50/50. Il trailing PROFIT_RAMP e l'isolamento degli stop CORR70 si ricalcolano sulle nuove coppie. Il flusso macro e le posizioni difensive V6 restano quelli congelati di U27 in ogni replay.

Finestra attiva dal 1º ottobre 2021 al 1º luglio 2026, apertura di valorizzazione finale. I conti partono dal 2 gennaio 2020 e hanno le stesse posizioni e lo stesso capitale prima della prima decisione modificabile. Dimensione iniziale USD 10.000, quote frazionarie, costo 1 USD per ordine più 15 bp per lato. Stress a 30 bp, un giorno di ritardo e combinazione. Si riportano separatamente i risultati della finestra attiva e quelli dell'intero conto.

## Risultati USA

Costi ordinari, capitale in continuità. Il CAGR attivo è confrontabile sulla stessa finestra tra tutte le regole. Il CAGR completo include anche il periodo iniziale identico a U27.

| Regola | Mesi con coppia diversa su 57 | CAGR attivo | Drawdown attivo | CAGR completo |
|---|---:|---:|---:|---:|
| U27 | 0 | 56,87% | −26,59% | 42,75% |
| Ridge 1% | 1 | 56,51% | −26,59% | 42,51% |
| Ridge 2% | 8 | 55,80% | −26,59% | 42,03% |
| Ridge 5% | 32 | 43,99% | −29,76% | 34,08% |
| Ridge 10% | 37 | 30,39% | −25,79% | 24,70% |
| Ridge 20% | 43 | 25,40% | −28,27% | 21,19% |
| Momentum cluster 10% | 35 | 44,87% | −16,37% | 34,68% |
| Ridge 10%, fit precedente alla correzione TR | 38 | 25,63% | −29,75% | 21,36% |
| Ridge 10%, score ticker originale scalato | 21 | 49,90% | −27,58% | 38,08% |

Il 10% primario cambia 50 posizioni in 37 rinnovi. Le nuove coppie rendono in media **−2,46 punti per mese modificato** prima di stop e costi, in 14 mesi meglio e in 23 peggio rispetto alle coppie originali. La quota di coppie con entrambi gli ETF nello stesso cluster sale dal 49,1% al 70,2%. A maggio 2024 il bonus sostituisce UNG e URA con IGV e FDN. Il conto passa dal +23,79% al −1,73% nel mese. A febbraio 2022 passa da +14,87% a −3,43%. A maggio 2026 da +16,13% a −1,29%. I contributi economici risultano dai replay netti; i rendimenti prima delle protezioni sono riportati separatamente in `CHOICES.csv`.

Il bonus Ridge dell'1% decide un'unica sostituzione, EWZ con KBE a novembre 2021, e perde circa un punto percentuale lordo sulla coppia di quel mese. Al 2%, tre sostituzioni migliorano il rendimento lordo e cinque lo riducono. Le prove con quasi-spareggio sono state aggiunte dopo aver visto le varianti principali. Il loro risultato non dà evidenza di un vantaggio a pesi piccoli.

Con ritardo e 30 bp per lato insieme, il CAGR attivo scende dal 46,79% di U27 al 24,65% del Ridge 10%, dal 46,79% al 46,30% con Ridge 1% e al 45,78% con Ridge 2%. Il momentum sui cluster migliora il drawdown nella finestra attiva, con −19,59% contro −26,59% nello stress combinato; cede 8,58 punti di CAGR nello stesso stress. È un compromesso storico tra rendimento e drawdown e appartiene a una regola diversa dal Ridge in esame.

## Confidenza e audit

Sul confronto Ridge 10% meno U27 il differenziale log annualizzato è −18,48 punti, intervallo simultaneo a blocchi di sei mesi da −44,75 a +7,80. Anche escludendo descrittivamente i due mesi con il maggior effetto assoluto resta a −10,32 punti. Nessun vantaggio di CAGR osservato in 32 confronti correlati. Il campione è di 57 mesi e le varianti condividono dati e molte posizioni. Gli intervalli non autorizzano inferenze generali su regole mai provate o su dati futuri.

36 conti ricostruiti indipendentemente dagli ordini. Verificati i 57 Top2 nativi, CAGR/drawdown/ordini delle tre configurazioni U27 pubblicate, i prefissi prima dell'attivazione e l'invarianza delle scelte a tre date di taglio degli input. Le appartenenze dei cluster e le etichette incorporate nei fit precedono ciascuna decisione. Restano limitazioni nei prezzi rettificati, nella maschera di osservabilità USA e negli stop sintetici U27.

Il test risponde alla domanda operativa sul secondo stadio. Un segnale utile a ordinare i rendimenti medi dei cluster può offrire un confronto diverso da quello utile a decidere tra due ETF già ai primi posti del ranking. In questo campione il bonus, anche molto basso, non migliora la scelta. U27 mantiene il ranking originale.

## Replay

Con lo ZIP completo estratto, usare Python 3.12 con numpy 2.3.5, pandas 2.2.3 e le dipendenze minime di U24. Da `cluster_soft`:

```sh
python run_soft.py
python analyze_soft.py
```

`prepare.py` rigenera gli input congelati dagli archivi OLC104 e OLC07 e dai due risultati della prova cluster precedente, elencati con SHA-256 in `inputs/SOURCE_HASHES.json`. `SUMMARY.csv`, `COMPARISON.csv`, `ANNUAL.csv`, `CHOICES.csv` e `BOOTSTRAP.csv` documentano i risultati. Lo ZIP conserva anche il ledger, gli ordini e gli stop dei 36 conti.
