# OLC25 — Leadership persistente: verifica economica e diagnostica (2 novembre 2026)

**Esito: NEGATIVO per l'aggiunta diretta del momentum/persistenza al ranking AUTH. Nessuna promozione.** Analisi storica esplorativa sui medesimi universi già studiati, **non** una nuova prova prospettica; nessun nuovo modello ETF addestrato. Parent OLC20 congelato al commit `6c387fac4c2e544bb9dc90f6622cd94faba6d7c2`.

## Ipotesi e confronto

La precedente diagnostica mostrava sottoselezione pluriennale di QDVE.DE in EU165. Qui il test non favorisce QDVE: tre segnali ex-ante ricavati dai Close precedenti a ogni decisione (momentum 126 sedute, momentum 252 sedute, media degli ultimi tre ranghi mensili a 126 sedute); due pesi fissi 20/40% sovrapposti a FUSION AUTH. Tutte le varianti sono identiche per EU165/USA149 e vengono valorizzate dal medesimo motore con V6 candidate-specific, ALARM e FAST_LOCK3, coefficienti costo legacy .001/.003. L'effetto incrementale è rispetto allo **stesso** riferimento AUTH e alla **stessa** politica economica. I 15 controlli rimescolano il segnale tra ETF eleggibili della stessa data (cinque repliche per famiglia al peso .40), senza selezionarne alcuna.

### CAGR 2021–2024, FAST_LOCK3, costo legacy .001

| Variante | EU165 | USA149 | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|
| **AUTH** | **23,20%** | **50,77%** | -28,61% | -20,23% |
| 126d, 20% | 13,28% | 10,68% | -29,61% | -29,26% |
| 126d, 40% | 9,43% | 3,02% | -31,81% | -35,77% |
| 252d, 20% | 10,68% | 15,20% | -36,12% | -31,37% |
| 252d, 40% | 11,23% | 9,42% | -32,66% | -31,35% |
| Persistenza3, 20% | 21,00% | 26,44% | -26,09% | -28,99% |
| Persistenza3, 40% | 18,09% | 11,96% | -25,52% | -35,06% |

**Nessuna delle sei varianti** migliora il CAGR in uno dei mercati nel periodo primario: tutte peggiorano **entrambi** i mercati. Anche ALARM, fee .003 e intervallo FULL non mostrano un miglioramento congiunto. In particolare Persistenza3-20% su FULL FAST_LOCK3 .001 porta EU 19,76%→15,73%, USA 39,48%→41,40%: il vantaggio USA è confinato alla finestra completa già esplorata e non valida come progresso congiunto. Nella finestra principale FAST_LOCK3 .003 Persistenza3-20% EU 19,88→18,15%, USA 42,73→19,93%.

L'unico trade-off secondario tangibile: Persistenza3-20% EU MaxDD migliora da -28,61% a -26,09% e turnover da 12,41 a 10,67 annuo, ma perde 2,20 punti di CAGR; negli USA peggiorano sia crescita sia rischio.

### Segnali negativi: controllo contro perturbazioni arbitrarie

| Famiglia al 40%, FAST_LOCK3 .001 | CAGR EU reale | Mediana shuffle EU | Shuffle EU >= reale | CAGR USA reale | Mediana shuffle USA | Shuffle USA >= reale |
|---|---:|---:|---:|---:|---:|---:|
| 126d | 9,43% | 5,44% | 1/5 | 3,02% | 7,15% | 5/5 |
| 252d | 11,23% | 11,31% | 3/5 | 9,42% | 6,05% | 2/5 |
| Persistenza3 | 18,09% | 10,89% | 0/5 | 11,96% | 9,23% | 1/5 |

La persistenza sembra contenere informazione *relativa ad alcune perturbazioni arbitrarie*, specie in EU, ma **non** produce un rendimento aggiuntivo sul riferimento AUTH. Cinque controlli per famiglia non forniscono p-value calibrati, né frequenze posteriori. Non vanno sommati ai risultati storici di altri lotti.

