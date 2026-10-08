# L2-K — Attribuzione economica del componente Titanium e audit metodologico

**8 ottobre 2026 — COMPLETATO PER UN PROXY TITANIUM, NON PER L'INTERA STRATEGIA HYBRID24.** Tutto il lavoro svolto su `AM1975MA/Test`; nessun file alterato in `Etf_trader`. Nessun nuovo ML. Dati Original149 già ripetutamente esplorati: sviluppo diagnostico, non conferma indipendente.

## Origine e verifica
- [Protocollo fissato prima dei risultati](L2K_ATTRIBUTION_PROTOCOL.md), commit `8f5ca709ebad3af4a75587acc5f89c1458e2094c`.
- Fonte prezzi Original149 2026, Yahoo Repeat2: GitHub Actions [37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact `11272972639`.
- Fonte segnale Titanium `TIT_R_SOURCE_ONLY.csv`: GitHub Actions [37150436612](https://github.com/AM1975MA/Test/actions/runs/37150436612), artifact `11283503395`, file nello ZIP `work/original149/titanium/TIT_R_SOURCE_ONLY.csv`, SHA256 `16b955a433b11bcb723f0b649b7c090bb8979d6ef21a3aaa342fec546663118f`.
- **Parità prezzi 149/149 file CSV byte-identici** tra Yahoo Repeat2 e l'input `titanium_raw` che ha generato TIT_R. **16.986** score (114 date, 149 ETF), di cui **113 periodi investibili chiusi** dal 2017-02-01 al 2026-07-01.
- Audit indipendente **PASS**: SPY 113 mesi verificato sugli Open originali; 113 selezioni TIT_R indipendentemente ricostruite; 339 righe ledger 3 portafogli; max errore rendimento lordo `9.89e-17`, fee `6.63e-16`, capitalizzazione e CAGR riconciliati.

## Limite fondamentale: NON equiparare score normalizzato e grezzo
`TIT_R` è il percentile del blend prodotto da `models.variants()`. La funzione ausiliaria `kernel.simulate()` applica la soglia margine 0.12 invece a un altro score, `titanium_score` grezzo. L'applicazione diagnostica del margine 0.12 a `TIT_R` ha selezionato **75/25 Top1/Top2 in tutte le 113 date**. Pertanto i dati in questo rapporto rappresentano un **proxy TOP2 75/25** sul segnale Titanium (con fee calcolate sul nozionale reale e senza governor), NON una replica matematicamente identica di `kernel.simulate` e tantomeno del **motore operativo MA3/Hybrid24**, che riceve un ulteriore hybrid producer/controllo giornaliero. L'errata equivalenza delle scale è stata scoperta nell'audit e dichiarata, **senza ottimizzare pesi o rieseguire varianti**.

## Attribuzione economica aritmetica dei rendimenti lordi, per mese

Identità per ciascuna data: `r_scelto = r_SPY + (r_categoria_EW - r_SPY) + (r_scelto - r_categoria_EW)`. Categoria_EW: media di tutti gli ETF del macrogruppo disponibili **all'entrata** (universo 2026; ipotetica e non necessariamente investibile). Err massimo identità `6.94e-18`. Ogni comparatore usa stesso calendario degli Open.

| Componente | Media mensile lorda | Intervallo 95% esplorativo, bootstrap blocchi da 3 mesi |
|---|---:|---:|
| SPY | +1.3023% | n.a. |
| Categoria vs SPY | **−0.4100 punti %** | [−1.0095,+0.3112] pp |
| Selezione ETF nella categoria vs EW | **+0.7499 punti %** | [−0.3687,+1.8613] pp |
| Totale segnale Titanium proxy | +1.6422% | n.a. |
| Titanium − SPY | +0.3399 punti % | [−0.9562,+1.7073] pp |
| Titanium − semplice momentum 12–1 nella **stessa categoria** | **+0.0374 punti %** | [−1.3518,+1.3708] pp |

**Conclusione:** non è stata dimostrata una performance della selezione within-category distinta da un semplice momentum. Ogni intervallo dei differenziali attraversa lo zero; ripetuti studi sullo stesso storico indeboliscono ulteriormente ogni lettura di significatività. Correzione diagnostica *post hoc* per beta SPY stimato solo su 252 sedute passate: differenza intra-categoria media da +0.7499 a **+0.6463 pp**, CI descrittivo **[−0.4514,+1.7673] pp**, sempre inconclusiva.

## Replay di capitale: proxy TIT_R 75/25, **NON Hybrid24**

Self-financing trading mensile sugli Open successivi, fee 0.1% del controvalore reale acquistato o venduto, primo ingresso e liquidazione finale, nessun trade terminale fantasma; senza governer / stop. Valori 2017-02-01–2026-07-01:

| Proxy | CAGR | Max drawdown campionato mensilmente | Turnover annuo, controvalore/capitale |
|---|---:|---:|---:|
| TIT_R Top2 75/25 | **13.81%** | **−40.57%** | 20.21× |
| Momentum 12–1 within-category con stessi pesi 75/25 | **14.41%** | −28.95% | 17.77× |
| SPY Buy/Hold | **15.23%** | −23.31% | 0.11× |

I gross return mensili NON sono additivi nel CAGR. Questi risultati NON smentiscono automaticamente i precedenti **full Hybrid24** (altro motore, altri componenti, diverse protezioni); dimostrano che sul semplice Titanium il selettore non presenta una superiorità economica robusta.

## Regime, concentrazione, coda
Top1 delle 113 scelte: **58 real assets, 28 emerging, 23 settoriali/tematici US, 3 developed global, 1 bonds/cash, 0 US broad**. Categorie cicliche dominanti, dunque rischio fattoriale rilevante. Peggiori 3 mesi del proxy: 2020-02 ARGT **−30.13%**, 2022-11 UNG **−27.76%**, 2018-11 KWEB **−20.09%**. Circa 40.7% mesi negativi. Selection within-category nel 2018 **−1.97 pp/mese**, 2020 **−2.27**, 2021 **+3.07**, 2023 **+3.56**, 2025 **+2.95**, 2026 gen–mag **−2.08**: elevata dipendenza dal regime/campione. La segmentazione della volatilità SPY prima del segnale è diagnostica, non una regola ML.

## Audit del motore: distinguere due simulatori
- `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py::period_path` è un **helper ausiliario**: dopo il raggiungimento di −5.5% con slip 0.1%, `governor=True` imposta artificialmente il rapporto a `0.75+0.25*0.944 = 0.986`, non 0.944; applicato a una posizione precedentemente investita per intero, il cambio di valorizzazione richiede un audit di conservazione del capitale. **Non usarlo per attribuire il rendimento del sistema vero.**
- `vendor/etf_trader_v2/src/etf_trader/ma3/ddfirst.py::simulate_ddfirst` e `ma3/v6.py::simulate_with_alt` usano quantità monetarie e test di gap Open; **non** applicano la formula semplificata 0.986. Questo non dimostra un bug nella pipeline operativa.
- Un monitor sintetico, NON del rischio effettivamente attivato da MA3, di stop fisso 5.5% sul prezzo iniziale rileva 102/226 gambe interessate e 21 prime violazioni con Open sotto stop. Serve solo a motivare la verifica degli Open/gap nel vero motore, non è una stima di P&L.

## Decisione per il prossimo gate
**NON addestrare nuovi modelli.** Prima ricostruire con parità totale score->hybrid producer->MA3 DDfirst/HighCAGR24/V6->trading e risk engine giornaliero e solo allora attribuire le differenze di CAGR e drawdown ai vari layer. Usare strumenti cash BIL/SHV come già presenti nell'engine, senza imporre BIL come target ML. Serve inoltre una valutazione davvero futura con universo e prezzi acquisiti as-of; le vintage 2026 del medesimo mercato non bastano.

**Riproduzione:** script `run_attribution.py`, `beta_factor_check.py`, `independent_audit.py`; file `MONTHLY_ATTRIBUTION.csv`, `ANNUAL_ATTRIBUTION.csv`, `REGIME_ATTRIBUTION.csv`, `PERIOD_SPLITS.csv`, `BETA_DIAGNOSTIC.csv`, `EXECUTION_PROXY.csv`, `TRADE_LEDGER.csv`, `STOP_*.csv`, `RESULT.json`, `INDEPENDENT_AUDIT.json`. Forniti con report nella ZIP conversazionale `ETF_Trader_L2K_attribuzione.zip`. Input Yahoo/Titanium grezzi si recuperano dagli ID GitHub citati (non duplicati in ZIP).
