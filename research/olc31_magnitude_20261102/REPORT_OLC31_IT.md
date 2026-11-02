# OLC31 — Risultati della prima revisione della magnitudine economica

**2 novembre 2026 — G0/G1/G2 conclusi: esito negativo per la calibrazione lineare diretta dei raw-score.** Nessun nuovo portafoglio simulato, nessun trading, nessun aggiornamento di `main`; G3/G4 non autorizzati dal protocollo. Il protocollo maestro era stato pubblicato PRIMA dei risultati, commit `ce7b992e4ac175c3ca12c408ae842a3b74888b48`. G2 era congelato al commit `670546a828d85f9b4ce044239b38bb2573252c99`, precedentemente ai 24 fit annuali.

## Domanda verificata

Una maggiore distanza fra score grezzi dei learner e la combinazione delle previsioni C21/C42/C63 conservano informazione sulla **differenza economica reale** dei rendimenti futuri Open→Open oltre all'ordinamento attuale FUSION? Non cercavamo una nuova classifica dopo l'evento né il massimo CAGR ex-post: testavamo la capacità di stimare la magnitudine relativa in bp in EU165 e USA149.

## Audit codice e data lineage

- OLC08 salva `RETURN_RAW`, `ET_RAW`, `XGB_RAW` prima delle conversioni `rank(pct=True)`; OLC11 salva i regressori raw; OLC16 contiene `C21_ET`, `C21_XGB`, `C42_ET`, `C42_XGB`, `C63_ET`, `C63_XGB`, target maturi e calendario Open. I punteggi non sono previsioni percentuali di rendimento, perché i learner sono stati addestrati su obiettivi di rango/forza relativa.
- Tutti i cinque archivi sorgente corrispondono ai SHA256 dichiarati. 13.781 EU e 13.410 USA raw/percentili ricostruiti **esattamente**, nessuna differenza nel campo RETURN tra OLC08/16/20.
- **32 conti parent** OLC19/20 (4 controlli ×2 universi×2 politiche rischio×2 costi) identici su tutti gli array, inclusi NAV/posizioni/ledger. Parità non certifica l'eseguibilità dei prezzi.
- EU quote stato 167 strumenti inclusi due valori tecnici/cash, universo forecast165; USA149. Le scelte sono fondate sui forecast validi alla data del segnale, non sulla disponibilità dell'etichetta futura.

**Problema serio nel FULL 2020:** il 1 giugno 2020 (chiusura Xetra/Frankfurt per Whit Monday) nel file europeo solo 11/167 strumenti risultano osservati; due mensilità hanno appena 9/148 etichette Open→Open valide. Il backtest storico legacy continua a riprodursi ma non valida come eseguibili le aperture sintetiche/non osservate. È una criticità di fonte/contratto, distinta dalla qualità del modello. Nel 2021–2024 le aperture originali sono valide per 7.302/7.304 casi EU e i prezzi preparati USA per 7.152/7.152; due osservazioni LEEU.DE nel 2024 hanno quote mancanti. USA resta priva di maschera originale delle quotazioni osservate. 2026-06-30 è una riga terminale senza futuro.

## G1 — informazione descrittiva nei score grezzi

2021–2024, 48 segnali per mercato. Pearson medio entro il Top5 AUTH con il prossimo rendimento lordo Open→Open:

| Source score | EU165 | USA149 |
|---|---:|---:|
| FUSION | +0,0368 | +0,1394 |
| RETURN_RAW | −0,0921 | −0,0250 |
| ET_RAW | −0,0672 | +0,2089 |
| XGB_RAW | +0,0693 | +0,1585 |
| C63_ET | +0,0441 | +0,2117 |

Alcuni raw score sembrano informativi in un mercato ma non nell'altro. Differenza XGB_RAW-FUSION +0,0325 EU e +0,0191 USA: intervalli descrittivi 95% a blocchi 6 mesi EU [−0,164;+0,237], USA [−0,113;+0,141]. C63_ET-FUSION EU +0,0073 [-0,201;+0,217], USA +0,0723 [−0,139;+0,254]. Null shuffle per data/ticker (seed 31001..31005) conservati. **Nessuna evidenza di informazione economica univocamente dominante**; G1 da solo non giustifica modifiche al Top2. Top1-versus-Top2 usa solo 48 differenziali per mercato, non indipendenti fra ETF.

## G2 — test prequential calibrato su identico supporto

