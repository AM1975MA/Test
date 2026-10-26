# ETF Trader V3 EU148 — audit liquidità e fattori, 26 ottobre 2026

**STATO: ricerca, NON pronto alla produzione.** Test realmente eseguito sui 101 segnali 2018-01–2026-05 (2076 NAV giornalieri fino a 2026-07-01), senza modificare o rifittare il ranker V3 a 127 foglie. L'originale FULL +3,9082151397% CAGR e l'EQUITY +10,9629154421% sono stati riprodotti con precisione assoluta inferiore a 1e-10. Questo OOS è stato già esaminato nei precedenti test: NON è un holdout indipendente.

## Provenienza e codice

- Originale paired V3 USA–EU: [PAIRED_US149_EU148_RESULTS_20261025.md](PAIRED_US149_EU148_RESULTS_20261025.md)
- Originale controllo categorie/beta: [CATEGORY_GATE_RISK_MATCHED_RESULTS_20261025.md](CATEGORY_GATE_RISK_MATCHED_RESULTS_20261025.md)
- Replay core indipendente committato in GitHub: [liquidity_factor_replay_20261026.py](liquidity_factor_replay_20261026.py) e [.github/workflows/v3-eu148-liquidity-factors-replay.yml](../../../.github/workflows/v3-eu148-liquidity-factors-replay.yml). **GitHub Actions run PASS**: https://github.com/AM1975MA/Test/actions/runs/40287122251 ; l'artefatto contiene i CSV di decisioni, NAV, benchmark EXSA con stesso cash, regressioni HAC e manifest. Riproduce tutti i 13 CAGR della tabella con gli stessi dati originali. Bundle di conversazione v3_category_liquidity_factor_20261026_REPRODUCIBLE.zip: sorgenti Python estesi, stress AUM, CSV, hash SHA256 e README.
- Prezzi derivati 148 Xetra verificati e dati del matched V3 127 frozen 2026-10-25, non ricalibrati; zero uso di futuri nella logica dei gate.

## 1. Liquidità ex ante: 63 sessioni, tre soglie

Alla chiusura del giorno del segnale: quote realmente disponibili, almeno il 90% delle ultime 63 sedute con Volume vendor positivo e mediana del controvalore giornaliero Close×Volume non inferiore a 50.000 / 250.000 / 1.000.000 EUR, contando il volume nullo come zero. L'ETF scelto che non supera il gate viene **sostituito con cash EUR a rendimento zero**, mai con un sostituto scelto ex post. L'esecuzione è modellata al successivo Open con costi 10bps per lato, NAV giornalieri comuni reali.

| Top5, CAGR EUR netto | Nessun filtro | ADV≥50k | ADV≥250k | ADV≥1m |
|---|---:|---:|---:|---:|
| FULL | +3,91% | +6,73% | +5,23% | +2,70% |
| EQUITY | +10,96% | +11,51% | +8,92% | +4,45% |
| REL_MOM_GATE | +9,58% | +10,88% | +8,14% | +4,32% |

Su 505 selezioni Top5 FULL, respinte 121 (50k), **249 (250k)** e 393 (1m). La strategia FULL gate 250k resta in **cash medio 49,3%** del capitale; EQUITY con gate 250k cash **44,75%**, REL_MOM_GATE gate 250k cash **45,35%**. Il minor MaxDD è almeno in parte dovuto alla ridotta esposizione investita: non confondere abbattimento del rischio con maggiore capacità predittiva.

La metrica ADV è esclusivamente una stima di volume riportato dal provider, NON book profondo, spread bid-ask o volume negoziato consolidato; la policy di backtest presume erroneamente che le vecchie posizioni possano sempre essere vendute, anche quando non più liquide. Test di veto esplorativo, NON certificazione di negoziabilità.

## 2. Benchmark con identica esposizione in EXSA e cash

EXSA comprato/venduto alle stesse date/Open e 10bps per lato, con peso mensile del capitale investito uguale a quello della rispettiva politica V3 e il resto in cash senza rendimento.

| Politica | CAGR V3 | CAGR EXSA con stesso cash | Differenza |
|---|---:|---:|---:|
| FULL no gate | +3,91% | +8,86% | -4,95 pp |
| FULL ADV250k | +5,23% | +3,77% | +1,47 pp |
| EQUITY no gate | +10,96% | +8,86% | +2,11 pp |
| EQUITY ADV250k | +8,92% | +4,67% | +4,25 pp |
| REL_MOM_GATE no gate | +9,58% | +8,86% | +0,73 pp |
| REL_MOM_GATE ADV250k | +8,14% | +4,42% | +3,72 pp |

