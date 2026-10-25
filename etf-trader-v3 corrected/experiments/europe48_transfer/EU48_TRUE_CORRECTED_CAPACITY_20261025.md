# ETF Trader V3 Corrected — EU48 15/31/63/127 foglie con kernel VERAMENTE corretto (25 ottobre 2026)

**Esito: sei training annuali PASS, replay economico PASS, tutti i controlli legacy PASS.** I risultati sono riferiti esclusivamente alla capacità del primo stadio del ranker, **non** alla V3 full-stack e **senza** decision tree, risk overlay, Stage19 o ricalibrazione sui 65 mesi già studiati.

## Perché era necessario ripetere i test

I primi report EU48 chiamati V3 127 foglie impiegavano il **kernel di feature legacy V2**. Il test di integrità originale [40112742559](https://github.com/AM1975MA/Test/actions/runs/40112742559) rilevava differenze in 9 feature downside, 11.236 celle numericamente modificate e 16.724 differenze di missingness rispetto al reale `etf_trader_v3.source_only.kernel`. Quindi i risultati del vecchio modello lossguide 15/31/63/127 foglie non erano trasferibili al vero V3 corrected.

Questa verifica ripete indipendentemente la stessa ricostruzione OHLCV e feature, stesso riferimento SPY osservabile prima dell'apertura EUR, 48 ISIN europei distinti, 125 feature, 3 seed (101,202,303), 360 boosting round e fitting annuale con etichette 21D già maturate 2017+, stessi 65 segnali mensili gennaio 2021–maggio 2026. I prezzi di acquisto/vendita sono Open EUR successivi, 1.374 sessioni 2021-02-01..2026-07-01, fee 10 bps one-way sul nozionale scambiato, portafoglio **unrestricted da 48 fondi**, e allocazioni Top1, Top2 e Top5 equal-weight per le politiche con più nomi.

## Prove reali

- [Fit annuali sei anni](https://github.com/AM1975MA/Test/actions/runs/40189199418) — sei job PASS 2021–2026; hanno ricalcolato i punteggi con **il vero kernel corrected**, per `max_leaves=15,31,63,127` e i due controlli legacy V2 depth4/127.
- [Replay economico completo](https://github.com/AM1975MA/Test/actions/runs/40189614773) — PASS, 65 mesi e controllo indipendente originale V2 **CAGR Top1 4,727914934% entro 1e-10**. Previsioni dell'originale depth4 replicato entro 1.5e-8 per approssimazione floating point e identici ETF Top1 per ogni mese. Il replay originale legacy deep 127 replica il modello precedentemente archiviato.
- [Fonte di confronto kernel](https://github.com/AM1975MA/Test/actions/runs/40112742559) — 9 feature downside differenti; nessuna modifica alle quotazioni/label originali.

## EUR48 65-mesi: risultati economici netti, senza meta tree

| Primo stadio | CAGR Top1 | CAGR Top2 equal 50/50 | CAGR Top5 equal | MaxDD Top1 | MaxDD Top2 |
|---|---:|---:|---:|---:|---:|
| V2 originale, depth4, feature legacy | **+4.7279%** | +3.7339% | +4.9605% | **−25.8932%** | **−25.0465%** |
| V3 127, feature legacy (vecchio report) | −0.2257% | +3.6116% | +4.7139% | −41.1836% | −30.6400% |
| **V3 corretto, leaf15** | +1.3963% | +4.4597% | +6.9490% | −35.6051% | −30.1202% |
| **V3 corretto, leaf31** | **+8.3941%** | **+6.2693%** | **+7.1878%** | −34.6065% | −32.3849% |
| V3 corretto, leaf63 | +4.9985% | +3.6747% | +2.4897% | −30.5161% | −35.2967% |
| V3 corretto, leaf127 | +3.8462% | +0.8164% | +2.3987% | −33.5516% | −35.4905% |

**Differenza determinante:** V3 corretto 31 foglie vs 127 corretto **+4.5479 punti CAGR Top1** e **+5.4529 punti Top2**. V3 corretto 31 vs V2 depth4 **+3.6662 punti CAGR Top1**, **+2.5354 punti Top2**; tuttavia **MaxDD Top1 peggiore di 8.71 pp** e Top2 di 7.34 pp rispetto al V2.

Gli stessi limiti di rischio non sono quindi risolti, e **non** va confuso questo confronto isolato con la precedente V2 full-stack Stage19 (CAGR −0,15% e gestione del rischio differente).

## Competenza intrinseca del ranker 21 giorni, senza sfruttare il CAGR per il fitting

| Ranker | Top1 vero vincitore su 48 | Top3 coverage | Selected excess 21D medio vs 48 fondi | Spearman medio |
|---|---:|---:|---:|---:|
| V2 legacy depth4 | 2/65 (3.08%) | 5/65 (7.69%) | +0.2008% | +0.0251 |
| V3 corrected leaf15 | 1/65 (1.54%) | 5/65 (7.69%) | −0.0856% | +0.0283 |
| V3 corrected leaf31 | 2/65 (3.08%) | 5/65 (7.69%) | +0.3468% | +0.0307 |
| V3 corrected leaf63 | 2/65 (3.08%) | 8/65 (12.31%) | +0.1690% | +0.0162 |
| V3 corrected leaf127 | 1/65 (1.54%) | 4/65 (6.15%) | +0.0470% | +0.0153 |

Questi sono soltanto **65 mesi**, e un vincitore assoluto scelto a caso fra 48 ha probabilità 2,08%: l'apparente capacità Top1 non è probante. La media forward degli ETF scelti rispetto all'universo è piccola; il CAGR emerge dalla sequenza delle scelte e dai prezzi economici, non da una precisione sostanziale nell'individuare il miglior ETF.

## Dipendenza temporale: CAGR NON sufficiente

Rendimenti semplici Top1 delle singole finestre annuali (2021 da febbraio, 2026 fino a luglio), già netti del 10bp sul nozionale:

| Anno | V2 depth4 | V3 corrected leaf31 | V3 corrected leaf127 |
|---|---:|---:|---:|
| 2021 | +4.82% | −6.50% | +8.40% |
| 2022 | +5.84% | +3.32% | −15.61% |
| 2023 | +3.58% | +27.65% | +21.73% |
| 2024 | +1.83% | +13.63% | +0.02% |
| 2025 | −2.97% | +4.68% | −1.92% |
| 2026, parziale | +13.07% | +5.44% | +12.28% |

Il leaf31 supera il leaf127 nel 2022, 2023, 2024 e 2025, ma peggiora nel 2021 e nel 2026 parziale. Non è automaticamente robusto verso regimi nuovi. Ogni confronto su questo calendario è stato esposto a **test multipli e ripetizioni di esperimenti**, e l'universo di 48 ETF esistenti nel 2026 presenta possibile survivorship bias.

Bootstrap esplorativo dei 65 differenziali mensili **net log growth** Top1, ricampionamento circular block da 6 mesi e 5000 repliche:
- corrected 31 vs corrected 127: **+0.357 pp log/mese**, intervallo 95% **[−0.510, +1.146] pp**;
- corrected 31 vs V2 depth4: **+0.286 pp log/mese**, intervallo **[−0.632,+1.159] pp**;
- corrected 31 vs corrected 127 Top2: **+0.438 pp log/mese**, intervallo **[−0.141,+1.012] pp**.
**Tutti questi intervalli includono zero**; senza correzione per multi-test e con storico riutilizzato, non è giustificato promuovere leaf31 a standard V3 su EUR48.

## Conclusione

1. Il problema storico del vecchio EU48 V3 127 era **amplificato da due errori di trasferimento**: prima utilizzo del feature kernel legacy, poi eccessiva capacità del ranker rispetto al dominio più stretto.
2. Su questo set storico **leaf31 + vero kernel corrected** è il candidato più interessante in termini di rendimento e Top2/Top5, ma non presenta evidenza statistica adeguata e **il MaxDD deteriora rispetto al vecchio V2**.
3. Il controllo del rischio e la regola di portafoglio non sono stati modificati in questo test; l'algoritmo Top2 equal-weight è **diverso** dalla precedente proposta V3 condizionale 75/25 con soglia percentile matematicamente impossibile (gap fra #1 e #2 sempre 1/48). Non usare quel confronto per attribuire benefici alla selezione.
4. **Non ritarare** foglie o decision tree dopo il risultato. Preservare V2 e V3 operativi. Prossima ricerca: confronto proprio sul rischio con identica politica EUR sia V2 sia V3, e ulteriore holdout ISIN storico vero, oppure test prospective lock con prezzi successivi, prima di autorizzare una sostituzione.

**Stato:** esperimento di primo stadio, kernel corretto effettivamente verificato, risultati/curve riproducibili; nessun aggiornamento di produzione.
