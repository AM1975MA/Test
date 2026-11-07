# OLC62 — Test preregistrato della rappresentazione temporale prima del ranking

**Data: 2026-11-07. Prima di qualsiasi outcome OLC62.** Ricerca retrospettiva, non nuovo holdout. Nessuna modifica ad OLC19, main o modello di produzione. Nessuna ricerca di nuove fonti. Non usare i risultati per scegliere una soglia o variare iperparametri in questo lotto.

## Ipotesi falsificabile
Le 42 feature OLC14 sono percentili cross-sectional istantanei. La differenza temporale di tali percentili, calcolata prima del segnale, può contenere informazione aggiuntiva per selezionare le migliori due opportunità a 21 sedute, non già contenuta in uno snapshot singolo.

## Input immutabili
- OLC14 Heads checkpoint SHA256: a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458.
- OLC14 Results checkpoint SHA256: 4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1.
- OLC61 predictions congelate `OLC61_PREDICTIONS.csv.gz`, input per confronti. Parent `run_olc61.py`, modello statico ECON21. Verifica SHA di riferimento e parità delle chiavi, features e score originali, label, supporto.

## Bracci fissi, nessuna ricerca di griglie
1. `B0_FUSION_CONTEXT`: score preesistente originale; controllo severo.
2. `B0_NATIVE`: score OLC14 statico originale.
3. `OLC61_ECON21`: learning-to-rank da 42 feature snapshot con label economiche, già congelato; controllo di rappresentazione a parità di target e learner.
4. **`OLC62_TRAJECTORY42`**: stesso learner LightGBM e identico target/iperparametri di `OLC61_ECON21`, ma ingresso con 42 feature native + loro variazioni tra t e t-1 mese e t e t-3 mesi (totale 126 dimensioni). Nessun altro input, nessuna identità ticker o ETF, nessuna informazione di FUSION nel nuovo learner.

### Temporalità e train
- Per ciascun anno 2021–2025 e ciascun mercato, training cronologico expanding su sole etichette 63 sedute mature per **intero gruppo** prima del 1 gennaio anno fit. Nessun futuro come feature o per filtrare l'eligibility dei dati di predizione.
- Lag t-1 e t-3 per `signal_date` *mese di calendario esatto*, per ticker: sono NaN se non esistono quote e feature di quel mese. Per il lag dei segnali vicini al cutoff utilizzare XP dell'anno precedente come storia senza label, essendo già osservato alla data del segnale. Variazione = valore feature ranking corrente minus ranking precedente; NaN preservati. Assenza passata non filtrata dal futuro; stesso supporto di OLC61.
- LightGBM LambdaRank 180 alberi, num_leaves7, min_child_samples80, learning_rate.04, reg_lambda10, bin127, truncation10, label_gains[0,1,3,7,15,31], seed611, n_jobs2, impostazioni restanti identiche a OLC61 `ECON21`. Nessun retuning.

## Valutazione
- MAIN 2021–2024: rendimento medio statico Top2 21 e 42 sedute, percentuale future-top-quintile a21, persistenza simultanea nei quintili di 21/42, ampiezza `g1_bp`, differenza rispetto a FUSION e OLC61_ECON21 in 48 eventi appaiati per mercato. 2025 solo diagnostico, già mined. Pesi 50/50 con ties identici a OLC61. Nessun CAGR nuovo, nessun portafoglio eseguito.
- Bootstrap descrittivo circolare a blocchi 6 mesi (4000 iterazioni, seed 6201), incertezza sulla differenza tra medie mensili r21; non corregge il data mining pregresso.
- Analisi diagnostica FIXED: dei primi 10 score FUSION, quota delle future Top2 reali già presente; correlazione per data fra rank-velocity `ret_21_rank` e futuro `g1_bp` sull'universo; la stessa diagnostica per `eff_63_rank` e `cluster_breadth63_rank`. Segnalare numero osservazioni, stabilità dei rank e missing. Non selezionare uno di questi indicatori ex post per un trading rule.

## Go / No-Go
Promuovere a fase successiva (non produzione) **solo** se r21 medio di TRAJECTORY42 batte SIA FUSION SIA OLC61_ECON21 in EU e USA MAIN, mantenendo r42 e persistenza almeno pari a FUSION in entrambi, senza difetti causali. Altrimenti NO PROMOTION e non moltiplicare i parametri. 2019–2026 già esplorato, risultati in-sample di ricerca pur con fit cronologici.

## QA immutabile
Parità 42 feature snapshot, lags effettivamente in passato, nessun collisione ticker/mese, nessuna mutazione di OLC14/O19, etichette mature, training & prediction same-event eligibility, CSV e model reload, peso selezioni =1, checksum di output e verifica indipendente aggregazioni mensili. Registrare qualsiasi modifica al protocollo, soprattutto dopo aver visto i risultati.