# TENSOR149_TCN5D — protocol preregistrato, 2026-10-20

Ambito: **solo ricerca**, branch \`research/original149-tcn5d-causal-20261020\` in \`AM1975MA/Test\`. Nessuna modifica al repository di produzione, né al ranking Compact21 canonico. Nessuna ricerca di iperparametri guidata dal CAGR.

## Origine dati

Usare esclusivamente i 149 CSV OHLCV congelati di \`evidence_v1/data/original149/\`, con \`manifest.json\` e validazione SHA-256 di ciascun CSV. Le 125 feature devono usare *esattamente le formule Compact21* pubblicate in \`vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py\`, ma **su ogni seduta**, non esclusivamente sugli ultimi giorni del mese. Confermare parità numerica sulle date mensili esistenti. Feature cross-sectional rank e deviazione robusta si calcolano per data sulle sole quotazioni esistenti a t. Il pannello include soltanto ETF dell'universo originale, nessuno esterno.

## Architettura e target

- Input \`(B,30,125)\`: finestra delle ultime 30 sedute inclusa chiusura t. Ammissibilità: prezzo noto a t e almeno 30 feature valide su ciascuna delle 30 sedute.
- TCN causale con due convoluzioni kernel 3 (dilatazioni 1 e 2), 24 canali, LayerNorm, dropout 35%, combinazione di stato finale e mean pooling temporale. AdamW, LR 0.001, weight decay 0.003, batch 256, max 5 epoche e early stopping pazienza 2, seed 20261020.
- Target per ETF alla chiusura t: rendimento \`Open(t+6)/Open(t+1)-1\`, quindi *cinque* sedute acquistabili, poi trasformato in percentile cross-sectional \`2*rank_pct-1\`. Il target non è una feature.
- Loss SmoothL1, peso 2 alle etichette nei due tail (|rank| >=0.6). Nessun dato target usato nella selezione di inferenza.
- Campionamento train, validation e test ogni cinque sedute su una griglia globale fissa a partire dal giorno 280 del file. I 30 valori quotidiani restano conservati in ciascun tensore.
- Normalizzazione train-only, NaN imputati a zero **dopo** centering e scaling; clipping z ±6. Nessuno scaler su validation/test.

## Split temporale

Per test OOS anno Y: train su signal >=2008 fino ai target **usciti strettamente prima del 1 gennaio di Y−1**, validazione su segnali di Y−1 con exit maturata prima di Y, test sull'anno Y senza alcun aggiornamento intra-anno; quindi un embargo strutturale per label. Le finestre temporali in input usano solo feature fino alla chiusura di ciascun segnale. Inizio degli anni OOS possibile nel 2017; cutoff ultimo target 2026-07-01.

### Esperimento iniziale e confronto

Primo run limitato a OOS 2024–2025 per il controllo operativo; se supera i gate di esecuzione, estensione con stesso codice, stessi iperparametri e split a tutti gli anni 2017–2026. Il pilot ha valenza diagnostica e **non** indipendenza scientifica: questi dati storici sono stati usati in altri esperimenti.

Tre previsioni settimanali sulle stesse 149 posizioni ammissibili: TCN sequenziale, Ridge sui 125 valori del giorno t (alpha 300), momentum21 come controllo ingenuo. Per tutti: selezione Top5 long equal weight; entrata all'open(t+1), uscita all'open(t+6), 10bp entrata + 10bp uscita *per ogni periodo* (approssimazione prudenziale di turnover pieno), stesso input, stesso universo e stesso calendario. Non va confrontato direttamente con CAGR mensili F3/H1 senza armonizzare le regole di trading.

Metriche prima del PnL: RankIC giornaliero ponderato per data decisionale, percentile realizzato dell'ETF Top1, Top5 overlap effettivo, regret rispetto al decile superiore dei rendimenti futuri. Metriche economiche: CAGR netto, MaxDD da NAV giornaliero agli open, Sharpe, durata OOS. Salvare tutte le predizioni OOS, curve giornaliere, manifest, audit per fold.

## Interdizioni e avvertenze

I ~600k esempi ETF×giorno condividono mercato e informazioni: non sono indipendenti. Anche le valutazioni ogni cinque giorni sono economicamente correlate tra ETF. Uno score di ritorno relativo non elimina automaticamente beta, esposizione alla volatilità o rischio sistematico. Nessun hyperparameter tuning dopo lettura del risultato pilot; eventuali alternative 10D/21D, GRU o GNN devono ricevere loro protocollo e gruppo di controllo. Dati storici survivor-biased e adjusted OHLC di Yahoo, non prezzi reali eseguibili. Nessuna adozione in produzione.
