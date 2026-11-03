# ETF Research — checkpoint OLC44/OLC45 del 3 novembre 2026

**Stato:** OLC44-A, OLC45 e OLC45-B eseguiti; risultati, codice, audit e manifest versionati nel repository pubblico `AM1975MA/Test` su branch di ricerca. Nessuna modifica a `Etf_trader` o ai panieri operativi. **NON è stato eseguito ancora un riaddestramento nativo completo di OLC19 sugli ETF aggiunti.**

## Step 1 — riproducibilità dei vecchi modelli

Il replay OLC19 originale è numericamente verificato per NAV, liquidità e contabilità. Ma i suoi score sono congelati sul vecchio universo. Servono 42 input Hybrid e la catena di modellazione 21/42/63 con allenamento storico di tutti gli ETF, prima di attribuire una performance all'universo ampliato.

## Step 2 — modello supervisionato causale di ammissione OLC44-A

[Report](https://github.com/AM1975MA/Test/blob/research/olc44-causal-score-gate-20261103/research/olc44_causal_gate_20261103/REPORT_OLC44_A_IT.md) · [Codice](https://github.com/AM1975MA/Test/blob/research/olc44-causal-score-gate-20261103/research/olc44_causal_gate_20261103/olc44_prequential_gate.py) · [Risultati](https://github.com/AM1975MA/Test/tree/research/olc44-causal-score-gate-20261103/research/olc44_causal_gate_20261103/results) · [GHA](https://github.com/AM1975MA/Test/actions/runs/41732239967).

| Proxy AUTH Top2 2022–2024 | EU | USA |
|---|---:|---:|
| CAGR lordo base | 28,71% | 50,37% |
| CAGR lordo con Ridge causalmente addestrato | 29,42% | 44,09% |
| Switch attuati / corretti | 3 / 2 | 3 / 0 |
| Incremento paired logbp/mese; bootstrap CI95% | +4,55 [−11,69,+24,26] | −35,55 [−82,82,0] |

NON è un CAGR OLC19 con stop, non comprende risk overlay e non è una validazione vergine. Non promuovere.

## Step 3 — vantaggio specifico dei nuovi settori OLC45

[Report](https://github.com/AM1975MA/Test/blob/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/REPORT_OLC45_IT.md) · [Codice](https://github.com/AM1975MA/Test/blob/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/olc45_factor_shapley.py) · [Risultati](https://github.com/AM1975MA/Test/tree/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/results).

Aggiungendo quattro ETF UCITS EU (G2X.DE, USPY.DE, WTIC.DE, 2B76.DE), sui 48 mesi2021–24 il miglior rendimento assoluto futuro sale in **12/48** date, +**91,76 logbp/mese** in media; la migliore coppia teorica +74,01 logbp/mese. Esatta attribuzione Shapley: **76,55% gold miners**, 13,47% cyber, 9,57% broad commodity, 0,40% robotica. USA +3 fondi soltanto **2/48** e +18,81 logbp/mese Top1. Sono opportunità ex-post, NON CAGR.

## Step 4 — due ETC su singole commodity OLC45-B

[Report](https://github.com/AM1975MA/Test/blob/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/REPORT_OLC45_B_ETC_IT.md) · [Codice](https://github.com/AM1975MA/Test/blob/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/olc45b_etc_probe.py) · [Risultati](https://github.com/AM1975MA/Test/tree/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/results_ETC).

Due esposizioni **ETC e NON UCITS**: argento fisico `PHAG.MI` ISIN `JE00B1VS3333`, gas futures `NGAS.MI` ISIN `JE00BN7KB334`. Dopo gli ETF +4, migliori assoluti extra in **16/48** date (13 gas,3 argento), incremento teorico Top1 **+319,55 logbp/mese**, Top2 **+206,49 logbp/mese**. Nel 2021/2022 valore medio Top1 +470,66/+611,30 bp, nel 2023 solo +0,87. Estrema dipendenza di regime.

**GATE BLOC­CANTE:** 107/2064 High/Low incoerenti argento + 81/2064 gas = **188/4128 barre (4,55%)**; dati insufficienti per simulare stop intraday. Non sono stati effettuati ordini e non è stata dichiarata nuova performance eseguibile. Le seconde sedi Xetra non hanno storico Yahoo valido in questo test. Servono prezzi da provider indipendente e controllo corporate actions prima di ogni modellazione rischio.

Fonti di struttura degli strumenti: https://www.wisdomtree.com/it/products/commodities/wisdomtree-natural-gas ; https://www.wisdomtree.com/it/products/commodities/wisdomtree-physical-silver ; https://www.borsaitaliana.it/etc-etn/formazione/cosaunetc/cosaunetc.en.htm .

## Risposta alla domanda principale

**L'informazione nascosta ora evidenziata riguarda soprattutto *quali opportunità non erano nel paniere*. Non abbiamo ancora individuato un segnale che preveda in modo robusto i mesi vincenti.** La convergenza verso 50% di CAGR EU NON è stata dimostrata. Gli anni precedenti al luglio2026 sono ampiamente riutilizzati: il prossimo modello deve congelare i parametri prima degli esiti futuri.

## Ordine prioritario dopo questa consegna

1. **OLC44-NATIVE — parità vecchi score:** recuperare la catena completa di input, archivi OLC14 Head e OLC19 parent, riprodurre feature, score e scelte originali; il test a quattro feature non è un sostituto.
2. **ETC price QA indipendente:** soluzione degli High/Low, confronto ufficiale emittente/seconda venue, disponibilità cronologica, risk policy distinta per strumenti di debito.
3. **Due universi di ricerca pre-registrati:** EU152 PIT + ETF UCITS vs EU152 PIT + ETF UCITS + ETC ammessi, senza duplicati, con score ripetuti dal primo stadio e uscite/costi uguali.
4. **OLC46 separazione fattore/specialista e risk-admission:** valutare la previsione out-of-time del beneficio di ciascun fattore, non il vincitore ex-post, poi usare governance di switching controllata. Niente threshold grid-fit su 2021–2024.


## Step 5 — Origine delle barre High/Low anomale, verifica OLC45-C

[Codice](https://github.com/AM1975MA/Test/blob/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/olc45c_ohlc_integrity.py) · [Risultato grezzo/adjusted](https://github.com/AM1975MA/Test/blob/research/olc45-opportunity-factor-audit-20261103/research/olc45_opportunity_20261103/results_RAW_QA/olc45c_quote_adjustment_diagnostic.csv) · [Esecuzione GitHub](https://github.com/AM1975MA/Test/actions/runs/41734327351).

Confronto sul periodo 2017-01→2025-02 tra Yahoo **raw** `auto_adjust=False`, Yahoo adjusted `auto_adjust=True`, e adjusted ricostruito moltiplicando tutti OHLC per il fattore `Adj Close/Close`. In tutti i casi, gli stessi giorni rimangono incoerenti:

| Ticker | Anomalie raw | Anomalie adjusted | Identità date |
|---|---:|---:|---|
| PHAG.MI | 107/2064 | 107/2064 | Sì |
| NGAS.MI | 81/2064 | 81/2064 | Sì |
| CMOD.MI | 524/2053 | 524/2053 | Sì |

Quindi gli errori High/Low sono **già nella fonte originale**, non un problema dei dividendi o del fattore di aggiustamento dei prezzi. Non inventare High/Low o stop da dati sintetici. La soluzione è un vendor o una venue indipendente con storico intraday/OHLC verificato. Il beneficio E1/E2 rimane solo storico Open-only se il prezzo di Open è osservato; la qualità dello stop e la negoziabilità non sono certificate.

**Raccomandazione operativa finale:** benchmark OLC19 EU165 **23,1999% CAGR** e USA149 **50,7722% CAGR** restano invariati nel 2021–2024. Nessun CAGR nuovo attribuibile al *modello nativo* ampliato è stato dimostrato. Mantenere OLC44 modello supervisionato come diagnostica negativa/fragile, OLC45 come misura di opportunity, e passare soltanto dopo recupero input nativi + quote indipendenti a fullstack extended.
