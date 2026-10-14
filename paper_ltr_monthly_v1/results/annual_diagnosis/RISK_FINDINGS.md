# Diagnosi rischio LINEAR annuale, 2021 e 2023

Analisi degli artefatti salvati; nessun nuovo fit o replay economico. Repository: esclusivamente AM1975MA/Test. I risultati seguenti sono descrittivi, non attribuzioni causali.

## Quale gestione rischio era realmente attiva

Il replay verificato `holdout70/v2_canonical_same_source_compare.py:205` usa il Top2 con allocazione continua. `producer.allocations_from_score` (`vendor/etf_trader_v2/src/etf_trader/ma3/producer.py:239`) imposta peso Top1 `0.60+0.40*min(margin/0.13,1)^2`; non applica un router Opportunity. `confidence_weights` (`vendor/p45/v2_stage19_kernel.py:91`) puo portare Top1 al 100% con margine >=0.03, condizionato da stato rischio e accordo ET/XGB.

Il DD-first sistemico e presente, ma trasformato: `risk_gross_transform` (`vendor/p45/v2_stage19_kernel.py:83`) rimappa 0.95 a 1.00, 0.75 a 0.945 e lo stato severo 0.25 a 0.66 (`highcagr24.py:7`). Non e un limite garantito al drawdown di portafoglio. `simulate_arch` (`vendor/p45/v2_stage19_kernel.py:160`) aggiunge riduzione al 25% su gap sistemico, cooldown di tre sedute, stop 5.5% condizionale con slippage 0.1%, costi 0.1%, residuo BIL/SHV e possibile alternativa V6.

**Precisazione Opportunity:** questo benchmark canonico non attiva ne il router Opportunity a cluster, ne il separato `opportunity_cap`. La catena Titanium effettiva (`vendor/etf_trader_v2/scripts/build_tit_r_source_only.py:42-53`) costruisce Compact, Tail, Macro, extra; chiama `models.fit_predict` (`models.py:138`) e `variants()['baseline']` (`models.py:228`), che combina 70/30 Compact/Tail e bonus Macro. Il router nel diverso percorso `source_only/kernel.py:432,529` non viene chiamato. Lo score finale (`v2_stage19_kernel.py:31`) combina BASE e ET/XGB smussati. Nel replay `G` e soltanto `g` (`v2_canonical_same_source_compare.py:232`); non esiste chiamata a `opportunity_cap` o `shock_caps`. BASE e LINEAR condividono questa identica ricetta. I numeri verificati non cambiano, ma la precedente descrizione «tutti i layer, incluso Opportunity» era troppo ampia.

## Evidenze archiviate e limiti

Nei sei NPZ annuali candidate/baseline_control sono salvati esclusivamente `dates,equity,turnover,d1,d2,weight1,margin,alt_idx` (`v2_canonical_same_source_compare.py:246`). Possiamo ricostruire rendimento netto, differenze di target/pesi, concentrazione e turnover. Non sono salvati `X` (gross effettivo), `AW` (peso alternativa), posizioni effettive, trigger gap, stop, cooldown o costo separato. `DAILY_LEADERS.csv` contiene target, non inventario effettivo dopo gli stop. Non si puo separare esattamente selezione e gestione rischio con questi soli file.

Nel 2021 rendimento LINEAR r1/r2/r3: +7.0154%, -4.8597%, +3.3561%; nel 2023: +2.0544%, +5.8560%, +8.5194%. Giorni con peso target Top1=100%: 2021 8.73%/17.06%/17.06%; 2023 9.20%/24.80%/24.80%. `alt_idx>=0` e assente in entrambi gli anni, in tutti i sei percorsi: l'alternativa V6 non puo spiegare il divario di questi anni. Le quote non misurano l'esposizione effettiva dopo stop/gap.

## Confronto controllato concordato con esperto ML

Singola variante annuale LINEAR allenata su **tutto** il training maturo al cutoff, mantenendo feature, loss, L2, solver, decili, anni e tre download invariati. Preprocessing sullo stesso training completo; nessun tuning su 2021/2023. Valutare tutti gli anni 2017-2026 e i gate originali, riportando anche gli anni peggiorati. Ipotesi: l'esclusione permanente del 10% finale causa un ritardo evitabile; il miglioramento resta da verificare. Non eseguito in questa diagnosi.

Prima o contestualmente e fattibile un replay strumentato senza fit, con parita esatta di equity/turnover preesistente e log di esposizioni, posizioni e trigger. I tre raw congelati specifici non risultano presenti localmente; la workflow li recupera dall'artefatto `yfinance-repeatability-v1-raw`, run 37121749852. Servono quegli stessi raw con verifica degli hash INPUT_LINKAGE e runtime congelato. La fattibilita e tecnica; nessuna stima di durata e verificata e nessun nuovo download o replay e stato avviato.
