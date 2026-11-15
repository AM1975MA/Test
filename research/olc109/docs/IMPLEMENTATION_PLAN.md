# OLC109 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eseguire e validare110 confronti congelati per gruppi causali di ETF, pesi e protezione.

**Architecture:** Pannello V3 immutabile, engine contabile compatibile con guardie sell-only, nuovi segnali indipendenti, runner deterministico. Revisore distinto ricostruisce tutti i conti e controlla segnali/fonti.

**Tech Stack:** Python3.12, numpy, pandas, scipy, matplotlib; nessun nuovo pacchetto richiesto.

**Spec:** docs/DESIGN_AND_PROTOCOL.md

## Global Constraints

- 22configurazioni×5scenari, nessuna ottimizzazione dei parametri dopo i risultati.
- Input SHA14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96.
- Proteggere OLC108 e automazioni/repository remoto; nuovo lavoro solamente olc109.
- Output persistenti: rapporto, grafico, codice, dati necessari, registri e audit.

## Review Focus

- Dati futuri alterati non devono modificare alcuna scelta passata: test prefix dei segnali.
- Duplicati quasi identici non devono occupare due posti: test gruppi e correlazione rappresentanti.
- Riduzioni con gap/ritardi/Open mancante devono restare sell-only: test engine.
- Cash/commissioni devono riconciliarsi indipendentemente, con tutte le fallite incluse: audit110.
- Pochi gruppi/varianza nulla/mancanza liquidità devono produrre cassa senza valori non finiti: test segnali.

### Task1: Input e segnali

**Files:** src/cluster_selectors.py,src/prepare_liquidity.py,tests/test_cluster_selectors.py,data/LIQUIDITY.npz.
**Interfaces:** prepare_features(panel,legacy,turnover)→dict; build_snapshot(panel,f,k)→dict; make_policy(panel,f,snapshots,arm)→policy(k,current_weights); make_guard(f,kind)→guard(k,current_weights).

- [ ] Scrivere ed eseguire test causali e invarianti prima del codice.
- [ ] Copiare panel e core congelati; derivare turnover con manifest.
- [ ] Implementare gruppi, statistiche, ordinamenti, selettori e pesi esattamente dal protocollo.
- [ ] Test e hash input; nessuna ricerca dei rendimenti prima del freeze.

### Task2: Protezione nell'engine

**Files:** src/engine.py,tests/test_guard_engine.py; implementatore separato.
**Interfaces:** simulate(...,guard_policy=None,guard_mask=None); None non emette istruzione; TREND_REDUCE sell-only e immutabile.

- [ ] Test prima del cambiamento: tempi, mask, precedenza mensile, gap, missingOpen, aggiunte rifiutate.
- [ ] Implementare guardia; suite baseline invariata.

### Task3: Esecuzione e controlli

**Files:** src/run_research.py,results/RUN_MANIFEST.json,results/SCORECARD.csv.
**Interfaces:** Riutilizzare daily/orders/instructions/decisions e metriche del core.

- [ ] Congelare hash protocollo/codice finanziario/input prima del primo run.
- [ ] Eseguire tutti110 percorsi e rendimenti annuali; salvare anche risultati negativi.
- [ ] Confrontare baseline con OLC108; audit indipendente completo e controlli di fonte mirati.

### Task4: Interpretazione e consegna

**Files:** analysis/analyze_results.py,RAPPORTO_OLC109_IT.md,figures,README_IT.md,manifest e archivio.

- [ ] Calcolare confronti controllati, bootstrap primario e segmenti, senza scegliere un vincitore retrospettivo come validato.
- [ ] Revisione distinta di codice e interpretazione; risolvere errori materiali e rieseguire soltanto ciò che cambia.
- [ ] Generare e verificare figura/rapporto, pacchetto riproducibile e salvataggio dei deliverable.
