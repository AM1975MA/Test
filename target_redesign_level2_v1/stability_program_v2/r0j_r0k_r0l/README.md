# R0-J → R0-L: dati reali, obiettivo ranker e loss selettiva

**Decisione:** percorribilità *tecnica* di una loss pairwise che evita confronti di rendimento ambiguo, **NON** miglioramento CAGR/stabilità verificato su ETF veri.

- [Rapporto di chiusura con risultati e limiti](../../../docs/superpowers/reviews/2026-10-09-r0j-r0k-r0l-completion.md)
- [Programma Data + Superpowers aggiornato](../../../docs/superpowers/plans/2026-10-08-data-led-v2-stability-roadmap.md)
- [Statistiche di mercato, 267 date / 2.333.613 coppie](real_market_pair_statistics.json)
- [Sintesi del test sintetico R0-K e incompletezza dichiarata](r0k_synthetic_checkpoint.json)
- [Prototipo loss R0-L](cost_pairwise.py) e [test unitari](test_cost_pairwise.py)

## Che cosa è risultato

Le sole **8 inversioni di ordinamento** del target Compact21 fra i due snapshot Yahoo sono relative a coppie con differenza massima **0,0116 bp**, nessuna nel decile superiore. Mascherando differenze inferiori a **20 bp** (ipotesi derivata dalla somma di 0,1%+0,1% dei costi previsti per una compravendita), il **3,79%** delle coppie teoriche viene scartato; tra le coppie ammesse da una delle due vintage non vi è inversione di segno, ma **14 ammissibilità cambiano**. Non equivale a una prova che la banda sia ottimale o che il guadagno netto aumenti, né alla percentuale di coppie effettivamente campionate da XGBoost.

R0-K `rank:ndcg` non ha superato il gate congiunto nel mondo A (migliore stabilità, peggior cattura del vincitore); nel mondo B la parte `rank:pairwise` era già stata addestrata ma le predizioni non salvate. Non si ripetono i nove fit per riempire artificialmente il report.

## Esecuzione dei test su codice del repository

Ambiente usato: XGBoost 3.1.3, NumPy 2.3.5, pytest 9.0.2. Da questa directory:

```bash
python -m pytest -q test_cost_pairwise.py
```

La suite ha **otto prove**, inclusi gradiente contro differenze finite, maschera, gruppi, caso senza coppie e addestramento sintetico con `QuantileDMatrix`. I risultati locali sono PASS; **nessun CI remoto o backtest finanziario certificato**.

L'archivio di ricerca `ETF_Trader_V2_R0J_R0K_R0L_Completato_20261009.zip` include anche script completi per R0-J/K, supporto delle fixture precedenti e report (24 file, ZIP SHA256 `ab28c8a7009cbede1c5d02fdcd052886fc54625cc283e5c46ff1b44c134ef1ef`). I file Yahoo OHLCV originali (75 MB) sono un input *separato*, già congelato, non distribuito in questo piccolo archivio.

## Blocco prima della V2 reale

Il modulo `cost_pairwise.py` non applica da solo l'obbligo `exit_date_21 < annual_fit_cutoff`, e usa Hessiana **diagonale approssimata** / tutte le coppie ammesse anziché campionamento/normalizzazione native di `rank:pairwise`. Occorre progettare un worker shadow con controllo di causalità, esatto allineamento gruppi, memoria/tempo e comportamento X-only/Y-only, e poi fissare una banda basata su incertezza *indipendente* dalle performance 2017–2026.

**Nessuna modifica al motore V2, al rischio, agli stop, agli ETF di produzione o al codice dei repository `Etf_trader` e `Trader_selector`.**
