# OASIS — ritorno al paniere CANONICO dei 149 ETF originali

**Data congelamento:** 18 ottobre 2026, prima del primo test OASIS149.
**Branch isolato:** `research/oasis149-canonical-rebuild-20261018`.
**Repository:** `AM1975MA/Test`. Non modificare `etf_trader` né i risultati precedenti.

## La correzione chiesta dall'utente
L'universo di riferimento NON è il Top150 per completezza storico creato in un esperimento successivo e NON è il totale di 219 ETF. Sono **esattamente** i 149 ticker, nella composizione originale e nelle classi dichiarate, contenuti in `evidence_v1/data/original149/universe.csv`. Prezzi e SHA sono in `evidence_v1/data/original149/manifest.json`. Nessuna selezione/rimozione in funzione di rendimento, copertura o errori sperimentali. Verificare tutti e 149 hash dei file contro il manifest, 149 ticker unici, tutte le sei macroclassi e la cronologia delle aperture osservabili. In caso di errore bloccare l'intero esperimento, non scegliere un universo alternativo.

Il corpus risale a dati Yahoo acquisiti fino al 2026-07-31. Il periodo economico viene mantenuto 2017-02-01 → 2026-07-01 per confronti con il precedente motore: 2.366 sedute se e soltanto se tutte le aperture dei 149 sono valide, senza riempimento con prezzi futuri. La selezione contemporanea dei fondi sopravvissuti rimane **survivorship biased** e non è PIT; questo universo è già stato testato ripetutamente: un nuovo test non è un nuovo holdout.

## Coordinatore: cinque verifiche ordinate, con veto

- **D0 Fonte:** integrità/identità dei 149, valuta/fondo, corporate actions, consistenza timestamp, anomalie; non spacciamo Adjusted Open per effettivi prezzi broker né volume positivo per eseguibilità.
- **I1 Informazione:** verificare la capacità *predittiva ex ante* di preferire un ETF candidato a un ETF detenuto, con perdite e costi condizionati; non autorizzare trade da un modello che fallisce proper score.
- **R2 Rischio:** costruire lo stesso segnale su 2 ETF, Top6, uno per sei classi, sei classi pesi inverse-vol/25% cap, esposizione fissa 75%, overlay Student-t; isolare il solo effetto di concentrazione e cassa.
- **C3 Crisi:** valutare rischio specifico del portafoglio e delle singole posizioni, non solo un indice medio comprendente bonds/commodities/equity.
- **V4 Validazione:** nessun backtest incrementale senza costo, valuta, entrata open dopo segnale e confronti passivi; statistiche per 2017–20, 2021–23, 2024–26; bootstrap per blocchi con unità temporale.

## Passi ESEGUITI in questa prima Action
**D0** Caricare i 149 file e verificare SHA/membership, completezza e calendario. Nessun uso delle score ML storiche.
**I1** Riutilizzare senza cambiamenti il protocollo `oasis_v2/g1/PROTOCOL_FROZEN.md` con i 149 corretti: cinque modelli predefiniti NULL, momentum, residual logit, hierarchical regime, Student-t; stesso costo 0.3% log, coppia NEW vs HELD, 21 sedute, rolling fit solo da label maturate. Per gli ETF "held", generare in modo indipendente l'esatta strategia OASIS P3 sullo stesso paniere 149 ai soli fini di **campionamento condizionato**. Queste posizioni non sono dati futuri né predittori. Brier/logloss principale su `challenge`; calibrazione per epoca; richiedere miglioramento su NULL e momentum e CI bootstrap positiva prima di usare H2 in trading. Se G1 fallisce → dichiarare FAIL, **NON** rietichettare come opportunità redditizia un backtest favorevole.
**R2** Solo con il vecchio identico price-score OASIS senza H2: testare 7 strategie di rischio precongelate `oasis_v2/g2/PROTOCOL_FROZEN.md` sulla stessa cronologia 149, e verificare nel continuo l'eguaglianza economica del benchmark Top2 fra due simulatori indipendenti (soglia 1e-8 capitale normalizzato). Report rendimento CAGR, MaxDD giornaliero, ES5, Sharpe, costi e 12m block bootstrap. Aggiungere buy&hold SPY, buy&hold AGG e mix 60/40 **esclusivamente contesto**, con convenzioni costo non equiparate alle strategie attive.
**C3** Audit esplorativo: specificare in JSON giorni in drawdown in cui il vecchio P3 identificava una crisi e rischio portfolio non protetto; tenere separati nuovi modelli di rischio che non hanno ancora previsioni calibrate.
**V4** Appendere registro completo 149, previsioni G1 e 7 curve R2 con hash SHA256; tenere gli esiti negativi e non fare sweep di parametri sugli stessi anni.

## Risultato desiderato e stop rule
Dati esatti 149 e G1 proper score > NULL/Momentum in entrambe le epoche e superiore per bootstrap su unità temporali **prima** di qualsiasi produzione. R2 impone almeno un riferimento passivo 60/40 e un rischio di perdita misurato sulle singole posizioni. Anche se G1 passa in questo dataset già sfruttato, rimane sperimentale fino a prova nuova veramente PIT.

**Non si promette un salto di CAGR.** Obiettivo misurabile: superare in modo stabile un segnale nullo e una regola passiva con un vantaggio netto, non scegliere il vincitore ex post.
