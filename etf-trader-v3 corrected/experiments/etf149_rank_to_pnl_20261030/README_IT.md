# ETF149 — Audit causalmente allineato fra ranking e PnL (30 ottobre 2026)

**Stato:** ricerca storica descrittiva, **nessuna nuova performance prospettica**, **nessun aggiornamento dei modelli**.

## Domanda

Il punteggio mensile V2 (255 foglie) o Ridge contiene capacità predittiva tale da generare rendimento *effettivamente realizzato* nel mese di mantenimento? In quale orizzonte emerge l'informazione? Un miglior ranking produce sempre un miglior portafoglio?

## Dati e metodo

- Universo congelato di 149 ETF quotati negli USA, già definito nello studio V2/V3, **non survivor-bias-free**.
- Prezzi `Open` corretti per gli aggiustamenti Yahoo, archivio append-only fermo al **23 ottobre 2026**. I segnali sono quelli storicamente archiviati, calcolati alla chiusura di fine mese; l'esecuzione è all'apertura del mese seguente, uscita all'apertura del mese successivo.
- **V2**: 102 mesi di segnale, gennaio 2018–giugno 2026; Top 10 equiponderati. **Ridge**: 44 mesi, gennaio 2023–agosto 2026; Top 15 equiponderati. Le date comuni sono 42, gennaio 2023–giugno 2026.
- Stessi ticker, date e prezzi del motore economico precedente. Riproduzione degli utili lordi a livello di mese: errore massimo V2 2,98×10⁻¹⁶ e Ridge 2,08×10⁻¹⁶.
- **Ranking**: correlazione Spearman fra punteggio e rendimento del mese successivo su tutti i 149 ETF, e media pesata degli Spearman entro le 6 categorie.
- **Valore economico**: rendimento lordo medio del Top K meno rendimento di SPY, media di tutti gli ETF, o media delle rispettive categorie (residuo per categoria). Non è CAGR e non considera costi, spread, tasse o turnover: il simulatore economico precedente contiene le relative verifiche.
- Campionamento bootstrap circolare temporale per blocchi di 6 mesi (5.000 estrazioni); intervalli esplorativi **non corretti per molteplici modelli/ricerche**. Non si assume indipendenza fra gli ETF di una stessa data.
- Diagnostica a orizzonti fissi: 1, 3, 5, 10, 15, 20 sedute **all'interno del mese di detenzione**. Il numero di mesi a 20 sedute è inferiore perché alcuni mesi sono più corti: i valori a 20 giorni non sono direttamente confrontabili con gli altri orizzonti senza controllare le stesse date.

## Risultati principali (campione uguale 42 mesi)

| Misura | V2 | Ridge | Ridge – V2, intervallo 95% |
|---|---:|---:|---:|
| Spearman medio | +0,04264 | +0,12203 | +0,07939 [+0,0108; +0,1422] |
| Top K meno SPY, mensile lordo | +0,75545 pp | +0,72635 pp | −0,0291 pp [−1,06; +1,03] |
| Top K meno propria categoria, mensile lordo | — | — | −0,01 pp [−0,80; +0,81] |

**Interpretazione:** un ranking migliore non si converte automaticamente in rendimento: Ridge migliora l'ordinamento generale ma la selezione, la dispersione dei pay-off, le esposizioni e i pesi non mostrano superiorità economica sullo stesso periodo. I Top K sono differenti (10 contro 15): il confronto NON identifica l'effetto esclusivo del modello separato dalla costruzione del portafoglio.

## Risultati sull'intero storico proprio di ciascuno

| Misura | V2 (102 mesi) | Ridge (44 mesi) |
|---|---:|---:|
| Spearman medio sui 149 | +0,0481 | +0,1319 |
| Spearman entro categoria | −0,0150 | +0,1152 |
| Top K meno SPY lordo | +0,45 pp/mese | +0,83 pp/mese |
| Top K meno universo lordo | +0,90 pp/mese | +1,42 pp/mese |
| Top K meno rispettive categorie lordo | +0,69 pp/mese | +1,39 pp/mese |
| Mesi Top K sopra SPY | 52,9% | 54,5% |

Il portafoglio è superiore a SPY in appena poco più della metà dei mesi, nonostante gli Spearman medi positivi. Le correlazioni contemporanee (post factum) fra IC e rendimento attivo sono +0,288 V2 e +0,497 Ridge; servono a diagnosticare il meccanismo, non a decidere in anticipo.

### Distribuzione per quintili di punteggio

- Ridge: il quintile più basso rende in media +0,24%/mese e quello più alto +2,08%/mese; il contributo al rendimento specifico di categoria sale da −0,43 a +0,93 pp.
- V2: il quintile più basso rende in media +0,46%/mese e quello più alto +1,10%/mese; entro categoria il miglioramento è molto inferiore, da −0,08 a +0,15 pp.

Questo è coerente con la migliore capacità di Ridge di ordinare strumenti all'interno di categorie, ma i quintili non costituiscono portafogli investibili con costi e rischio controllati.

### Evoluzione del segnale durante il mese

