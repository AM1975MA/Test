# OLC35 — Attribuzione del rendimento mancato e vincolo di conservazione USA

**3 novembre 2026 · Diagnostica retrospettiva · Nessun nuovo modello / trade / portafoglio; `main` invariato.**

## Decisione

**Non cambiare la strategia USA.** La ricerca OLC35 ha localizzato *dove* si trova la distanza dal migliore ETF del mese scelto a posteriori, ma **non** ha trovato un modo prevedibile ex ante per catturare quella differenza. La struttura del divario è quasi identica in Europa e negli USA; non emerge da questa analisi una ragione per sacrificare il 50% circa di CAGR USA per tentativi di selezione indiscriminati in Europa. In questa fase non viene promossa alcuna modifica EU né USA.

## Riferimenti congelati e confrontabili per variante

| Studio (periodo ACTIVE2021_2024, fee legacy 0.001) | EU CAGR | EU MaxDD | USA CAGR | USA MaxDD |
|---|---:|---:|---:|---:|
| OLC17 TOP2_CONTEXT_REVALUE / ALL_PREOPEN_V6 | **20,38%** | −26,68% | **52,30%** | −19,79% |
| OLC19 TOP2_CONTEXT_REVALUE / FAST_LOCK3, stop friction 0.001, no stress | **23,20%** | −28,61% | **50,77%** | −20,23% |

Questi sono **CAGR storici da NAV simulati** nell'intervallo effettivo 04/01/2021–31/12/2024. Non sono il rendimento cumulativo, né risultati live dimostrati. OLC17 e OLC19 utilizzano contratti di esecuzione diversi: non si sommano e non si trattano come la stessa strategia. Il 52,30% di OLC17 è una variante di sensibilità informativa sull'esecuzione preopen, non un profitto live garantito. Il 50,77% è il riferimento OLC19 per FAST_LOCK3.

## Separare tre fonti del divario dal massimo futuro

Le 48 decisioni mensili EU e 48 USA derivano dal dataset di etichette OLC32 corretto. Per data e mercato si definiscono:

* **Outside-Top5** = massimo rendimento Open→Open fra ETF del paniere meno massimo dei cinque primi AUTH;
* **Within-Top5** = massimo dei cinque meno massimo fra i primi due AUTH;
* **Two-slot effect** = massimo fra i primi due meno la media dei **due log-rendimenti** individuali. Questo ultimo numero non equivale al rendimento composto di un portafoglio 50/50.

Le tre differenze (in bp di log-rendimento mensile) sono non negative e sommano esattamente a *migliore ETF ex post − media dei due ETF selezionati*. È una **scomposizione di opportunità retrospettiva, non un'attribuzione causale del P&L o una previsione economica negoziabile**.

| Indicatore, 2021–2024 | EU165 | USA149 |
|---|---:|---:|
| Segnali mensili verificati | 48 | 48 |
| Best ticker ex post nella Top5 | 13/48 = 27,08% | 10/48 = 20,83% |
| Best ticker ex post nella Top2 | 6/48 = 12,50% | 7/48 = 14,58% |
| GAP dal best ex post, media bp/mese | 733,44 | 1.403,04 |
| GAP fuori Top5, media bp/mese | 375,37 | 730,64 |
| GAP Top5\Top2, media bp/mese | 141,04 | 262,86 |
| GAP fra migliore Top2 e media due, bp/mese | 217,03 | 409,54 |
| **Quota gap esterna alla Top5** | **51,18%** | **52,08%** |
| **Quota gap Top5 esclusa dalla Top2** | **19,23%** | **18,74%** |
| **Quota gap secondo slot / diversificazione** | **29,59%** | **29,19%** |
| 5 mesi peggiori: quota divario totale | 22,96% | 21,20% |

**Interpretazione:** l'Europa non presenta un problema sensibilmente più accentuato degli USA nell'escludere dalla Top5 il singolo best ticker *del mese successivo*. Il sistema USA, pur generando un CAGR simulato più elevato, manca perfino più spesso il vincitore ex post: questo conferma che la distanza dall'oracolo futuro **non è una misura operativa della qualità della strategia**.

## Il selettore europeo crea meno vantaggio relativo ai concorrenti

| Etichette Open→Open, medie log-bp per mese | Europa | USA |
|---|---:|---:|
| Media dei due ETF AUTH (proxy, NON NAV) | +213,36 | +303,83 |
| Mediana del rendimento fra ETF del paniere | +69,72 | +33,25 |
| **Top2 meno mediana contemporanea** | **+143,63** | **+270,58** |
| Volatilità cross-sectional fra ETF (SD mensile medio, bp) | 291,37 | 457,32 |
| Vantaggio Top2 medio normalizzato per SD del mese | +0,437 | +0,523 |
| Top2 sopra mediana del mese | 31/48 | 31/48 |

