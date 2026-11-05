# OLC52 — Protocollo allocazione Top2 dipendente dal regime

**5 novembre 2026 — STATO: PROTOCOLLO, NON ESEGUITO.** Congelare la baseline OLC19. Nessun utilizzo live, nessuna nuova ottimizzazione della classifica ETF.

## Ipotesi

La min-var totale 25/75 porta EU165 da CAGR 23,20% a 29,31% nel 2021–24 ma cala al 18,57% annualizzato nel 2025–luglio2026 contro 23,40% per il 50/50. L'obiettivo è predire *prima* di ciascun ingresso il **valore economico netto di modificare l'allocazione**, senza usare anno, regime assegnato guardando il futuro, o un parametro scelto dopo la vista dei CAGR.

## Bracci fissati

- **B0**: OLC19 originale 50/50.
- **B1**: min-var totale sui due ticker OLC19, finestra 63 rendimenti prima dell'ingresso, cap simmetrico 25/75, stesso risk overlay e stop.
- **B2**: inverse residual volatility a 2 fattori EU (EUNL.DE, EXSA.DE), 63 sedute, cap 25/75, come benchmark alternativo di allocazione. B1 vs B0 è l'obiettivo primario.

Il controllo USA149 resta immutato; B2 è comparatore secondario, non si sceglie tra i bracci guardando il CAGR 2021–2024.

## Feature ex ante e test di incremento informativo

Un set ristretto di 4–6 segnali selezionati e definiti **prima** dell'esito:
1. **Incertezza della covarianza della coppia:** vol, corr, stabilità della stima e numero osservazioni in finestre 63/126 completamente precedenti alla decisione.
2. **Separazione economica dei forecast OLC14/16:** differenza calibrata dei forecast Top1/Top2, non differenza tra percentili adiacenti; qualità temporale del segnale.
3. **Ampiezza delle opportunità:** breadth/dispersione passata del paniere, leadership tra gruppi *realmente confrontabili*, senza utilizzare dispersione futura.
4. **Rischio residuo e sistematico:** varianza residuale, differenze di beta rispetto a fattori time-consistent, rolling as-of.

In caso di ridondanza o qualità PIT insufficiente, scartare la feature. Non includere l'identità del ticker, year dummies, dati aggiornati a posteriori o future leaders.

## Target, ML e policy

Per ogni mese t, target diagnostico `y_t = log(1+R_B1,t)-log(1+R_B0,t)` calcolato su stesso intervallo e con i costi; per il giudizio finale serve **rigiocare il ledger completo path-dependent** del motore OLC19, non sommare i controfattuali locali ignorando gli stop. Target economico netto e rischio/downside calibrati solo su dati precedenti al cutoff.

Primo modello: **Ridge/ElasticNet o logistica regolarizzata**, con fit expanding, scaling/imputazione train-only, embargo fino alla maturazione delle etichette. Non usare RandomForest/GBDT profondo/LSTM/LLM per decidere la concentrazione con poche decine di eventi indipendenti. Un piccolo albero interpretabile può essere uno *stress model* successivo soltanto se la prova primaria supera i gate.

Decisione iniziale: mantenere **B0** salvo vantaggio B1 predetto positivo al netto di costi e margine d'incertezza fissato nel training. Evitare griglie di soglie sul 2021–2024. Un mix intermedio B0/B1 è ammesso solo in un nuovo test preregistrato, non a posteriori.

## Gate di validazione

1. Ripristinare gli input originali e gli output mensili completi OLC51; controllare OLC19 e i dati PIT.
2. Estendere le feature con soli dati disponibili as-of e verificare zero leakage.
3. Replay pseudo walk-forward 2019–luglio2026 soltanto **diagnostico**: quel periodo, compreso 2025–26, è già stato studiato.
4. Controlli negativi (shuffle e noise), ablation feature, blocchi mensili correlati EU/USA, test per più ipotesi dopo almeno 54 configurazioni esplorate.
5. Replay OLC19 integrale con commissioni 0,001 / 0,003 e scenari spread/asta/stop realistici, MaxDD, turnover, errori e annualità.
6. **Conferma su mesi non ancora osservati con parametri frozen prima degli esiti.** Nessuna promozione fino a risultati prospettici e riproducibilità end-to-end.

## Perché ML sì e LLM no

ML semplicissimo può apprendere un *metagovernor* probabilistico della concentrazione, purché ci siano feature incrementali e dati indipendenti. LLM può supportare analisi qualitativa di eventi/fattori e documentazione dei dati, **non è il motore appropriato per produrre pesi numerici o classificare regimi senza training rigoroso**.

## Fonti

`OLC51_CHECKPOINT_IT.md` in questo ramo, report XLSX completo nella ChatGPT Library `/ETF_Research/OLC51_OLC52_Regime_20261105/`, e [checkpoint storico OLC44/45 su main](https://github.com/AM1975MA/Test/blob/main/research/OLC44_OLC45_CHECKPOINT_20261103.md).