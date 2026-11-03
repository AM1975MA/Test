# OLC34 — VIX come fonte indipendente per eventi economici estremi: esito finale

**3 novembre 2026 · Ricerca retrospettiva controllata · Decisione STOP · Nessun ordine / nessuna modifica a main**

## Protocollo e delimitazione
- Preregistrazione, **prima del primo calcolo dei risultati**: commit `320d11c9c29180f669f54dd45f92bb01b4d4e043` sul branch `research/olc34-external-vix-20261103`.
- Anomalia emersa **dopo il primo replay**: il mirror VIX Cboe riporta chiusure positive su festività senza diffusione di indici. Addendum trasparente **post-esito**: commit `84520a5a976fbca38b7baaa9e5d6b1bbfc461021`.
- Riparazione deterministica degli input (non degli esiti ETF): escludere giorni non presenti nel calendario di regolari sedute XNYS (`exchange_calendars 4.13.1`, proxy prudenziale del calendario ufficiale di diffusione VIX), ricostruire ultimo CLOSE con data **strettamente precedente** al segnale e valore 21 sedute prima. **Non** si considera il nuovo replay un test confermativo indipendente dal primo.
- Fonte VIX: Cboe via dataset `datasets/finance-vix`, blob Git `c05e0d9c28ddf3b98d0531017ef5b5180df05ae1`, attestazione mirror, non certificazione data provider point-in-time. Input corretti in `OLC34_VIX_ASOF_SIGNAL_EXCHANGE_FILTERED.csv`, blob Git `28c334adcf0f8f43477c8df99ae311a12b44d441`.
- Fonte ETF: etichette Open→Open OLC32 congelate, SHA256 `83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16`; correzione UE giugno 2020 già salvata, non riscritta.

## Risultato sul campione principale 2021–2024 (48 mesi per mercato)
Confrontiamo **P0** frequenza storica evento (null), **P1** classificatore OLC33 a 12 feature e **P2** stesso classificatore regolarizzato con 2 nuove feature indipendentemente misurate (VIX e log-variazione VIX in 21 sedute). Addestramento pooled EU/USA, 50/50 per mercato e pesi uniformi per mese; modelli nuovi ogni gennaio con soli esiti già maturi. P1/P2 hanno gli stessi ticker/date/etichette/criteri e stessa complessità di regressione logistica a parte i due input esterni. Nessun tuning a posteriori.

| Indicatore | Europa | USA |
|---|---:|---:|
| Coppie Top1–Top(2..5) valutabili | 190 | 192 |
| P0 Brier (↓ meglio) | 0,16615 | 0,15595 |
| P1 Brier (↓ meglio) | 0,17682 | 0,17116 |
| P2 Brier (↓ meglio) | **0,17376** | **0,17024** |
| Guadagno P1−P2 Brier (positivo favorevole) | +0,00306 | +0,00093 |
| Precisione media delle probabilità di evento elevato P2: AUPRC | 0,2353 | 0,1689 |
| Switch P1 | 1 | 7 |
| Switch P2 | **4** | **8** |
| Eventi ≥+300bp netti P2 correttamente selezionati | 1/4 | 2/8 |
| Eventi ≤−300bp netti negli switch P2 | 1/4 | 2/8 |
| Vantaggio medio P1 sul Top1 (bp/mese) | +3,75 | −6,22 |
| Vantaggio medio P2 sul Top1 (bp/mese) | **+6,99** | **−14,24** |
| P2−P1 (bp/mese) | +3,23 | **−8,02** |

Migliora **lievemente** il Brier rispetto a P1, ma in entrambi i mercati rimane **peggiore della baseline P0**. Con le soglie fisse del protocollo, gli interventi sono pochi (4 EU, 8 USA, meno dei 12 minimi per mercato) e non rappresentano un vantaggio ripetibile. La media congiunta P2 vs Top1 è **−3,6273bp/mese**; bootstrap moving-block 6 mesi, n=2000: 95% [**−39,8870; +46,7554**] bp/mese. Il vantaggio congiunto P2 vs P1 è **−2,3940bp/mese** [−36,6038; +44,8962]. Miglioramento Brier congiunto P1−P2 **+0,001993** [−0,003151; +0,008949], non robusto rispetto a zero. I bootstrap sono descrittivi, non corretti per la ricerca pregressa.

