# ETF Trader V5 gerarchica — rapporto dei test EU165

Data: 31 ottobre 2026. **Ricerca storica esplorativa, non sistema pronto per trading reale.**

## Tesi sperimentale

Predire separatamente il ritorno fattoriale e il residuo specifico di ogni ETF a 21/42/63 sedute. Verificare mediante ablazione se le previsioni *native* V2/V3 aggiungono capacità economica rispetto agli stessi modelli senza quelle feature. I cinque ranker originari sono input numerici e non semplici pesi di voto. Ogni anno il fit utilizza esclusivamente target giunti a maturazione prima del cutoff del 1 gennaio.

Universe: **EU165**, cioè ETF UCITS quotati in Europa, alcuni con azioni USA/globali. Storico 2019–2026, 159 ETF con dati sufficienti per le feature, 9.706 coppie ETF×mese. Quattro proxy fattoriali: EXSA (Europa), SXR8−EXSA (USA relativo), EXX1−EXSA (banche relative), LYQ2 (titoli di Stato euro). Stima di beta rolling causalmente su 126 sedute.

## Risultati dei portafogli — febbraio 2021/dicembre 2024

Portafogli Top5 persistenti, ribilanciamento mensile, esecuzione sul successivo Open disponibile, 0,10% commissione su ogni lato negoziato, esposizione dimezzata se EXSA sotto MA200, liquidità a tasso 0%.

| Politica | CAGR | MaxDD | Turnover lordo annuo |
|---|---:|---:|---:|
| V3 Pair25/Hybrid24 + MA200 | 15,67% | -16,51% | 13,24× |
| V5 fattori soltanto | 20,99% | -23,02% | 7,24× |
| V5 fattori + storico, LightGBM, senza V2/V3 | **22,06%** | -20,82% | 7,49× |
| V5 fattori + score V2/V3, LightGBM | **22,03%** | -20,73% | 6,99× |
| V5 fattori + V2/V3, Ridge | 15,04% | -21,95% | 5,79× |
| V5 LightGBM multi-orizzonte | 17,62% | -19,04% | 6,50× |
| V5 multi-orizzonte + buffer | 17,00% | -17,89% | 5,54× |
| V5 multi-orizzonte + buffer + inverse-vol | 16,39% | -16,57% | 6,53× |

Il modello con feature V2/V3 non migliora il modello **identico** senza di esse: differenza logaritmica annualizzata -0,032 punti percentuali, 95% bootstrap a blocchi di sei mesi [-0,764,+0,698]. Top5 comuni 91,7%. La differenza del modello V5 completo rispetto al V3 protetto è +5,45pp con 95% CI [-2,49,+13,50]: zero incluso.

## Instabilità per regime
- 2021–2022: V5 LightGBM V2/V3 CAGR **+1,44%**, contro V3 **+6,50%**.
- 2023–2024: V5 **+43,96%**, contro V3 **+24,11%**.
- 2025, ampiamente analizzato in precedenza: V5 **+20,02%**, contro V3 **+36,24%**.
- Aumentando i costi dallo 0,10% allo 0,30% per lato V5 LightGBM passa da 22,03% a **20,40%** di CAGR (2021–2024).

## Forecast skill fuori campione

Per il modello V5 LightGBM con score V2/V3, correlazione cross-sectional mensile dei rendimenti futuri:
- 21d IC **+0,0158**, alpha residuo IC **−0,0133**.
- 42d IC **−0,0255**, alpha residuo IC **−0,0064**.
- 63d IC **−0,0152**, alpha residuo IC **−0,0012**.

Intervalli calibrati in modo cronologico sui soli errori di forecast precedenti, periodo 2023–2024: nominale 80% → copertura reale circa **89,9%, 86,3%, 88,0%** a 21/42/63d, eccessivamente conservativa. Probabilità di battere EXSA dopo 20 bps, 21d Brier **0,2489**, contro **0,2486** per la frequenza storica; AUC intorno a 0,516, insufficiente per HOLD/SWITCH indipendente.

## Gate di validazione e decisione

- Replay dei tre benchmark nativi V3 esattamente coincidente entro 6,7e−16 sui 1.539 giorni confrontabili.
- Le etichette di training sono tutte mature alla data del fit annuale.
- Non chiamare "alpha V2/V3" il CAGR 22%: l'ablazione lo smentisce.
- Non promuovere V5 come modello operativo: ETF superstiti selezionati retrospettivamente nel 2026, dividendi/total return e spread non certificati, storici riutilizzati per molti esperimenti, nessun holdout vergine.
- Il motore è la prima V5 fattoriale con allocazione Top5; **non** è ancora l'ottimizzatore distribuzionale multi-periodo HOLD/SWITCH originariamente proposto.

Codice sorgente V5 e scorecard storiche nel ramo di ricerca; input e output completi nell'archivio ZIP congelato indicato in MANIFEST.json.