La mediana del paniere europeo è stata **più alta** di quella USA nel periodo, ma il maggior vantaggio relativo del Top2 USA (+271 bp vs +144 bp/mese) e la maggiore dispersione del paniere USA hanno contribuito al differente ambiente di opportunità. Questo NON scompone causalmente il CAGR dei NAV, che incorpora stop e ribilanciamenti. **Ipotesi per test futuri:** cercare un miglioramento della *selezione relativa EU*, più che inseguire il best ticker isolato. Nessun modello a tale scopo è stato testato in OLC35.

## Diagnostica delle protezioni: solo confronti interni OLC19

| OLC19 TOP2_CONTEXT_REVALUE | EU BASE | EU FAST_LOCK3 | USA BASE | USA FAST_LOCK3 |
|---|---:|---:|---:|---:|
| CAGR (%) | 22,23 | 23,20 | 50,55 | 50,77 |
| MaxDD (%) | −24,01 | −28,61 | −22,65 | −20,23 |
| Stop (conteggio) | 0 | 10 | 0 | 40 |
| Turnover annuale | 9,46 | 12,41 | 11,53 | 23,32 |

Sulla stessa finestra/fee/variante, FAST_LOCK3 in EU ha aumentato il CAGR di circa **+0,97 punti percentuali** rispetto alla configurazione BASE, ma ha peggiorato il MaxDD di circa **4,60 punti**. In USA, FAST_LOCK3 migliora il MaxDD di circa **2,42 punti**, mantenendo il CAGR vicino a quello BASE. Questi sono controlli già simulati, non una prova causale universale; né uno stop ridotto né una concentrazione maggiore soddisfano automaticamente la richiesta di aumento netto del rendimento europeo.

## Integrità e analisi di sensibilità

* **96/96** coppie Top2 realmente proposte da OLC17 nel 2021–24 coincidono esattamente con le scelte Top2 AUTH del dataset OLC32: 48/48 in ciascun mercato.
* **96/96** decomposizioni indipendentemente ricostruite; residuo massimo < 1e−9 bp (entro arrotondamento floating point).
* OLC32 EU esclude due etichette LEEU.DE non certificate (segnali 28/03 e 30/04/2024), senza attribuire loro zero rendimento.
* Una sola osservazione EU (30/08/2024, LBRE.DE) ha come vincitore ex post un ETF senza dati feature disponibili alla data del segnale: escluderlo dall'oracolo *scoreable as-of* riduce il divario europeo medio di appena **0,36 bp/mese**. **Non** è una nuova occasione sfruttabile da una strategia.
* I backtest originali non sono stati ricalcolati né modificati. Si mantiene la documentata carenza di quote USA originariamente marcate come osservate, la survivorship, il dato total-return, la conversione FX e la non-certificazione dei prezzi d'asta/bid-ask.
* Il campione storico è stato già riutilizzato in molti esperimenti OLC01–34: inferenze e scelte di nuove strategie devono essere validate su un periodo realmente successivo e indipendente.

## Raccomandazione per il prossimo test

**Solo laboratorio UE, USA interamente congelato.** Prima definire un solo intervento focalizzato sul *vantaggio relativo* del selettore europeo, non sul best ticker visto a posteriori. Il test dovrà preregistrare una regola causale semplice, una baseline EU realmente confrontabile, costi, turnover e MaxDD, e fermarsi se il beneficio non compare in un campione indipendente. Non esiste qui un miglioramento di CAGR EU già dimostrato; pertanto la strategia di produzione (ove presente) rimane immutata in entrambi i mercati. Un'eventuale eccezione alla conservazione USA richiederebbe una dimostrazione specifica di miglioramento europeo sostanziale, persistente e verificato, oltre all'approvazione esplicita.

## Riproducibilità

Il pacchetto scaricabile contiene i tre archivi di input esattamente versionati e i due sorgenti Python. Con Python 3.11+, pandas, numpy e matplotlib:

```bash
python src/run_olc35_attribution.py
python src/verify_olc35.py
```

Risultati e grafici in `results/` e `figures/`. Provenienza dei tre archivi in `OLC35_AUDIT.json`; hash dei prodotti in `OLC35_MANIFEST.json`. Tutte le quantità in bp sono **log-returns** mensili e NON CAGR, NAV né guadagni attuabili.
