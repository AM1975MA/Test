# L2-P — Singolo ETF: stop condizionale indipendente dal gate di mercato — protocollo congelato

**Congelato 8 ottobre 2026 prima di qualunque output L2-P**. UNICO repo `AM1975MA/Test` branch `research/target-redesign-level2-v1`; NON modificare `Etf_trader`. 149 ETF Original149 2017-02-01—2026-07-01: storico esplorato, quindi test diagnostico post hoc dopo l'analisi dei drawdown 2025, **NON** conferma fuori campione.

## Ipotesi unica e confronto corretto

La V2 usa un limite prezzo stop `prior_close*(1-0.055)` che però viene eseguito SOLO se `(UH OR SA)` per l'ETF e `(sysm OR ud1>=0.55)` per il mercato: l'ultimo gate ha impedito qualsiasi stop durante il DD di giugno–ottobre 2025. Il candidato più parsimonioso è **rimuovere SOLO il gate market** dalla protezione dei singoli ticker, lasciando immutati:
- stop (5.5%) dal close precedente, non dall'entry e senza inventare un trailing stop;
- segnali tecnici UH/SA calcolati esclusivamente sui close precedenti;
- fill `Open` in caso di gap sotto stop, altrimenti `stopprice*(1-0.001)` se Low oltre soglia;
- commissione `0.001` e cooldown di 3 sedute già presenti nel motore;
- capitalizzazione, ribilanciamento il giorno successivo (incluso eventuale re-buy), disponibilità di BIL/SHV, V6 ALT, HighCAGR24 e DDfirst;
- **stessi** d1/d2, weight1, score Titanium+MA3, medesimi 2366 input giornalieri Yahoo Repeat2.

Confronto codificato come **due sole sostituzioni** nel sorgente esatto `l2n_full_replay.py::simulate_arch`, da `and p1 and (sysm or ud1[k]>=.55)` a `and p1` e analogamente per `p2`. Tutte le altre istruzioni e float/loop identici. L'attivazione di UH/SA continua, quindi questo è un'ablazione del solo gate globale, **non** l'imposizione di stop uncondizionato né un ottimizzatore di soglie.

## Parità ed esiti obbligatori

Ricostruire con source congelato `/mnt/data/titanium-repeat-2.zip` e source L2-N/L2-O: Golden storico 43.146% **NON** ricalcolato sul medesimo raw; baseline corretta Repeat2 `CAGR=30.84370492564604%, DD=-25.6896102666868%, Sharpe=1.0869929498969` verificata con errore <=1e-10 prima di valutare candidata.

Nuovo replay full-source `stage19.simulate_arch` 2366 giornate, con ranking, gross G2, ALT, cash/governor invariati. Metriche: CAGR, daily DD e data economica, Sharpe, turnover/fees, conteggio stop, stop open-gaps, full-ledger differenze, raggruppamento anno e 2025 DD, frazione di giorni differenti; **retorno addizionale dei mesi critici vs nel resto periodo**. Riconciliare simultaneamente con una seconda contabilità monetaria Python indipendente dal Numba. Evitare distorsione di contare i tickers come date indipendenti.

Gate di NON inferiorità stabilito ora, non scelto in funzione del risultato:
1. CAGR candidato >=0.95×CAGR BASE matched Repeat2 (soglia circa 29.30%);
2. maxDD giornaliero candidato almeno 2.0 punti percentuali **meno negativo** del BASE;
3. annualized turnover <=1.10×BASE;
4. tutte le parità, contabilità, pricing stop e cronologia PASS.
ALL FOUR devono passare per **mera candidatura a studio prospettico**, senza promozione a V2. Se fallisce: NO GO, non cambiare stop 5.5%, il gate, o introdurre tempi di cooldown ex post. La prova continua a essere retrospettiva e selezionata dopo l'ispezione del 2025.

Block bootstrap descrittivo 3 mesi, 5000 estrazioni, sull'unità mese (non ticker), intervallo non corretto per tutti i precedenti esperimenti. Nel rendiconto distinguere **stop tecnici condizionati** da stop di prezzo eseguiti effettivamente; ciò evita di sostenere falsamente che basta aver rilevato una perdita del 5.5% per aver realizzato un ordine.
