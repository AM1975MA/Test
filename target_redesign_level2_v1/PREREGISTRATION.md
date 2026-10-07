# TARGET_REDESIGN_LEVEL2_V1 — Protocollo congelato (solo ricerca)

Data: 2026-10-08. Repository autorizzato: `AM1975MA/Test`. Nessuna modifica ai repository `Etf_trader` o `Trader_selector`. Questa branch NON modifica `vendor/etf_trader_v2`, i sorgenti canonici, i basket, le allocazioni o la logica di rischio.

## Ipotesi di ricerca

Il target storico `round(target_rank_21*100)` elimina informazioni sulla **magnitudine economica** delle differenze tra ETF e trasforma piccole revisioni dei rendimenti in possibili discontinuità del ranking/relevance. Testiamo in una linea indipendente la fattibilità di target economici continui e coerenti con l'esecuzione, **senza supporre** che da soli migliorino qualità predittiva o stabilità delle decisioni.

L'insieme dei prezzi è quello già congelato in `evidence_v1/data/original149` e, per confronti di revisioni, le tre vintage storiche note. Non occorre alcun nuovo fornitore ETF. L'uso storico di Original149 e Holdout70 è già “burned”: nuovi risultati su di essi possono essere **solo diagnostici**, mai evidenza confermativa.

## Target e definizioni — congelati prima dei fit

Il segnale `t` nasce a chiusura dell'ultima seduta del mese. Entrata `e` all'**Open della seduta successiva**; uscita `x_h=e+h` alla **Open** dopo `h` sedute, `h in {21,42,63}`. Fonte prezzi: gli stessi adjusted OHLC del baseline (`auto_adjust=True`). Non usare `Close[t]` come entrata eseguibile.

Per ogni ticker `i`:

- `gross_ret_h = Open[i,x_h]/Open[i,e] - 1`
- `net_ret_h = (Open[i,x_h]/Open[i,e])*(1-c)^2 - 1`, con `c=0.001` **per lato** come ipotesi conservativa e uniforme a livello di singolo trade; NON equivale ai costi effettivi di un portafoglio con turnover dinamico.
- **Target principale**: `alpha_cash_log_h = log(1+net_ret_h) - log(Open[BIL,x_h]/Open[BIL,e])`. BIL è già nel frozen universe; rappresenta un **proxy di benchmark investibile mantenuto in posizione**, non liquidità senza rischio/costi né un tasso risk-free puro. Non imputare la sua storia prima dell'inception.
- **Controllo**: `alpha_spy_log_h = log(1+net_ret_h) - log(Open[SPY,x_h]/Open[SPY,e])`. SPY è un riferimento di rischio azionario, non il benchmark universale di selezione cross-asset.
- **Rischio realizzato**: `adverse_excursion_h = max(0, 1 - min(Low[i,e:x_h-1],Open[i,x_h])/Open[i,e])`. Il minimo esclude i Low successivi all'Open di uscita e include l'eventuale gap di uscita. È una proxy della massima escursione sfavorevole (MAE), non il P&L di uno stop reale.

Se BIL/SPY è indisponibile sulla data, il rispettivo alpha resta NaN (nessun forward/backward fill). I rendimenti asset possono restare validi. L'orizzonte 21 è **primario**; 42 e 63 sono ausiliari e non devono essere sommati con pesi arbitrari. Un modello separato può apprendere i diversi orizzonti; nessuna combinazione predefinita è approvata.

### Affidabilità delle previsioni

**NON definire una etichetta `confidence` fittizia**. Solo dopo aver addestrato modelli causalmente fuori campione, costruire intervalli e calibrazione su residui **prequential/OOF**; quantili `q10/q50/q90` del target economico e rischio di downside si valutano con pinball loss, coverage e calibration gap. Non stimare la varianza dai residui in-sample come se fosse incertezza prospettica.

## Requisiti causali e qualità

1. Fitting annuale: per una riga train con segnale `t` e orizzonte `h`, esigere **`signal_date < cutoff` E `exit_date_h < cutoff`**. Trasformazioni, normalizzazioni del target e calibrazione dei residui devono essere fittate solo dopo questo filtro; nessuna label non matura deve influenzare fit o early-stopping.
2. Nessun `rank()` sugli outcome futuri per costruire il target economico; se si calcolano successivamente percentili per METRICHE, mantenerli nell'area di valutazione. La sottrazione di un benchmark comune per data non cambia da sola il ranking effettivo degli ETF.
3. Identità `signal_date,ticker` univoca; Open e Low coerenti e positivi; calendario trading condiviso; entry **esattamente una seduta** dopo signal; exit **esattamente h sedute** dopo entry; rifiutare errori invece di riempirli.
4. Controllo di parità con `fwd_ret_h` preesistente quando disponibile: ricostruzione Open-to-Open deve coincidere entro tolleranza numerica.
5. Mantieni input, date, composizione universo, eleggibilità e costi del baseline congelati per confronti. Se i target BIL riducono la copertura di training, quantificare righe/date perse ed effettuare confronto a **coorte identica**: non attribuire a un target l'effetto di cambiare campione.
6. Non utilizzare future `Low` come feature. L'escursione negativa è solo una label realizzata. OHLC adjusted storici sono proxy di total-return prices: dividend/corporate-action revision risk e simulazione di esecuzione esatta restano aperti finché il livello 1 non viene affrontato.
7. Le tre vintage Yahoo della stessa storia sono esperimenti di perturbazione, NON campioni statistici indipendenti. Nessuna ottimizzazione su Original149/Holdout70 può promuovere il nuovo modello.

## Fasi e criteri di esito

**Fase L2-A (questa branch):** implementare target builder indipendente, test sintetici di date/costi/parità/casi mancanti, nessun fit, nessuna modifica produttiva.

**Fase L2-B (successiva):** calcolare coverage per anno, per gruppo ETF e per horizon, distribuzione dei nuovi target, code, missingness, effetti di BIL non ancora quotato, correlazione rank storico / alpha realizzato e stabilità inter-vintage dei target numerici. Congelare hash dati/codice e lo stesso insieme di signal/ticker prima di ogni fit.

**Fase L2-C (successiva):** esperimento fattoriale target-vs-learner con learner regolarizzato fisso e comparatori:
1. control `target_rank_21` continuo;
2. economic `net_ret_21` continuo;
3. economic `alpha_cash_log_21` continuo.
Allineare rigorosamente stesse feature, stesse righe train/test, stessi cutoffs e learner. Report: Spearman/Rank IC, NDCG@5, selected realized economic alpha/regret, errori previsionali per anno, coppie di vintage, Top1 disagreement e churn. NDCG senza ritorno economico non basta. **Non** adottare automaticamente un target in base al solo CAGR.

**Gate di ricerca:** ammettere alla fase modelli soltanto un target con plausibilità economica, coerenza temporale e nessuna regressione materiale di qualità OOS rispetto al controllo a pari coorte; premiare stabilità delle decisioni assieme all'efficienza predittiva, non solo una minore varianza di CAGR. Intervalli OOS paired per data con bootstrap a blocchi temporali e reporting per anno/regime. Per promozione reale serviranno periodi prospettici non consumati dal tuning.

## Stato

Implementazione `targets.py` e test sintetici associati; **nessun training svolto, nessun CAGR del nuovo modello disponibile**. Lo status dei test va registrato solo dopo esecuzione effettiva. Non modificare il baseline per eseguire L2-A.
