# OLC70B — Addendum pre-esito: training su controfattuali generati dallo stato adattivo effettivo

**Registrato 7 novembre 2026 prima di eseguire OLC70B.** L'esito OLC70A baseline-state era già noto: Europa FULL CAGR 21,83%, USA FULL 35,99%, risultato congiunto negativo. OLC70B è quindi una diagnostica post-OLC70A ma con regole congelate prima di leggerne i nuovi outcome.

## Ipotesi
Il learner OLC70A ha addestrato etichette di controfattuali da stato della baseline OLC19, anche quando la policy adattiva raggiungeva stati diversi. OLC70B mantiene **esattamente** le quattro azioni A/B/C/D e feature/learner OLC70A, ma genera training labels dai quattro replay nativi da **un identico stato del portafoglio adattivo effettivamente raggiunto** a ogni segnale.

## Contratto sequenziale
Inizia con stato OLC19 vuoto al febbraio 2019. All'evento t prevede usando SOLO etichette precedenti mature almeno due mensilità prima (t−2), di stati della propria traiettoria; richiede 24 mesi con feature as-of validi, StandardScaler train-only + Ridge alpha25 separato per i differenziali B,C,D−A, feature identiche a OLC69/70A, edge fisso +5 logbp, fallback A, tie A/B/C/D. Dopo aver scelto la policy, esegue *quattro* rami OLC19 dall'identico snapshot pre-evento fino alla prossima apertura: i tre rami non scelti sono etichette di training future, MAI disponibili per la scelta corrente, e si conservano solo dopo la fine del mese. Il ramo scelto produce lo stato iniziale del mese successivo (posizioni, stop, cooldown, lock, V6, cash, target, remaining). Nessuna ricostruzione di un conto a partire da NAV mensili di altri conti.

## Gate
Ricostruire una seconda volta l'intera policy OLC70B con uno *solo* full replay OLC19 nativo dato l'array delle azioni predecise, verificare le sette matrici di contabilità **bitwise** contro la simulazione sequenziale a segmenti, a fee=.001. Stesso piano applicato fee=.003 per stress. Confronti predefiniti A, D e OLC70A MAIN/FULL/2024/2025/2026 parziale, CAGR e MaxDD, annual returns. Confronto di forecasting contro media cronologica con gli stessi dati disponibili. NO PROMOTION se FULL CAGR < OLC19 in uno dei due mercati oppure MAIN CAGR < OLC19 o FULL drawdown peggiorato >3 pp. Parametri e feature non cambiano a posteriori.
Ricerche originali 2019–2026 già fortemente mining; nessuna prova OOS nuova, no trading reale.
