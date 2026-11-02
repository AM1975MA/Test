# OLC26 — checkpoint 01 prima della valutazione economica

2 novembre 2026. Sono stati costruiti in locale gli input causali del supervisore e le previsioni annuali, ma i risultati economici dei candidati non sono ancora stati letti.

- Target leadership relativa su rendimenti Close→Close dei successivi 126 giorni di Borsa, con data esatta di maturazione prima del 1° gennaio di ogni anno di fit; nessuna label futura entra nel training.
- Per i fit annuali completi: 5 Ridge POOL (2022–2026), 10 Ridge STRAT (5 anni ×2 mercati). Il 2021 ricade sul riferimento AUTH senza fit, conformemente al protocollo.
- Altre 5 repliche placebo POOL e 5 STRAT con i semi 26001–26005; target futuri rimescolati solo fra ETF eleggibili nella stessa data e mercato.
- Feature limitate a FUSION AUTH e ranghi prezzo 63/126/252/PERSIST3, con una sola interazione; nessuna identità del ticker e nessun input futuro.
- Test locali pre-outcome 4/4 passano: maturazione stretta, pesi del training bilanciati EU/USA nel POOL, ricaduta su AUTH e predizioni invarianti con feature mancanti, determinismo dei controlli.
- Test di esecuzione economica sui riferimenti ancora da completare. Nessuna modifica a main, ai learner ETF originali o alle protezioni.