- V2, vantaggio lordo medio Top10 vs SPY: 5 sedute +0,11 pp, 10 sedute +0,44 pp, 15 sedute +0,37 pp.
- Ridge, vantaggio lordo medio Top15 vs SPY: 5 sedute +0,20 pp, 10 sedute +0,49 pp, 15 sedute +0,76 pp.

I valori a 20 sedute usano meno mesi e non vanno presi come una prova di timing ottimale. I segnali non giustificano cambiare il calendario di entrata/uscita.


## Controllo addizionale a parità di numerosità e categoria (eseguito)

Per rimuovere la confusione Top10-V2 vs Top15-Ridge, ho confrontato entrambi sui medesimi 42 mesi con **lo stesso K = 5, 10, 15**, prima senza vincoli e poi con **massimo tre titoli per macro-categoria**. Ogni portafoglio mantiene pesi identici, esecuzione alla prima apertura del mese, ribilanciamento con turnover drifted e costo di 10 bp per unità di nozionale negoziato (ogni lato).

| K e vincolo | V2 rendimento netto medio mensile | Ridge netto | Ridge − V2, CI bootstrap 95% |
|---|---:|---:|---:|
| 5, nessun limite | +2,123% | +1,983% | −0,140 pp [−1,487; +1,464] |
| 5, massimo 3/categoria | +2,264% | +1,725% | −0,538 pp [−1,674; +0,707] |
| 10, nessun limite | +2,287% | +2,097% | −0,190 pp [−0,858; +0,557] |
| 10, massimo 3/categoria | +1,859% | +2,020% | +0,161 pp [−0,654; +1,256] |
| 15, nessun limite | +1,627% | +2,253% | +0,626 pp [−0,253; +1,611] |
| 15, massimo 3/categoria | +1,772% | +2,031% | +0,259 pp [−0,298; +0,870] |

**Nessuna di queste differenze è statisticamente conclusiva.** I valori sono medi aritmetici mensili netti del costo simulato, non CAGR. Queste sei scelte di K/cap sono test diagnostici aggiuntivi fatti DOPO aver visto l'esperimento principale: non è lecito selezionare la variante apparentemente migliore e presentarla come nuova conferma fuori campione. La correzione per comparazioni multiple le renderebbe ancora meno persuasive.

I dati mensili e il codice completo sono nei file equal_k_same_months.csv, equal_k_summary.csv e run_equal_k.py. Il programma dei controlli usa gli stessi quattro input del ranking. Il numero di ETF selezionati e le restrizioni sono applicati identicamente ai due metodi.

## Limiti e decisione

1. **Survivorship bias**: i 149 ETF sono stati scelti ex post; gli ETF cessati non compaiono nell'universo.
2. **Selection/research bias**: V2, Ridge e i vari controlli sono già stati scelti dopo aver analizzato molti degli stessi anni. Questi intervalli non convalidano un modello nuovo.
3. **Asset allocation non controllata**: Top10 e Top15 differiscono per cardinalità ed esposizioni di categoria. Serve un esperimento futuro con identico costruttore di portafoglio e regole pre-registrate, non un confronto retrospettivo ottimizzato.
4. **Lordo, non netto**: l'IC del segnale non è rendimento negoziabile; costi e rischio restano da considerare nel motore di simulazione già validato.
5. **Esecuzione**: `Open` è adeguato al controllo storico comparabile ma non documenta slippage e quote effettivamente negoziabili.

**Decisione:** non cambiare i modelli. Registrare prospetticamente entrambi i punteggi e il risultato effettivo a parità di date/costi; studiare soprattutto l'area di conversione del ranking in PnL, e verificare le esposizioni e i costi prima di qualunque promozione a trading reale.

## Riproduzione

Mettere in una cartella locale i quattro input elencati nel `manifest.json` (SHA-256 fissati). In particolare il file `strategy_target_weights.npz` deve essere in `ETF149_Investment_System_Research/`. Eseguire:

```bash
export ETF149_DATA_ROOT=/percorso/dati
python run_rank_to_pnl.py
```

Su Windows PowerShell:

```powershell
$env:ETF149_DATA_ROOT = 'C:\ETF149\research'
python .\run_rank_to_pnl.py
```

Dipendenze: `numpy`, `pandas`, `scipy`. Il codice non usa API di mercato durante il calcolo. I dati sono espressamente riferiti allo snapshot storico, non aggiornati in automatico.

## Output

- `monthly_rank_and_pnl.csv`: un record per modello e mese, 146 righe.
- `signal_age_horizons.csv`: sviluppo dei rendimenti lordi per orizzonte.
- `score_quintiles_monthly.csv`: rendimenti dei quintili, per mese.
- `block_bootstrap_summary.csv`: stime e intervalli bootstrap.
- `ic_vs_realized_pnl.csv`: disallineamento fra capacità di ranking e rendimento economico.
- `score_quintile_summary.csv`, `signal_age_horizon_summary.csv`: aggregati di consultazione.
- `manifest.json`: firme dei quattro input e conteggi del campione.

Gli input pesanti sono archivi di dati già esistenti o archivi delle ricerche precedenti; non vengono duplicati inutilmente. **La pubblicazione nel repository `Test` va verificata prima di considerare questo rapporto versionato.**