La media annualizzata del differenziale giornaliero netto, stimata con HAC Newey-West lag21 contro EXSA con cash abbinato, per EQUITY ADV250k è +4,49 punti, **IC95% [-0,99; +9,98], p=0,108**; per REL_MOM_GATE ADV250k +4,00 punti, **IC95% [-1,45; +9,44], p=0,150**. Nessuno dei due è significativo al 5% neppure prima della correzione per multiple testing.

## 3. Stress impatto ordini per conto di 100mila e 1milione EUR

Modello di costo ***ipotetico non calibrato*** aggiuntivo per lato, titoli individuali e valore ordine EUR: minimo fra 200bps e 20bps moltiplicati per radice quadrata della frazione valore ordine / ADV mediano delle 63 sessioni precedente il segnale. Si somma una commissione di 10bps per lato. Patrimonio iniziale variabile; non usare questi rendimenti come aspettativa di esecuzione reale.

| CAGR con modello di impact | 100mila EUR | 1milione EUR |
|---|---:|---:|
| FULL | +1,50% | -1,67% |
| EQUITY | +8,24% | +4,93% |
| REL_MOM_GATE | +6,87% | +3,53% |
| EQUITY ADV250k | +8,60% | +7,92% |
| REL_MOM_GATE ADV250k | +7,82% | +7,14% |

Questi risultati sono molto sensibili alla qualità del Volume vendor; per strumenti con volume storico prossimo a zero il modello satura il limite di 200bps. Non provano costi reali e non includono profondità/partial fill/market impact broker verificati.

## 4. Regressioni fattoriali ex post sui NAV, HAC(21)

Tre fattori giornalieri Open-to-Open: EXSA Europa azionario, media equiponderata ETF EU_PROPERTY e media equiponderata ETF SOVEREIGN_EUR; regressione OLS con SE Newey-West 21 lag su 2075 rendimenti giornalieri. Sono proxy fattoriali retrospettivi calcolati su coorte 2026 survivor; non fattori genuinamente point-in-time né portafogli eseguibili senza ulteriori vincoli.

| Variante | Alpha media annualizzata 3 fattori | t-stat HAC | p-value |
|---|---:|---:|---:|
| FULL | -3,09 pp | -0,83 | 0,406 |
| EQUITY | +2,05 pp | +0,59 | 0,554 |
| REL_MOM_GATE | +1,04 pp | +0,30 | 0,766 |
| EQUITY beta-matched EUR cash | -0,96 pp | -0,28 | 0,779 |

**Nessun alpha individuale è statisticamente diverso da zero**. Il differenziale ex post EQUITY–FULL controllato sui tre fattori è +5,14 pp annui **IC95% HAC [+1,05; +9,23]**; REL_MOM_GATE–FULL +4,13pp **IC95% [+0,27; +7,98]**. Tuttavia la stessa OOS era stata osservata prima di selezionare la politica, gli IC non correggono il data snooping, e i fattori non rappresentano tutte le esposizioni equity/settori.

## 5. Diagnosi e decisione

- La selezione cross-asset equity/property/bond del V3 è una fonte importante della sua sottoperformance storica; il recupero della politica azionaria non sparisce del tutto nemmeno dopo la correzione per beta EXSA, vol, e proxy property/sovrano ex post.
- La liquidità e la capacità investibile sono un rischio strutturale ancora più grande di quanto fosse apparso: 249 su 505 slot FULL esclusi dal gate vendor ADV250k/Q90; i vecchi 10bps non rappresentano spread/eseguibilità reali.
- **NON si è ottenuta prova di alpha netto risk-adjusted statisticamente significativo**, né una validazione PIT su dati davvero nuovi. Non promuovere EQUITY-only, REL_MOM_GATE o soglia ADV250k per trading reale.
- Prossimi lavori necessari, distinti da una nuova ottimizzazione OOS: ottenere vero consolidated venue volume/quotes e bid-ask; introdurre gestione ordine con no-fill, postpone-sell e partial fills; definire dati universi point-in-time/survivorship free; matcher multirisk che includa beta, property, sovereign, size e settore con limiti ex ante; validare su un successivo periodo non utilizzato per scegliere soglie/varianti.

I sorgenti e file di input originali sono invariati.