### Diagnostica del ranking ex-ante

Nel 2020 QDVE.DE presenta rango mediano **1 su momentum 252 sedute** (per i segnali con lookback e prezzi osservati) ma rango mediano **52 su FUSION AUTH**, e non compare nel Top2. Nel 2021 è invece circa 47° sul momentum 126 sedute: non è sempre un leader su qualunque orizzonte. Nel 2023 il suo momentum 126 sedute raggiunge mediana circa 8°, ma AUTH rimane 27°; nel 2024 le medie si avvicinano (2° su momentum annuale e 2,5° su AUTH).

I ranghi e i coefficienti di correlazione cross-sectional fra prezzo-momentum e FUSION sono instabili nel tempo: nei mercati/anni recenti il momentum può essere sia complementare sia contrario ai segnali originali. Gli esiti Open-to-Open del Top2 selezionato dai mix semplici peggiorano già *prima* del controllo stop/costi nel 2021–2024 (EU AUTH +2,40% medio mensile vs Persistenza3-20% +2,30%; USA AUTH +3,60% vs +2,89%). Perciò il peggioramento non è spiegabile semplicemente dalle protezioni.

**Attenzione ai prezzi mancanti:** alcune aperture QDVE nel 2020 non hanno maschera `observed=True` pur avendo numeri finiti nel pannello; il buy-and-hold ex post nel grafico non è una certificazione di eseguibilità di ogni singola quotazione. A livello EU sono richieste entrambe le maschere `observed` per il momentum; negli USA la maschera originale non è presente e si usano soltanto prezzi preparati finiti/positivi. Non abbiamo certificato dati total-return, FX, delisting, esecuzione intraday o spread.

## Incertezza e integrità

Controllo AUTH: tutte le otto ricostruzioni economiche EU/USA, due contratti e due commissioni riproducono gli array OLC20 **esattamente**, prima dei candidati. Sono valutati **22 percorsi di selezione** (1 AUTH + 6 autentici + 15 null) × **8 conti** = **176 conti economici** con `validate_book` e V6 ricalcolato per ogni coppia. I tre test di feature/causalità/multiset null passano. Primo fallimento del test null risolto prima di guardare i candidati, registrato in CHECKPOINT_01_PRE_OUTCOME.md.

Bootstrap descrittivo per Persistenza3-20% contro AUTH: 48 mesi appaiati 2021–2024, 5000 ricampionamenti circolari a blocchi di sei mesi. Differenziale medio annuo in log-return, FAST_LOCK3 .001: EU -1,83 punti, IC95% [-10,95;+5,78]; USA -17,55 punti, IC95% [-45,90;+8,22]. Questi intervalli sono condizionali alla ricerca già svolta, non corretti per tutte le varianti e non sono probabilità posteriori. Zero non costituisce automaticamente un veto, ma in questo lotto i confronti economici primari sono chiaramente negativi.

## Implicazione e prossima ipotesi

La persistenza dei prezzi **non va inserita come bonus universale sul Top2**. Il ranking esistente sembra fragile alle perturbazioni, e negli USA è molto superiore a una regola ingenua di trend. Il problema interessante è diverso: apprendere **se e quando** la forza di 6–12 mesi preannuncia *leadership futura* con un supervisore causale leggero, usando solo etichette maturate e puntando ad aggiustamenti piccoli, non a riscrivere l'intero ranking. Questo sarà un nuovo lotto distinto, preregistrato, senza scegliere parametri in base alle celle OLC25.

File: `MAIN_MATCHED_COMPARISON.csv`, `NULL_COMPARISONS.csv`, `PAIRED_BOOTSTRAP.csv`, `MOMENTUM_IC.csv`, `QDVE_DIAGNOSTIC.csv`, `SELECTED_GROSS_O2O.csv`, test sorgente `tests/test_leadership.py`, codice `src/run_olc25.py`. Grafici `EU_LEADERSHIP_ANNUI.png` e `USA_LEADERSHIP_ANNUI.png`.
