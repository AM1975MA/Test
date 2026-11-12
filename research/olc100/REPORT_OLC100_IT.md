# OLC100 — Report di esecuzione e stato del forward test

**12 novembre 2026 — Research only. Decisione: INTEGRAZIONE VERIFICATA; TEST DI ALPHA PROSPETTICO NON AVVIATO.**

## Risultato operativo

- **48 replay nativi eseguiti**: 6 bracci congelati × 2 mercati × 2 livelli di fee (0,001; 0,003) × 2 frizioni stop (0,001; 0,005). Simulatore originale OLC19; nessuna modifica ai layer, nessuna selezione a posteriori.
- **4 controlli di parità OLC19** (due mercati × baseline e selezione originale) con le **sette matrici contabili bitwise identiche** a fonte congelata. Le quattro architetture di OLC67 con stesso contratto, fee e timing coincidono nelle metriche FULL, incluse minvar e delay.
- **180 pesi MINVAR63** ricalcolati da Close e maschere osservabili disponibili prima del segnale, esattamente coerenti con OLC56; max differenza numerica 5.55e-17.
- **Tutti i 7 test** dello schema packet prospettico passano. L'esecuzione senza un pacchetto preregistrato restituisce correttamente BLOCCATO, non un risultato fittizio.

## 1. Replay storico 2019–luglio 2026 (NON OOS)

Costi di base (fee 0,001, frizione stop 0,001):

| market   | arm         |   CAGR % |   MaxDD % |
|:---------|:------------|---------:|----------:|
| EU       | B_BASE      |    19.76 |    -28.61 |
| EU       | C_CANDIDATE |    22.61 |    -26.59 |
| USA      | B_BASE      |    39.48 |    -26.12 |
| USA      | C_CANDIDATE |    42.1  |    -27.6  |

Confronto dei soli controlli a fee 0,003 e frizione stop 0,005:

| market   | arm         |   CAGR % |   MaxDD % |
|:---------|:------------|---------:|----------:|
| EU       | B_BASE      |    15.37 |    -30.9  |
| EU       | C_CANDIDATE |    18    |    -30.71 |
| USA      | B_BASE      |    28.65 |    -28.94 |
| USA      | C_CANDIDATE |    31.43 |    -30.4  |

Lo scorecard integrale contiene tutti i 48 replay e tutti i controlli diagnostici; i drawdown sono su tutto il percorso, non misure sulla coppia sola. **Non usare differenze di CAGR di esperimenti disallineati come stime di contributo causale di un layer**: qui ogni confronto è calcolato nel medesimo simulatore, calendario e set input.

### Contrasti per componente

Differenza di log-rendimento annualizzato su 90 mesi. Gli intervalli sono bootstrap descrittivi a blocchi da sei mesi, 3.000 estrazioni, seed 100112, senza correzione per i molteplici test precedenti.

| market   | contrast                            |   annual_log_pp |   bootstrap95_lo_log_pp |   bootstrap95_hi_log_pp |
|:---------|:------------------------------------|----------------:|------------------------:|------------------------:|
| EU       | TOP2_CONTEXT_vs_ORIGINAL            |            2.82 |                   -1.33 |                    6.63 |
| EU       | ALLOCATION_MINVAR_vs_HALF_IMMEDIATE |            0.89 |                   -2.51 |                    4.57 |
| EU       | TIMING_DELAY3_vs_IMMEDIATE_HALF     |            1.89 |                   -0.7  |                    4.67 |
| EU       | PROTECTION_FASTLOCK3_vs_BASE        |            0.04 |                   -3.9  |                    4.17 |
| EU       | INTEGRATED_CANDIDATE_vs_BASE        |            2.35 |                   -2.05 |                    6.82 |
| USA      | TOP2_CONTEXT_vs_ORIGINAL            |            3.37 |                   -8.75 |                   13.33 |
| USA      | ALLOCATION_MINVAR_vs_HALF_IMMEDIATE |           -0.36 |                   -3.88 |                    3.17 |
| USA      | TIMING_DELAY3_vs_IMMEDIATE_HALF     |            2.63 |                   -5.09 |                   11.36 |
| USA      | PROTECTION_FASTLOCK3_vs_BASE        |           -2.86 |                   -8.55 |                    2.25 |
| USA      | INTEGRATED_CANDIDATE_vs_BASE        |            1.83 |                   -6.17 |                   10.54 |

Su **entrambi** i mercati l'intervallo storico descrittivo del confronto integrato OLC67–OLC19 comprende lo zero. Non è un test prospettico e **non sostiene una promozione**. Il rischio di overfitting selettivo rimane elevato dopo OLC01–99.

## 2. Audit di nuovi dati prezzi USA

Il pacchetto `V3_149_FORWARD_20261024.zip` è stato recuperato dall'artefatto GitHub Action [40082539622](https://github.com/AM1975MA/Test/actions/runs/40082539622); SHA256 `29d63efc647f113d6fb1aa9ade57983a711e78bb3b375d556fdcb340504f2be2`.

