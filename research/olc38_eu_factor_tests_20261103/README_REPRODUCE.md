# OLC38 — istruzioni per riprodurre l'audit europeo

Prerequisiti Python 3.11+ (test eseguito su Python 3.13), `numpy`, `pandas`, `scipy`, `matplotlib`.

I due archivi originali OLC19 (159 MiB circa) e OLC32 (10 MiB circa) sono in Library, con gli SHA256 fissati nel protocollo. Il pacchetto OLC38 include anche il **solo snapshot EU necessario** come `input/OLC38_MINIMAL_EU_SOURCE.zip` (~13MB): contiene i byte *identici* dei 5 membri originali, con SHA256 individuali nel `.manifest.json`. Non è una fonte finanziaria alternativa e non certifica i prezzi.

Da un'estrazione pulita:

```bash
python src/run_olc38.py --compact-source input/OLC38_MINIMAL_EU_SOURCE.zip --out results/replay
python src/verify_olc38.py --compact-source input/OLC38_MINIMAL_EU_SOURCE.zip --results results/replay
```

Oppure con gli input originali integrali:

```bash
python src/run_olc38.py --olc19 /path/OLC19_Rischio_Rientro_Checkpoint_20261102.zip --olc32 /path/OLC32_RESULTS.zip --out results/replay
python src/verify_olc38.py --olc19 /path/OLC19_Rischio_Rientro_Checkpoint_20261102.zip --olc32 /path/OLC32_RESULTS.zip --results results/replay
```

Il controllore richiede di riprodurre il riferimento 5 fattori OLC37 e lo scorecard OLC19. I checksum del pacchetto generato sono in `MANIFEST_SHA256.json`; i risultati sono diagnostiche e NON un simulatore del capitale investibile con ordini, FX, corporate actions o fattori look-through certificati. Stati USA e `main` non coinvolti.

Per vedere rapidamente gli output: `REPORT_IT.md`, tre immagini in `figures/`, tabella `results/F1_STYLE_TRAIN_BY_YEAR.csv`, coperture `results/F2_HOLDINGS_COVERAGE_BY_YEAR.csv`, decisioni ed esiti `results/F3_SIGNAL_DECISIONS_AND_PAYOFFS.csv`.
