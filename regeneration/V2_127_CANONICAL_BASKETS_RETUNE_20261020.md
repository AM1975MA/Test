# ETF Trader V2 | 127 foglie | panieri originali e ritaratura dei layer — 20 ottobre 2026

## Certificazione panieri: PARITY PASS

Confronto diretto, fonte primaria `AM1975MA/Etf_trader:data/SUPER_GOLD_BASKET_MEMBERSHIP.csv` vs esperimenti `AM1975MA/Test:regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv` sul branch `research-v2-127-allocations-20261020`.

- **Git blob SHA identici:** `e7d75a83f161a56aa8846088d6c5869d80a72af3` (uguaglianza byte-per-byte, comprese righe, basket ID e ordine).
- **SHA256 canonico:** `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- **500 panieri distinti × 24 ETF = 12.000 assegnazioni**, 149 ticker.
- Fonte generatrice originale `scripts/verify_official_baskets.py`: 6 categorie × 4 nomi, `random.Random(20260721)`; il ticker `PIN` è escluso perché privo di dati utilizzabili.
- **ATTENZIONE:** una copia locale temporanea `SUPER_GOLD_BASKET_MEMBERSHIP.csv` aveva SHA256 `9279984b7e6f47dcdae4a63a204ea1d486d4e47bc713cf88ade8d6973515ce62`. Questa copia NON è il riferimento; gli esperimenti quantitativi certificati usano solo il file con SHA 36a....

## Protocollo del nuovo test

- Congelati XGBRanker a **127 foglie**, le sue predizioni OOS dalla run [39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), OHLCV dei 149 ETF, date, target e costi.
- 500 panieri autentici, segnali da gennaio 2018, 101 mesi di esecuzione da febbraio 2018 a giugno 2026.
- Nessun riaddestramento XGBoost e nessun filtro di rischio (100% investito); esecuzione dal segnale mensile all'open successivo, commissione 10 bp sul notional scambiato.
- **21 configurazioni**: score XGB puro vs punteggio V2 (Tail/macro già composti) e 25/50/75% di interpolazione post-ranking; Top2/Top3, pesi uniformi o 50/30/20 e 40/35/25; regole condizionali Top2-vs-Top3 sul gap secondo-terzo.
- Il mix dei due ranking salvati NON rappresenta la ritaratura diretta del coefficiente Tail né del bonus macro; non attribuire a quei componenti individuali effetti che non sono stati identificati.

## Metriche ottenute

CAGR medio e MaxDD medio su 500 portafogli indipendenti per definizione di capitale (membership sovrapposte e dunque osservazioni statistiche dipendenti); **CAGR aggregato** e **MaxDD aggregato** sulla NAV media dei portafogli.

| Scelta | CAGR medio | MaxDD medio | CAGR agg. | MaxDD agg. | Turnover annuo |
|---|---:|---:|---:|---:|---:|
| V2 legacy 75/25, condizionale 100/0 | 9,44% | -52,45% | 12,05% | -38,20% | 13,88 |
| V2 score, Top2 50/50 | 10,30% | -48,06% | 12,07% | -37,79% | 12,53 |
| **V2 score, Top3 uguali** | **10,49%** | **-43,49%** | 11,64% | **-37,77%** | **10,76** |
| XGB raw, Top2 50/50 | 11,27% | -47,53% | **12,92%** | -39,66% | 13,90 |
| XGB raw, Top3 50/30/20 | 11,16% | -45,45% | 12,52% | -39,59% | 13,30 |
| 75% raw +25% V2, Top2 uguali | 11,14% | -47,37% | 12,85% | -39,18% | 13,54 |
| V2, Top2 se gap23>0,06, altrimenti Top3 uguali | 10,46% | -44,75% | 11,76% | -37,72% | 11,59 |

Nota: CAGR storico include ~1 anno senza posizioni prima del primo segnale nel 2018. Non è una metrica di guadagno necessariamente replicabile.

## Controllo delle differenze tramite bootstrap appaiato

6-month circular block bootstrap, 5.000 ricampionamenti su **101 mesi attivi comuni**, aggregando prima i panieri per ciascun mese, confronto verso legacy. CI95% su differenza dei rendimenti logaritmici annualizzati:

| Configurazione | Delta log annualizzato | CI95% (punti percentuali) |
|---|---:|---|
| V2 Top2 equal | +1,04 pp | [-0,43; +2,51] |
| V2 Top3 equal | +1,32 pp | [-1,24; +3,84] |
| Raw XGB Top2 equal | +2,04 pp | [-0,95; +5,39] |
| Raw XGB Top3 50/30/20 | +1,96 pp | [-1,01; +5,35] |

**Tutti gli intervalli includono zero.** La selezione retrospettiva tra 21 configurazioni introduce inoltre multiple-testing/data snooping. 2024–2026 è già stato esaminato e NON costituisce un nuovo periodo out-of-sample di conferma.

## Decisione ingegneristica

Non cambiare ancora né ranker produttivo né risk layer. Mantenere tre modelli concorrenti per validazione futura con preregistrazione:

1. **V2 score / Top3 33-33-33** (drawdown minore sui panieri, più diversificazione, turnover minore).
2. **XGB puro / Top2 50-50** (CAGR maggiore con rischio aggregato peggiore).
3. **XGB puro / Top3 50-30-20** (CAGR vicino a Top2, drawdown medio più contenuto).

Il **massimo drawdown aggregato resta circa -38/-40%** per tutte le strategie: i pesi Top2/3 non mitigano la componente sistemica. Non mascherare questo fatto nei risultati.

Successivo test separato: ricostruire predizioni **Tail e macro annuali** già maturate e ritarare *direttamente* rispettivamente `0.30` Tail e bonus `0.15`, con pesi scelti solo usando mesi anteriori e un controllo effettivamente futuro. Soltanto **dopo** validare l'allocazione si abilita rischio.

I CSV, codice replay e membership canonica verificata sono nel pacchetto allegato alla conversazione `V2_127_retune_canonical_repro.zip`, non nel repository produttivo.