- Un unico `Ridge(alpha=10)` condiviso fra EU/USA con StandardScaler train-only, market weight 50/50 e peso eguale ai mesi. Fit expanding 2021–2026; label mature solo se `next_entry_open_date < 1 gennaio anno`; training con mesi 2020 troppo incompleti esclusi **per contratto di qualità preregistrato**.
- `B1`: FUSION soltanto; `B2`: FUSION più nove raw score originali. Due target separati: rendimento log assoluto Open→Open e rendimento log relativo al futuro mediano del medesimo mercato/mese (quest'ultimo è **soltanto il label**). Nessun fit dei learner ETF originari, nessun target casuale e nessuna ottimizzazione CAGR.
- 24 fit annui totali (6 anni ×2 candidati ×2 target), 19.662 previsioni storiche prequential valutabili (7.189 EU e 7.152 USA nel periodo 2021–2024, medesimo supporto per B1/B2). Le restanti 113 etichette EU originali nel 2021–24 senza tutte le raw feature sono escluse **da entrambi i modelli**, non solo da B2.

### Risultato principale (2021–2024)

| Mercato | RMSE relativo B1 → B2 | MAE relativo B1 → B2 | Differenza MSE (B1-B2) |
|---|---:|---:|---:|
| EU165 | 302,54 → **308,61 bp** | 216,21 → **221,00 bp** | **−3.712 bp²** |
| USA149 | 468,97 → **470,40 bp** | 319,53 → **320,15 bp** | **−1.341 bp²** |

**Segno negativo della differenza MSE significa che B2 è peggiore**, non un vantaggio. Anche sull'assoluto B2 peggiora (EU RMSE 478,34→481,10 bp; USA 578,12→581,01 bp). Nel sottogruppo Top5, MSE relativa B1→B2: EU 273.433→297.793 bp², USA 599.057→606.665 bp².

Block bootstrap 6 mesi, 4.000 estrazioni descrittive, differenza MSE relativa B1-B2: EU −3.712 bp², IC95% [−8.422;+582]; USA −1.341, IC [−2.821;+116]. Gli IC comprendono zero: non dimostrano beneficio robusto né sono probabilità posteriori. Il risultato resta sfavorevole nella differenza puntuale per entrambi i paesi. Nessun indice qui corregge la sequenza di tutti gli OLC test precedenti.

Anni 2021–2024: per l'errore quadratico relativo EU B2 peggiora 2021/2022/2023 e migliora marginalmente 2024; USA peggiora in tutti e quattro gli anni. Nel 2025/2026 parziale gli esiti sono misti, non una nuova convalida pulita.

## Collaudo e revisione avversaria

- 5 test unitari del contratto matematico G0: tutti superati.
- 5 test integrati G2: maturity cutoffs, market balance 50/50, perturbazione di label future senza cambiare fit precedenti, invarianza a riordino delle righe, supporto B1/B2 e ricostruzione indipendente delle MSE dai file OOF: **superati**. Un test conteggio inizialmente aveva una soglia arbitraria >20.000 righe ed è stato correttamente sostituito dalla riconciliazione con l'audit dei supporti (conteggio effettivo 19.662). Un errore iniziale di bootstrap dovuto a segnali EU/USA di maggio 2021 su giorni diversi è stato corretto allineando per *mese di calendario* comune; le 48 osservazioni di ciascun mercato non sono cambiate.
- Nessuna pretesa di audit esterno indipendente; si tratta di test e verifiche interne dell'artefatto storico.

## Interpretazione, ipotesi falsificate e decisione

La formula `rank(pct=True)` cancella matematicamente le distanze dei raw score, ma i raw score **non sono già stimatori calibrati di rendimento economico**: imparano prevalentemente ranghi futuri e cambiano scala tra modelli e anni. G1 ha trovato segnali deboli e disomogenei; il test B2 completo e non ritoccato ha peggiorato l'errore economico in entrambi gli universi, anche nel Top5. **Il protocollo blocca G3 (sostituzioni) e G4 (replay)**: nessuna ragione empirica sufficiente per alterare l'operatività.

Questo esito **non dimostra** che la magnitudine sia irrilevante in generale. Restringe la conclusione al test di calibrazione lineare dei raw score del modello esistente. Possibili programmi successivi, solo in NUOVI lotti dopo registrazione: un modello realmente addestrato su ritorno Open→Open e vantaggio differenziale; confronto distribuzionale dell'evento `large economic edge` e intensità *condizionata*, modello di retention/permanenza con controllo anti-veto OLC23, nuovi dati point-in-time e validazione in avanti. Prima di nuovi learner occorre una revisione della qualità dati e dei target, compreso il calendario multi-borsa e le quote USA osservate.

**Stato:** chiusi G0, G1, G2; chiusura negativa del challenger B2. Non avviati G3/G4, nessuna promozione, nessuna modifica a `main`, nessuna operazione di trading. Tutto lo storico 2019–2026 è già più volte esplorato e nessuna finestra è un vero holdout nuovo.

## Fonti, riproducibilità e file

- `PROTOCOLLO_MAESTRO_IT.md` congelato su GitHub branch `research/olc31-economic-magnitude-20261102` prima dei test; checkpoint G0 e pre-G1/G2 con commit distinti.
- `g0_source_parity.py`, `g1_raw_gap_diagnostics.py`, `g1_uncertainty.py`, `g2_prequential_calibration.py`, test, 00–14 output numerici e log.
- Sorgenti GitHub congelate: OLC08 `train_pack.py`, OLC11 `train.py`, OLC12 `integration.py`, OLC16/20 `score_validation.py`, OLC19 motore V6/risiko, con manifest SHA256 e mapping registrato.
- Calendario ufficiale 2020 Xetra/Francoforte: https://xontro.de/sites/data/media/documents/Newsletter/XONTRO_KI_englisch/Floor_KI_2020_97_M_72_Feiertage_e.pdf
- Riferimento metodologia test multipli: Hansen, Superior Predictive Ability (2005); scikit-learn `TimeSeriesSplit`, purging delle label e rigoroso cutoff per anni.
