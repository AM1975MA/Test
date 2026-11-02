# OLC26 — supervisore condizionale di leadership persistente

2 novembre 2026. Lotto esplorativo separato dopo la verifica NEGATIVA OLC25 (6957249c82516843ca2b215ded648679f3a5de6a); nessun holdout vergine. Parent economico OLC20 6c387fac4c2e544bb9dc90f6622cd94faba6d7c2. Non modificare main, non fare trading, non toccare i predittori ETF già addestrati, target originali, stop, V6 o calendari.

## Ipotesi preregistrata
Il solo momentum 126/252 e la persistenza non vanno miscelati indiscriminatamente al Top2. Testare se un piccolo correttore supervisionato può imparare *quando* un segnale di forza storica anticipa leadership relativa a ~6 mesi, preservando sostanzialmente la gerarchia AUTH.

## Input puntuali e qualità
Punteggi AUTH FUSION OLC20 per ogni ETF e signal_date; Close OHLC della stessa data e di 63,126,252 sedute precedenti, osservati e positivi per EU. USA: finite positive prepared quotes (original observed mask assente). Rango percentile per ticker all'interno di ogni universo/data; missing dei momentum -> predizione AUTH invariata, non esclusione del ticker.

Features esatte (nessuna identità ticker, regime target, dummy mercato, forward return):
1. AUTH FUSION,
2. percentile momentum 63 sedute,
3. percentile momentum 126 sedute,
4. percentile momentum 252 sedute,
5. media dei percentili momentum126 su tre segnali mensili consecutivi,
6. interazione (momentum126 × persistenza3).

## Target e disponibilità
Futura leadership: percentile cross-sectional dei rendimenti logaritmici Close[t+126 sedute]/Close[t] sul pannello OHLC. Per EU occorre observed=true a entrambe le estremità; USA richiede finite positive. Non si calcola il target nel mese senza quotazione futura. Per ogni segnale si registrano **data esatta di maturazione t+126** e maschera ticker. Il target di correzione è `Y = percentile_future126 - AUTH_FUSION`. Nel fit dell'anno Y usare SOLO righe con complete 6 features e label, con maturity_date STRICTLY < 1 gennaio Y; gruppi che non hanno ancora maturato restano esclusi. Nessun riaddestramento mensile, nessun lookahead da etichette incomplete, nessuna selezione ticker da forward availability nelle previsioni.

## Modello fissato
StandardScaler fit solo sul training, Ridge con alpha=50 e intercetta. Due e SOLO due recipe:
- POOL: un Ridge per anno addestrato su EU+USA, mercati bilanciati per massa 50/50, mensilità bilanciate entro mercato, ETF bilanciati entro mese.
- STRAT: un Ridge per anno/mercato, stesso alpha/scaler/features, mesi bilanciati entro mercato. Non scegliere diverse soglie o ricette per mercato.

Un anno con meno di 12 mesi maturi completi per ciascun mercato nel POOL (o nel mercato corrispondente in STRAT) ricade su AUTH. Il primo periodo 2019–2020 non ha fit. L'aggregato dei pesi sample_weight è normalizzato a numero di righe (media=1), mantenendo il bilanciamento.

## Output del layer e correzione
Predire il residuo con Ridge. `delta=clip(predicted_residual, -0.10, +0.10)`; `S=AUTH_FUSION+0.50*delta`. Nessun aggiornamento per ticker con feature non tutte finite. Nessuna variazione da score future. Stessi coefficienti/iperparametri EU/USA, nessun fit che scelga CAGR.

## Controlli negativi
Cinque replicati per recipe, seed26001..26005: all'interno di ciascuna data e mercato, permutare i target maturati del training fra ticker validi (non l'input, non la data). Ogni annual fit e confronto ricostruito con il seme fissato. Null non è candidato di trading, non scegliere fortunati; frequenze non sono posteriori o p-value corretti per la ricerca.

## Replay e criterio
Usare OLC20/O19 senza modifica motore, V6 candidate-specific. ALARM e FAST_LOCK3, fee .001/.003. Baseline AUTH senza fit identica bitwise agli 8 parent accounts. Primario HALF/2021–2024: challenger comune solo se il CAGR aumenta su EU e USA nello stesso contratto a fee .001; controllare anche rischio, fee .003, FULL/anni/2020. Nessun risultato selezionato su 2025–26 parziale.

## Verifica
Test per maturazione rigorosa, assenza di future feature, identità score per fallback/missing, pesi EU/USA e data, determinismo seed, maschera shuffle, V6 non overlap, indipendenza metrica/NAV, parity AUTH. Persistenza di modelli/predizioni/curve autentiche e metriche negative. Questa è ricerca retrospettiva già riutilizzata molte volte; nessuna promozione automatica.
