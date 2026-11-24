# Perseo U25–U27 — rotazioni locali e stop individuali

24 novembre 2026. **U27 CORR70 è il candidato principale di ricerca.** Conserva U24 PROFIT_RAMP e rimuove il cooldown globale provocato da uno stop individuale quando i due ETF hanno correlazione giornaliera sotto 0,70. L'allarme sistemico può ancora ridurre entrambe le esposizioni. La regola è comune a Europa, USA e Trade Republic.

## Confronto a condizioni omogenee

Conti storici dal 2 gennaio 2020 al 1 luglio 2026, 10.000 iniziali, commissione di 1 unità per ordine più 15 punti base per lato. EUR per EU/TR e USD per USA. Prezzi congelati, quote frazionarie e drawdown alle aperture.

| Paniere | U20 CAGR / DD | U24 CAGR / DD | U27 CORR70 CAGR / DD | Δ CAGR vs U24 |
|---|---:|---:|---:|---:|
| Europa | 20,78% / −31,25% | 23,85% / −27,43% | 23,91% / −27,43% | +0,06 pp |
| USA | 40,23% / −26,81% | 39,99% / −26,60% | 42,75% / −26,59% | +2,75 pp |
| Trade Republic | 25,07% / −29,53% | 25,36% / −27,93% | 26,41% / −26,85% | +1,04 pp |

Su Trade Republic il CAGR 2020–2022 passa da −6,05% con U20 e −5,46% con U24 a **−3,02%**. Il drawdown del sottoperiodo passa da −27,93% a −26,61% rispetto a U24. Dal 2023 il CAGR TR cede circa 1,03 punti, da 59,81% a 58,78%. La perdita precedente al 2023 si riduce, con margine di miglioramento ancora ampio.

Ai costi standard CORR90 alza USA al 43,06%, mentre CORR80 con filtro di ampiezza del mercato alza Europa al 24,18%. CORR70 è preferita dopo aver osservato i risultati perché limita il drawdown TR e conserva il segno del vantaggio di CAGR su tutti i panieri negli stress. CORR80/CORR90 fanno salire il drawdown TR nel ritardo di una seduta da −26,66% a −29,95%.

## Stress di esecuzione

Δ CAGR rispetto a U24 simulata nelle stesse condizioni. I costi di stop sono slippage aggiuntivo applicato al prezzo simulato dello stop.

| Scenario | Europa | USA | Trade Republic |
|---|---:|---:|---:|
| 30 bp per lato | +0,12 pp | +3,29 pp | +1,33 pp |
| Ritardo di una seduta | +0,05 pp | +4,14 pp | +0,03 pp |
| 30 bp per lato e ritardo | +0,12 pp | +4,62 pp | +0,38 pp |
| 50 bp di slippage sugli stop | +0,06 pp | +2,45 pp | +0,94 pp |
| 30 bp per lato, ritardo e 100 bp sugli stop | +0,11 pp | +3,95 pp | +0,26 pp |

Nello stress più severo i CAGR assoluti di CORR70 diventano 12,85% EU, 28,50% USA e 19,22% TR. Il segno relativo resiste, mentre il margine europeo resta esiguo. Il drawdown USA peggiora di 0,04 punti a 30 bp per lato e di 0,12 punti nel caso con slippage sugli stop di 50 bp. Il ritardo differisce le decisioni e lascia attivo lo stop simulato.

## Perché i cambi di selezione U25 e U26 restano in ricerca

U25 FALLBACK_RETAIN usa un ETF del ciclo precedente quando manca un proxy, l'ETF proposto è debole e il precedente ha un trend relativo migliore. Su TR il CAGR sale al 26,96%, il periodo 2020–2022 migliora a −2,88% e il segno resiste ai costi e al ritardo. In Europa il CAGR scende al 20,48% e il drawdown peggiora a −29,22%. Sulla TR, febbraio 2021 e febbraio 2022 spiegano quasi tutto l'effetto. Escludendo descrittivamente quei due mesi, il vantaggio log annualizzato scende da +1,27 a +0,04 punti.

In U26 abbiamo provato a confrontare i due ETF dopo cinque sedute, a rientrare sulla proposta se recuperava e a tenere metà della quota sul titolo precedente. Queste varianti non hanno salvato il rendimento europeo. La nuova uscita in cash sulle perdite relative del solo fallback ha posto un costo su TR anche quando ha aiutato EU. I risultati completi e le date in cui cambiano i segnali sono nei CSV.

## Verifica e limiti

180 replay, inclusi i controlli e gli stress, ricostruiti dagli ordini. I 18 conti U20/U24 coincidono con i ledger salvati. Le nuove regole sono state verificate a tre cutoff per mercato con perturbazione dei prezzi futuri. Gli ordini restano simulati. Le serie USA non hanno la maschera di osservabilità delle altre due fonti. Restano i limiti U24 su cataloghi, prezzi, liquidità e stop intraday.

Il bootstrap appaiato a blocchi di 12 mesi preserva la dipendenza fra panieri. Per CORR70 gli intervalli simultanei 95% sul vantaggio log annualizzato sono da −0,26 a +0,36 pp in Europa, da −4,06 a +7,95 pp negli USA e da −2,19 a +3,85 pp su TR. Ogni intervallo include zero. Il metodo controlla la famiglia U25–U27 sul campione riusato. Per conferma prospettica servono serie prezzi e proposte maturate dopo il 1 luglio 2026 e un replay a regola congelata, partendo dalle posizioni già aperte.

## Riproduzione

Con il checkpoint completo ripristinato, eseguire da `research/perseo_20261124`. Le dipendenze sono quelle in `u24/requirements.txt`. I dettagli e le condizioni fissate prima dei replay sono nei protocolli delle tre campagne.

```sh
python u25/run25.py
python u26/run26.py
python u27/run27.py
python u27/analyze27.py
python u27/stress27.py
```

La sintesi di tutte le varianti rispetto a U24 è in [COMPARISON_U24.csv](results/COMPARISON_U24.csv), quella degli stress in [STRESS_SUMMARY.csv](results/STRESS_SUMMARY.csv) e i confronti annuali nei file `results/ANNUAL.csv` di ciascuna campagna.