- **149/149** ticker corrispondenti alle colonne dell'input nativo USA OLC19; 80 sedute aggiuntive complete da **2 luglio a 23 ottobre 2026**; **11.920 righe** OHLCV, nessuna anomalia OHLC nel controllo automatico.
- L'anchor Open OLC19 a 1 luglio 2026 coincide entro 1 bp per 146 ticker. Tre ticker (**BKLN, DIA, SPLV**) presentano livelli rettificati differenti, da ricondurre agli aggiustamenti del provider, **non** da eliminare o riscrivere.
- Usando **solo un fattore di scala per ticker definito sull'anchor**, la massima variazione di quel rapporto negli 8 giorni precedenti è 0.0000320%: sufficiente per dichiarare compatibile il tratto di prezzo per un'analisi esplorativa, **non** per certificare retroattivamente corporate action, total-return e fill broker.
- I dati provengono dalla pipeline *V3 Corrected*, **non dall'OLC19 operativo**: non possiamo sostituire Return125, Hybrid42, memoria e TOP2_CONTEXT_REVALUE con score V3 diversi.

### Unico segnale 30 giugno verificabile: diagnostica dei prezzi, non NAV

Per il Top2 USA OLC19 originale 30 giugno, **PPLT/PALL**, l'Open 1 luglio→3 agosto dà rendimenti lordi statici **2.095% / 2.730%**. La coppia 50/50 produce **2.412%** contro **2.314%** con il peso minvar congelato **0.655077** (differenza **-0.098 punti percentuali**). Sono solo prezzi ETF, senza V6, DELAY3, stop o commissioni: non validano alcuna delle sei strategie intere.

## 3. Perché non abbiamo ancora il CAGR OLC100 luglio–ottobre

1. **EU:** non è disponibile nel materiale collegato un'estensione coerente delle 167 colonne quotazioni native (165 universo/ausiliari), osservabilità e calendario fino al 23 ottobre.
2. **EU/USA:** non sono stati prodotti, con codice e modelli congelati, i successivi score originali Return125/ET/XGB e le coppie Top2 per ogni mese.
3. **V6:** non esiste l'estensione certificata dei budget espositivi, osservabilità e stati di protezione derivati dai nuovi input.
4. Non esiste una **ricevuta esterna pre-outcome** dei futuri segnali post-12 novembre per una valutazione prospective autentica.

**Decisione:** sorgente prezzi USA = VALIDATA ENTRO LO SCOPO; replay OLC100 luglio–ottobre = BLOCCATO PER DATI/SEGNALI MANCANTI; promozione live = NON AUTORIZZATA. Un programma che ricicli Top2 di giugno o carichi i rendimenti successivi come feature non è una validazione e viene rifiutato.

## 4. Percorso di ripresa, senza re-ottimizzare

**Gate A — Dati:** reperire snapshot OHLCV EU e USA completi con orari, quote osservate, adjusted/total return, corporate action, membership point-in-time. Non modificare le righe native congelate.

**Gate B — Predittore:** ricostruire la produzione di Return125, ET/XGB Hybrid42, memoria 40/30/30, FUSION 47,5/52,5 e TOP2_CONTEXT_REVALUE con source/versioni originali, e dimostrare parità nei mesi congelati 2026 prima di estendere lo storico. Se i checkpoint non consentono una ricostruzione esatta, marcare esplicitamente `RECONSTRUCTION_NOT_EQUIVALENT`.

**Gate C — Account:** prolungare V6 e OLC19 FAST_LOCK3, più i sei bracci predefiniti, con stessa contabilità, mask di quotazioni e costi. Calcolare causal contrasts a coppia e stato uguali e replay integrali on-policy separati.

**Gate D — Prospettico:** il prossimo segnale mensile successivo al freeze (atteso a fine novembre 2026) va firmato con snapshot e acquisito su GitHub **prima della prima apertura negoziabile**. La verifica locale di coerenza non attesta da sola il tempo; serve timestamp GitHub server e SHA immutabile verificati separatamente, poi solo outcome maturi. I controlli a 12/24/36 mesi sono preregistrati, non interruzioni per ottimizzare sul risultato.

## Materiali riproducibili

- `run_olc100_controls.py`: 48 replay nativi, QA e contrasti con intervalli descrittivi.
- `audit_olc100_bridge_prices.py`: verifica USA 149 ticker, anchor/overlap e un test di prezzi della coppia originale.
- `validate_olc100_forward_packet.py` e `test_olc100_packet.py`: contratto prospettico e 7 test automatici anti-leakage.
- `results/OLC100_QA.json`, `results/OLC100_BRIDGE_SOURCE_QA.json`, `results/OLC100_HISTORICAL_SCORECARD.csv`, `results/OLC100_LAYER_CONTRASTS.csv`, `results/OLC100_USA_PRICE_BRIDGE_DIAGNOSTICS.csv`.

**Non sono stati modificati GitHub main, i checkpoint congelati o alcuna strategia live.**
