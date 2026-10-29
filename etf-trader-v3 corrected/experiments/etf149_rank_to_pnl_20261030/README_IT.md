# ETF149 — Ranking, persistenza del segnale e PnL (30 ottobre 2026)

**Stato:** audit retrospettivo di segnali congelati. Nessuna nuova performance prospettica e nessuna ottimizzazione dei modelli.

## Ipotesi
Un modello può ordinare bene i 149 ETF ma trasformare male il ranking in rendimento del portafoglio. Separiamo qualità del ranking (Spearman), qualità della scelta delle prime posizioni (Top K), risultato economico lordo rispetto a SPY e durata del segnale.

## Protocollo
- Universo: 149 ETF USA definiti ex post, con **survivorship bias** non corretto.
- Segnali originali V2 a 255 foglie e Ridge senza Kalman, senza nuova ottimizzazione.
- Esecuzione all'apertura del mese successivo al segnale, chiusura all'apertura del mese ancora successivo: prezzi Open aggiustati.
- V2 Top10: 102 mesi di origine, gennaio 2018–giugno 2026. Ridge Top15: 44 mesi, gennaio 2023–agosto 2026. **42 mesi comuni**, gennaio 2023–giugno 2026.
- Spearman fra score e rendimenti di tutti i 149 ETF e media dello Spearman entro le sei categorie; rendimento TopK meno SPY, universo equiponderato e medie delle rispettive categorie.
- Orizzonti: 1, 3, 5, 10, 15, 20 sedute, SOLO se disponibili entro il mese. A 20 sedute il campione è più piccolo.
- Bootstrap temporale circolare, blocchi di 6 mesi, 5.000 estrazioni; intervalli NON corretti per tutti gli esperimenti storici precedenti, perciò **esplorativi**.
- Confronto lordo del segnale, non CAGR investibile. Costi, spread, turnover, imposte fuori da questo audit; già trattati nel simulatore economico.

## Risultati: 42 mesi identici
| Misura | V2 Top10 | Ridge Top15 | Delta Ridge – V2 |
|---|---:|---:|---:|
| IC Spearman medio | +0,04264 | +0,12203 | **+0,07939**; CI 95% [+0,0108; +0,1422] |
| TopK – SPY, medio mensile lordo | +0,7555 pp | +0,7263 pp | **−0,0291 pp**; CI [−1,06; +1,03] |
| TopK – categoria media selezionata | — | — | circa −0,01 pp; CI [−0,80; +0,81] |

**Risultato:** Ridge ordina meglio l'universo ma non produce un rendimento di portafoglio superiore. Numero di posizioni diverso (10 contro 15), quindi il confronto NON isola esclusivamente il modello.

## Campione completo, periodi differenti
| Indicatore | V2, 102 mesi | Ridge, 44 mesi |
|---|---:|---:|
| Spearman complessivo | +0,0481 | +0,1319 |
| Spearman medio entro categoria | −0,0150 | +0,1152 |
| TopK – SPY lordo / mese | +0,45 pp | +0,83 pp |
| TopK – universo lordo / mese | +0,90 pp | +1,42 pp |
| TopK – medie categorie selezionate / mese | +0,69 pp | +1,39 pp |
| Frazione di mesi con TopK sopra SPY | 52,9% | 54,5% |

**Quintili:** Ridge dal peggiore al migliore quintile +0,24% → +2,08% di rendimento medio al mese, residuo di categoria −0,43 → +0,93 pp. V2 +0,46% → +1,10%, residuo −0,08 → +0,15 pp.

**Persistenza TopK – SPY:** V2 5/10/15 sedute +0,11/+0,44/+0,37 pp; Ridge +0,20/+0,49/+0,76 pp. Non giustifica modifiche al calendario. Le correlazioni contemporanee mensili fra IC e vantaggio lordo TopK sono +0,288 V2 e +0,497 Ridge; non costituiscono un segnale utilizzabile prima della realizzazione del rendimento.

## Verifica e limiti
- Riproduzione dei rendimenti lordi del simulatore storico: errore massimo assoluto V2 **2,98×10⁻¹⁶**, Ridge **2,08×10⁻¹⁶**.
- Ricerca ripetuta sulle stesse date: NON è nuova conferma indipendente.
- ETF cessati non inclusi, quindi rimane survivorship bias.
- Top10/Top15 e allocazioni diverse, rischio e costi non uniformati in questa diagnostica.

## Input: SHA-256 dei file usati
| File locale | SHA-256 |
|---|---|
| etf149_forward_20261023.zip | 29d63efc647f113d6fb1aa9ade57983a711e78bb3b375d556fdcb340504f2be2 |
| v2_deep_leaf_complete_results.zip | c81ffc723572c6218638f925e1d696896876067fc2f6a10d15312325d17a70ee |
| ETF149_Predictive_Research_2020_2026.zip | 1bfd21d20ebb3377cd6c90d4ae1f7586257ea9abeeded12d741b589f49b82373 |
| strategy_target_weights.npz | 13c66a452bb5e9c75c5704a83bac551970b39d37ec2ec4eb8f9d88335d25b616 |

La fonte dell'archivio prezzi è già presente nel repository, sotto la cartella etf-trader-v3 corrected/experiments/l00_rank_reg_fusion/results/forward_20261024/archives/. L'archivio V2 è disponibile nell'artifact Actions v2-deep-leaf-complete-results del run 39482809691. Gli altri input sono quelli congelati dagli esperimenti precedenti.

## Riproduzione e output
Sistemare i quattro input congelati nella directory locale con i pesi in ETF149_Investment_System_Research/strategy_target_weights.npz. Impostare la variabile di ambiente ETF149_DATA_ROOT a tale directory, poi eseguire:

    python run_rank_to_pnl.py

Dipendenze: numpy, pandas, scipy. Il programma non usa API di mercato e scrive le tabelle mensili, i quintili, la persistenza per orizzonte, i bootstrap e il manifest.

**Decisione:** mantenere congelati i modelli e misurare la conversione da ranking a PnL su date nuove realmente prospettiche, con stesso numero di posizioni, date, limiti, costi e rischio. Evitare di scegliere a posteriori k o il giorno di vendita.