## Integrità della fonte esterna
Tre segnali mensili puntavano direttamente a una data con valore VIX non diffuso nella normale seduta: 2022-05-31 da `2022-05-30` (Memorial Day), 2024-11-29 da `2024-11-28` (Thanksgiving), 2025-11-28 da `2025-11-27` (Thanksgiving). In totale **30/91** valori mensili hanno dovuto essere ricalcolati perché lo spostamento di 21 sedute risentiva anche di righe in giorni festivi. Nessun prezzo VIX è stato inventato o interpolato. La convenzione XNYS è un filtro prudente, non la prova di original quote certification. Cboe dichiara espressamente l'assenza di diffusione indici il 28 novembre 2024: https://cdn.cboe.com/resources/schedule_update/2024/Cboe-U-S-Indices-and-Theoretical-Options-Pricing-Service-Thanksgiving-Holiday-Reminder.pdf

## Verifiche indipendenti
- Originale OLC32 e snapshot VIX filtrato verificati su SHA / blob Git.
- **720** coppie mensili OLC33/OLC34 confrontate; ricostruzione P1, P0 e spread OLC33: **errore numerico massimo 0**; decisioni OLC33 e risultato netto: **0 discrepanze**.
- Ultimo VIX usato **antecedente** al segnale, non oltre 7 giorni e in seduta XNYS: 0 violazioni.
- Le etichette 2024 modificate artificialmente dopo il cutoff **non** cambiano le previsioni 2021–2024 (errore max < 1e-16); cambiano legittimamente 94 previsioni 2025 con training aggiornato: controllo causalità superato.
- Maturazione dei target strettamente prima dell'anno del training. No target come feature; fallback in caso di dati mancanti; calendario EU 2020 corretto; etichetta terminale 2026-06 esclusa; `LEEU.DE` non osservato escluso, USA prepared Open senza certificazione observed raw.

## Gate di successo e arresto
Tutti i gate principali sono **falliti**: Brier P2 inferiore a P1 e P0 in entrambe le regioni, intervallo bootstrap inferiore del miglioramento Brier >0, almeno 12 switch verificabili in ciascun mercato e precisione 1,5× base, utilità economica positiva sia vs Top1 sia vs P1 in entrambe le regioni, limite inferiore bootstrap economic >0, controllo di coda con numero minimo di interventi.

**Decisione: STOP**, nessun aumento di complessità, soglie, finestre o sottouniversi a valle degli esiti; nessun NAV operativo o promozione di VIX al motore ETF. Il VIX potrebbe avere valore in altri obiettivi, ma questo test **non lo dimostra**. Il periodo 2021–2024 è già più volte esplorato in OLC01–33, quindi non è un holdout realmente indipendente; 2025–2026 restano periodo diagnostico, non secondo tentativo di scelta.

## Riproduzione

```bash
python src/olc34_vix_context_exchange_filtered.py \
  --input /path/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz \
  --vix results/OLC34_VIX_ASOF_SIGNAL_EXCHANGE_FILTERED.csv \
  --baseline-src /path/olc33_tail_condition.py \
  --out results/replay
python src/verify_olc34.py
```

Prerequisiti `python>=3.11`, `pandas`, `numpy`, `scikit-learn`, `exchange-calendars` (per la verifica delle sedute). Lo script di audit locale riferisce ai percorsi sotto `/mnt/data`; adattarli o usare l'archivio distribuito con la stessa struttura.

**Limiti decisivi:** ritorni in log bp, non performance NAV senza frizioni; costo di 20bp ipotetico, quotazioni di asta non certificate, fiscalità, spread, bid-ask, survivorship, dividendi/FX e maschera `observed` originale USA assente; serie VIX mirror con date pseudo-observed e non autenticata a livello singola seduta. Il dato esterno fornisce informazione nuova all'esperimento OLC33, ma non un holdout indipendente nel tempo.