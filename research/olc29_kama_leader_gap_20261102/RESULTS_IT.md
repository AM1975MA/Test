# OLC29 — KAMA nel modello per intercettare il miglior ticker e la persistenza

**2 novembre 2026. Esito: negativo sul criterio richiesto: KAMA non riduce la distanza dal miglior ETF europeo e non anticipa la scelta di QDVE.DE.** Questo lotto di ricerca usa esclusivamente KAMA (ER10; fastest2/slowest30, pendenza5, sopra/sotto media e persistenza su 3 segnali mensili) nell'intervento sul ranking AUTH congelato. Non sono stati adattati i predittori ETF, usate EMA/Hull o cambiate le protezioni.

Protocollo registrato su `research/olc29-kama-leader-gap-20261102`, commit `4b2833c2c86817a1c2074744d0fbd6a8fde7e018` **prima di leggere risultati candidati**. Baseline OLC20 AUTH; motore OLC19, V6 ricalcolata per ogni coppia, FAST_LOCK3 e ALARM, fee legacy 0.001 e 0.003.

## Il criterio primario: identificare e detenere il migliore ex post

Benchmark fisso per ogni finestra e mercato, selezionato con conoscenza dei rendimenti futuri e quindi **non investibile come strategia prospettica**: 2021–2024 QDVE.DE (EU) e ARGT (USA); periodo completo febbraio2019–luglio2026 QDVE.DE (EU) e SMH (USA). Nessun ticker nominativo viene usato nelle regole di KAMA.

### 2021–2024

| Mercato | Variante | Mesi Top2 con best | Peso giornaliero effettivo medio sul best | Copertura nominale dei mesi positivi best | % dei posti Top2 in futuri leader decile top (126 sedute) | Gap log_NAV vs best, punti log % |
|---|---|---:|---:|---:|---:|---:|
| EU | AUTH | 6/48 | 6,02% | 7,37% | 29,35% | -2,90 |
| EU | KAMA_PERSIST | 6/48 | 6,05% | 7,37% | 28,26% | -8,27 |
| EU | KAMA_OPPORTUNITY | 6/48 | 6,02% | 7,37% | 27,17% | -12,22 |
| USA | AUTH | 2/48 | 2,07% | 0,00% | 28,13% | +52,68 |
| USA | KAMA_PERSIST | 2/48 | 2,07% | 0,00% | 28,13% | +52,68 |
| USA | KAMA_OPPORTUNITY | 2/48 | 1,99% | 0,00% | 31,25% | +20,00 |

Il gap log_NAV è **log(NAV finale/NAV iniziale) - log(prezzo best finale/prezzo best iniziale)**, sulla stessa finestra effettivamente comparabile. Per EU MAIN l'ultima Open `observed=true` di QDVE è 2024-12-30, non la valutazione del portafoglio del 2024-12-31; si usa per entrambe le curve **2024-12-30** senza riempire il dato mancante. Si devono distinguere questi gap su intervallo perfettamente allineato dal CAGR ufficiale OLC20 su 2024-12-31.

Il 'peso medio effettivo' è una stima di quota giornaliera da `primary_units * Open/NAV`, incluse uscite per stop; la copertura dei mesi positivi misura un'esposizione Top2 teorica al **50%** nei soli mesi di rialzo del best e NON un contributo P&L o un rendimento causalmente ottenibile.

### Diagnosi del miglior ticker europeo

Il KAMA di QDVE era sopra la media in 7/12 mesi 2020, 5/12 2021, 6/12 2022, 8/12 2023, 5/12 2024, ma il filtro KAMA **persistente su tre segnali** risultava soddisfatto rispettivamente in 0, 1, 0, 2 e 0 mesi. La selezione originale QDVE nel Top2 avviene 6 volte nel 2024; nessuna proposta KAMA lo anticipa. Il **31 agosto 2021**, QDVE era 7° in AUTH, KAMA positivo e sopra soglia (ER10 0,460); ma KAMA_OPPORTUNITY preferisce XDWT.DE, il cui slope KAMA è superiore. La misura KAMA riconosce diverse forze rialziste senza distinguere la più persistente e remunerativa.

Sui 90 segnali storici, KAMA_PERSIST cambia 1 coppia EU e 0 USA; KAMA_OPPORTUNITY cambia 20 EU e 37 USA. Nei cambi con prezzi Open eleggibili: EU OPPORTUNITY 19 casi, differenza lorda media entrante−uscente **-1,62 punti log % per mese**; USA 36 casi, **-4,95 punti log %**. È un confronto diagnostico di un singolo slot, non l'attribuzione additiva dell'intero portafoglio con stop/V6.

### Guardia economica (secondaria)

FAST_LOCK3, periodo primario 2021–2024, fee legacy .001:

| Variante | CAGR EU | CAGR USA | MaxDD EU | MaxDD USA |
|---|---:|---:|---:|---:|
| AUTH | 23,20% | 50,77% | -28,61% | -20,23% |
| KAMA_PERSIST | 21,58% | 50,77% | -28,61% | -20,23% |
| KAMA_OPPORTUNITY | 20,41% | 38,86% | -28,61% | -24,77% |

La regola KAMA_PERSIST è identica alla baseline negli USA, quindi nessun alpha, nessuna validazione americana indipendente. Sull'intero periodo, KAMA_OPPORTUNITY peggiora entrambe le curve rispetto ad AUTH; anche fee .003 è sfavorevole. I CSV conservano anche ALARM, tutti i periodi, NAV e costi.

## Controlli

- 24 conti OLC29 eseguiti e registrati: 3 varianti×2 mercati×2 rischio×2 commissioni.
- Tutti **8 conti AUTH** coincidono per ciascun array economico salvato con OLC20 originale.
- Le decisioni effettive del motore coincidono con le coppie previste dall'adapter; supporto finito invariato; ogni V6 ricalcolata senza duplicare ticker primari.
- Due test di perturbazione dei prezzi dopo il 1 gennaio 2023 per ciascun intervento×mercato (4) lasciano identici gli indicatori e tutte le decisioni anteriori.
- Ricostruzione indipendente dei rendimenti giornalieri e del NAV finale controllata nei 12 archivi che conservano NAV completi (8 AUTH + 4 candidati fee.001 FAST_LOCK3); tutti e 24 i flussi di log-return riproducono la crescita contabile aggregata.
- Per EU la maschera `observed` è rispettata; per USA manca la maschera originale e si usano soltanto Close/Open preparati finiti e positivi. Nessuna imputazione di prezzi.

## Interpretazione

**KAMA da solo non spiega né corregge la mancata selezione precoce del leader europeo.** Una media adattiva ha capacità descrittiva di trend/riduzione rumore, ma il passaggio da segnale di direzione a migliore investimento relativo fra 165 candidati è un problema distinto. Questi parametri preregistrati non escludono ogni possibile uso di KAMA; sconsigliano di introdurre la regola attuale nel modello operativo. La storia 2019–2026 è stata riutilizzata molte volte: non è un vero holdout, i best ticker sono selezionati ex post e l'esecuzione intraday reale non è certificata.

**Nessuna modifica a main, nessuna promozione o trading.**
