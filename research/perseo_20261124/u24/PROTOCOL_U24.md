# U24 — protezione condizionata e rientro, 24 novembre 2026

Protocollo scritto prima dell'esecuzione U24. Motivazione derivata da U23: il trailing aiuta EU ma interrompe recuperi TR; il cooldown graduale aiuta USA ma non TR. Verificare condizioni osservabili comuni, senza identificativo del mercato nelle decisioni. Il benchmark S&P è semplicemente quello già mappato nel paniere.

Stessa U20 UNIFIED congelata, stessi prezzi/costi/motore U23. 10.000 iniziali, 1 unità per ordine e 15bp/lato; stress 30bp e una seduta di ritardo con BASE corrispondente. Nessuna nuova ottimizzazione di ticker o ranking. Warmup solo dal 2020. Segnali da chiusure precedenti, revisione ogni cinque sedute e cambi proposta; conti continui.

Famiglia chiusa di 12 regole (3 controlli e 9 nuove):

- BASE, TRAIL_CASH, RAMP: controlli identici U23.
- TRAIL_CONFIRM: trailing U23, ma uscita solo dopo due chiusure consecutive sotto la rispettiva barriera e con rendimento21 negativo. Rientro originale sopra le dieci chiusure precedenti e rendimento5 positivo.
- TRAIL_HALF: stesso stato trailing U23, ma solo metà della quota proposta trasferita in cash.
- TRAIL_FAST: uscita trailing originale; rientro dopo due chiusure sopra EMA10 e rendimento5 positivo. EMA10 richiede dieci osservazioni.
- TRAIL_PROFIT: trailing originale si arma solo se il massimo dalla nuova proposta/rientro ha superato il prezzo iniziale di almeno la banda corrente; distingue protezione di un profitto da stop di una nuova posizione.
- TRAIL_WIDE: trailing originale con banda clamp(2*sigma21*sqrt(21),8%,35%) invece della banda su cinque sedute; rientro originale.
- RAMP_GATED: rampa 25/50/75% soltanto quando S&P supera EMA21 e rendimento5 è positivo per due chiusure E rendimento5 ponderato della proposta è positivo. Altrimenti cooldown originale. Non cambia stop individuali, allarmi sistemici né limite g.
- CONFIRM_RAMP, HALF_RAMP, PROFIT_RAMP: rispettiva guardia più RAMP_GATED.

Il picco riguarda la presenza nella proposta del selettore, non un prezzo medio di carico. L'armamento PROFIT non è dunque un profitto contabile garantito. Segnali mancanti non autorizzano nuova uscita o accelerazione. La condizione di rientro non è una probabilità calibrata.

108 conti fissi =12x3x(15bp,30bp,15bp con ritardo1). Nessuna aggiunta di varianti dopo i risultati. Selezione annuale dal2022 sui24mesi precedenti: una sola regola comune ai3panieri, minimo vantaggio log annualizzato meno0,5*peggioramento DD, necessario vantaggio positivo su tutti. Procedura prudente richiede anche limite inferiore80% del minimo vantaggio>0, bootstrap appaiato3mesi/500repliche. BASE se nessuno passa. Scelta basata su chiusure prima del primo gennaio, simulazione successiva senza azzerare cash/posizioni/cooldown. 12 conti WF a15/30bp.

Analisi completa per mese, anno, 2020–22 e2023+, costi, ordini, cash. Bootstrap appaiato12mesi/3.000repliche, intervalli95% nominali sul delta log annualizzato; riportare anche la frequenza del minimo vantaggio positivo. Non sono probabilità di successo futuro e non correggono l'intera ricerca storica. Risultati locali e selezione globale separati.

QA: parità bitwise dei9controlli a15bp, ricostruzione indipendente cash/quote da ordini di tutti120conti, bilanci e commissioni, perturbazioni di dati futuri sui segnali e conti, cutoff della scelta annuale. Audit limitato alle nuove trasformazioni; eredita cataloghi non point-in-time, rettifiche non verificate, maschera USA assente, stop sintetici e liquidità incompleta. Nessun aggiornamento live.
