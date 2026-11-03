# ETF — E1/E2 ampliamento settoriale EU165 e USA149

**Ricerca in ramo isolato. Nessuna modifica a `Etf_trader` o a `main`.**

- [E1 — Opportunità massima ex-post con 5 nuovi UCITS e 3 USA](./RESULTS_IT.md) — non è un CAGR di strategia.
- [E2 — CAGR economico simulato con 4 nuovi UCITS e 3 USA](./RESULTS_E2_CAGR_IT.md) — test di due semplici regole *causali* a momentum, senza rifit del ranking OLC19. Il CAGR EU **peggiora**, quindi nessuna promozione.
- [Tabella completa di CAGR, MaxDD, costi e turnover](./E2_SCORECARD.csv); [tutti i periodi](./scorecard_all_periods.csv); [rendimenti annuali](./annual_returns.csv).
- [Codice exact-book replay E2](./run_olc19_expansion_replay.py); [decisioni di acquisto](./new_sector_decisions.csv); [analisi rischio degli switch](./switch_relative_forward_monthly.csv); [qualità prezzi](./price_quality.csv); [manifest SHA256](./E2_MANIFEST.json); [bootstrap appaiato](./PAIRED_BLOCK21_BOOTSTRAP.csv).

## Come ripetere E2 (dati originali non pubblicati nel repo)

Servono gli archivi delle quote esatte usate:
1. `OLC19_Rischio_Rientro_Checkpoint_20261102.zip` dalla Library ETF_Research (165.7 MB). Non sostituire con un checkpoint diverso.
2. `ETF_sector_daily_OHLC_GH.zip`, artifact scaricabile dal [run GitHub Actions 41724810594](https://github.com/AM1975MA/Test/actions/runs/41724810594), con gli adjusted OHLC giornalieri scaricati nel 2026.
3. Ambiente `python>=3.11`, `numpy`, `pandas`.

**Estrarre** lo ZIP OLC19 in una cartella temporanea, così da avere `<extract>/olc19_combined_risk_20261102/src/combined_engine.py` e l'intero albero sottostante. Impostare le variabili di ambiente `OLC19_CHECKPOINT_ZIP` al file zip originale, `E1_PRICE_ARTIFACT` allo zip E1, `OLC19_SOURCE_ROOT` a `<extract>/olc19_combined_risk_20261102` e `E2_OUTPUT_DIR` alla directory di output desiderata. Eseguire:

```bash
python research/sector_opportunity_e1_20261103/run_olc19_expansion_replay.py
```

Il programma verifica la perfetta parità numerica con il `NAV` originale OLC19 per l'esecuzione base e calcola `CAGR` dal modulo OLC19 ufficiale. La verifica esterna di tutte le sei matrici originali è stata condotta nel run locale: NAV, ledger, quantità ETF, quantità difensive, liquidità e target **esattamente uguali** agli archivi.

### Vincoli

- I nuovi ETF NON ricevono score V2/V3/OLC19 originale; le regole MOM63 e MOM63+126 sono *shadow challengers*, non ranking nativo riaddestrato.
- `CMOD.MI` scartato dal motore con stop per **539/2400 barre OHLC incoerenti**. E1 Open-only lo comprendeva perché valutava un fenomeno diverso.
- L'input storico corretto include azioni societarie rettificate ex-post e un universo di fondi selezionati nel 2026. Il 2021–2024 NON è un holdout vergine e non fornisce prova prospettica.

**Conclusione:** più temi = maggiori opportunità ex-post; due scorciatoie basate sul momentum = CAGR più basso. L'estensione nativa richiede rifit dell'intera pipeline originale, nuovi ETF inclusi solo quando eleggibili as-of.
