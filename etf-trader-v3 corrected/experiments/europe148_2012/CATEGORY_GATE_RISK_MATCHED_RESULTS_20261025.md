# ETF Trader V3 — EU148 categoria/rischio gate — 25 ottobre 2026

**Stato: eseguito e riprodotto, ricerca; NON produzione.**
Codice, dati, 101 mesi e business-case in branch di ricerca research/v3-europe148-historical-20261024.

## Sorgenti e tracciabilità
- Run COMPLETED/SUCCESS: https://github.com/AM1975MA/Test/actions/runs/40229509953
- Sorgente: category_gate_controlled_audit.py, accanto a questo report
- Workflow: .github/workflows/v3-eu148-category-gate-risk-matched.yml
- Artefatto: v3-eu148-causal-category-gate-risk-matched-cost-sensitivity; contiene NAV giornaliero, scorecard 10/25/50/100 bps, 101 decisioni ex-ante, beta/vol as-of, ordini mensili e bootstrap
- Input congelati: https://github.com/AM1975MA/Test/actions/runs/40218758892 (148 EU veri); https://github.com/AM1975MA/Test/actions/runs/40227417589 (V3 autentico 127 leaf, 18 fitting USA-EU)

## Contratto dell’esperimento

Il vero first-stage V3 XGBRanker 127 foglie / 125 feature rimane **immutato**. 101 segnali 2018-01–2026-05; 2076 sessioni economiche comuni USA/EU con primo Open 2018-02-01 e ultimo 2026-07-01; EUR, uno stesso account Top5 con 5 posizioni a peso uguale, senza leva. Prezzo Open reale, 10bps per lato e stress fino a 100bps.

**Exact replay PASSED**, precisione 1e-10 sul CAGR identico al test precedente: FULL 3,9082151397%, EQUITY 10,9629154421%. Nessun futuro usato per decidere posizioni.

Cinque politiche:
1. FULL: Top5 unrestricted, qualsiasi ETF delle 6 categorie.
2. EQUITY: Top5 azionari del ranking già allenato senza refit.
3. REL_MOM_GATE: conserva bond/property SOLO se, prima del trade, prezzo relativo a 126 sessioni batte EXSA nello stesso intervallo E momentum a 21 sessioni è positivo. Altrimenti sostituisce il titolo con il migliore ETF equity escluso, seguendo il ranking fissato.
4. EQUITY_BETA_MATCH_FULL: titolo equity-only con cash EUR a rendimento 0%, per target beta EXSA estimato dai 126 rendimenti giornalieri antecedenti al segnale, senza leva e fattore scalare troncato [0,1].
5. EQUITY_VOL_MATCH_FULL: stesso approccio ma matching di volatilità giornaliera trailing 126 sedute.

Beta-matching e vol-matching **non sono un fattore-neutral completo**, né assicurano identici MaxDD o esposizioni settoriali.

## Risultati Top5 con 10 bps per lato

| Policy | CAGR EUR | MaxDD | Sharpe giornaliero annualizzato | Turnover nozionale sommato |
|---|---:|---:|---:|---:|
| V3 FULL | **+3,91%** | -46,97% | 0,293 | 150,78 |
| V3 EQUITY | **+10,96%** | -44,47% | 0,608 | 140,21 |
| REL_MOM_GATE | **+9,58%** | -45,32% | 0,549 | 144,55 |
| EQUITY_BETA_MATCH_FULL | **+7,38%** | -46,21% | 0,462 | 129,58 |
| EQUITY_VOL_MATCH_FULL | **+8,32%** | -44,47% | 0,504 | 132,16 |

FULL: 124 selezioni bond/property sui 505 ETF-mese; REL_MOM_GATE conserva **26** e ne sostituisce **98**. Differenze di portafoglio in 36/101 mesi. Beta as-of medio FULL **1,0486**, EQUITY **1,1482**, moltiplicatore cash equity beta **0,8876**; errore medio assoluto residuo matching beta **0,0312**. In 7/101 mesi il beta target è più alto di quello attuabile senza leva oltre 0,05. Il delta residuo beta matched vs FULL è +3,47 punti CAGR, con DD solo modestamente differente.

**Benchmark** EXSA europeo acquistato e mantenuto con stesso intervallo/costi: CAGR +8,84%, MaxDD -35,22%. Gate supera CAGR di soli +0,74 punti ma ha -45,32% DD; non ha dimostrato alpha risk-adjusted. EQUITY supera EXSA +2,12pp ma l'IC storico vs EXSA include zero nel confronto precedente.

## Friction stress: CAGR % a costo fissato per lato

| Top5 | 10 bps | 25 bps | 50 bps | 100 bps |
|---|---:|---:|---:|---:|
| FULL | +3,91 | +1,15 | -3,29 | -11,59 |
| EQUITY | +10,96 | +8,22 | +3,80 | -4,51 |
| REL_MOM_GATE | +9,58 | +6,79 | +2,30 | -6,14 |
| EQUITY beta matched | +7,38 | +4,92 | +0,95 | -6,54 |
| EQUITY vol matched | +8,32 | +5,80 | +1,72 | -5,97 |

Ordini con volume indicato **zero** dal provider: FULL 4; EQUITY 5; GATE 4; beta e vol matched 5. I costi stressati non possono certificare l'effettiva eseguibilità a un certo spread. A 50bps di costi reali, tutti i CAGR sono nettamente sotto EXSA buy-and-hold.

## Incertezza campionaria e molteplicità delle ipotesi

Moving-block bootstrap circolare di 101 periodi fra Open, 10.000 replicazioni, seed 20261025, campionamento accoppiato di entrambe le strategie, blocchi **6 mesi**, differenza **in punti di CAGR**.

| Differenza | Delta osservato | IC95% bootstrap |
|---|---:|---:|
| EQUITY - FULL | +7,05 | [+2,70; +12,35] |
| GATE - FULL | +5,67 | [+1,73; +10,83] |
| EQUITY beta matched - FULL | +3,47 | [+0,34; +7,45] |
| EQUITY vol matched - FULL | +4,41 | [+0,90; +8,88] |
| GATE - EQUITY | -1,38 | [-3,19; +0,14] |

Stesso segno del delta anche con 3 e 12 mesi di blocco. **Importantissimo**: restrizione azionaria e ipotesi di layer nascono da ispezione precedente dello stesso OOS. Questi intervalli NON correggono data snooping e NON sono prova indipendente di alpha futuro.

## Conclusione tecnica e prossimo gate

Lo storico supporta un **problema di allocazione/eligibility cross-asset a monte del ranker**, non solo un problema dell'albero di decisione. Il vantaggio della restrizione azionaria non sparisce allineando approssimativamente ex ante beta o volatilità al FULL. Un gate causale a momentum 126+21 recupera ~5,67 punti CAGR rispetto al FULL, ma non batterà necessariamente il benchmark fuori campione.

**Non promuovere una restrizione equity-only rigida a produzione.** La logica desiderabile è: layer categorie esplicito, budget di rischio separato, asset difensivi ammessi condizionatamente su segnali causali, filtro di liquidità ex-ante e costi realisticamente elevati. Testare tutto solo su periodi/veri universi non ancora usati, con neutralità fattoriale più stringente e senza variare soglie su questo campione.

Limiti irrisolti: survivor bias universo 2026, OHLCV non point-in-time, zero-volume trades, FX execution, prezzi adjusted/corporate actions, concentrazione dei segnali, esposizione a fattori equity/settori non completamente neutralizzata, impossibilità di abbinare perfettamente rischio e drawdown con solo cash, mercato europeo non identico all'americano, Stage19/meta-tree non testati in questo controllo.
