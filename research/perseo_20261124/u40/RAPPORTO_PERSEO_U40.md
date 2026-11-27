# Perseo U40 · Verifica della previsione su Europa e Trade Republic

27 novembre 2026

**U39 non produce un miglioramento comune nei due conti.** La proiezione dei cambi USA perde in Europa e guadagna poco su Trade Republic. La sostituzione scelta direttamente in Europa riduce il drawdown storico. I controlli sugli stessi mesi mostrano che gran parte del risultato può dipendere dalle date di intervento e da poche sostituzioni.

## Impostazione

Il riferimento riproduce U38, con il suo ripiego parziale quando mancano entrambe le repliche USA e il suo rientro dopo stop. Tutti i conti usano il periodo dal 2 gennaio 2020 al 1º luglio 2026. Il caso ordinario usa 15 punti base per lato e un'unità monetaria per ordine. Gli altri scenari aumentano i costi, il ritardo e lo slippage degli stop. Si ricalcola la correlazione delle due posizioni e si usa la difesa V6 archiviata.

Il primo test conserva il calendario e i cambi USA di U39 e chiede a ciascun mercato locale di trovare un ETF replicante con le soglie U20. Si usa il catalogo storico TR completo, pari a 1.846 ISIN marcati negoziabili nell'archivio. Il miglior proxy viene stimato soltanto su prezzi noti prima dell'apertura locale. I 120 confronti con il proxy del segnale USA originale hanno riprodotto esattamente scelta, tracking e correlazione archiviati. Quando una nuova replica passa e cambia davvero il titolo, si aggiorna anche la condizione usata per il ripiego U38.

Il test diretto usa i punteggi U19 LOCAL archiviati. I Top2 dei 175 gruppi mensili Europa/TR sono riprodotti dall'archivio dei punteggi. La regressione è addestrata sui rendimenti relativi a 21 sedute dei candidati della rosa originale, con eventuali esclusioni per mancanza di quotazioni e al massimo dieci titoli. La banca dei rendimenti vede solo episodi già maturati. Nel controllo esteso l'ETF già in portafoglio può entrare come termine di confronto. La selezione di un nuovo acquisto resta fra i dieci originali. In questo controllo si conservano le quote al benchmark di U38.

## Risultato economico verificato

| Regola | Europa CAGR / MaxDD | Trade Republic CAGR / MaxDD |
|---|---:|---:|
| U38 | 25,58% / −25,42% | 28,61% / −26,58% |
| U39 USA con modello dei vicini, trasferito | 25,04% / −25,42% | 28,70% / −26,59% |
| U39 USA ristretto al Top10, trasferito | 25,86% / −24,71% | 24,73% / −25,75% |
| Modello locale con vicini, solo nei ripieghi | 25,28% / −25,42% | 28,61% / −26,58% |
| Modello locale con vicini e confronto diretto con l'ETF posseduto | 25,86% / **−21,92%** | 26,16% / −24,20% |

Delle 22 sostituzioni USA del modello con vicini, **2** diventano nuove posizioni proposte in Europa e **9** su TR. Il modello USA addestrato sul Top10 produce 21 sostituzioni, di cui 4 utilizzabili in Europa e 19 su TR. Quest'ultimo dato indica che trovare una replica è una condizione di eseguibilità. Le 19 proiezioni TR riducono di 3,88 punti il CAGR ordinario. Il guadagno ordinario TR del modello principale è +0,09 punti di CAGR. Togliendo il cambio più favorevole scende al **26,05%**, contro il 28,61% di U38.

Per il ramo che agisce soltanto nei ripieghi, il modello locale TR vede cinque confronti nella finestra con supporto predittivo e applica zero sostituzioni. Due ETF già proposti sono fuori dalla rosa utilizzabile e le altre differenze stimate restano sotto soglia. Il controllo esteso confronta anche l'ETF già posseduto quando ha un punteggio disponibile. Su TR esegue 15 cambi nominali, abbassa il drawdown di 2,38 punti, e riduce il CAGR di 2,45 punti nel caso ordinario. Con il vincolo aggiuntivo che un sostituto deve preservare la replica, il CAGR è 26,94%.

### Europa e la prova sugli stessi ingressi

Il ramo locale esteso proposto dal modello dei vicini migliora il CAGR ordinario di 0,28 punti in Europa. Il guadagno di CAGR è positivo nei quattro scenari. Il drawdown migliora da 25,42% a 21,92%. **Otto delle dodici scelte casuali** negli stessi mesi ottengono un CAGR più alto. Il CAGR mediano dei conti casuali è 26,26%, con drawdown mediano del 22,44%. I modelli a soli prezzi e con vicini riassegnati hanno drawdown ordinario intorno al 21,97%.

Nel replay effettivo senza la migliore sostituzione il CAGR europeo scende al **24,54%** e il drawdown risale al **24,72%**. Togliendo le tre migliori sostituzioni, il CAGR scende al **23,11%** e il drawdown risale al **25,38%**. Le omissioni sono stress a posteriori. I conti possono quindi segnalare date in cui ridurre la dipendenza dall'ETF originario. Il vantaggio nella scelta precisa del nuovo ETF resta da dimostrare.

## Controllo della previsione nella rosa locale

A 21 sedute, sulle date con almeno cinque esiti osservabili, lo Spearman medio in Europa è 0,110 per U19 nativo, 0,074 per il modello a soli prezzi, 0,006 con i vicini reali e 0,095 con i vicini riassegnati. Il modello con vicini è misurato su 44 date.

Su TR, su 43 date, lo Spearman medio è −0,027 per il nativo, −0,028 per i soli prezzi e +0,008 con i vicini reali. Il confronto sui soli ripieghi TR ha cinque date. L'incidenza dei titoli con esito nel miglior quintile e il rendimento dei titoli scelti non evidenziano un miglioramento generalizzabile.

## Decisione e limiti

**U38 rimane il riferimento in Europa e Trade Republic.** L'esperimento locale europeo è utile per indagare quando la seconda posizione merita di essere rivista. Le sostituzioni USA restano un ramo di ricerca sul mercato di origine. La finestra comparabile di questo test termina il 1º luglio. Dopo quella data gli archivi disponibili hanno un universo TR diverso e non comprendono la stessa graduatoria locale U19 su entrambi i mercati. Il confronto di luglio–ottobre del test USA appartiene quindi alla sola verifica U39 USA.

La ricerca usa dati storici e cataloghi archiviati, con gli stessi limiti U38 su liquidità, aggiustamenti e prezzi simulati. Escludere il cambio più favorevole è una verifica di concentrazione. Le epoche sono note alla ricerca. Le decisioni mensili conservano separazione temporale tra caratteristiche e risultati osservati, verificata anche perturbando le quotazioni future.
