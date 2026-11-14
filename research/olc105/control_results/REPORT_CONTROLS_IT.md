# OLC105 — Risultati dei controlli, NON risultati OLC19/OLC67

**Completamento parziale: World e momentum eseguiti; i quattro bracci ML restano bloccati.**

Finestra: apertura 2020-03-02 → chiusura 2026-11-13; novembre parziale. 81 segnali mensili eleggibili. Scenario illustrativo EUR 10.000, EUR 1 per ordine e shortfall ipotetico 15 bp per lato.

| Controllo | CAGR calendario | Cumulato | MaxDD chiusure | Ordini | Costi simulati |
|---|---:|---:|---:|---:|---:|
| WORLD_PASSIVE | 14.54% | 148.39% | -24.68% | 1 | EUR 15.98 |
| MOM252_TOP2_HALF_IMMEDIATE | 15.29% | 159.50% | -24.09% | 204 | EUR 1309.05 |

## Definizioni e limiti
- World fisso: ISIN IE00BFY0GT14, scelto prima degli outcome, acquisto alla prima apertura eleggibile e mantenimento.
- MOM252: due maggiori rendimenti a 252 osservazioni precedenti, 50/50, ribilanciamento mensile alla prima apertura successiva. Nessun apprendimento, V6 o FAST_LOCK3: solo controllo semplice.
- Universo: i 29 ISIN congelati, con le fonti alternative dello stesso ISIN già preregistrate. Le sei serie settoriali sono tagliate prima del 3 maggio 2016. Nessun fondo aggiunto dopo gli outcome.
- Elegibilità: 252 rendimenti richiedono 253 osservazioni; ultima quota al massimo cinque giorni prima del segnale, almeno 12 fondi e tutti i sei macro-gruppi presenti. Il controllo World ha la stessa partenza.
- Contabilità con unita economiche frazionarie su OHLC rettificate per total return Yahoo: NON quote intere né fill reali Trade Republic. Le distribuzioni sono incorporate nei prezzi rettificati, non accrediti cash broker.
- Commissioni e shortfall sono detratti dal capitale disponibile, per ogni strumento effettivamente comprato/venduto. I 5/15/30 bp non sono spread osservati. Cash non remunerato, fiscalita esclusa.
- Nessuna esecuzione su Open mancante: il ribilanciamento viene rinviato, non riempito usando prezzi inventati. Il Close precedente è usato soltanto per valorizzare posizioni durante assenza di quota.
- I flag OHLC rimangono invariati e non servono a scegliere i vincitori. Questa prova non usa i Low per simulare stop; non certifica le barre.
- Si tratta di uno studio retrospettivo su nuovi fondi, non di mercati o periodi indipendenti e non di una previsione dei rendimenti futuri.

## Stato del test richiesto
Non è lecito confrontare queste due curve con i CAGR OLC19/OLC67 dei vecchi universi e concludere che il ML funzioni o fallisca. Il test ANCHORED_TRANSFER non è stato eseguito: i modelli binari originali non sono stati trasportati al runner.
Sono state censite 1.287 registrazioni di artifact e verificato lo snapshot pubblico dei sorgenti, ma ciò non sostituisce gli archivi congelati della Library. Nessun dato mancante è stato inventato.

## Verifiche
{
  "status": "PASS_DECLARED_CONTROLS_ONLY_NATIVE_ML_BLOCKED",
  "run_id": "43634911150",
  "code_commit": "af81bd067ff1cc7d59b9fb1cb4cbb69dfa549b01",
  "captured_input_checksums": 148,
  "candidate_funds": 29,
  "monthly_decisions": 81,
  "replays": 38,
  "metric_rows": 76,
  "max_self_financing_error_eur": 2.9103830456733704e-11,
  "max_independent_metric_error": 0.0,
  "fractional_adjusted_economic_units": true,
  "whole_share_broker_simulation": false,
  "V6_or_FAST_LOCK3_applied": false,
  "TradeRepublic_actual_quotes_used": false,
  "personal_taxes_included": false,
  "raw_sources_unchanged": true,
  "asof_cutoff": "2026-11-13",
  "prospective": false,
  "generated_at_utc": "2026-11-14T19:58:15.010433+00:00"
}

File: CONTROL_SCORECARD.csv, CONTROL_DAILY.csv.gz, CONTROL_ORDERS.csv.gz, MOMENTUM_SIGNALS.csv, ASOF_ELIGIBILITY.csv, FROZEN_INSTRUMENT_QA.csv, NATIVE_ML_GATE.json. Nessuna modifica a main o alle automazioni.
