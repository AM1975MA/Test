# OLC31 — G0: audit origine dati e parity, prima della stima economica

2 novembre 2026. Questo checkpoint contiene solo controlli di sorgente, di maschera e di replay dei conti *già persistiti*. Non sono stati eseguiti fitting, backtest o trading.

## Esito
**G0 parità e periodo principale: PASS, con una eccezione rilevante di qualità prezzi nel 2020.**

- Tutti e cinque gli archivi sorgente passano SHA256 contro il manifesto pre-registrato.
- Ricostruzione percentile da RETURN_RAW, ET_RAW, XGB_RAW: errore numerico esattamente zero, su 13.781 righe EU e 13.410 USA.
- RETURN nel riferimento OLC20 coincide esattamente con la stessa colonna in OLC08 e OLC16, senza chiavi mancanti.
- Tutti 32 conti OLC19 (4 controlli x 2 contratti rischio x 2 costi x 2 mercati) coincidono integralmente con OLC20, tutte le matrici e lo storico NAV.
- Le serie di forecast autenticati hanno 90 segnali gennaio2019–giugno2026 e 165 ticker EU /149 USA. Lo stato quote EU contiene 167 ticker perché comprende anche strumenti tecnici/di cassa: non identificare automaticamente le 167 colonne con un universo investibile di 167.

## Qualità delle etichette Open→Open

| Mercato/finestra | Validità quote alle due aperture | Nota |
|---|---:|---|
| EU principale | 7302/7304 (99.973%) | Non contare terminale 2026-06-30 come mese maturato |
| EU intero | 13334/13781 (96.756%) | Non contare terminale 2026-06-30 come mese maturato |
| USA principale | 7152/7152 (100.000%) | Non contare terminale 2026-06-30 come mese maturato |
| USA intero | 13261/13410 (98.889%) | Non contare terminale 2026-06-30 come mese maturato |

**Eccezione maggiore EU:** segnali 2020-04-30 e 2020-05-29 validano solo **9/148 ticker** su entrambe le scadenze, perché la data condivisa 1 giugno 2020 ha `observed=True` soltanto per **11 dei 167 ticker dello stato EU**. Xetra e Frankfurt erano effettivamente chiusi per Whit Monday il 1 giugno 2020 (calendario XONTRO/BRAINTRADE emesso il 28 febbraio 2020). I valori `O` positivi su ticker non osservati NON diventano quotazioni eseguibili. Questi due mesi non devono essere trasformati in 0 né analizzati come completi. Il replay parent resta esatto, ma la parità NON certifica i prezzi/riempimenti legacy.

**Altra eccezione EU 2024:** `LEEU.DE` manca di quotazione osservata all’Open 2024-05-02: invalida l’etichetta 2024-03-28 e quella 2024-04-30 per quel ticker, non l’intero mese. USA mantiene 100% di prezzi `O` preparati finiti, ma manca la maschera originale delle osservazioni: copertura apparente NON è certificazione di eseguibilità.

**Riga terminale:** 2026-06-30 segnala ingresso e uscita sul medesimo 2026-07-01, per cui **zero etichette future sono mature**. È stato scritto un test failing-first e aggiornato il controllo per escluderla. Non attribuire rendimento futuro piatto.

## Decisione gates
- Autorizzare G1 **sulla finestra principale 2021–2024**, usando solo ticker con entrambe le aperture osservate (EU) o preparate finite positive (USA), segnali e supporti invariati al momento della scelta.
- Non usare il FULL 2019–2026 per certificare la qualità delle etichette future O2O finché non si risolve l’eseguibilità dei due mesi del 2020; si possono riportare i conti storici legacy solo con caveat.
- Non procedere a G2 o G4 automaticamente; serve prima G1 diagnostico e verifica indipendente.
- Il riferimento del benchmark miglior ticker ex-post non diventa un criterio di promozione.

## Tracciabilità
`00_SOURCE_MANIFEST_G0.json`, `01_KEY_COVERAGE_G0.csv`, `02_SCORE_LINEAGE_G0.csv`, `03_O2O_LABEL_COVERAGE_G0.csv`, `g0_source_parity.py` e `G0_RUN.log` sono gli output canonici.

Fonti: repo OLC20/OLC19 e comunicazione BRAINTRADE/XONTRO 2020, https://xontro.de/sites/data/media/documents/Newsletter/XONTRO_KI_englisch/Floor_KI_2020_97_M_72_Feiertage_e.pdf
