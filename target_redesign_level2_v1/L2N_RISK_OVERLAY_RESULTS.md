# L2-N — Test completo V2: filtro di rischio con volatilità residuale + accelerazione

**Data: 8 ottobre 2026. Stato: COMPLETATO, AUDIT PASS, CANDIDATO RESPINTO.** Unico repository modificato: `AM1975MA/Test`, branch `research/target-redesign-level2-v1`; `Etf_trader` invariato.

## Protocollo preregistrato prima del risultato
[L2N_RISK_OVERLAY_PROTOCOL.md](L2N_RISK_OVERLAY_PROTOCOL.md), commit `acb590be8d96d543d9ccb5544e4a92b6132a46c1`.

Su ogni ETF già scelto da MA3 (top1 e top2): `fragile=(vol_orthog_rank>=0.80) & (accel_21_vs_42<0)`, entrambe caratteristiche **disponibili alla data di segnale mensile** dal panel storico L2-M Repeat2. Nessun veto sui ticker, nessun rifitting. Esposizione ponderata fragile `f = w1*fragile1+(1-w1)*fragile2`, dove `w1` è il peso di concentrazione dopo le regole canoniche MA3. Unico intervento `G2_nuovo = min(G2_originale,1-0.25*f)`, applicato per il mese successivo. Denaro liberato valorizzato dal motore V2 vero in **BIL/SHV**, mantenendo invariati V6 alternative, stop e controlli sistemici. Non cercare altri valori/soglie sullo stesso Original149.

## Parità certificata — V2 FULL COMPLETA
Usati esclusivamente gli input già congelati `titanium-repeat-2.zip`: 149 ETF adjusted Yahoo, OOS `TIT_R`, `ENSEMBLE_TAIL_OOS` con ET/XGB e calendario; rischio `ddfirst`/HighCAGR24/Stage19 e V6 ricostruiti dal codice repo. **2.366 sedute** dal 2017-02-01 al 2026-07-01, calendario originale, costi 0.1% sull'operatività reale modellata. Il motore baseline ricostruito da zero replica esattamente i risultati del precedente `compact21_stability_v1/results/FULL_REPLAY.json` Repeat2: CAGR `30.84370492564604%`, MaxDD giornaliero `-25.689610266686813%`, Sharpe `1.0869929498969455`; errore <=3.4e-16. L'esperimento **non è un Top1 o Titanium-only proxy**. Il Golden Annual V2 storico `43.145952%` è un'altra provenienza **ancora da riconciliare**, non è il baseline matched di questo test.

## Risultati (un SOLO challenger)
| Metrica | V2 BASE Repeat2 | V2 + L2-N |
|---|---:|---:|
| CAGR | **30.8437%** | **29.5656%** |
| MaxDD giornaliero | **−25.6896%** | **−25.6896%** |
| Sharpe | 1.086993 | 1.088671 |
| Terminal wealth (base 1) | 12.478988 | 11.380272 |
| Turnover annuo | 12.9605× | 12.6379× |

**CAGR −1.2781 punti percentuali, DD invariato, Sharpe +0.00168 (trascurabile), capitale finale −8.80%.** Attivazioni: **37/113** mesi, cap aggiuntivo vincolante sul g originale su **728 sedute**; effettiva riduzione degli investimenti dopo il rischio preesistente su **712 sedute**. 2 sole feature mancanti nel primo mese 2017, trattate come non attive secondo protocollo.

Il peggior drawdown del BASE (e del challenger) avviene dal **18 giugno al 7 ottobre 2025**. In questo intervallo **nessun cap L2-N è attivo**; dal 2025-06 a 2025-10 i Top1 mensili sono **IGV, UNG, UNG, ARGT, EPOL**. Non è un motivo per modificare retroattivamente le soglie.

Nei 37 mesi di attivazione, il log-return mensile medio dei BASE è **+2.3735%** contro **+2.0816%** della variante. In 21/37 periodi attivi con BASE positivo, il differenziale medio di log-return overlay − BASE è **−1.0095 pp/mese**; negli altri 16 periodi negativi è **+0.6500 pp/mese**. Il filtro limita alcune perdite ma taglia più opportunità rialziste: trade-off netto sfavorevole.

Bootstrap paired per date mensili, blocchi di 3 mesi, 5.000 estrazioni: delta medio log-mensile **−0.0008156**, intervallo descrittivo 95% **[−0.002170, +0.000504]** include lo zero, senza correzione multipli test e su storico già ampiamente utilizzato. **Nessuna conclusione causale prospettica**.

## Audit e riproducibilità
Secondo programma indipendente **PASS**: ricostruzione dati/flag 113 mesi, causalità `signal_date<entry_date`, esposizione addizionale MAI maggiore del baseline, verifica di 2.366 saldi giornalieri positivi, Sharpe/CAGR/DD via metodo indipendente, coeff. fee, costi/trade e delta annuali. Errore di parità del baseline ≤ `2.22e-16`. La fonte dati Yahoo è stata scaricata nel 2026: non point-in-time. Versioni e SHA256 degli input congelati nel manifest di riproducibilità.

**Pacchetto conversazionale completo** `ETF_Trader_L2N_full_v2_risk_test.zip` (11 file, ZIP integrity PASS): `l2n_full_replay.py` (sorgente standalone motore giornaliero), `l2n_independent_audit.py`, `DAILY_CAPITAL.csv`, `MONTHLY_RISK_FLAGS.csv`, `PAIRED_MONTHLY_ATTRIBUTION.csv`, `ANNUAL_OVERLAY_ATTRIBUTION.csv`, `L2N_RESULTS.json`, `INDEPENDENT_AUDIT.json`, `RUN.log`, `MANIFEST.json`, e rapporto. I prezzi originali e il pannello L2-M non sono duplicati nel pacchetto e sono recuperabili dai precedenti artefatti del progetto.

## Decisione
**NO GO**. Un indicatore semplice `high residual vol AND negative acceleration` non protegge il peggior drawdown, riduce rendimento e turnover, non produce nuovo Sharpe significativo. Tenere la V2 BASE invariata. La prossima ricerca, solo se opportuno, deve prima attribuire cause/evoluzione del drawdown 2025 già visto nel motore completo e riconciliare il 43.145952% del Golden originale, senza ottimizzare ulteriori soglie sullo storico usato.
