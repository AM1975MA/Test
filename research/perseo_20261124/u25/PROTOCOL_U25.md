# Perseo U25 — selezione locale quando manca un proxy

Protocollo congelato prima del replay. U24 PROFIT_RAMP a regola fissa è il riferimento di ricerca. Il controllo U20 resta il replay BASE di U24. L'obiettivo è ridurre la perdita Trade Republic 2020–2022, conservare il guadagno europeo dopo i costi e controllare che il risultato USA e i drawdown complessivi reggano.

Tutti gli interventi avvengono al calendario di proposte U20 (79 decisioni per mercato). I due ranghi locali sono quelli congelati U20, disponibili al momento di ogni decisione. Negli USA la replica è l'identità: le regole riservate ai proxy mancanti equivalgono a U24. La regola universale può intervenire anche negli USA. Esposizione macro, alternativa difensiva V6 U24, stop e rampa rimangono fissati. Nel caso di sostituzione degli ETF si ricostruiscono i segnali PROFIT_RAMP e le date in cui il portafoglio cambia.

## Regole

- LOCAL_CONTROL: sceglie il paio locale su EU e TR alle date U20. Controllo della qualità della selezione locale su quella stessa cadenza.
- FALLBACK_RELATIVE: su uno slot senza replica, interviene se il titolo U24 perde rispetto al benchmark sia a 21 sia a 63 sedute. Cerca tra i due titoli locali il migliore con trend relativo normalizzato maggiore di 0,5 e almeno 0,5 sopra quello corrente.
- FALLBACK_RETAIN: applica lo stesso criterio includendo il corrispondente titolo del portafoglio proposto al precedente evento.
- FALLBACK_DEFEND: se uno slot senza replica ha ritorni sia assoluti sia relativi negativi a entrambe le scadenze, usa il benchmark se il suo ritorno a 63 sedute è positivo, altrimenti la liquidità.
- PAIR_SWITCH: se almeno uno slot è senza replica, valuta il paio locale. Lo usa se entrambi i trend relativi medi U24 a 21/63 sono negativi e la media dei punteggi locali è maggiore di 0,5 e almeno 0,5 sopra U24.
- UNIVERSAL_SWITCH: stesso confronto tra coppie senza il requisito dello slot senza replica.

Il punteggio è la media dei due log-rendimenti relativi (21 e 63 sedute), ognuno diviso per la volatilità giornaliera relativa stimata sulle ultime 63 sedute e scalata alla sua finestra. Tutti i prezzi e le maschere sono aggiornati alla chiusura precedente. Servono almeno 50 variazioni relative valide, prezzo osservato alle estremità delle finestre e almeno il 90% di osservazioni negli ultimi 63 giorni per i nuovi titoli locali. Una scelta alternativa duplicata viene esclusa per le regole per slot. Gli ETF cash non competono nel punteggio. In assenza di evidenza vale la proposta U24.

## Valutazione

Commissione fissa di 1 unità per ordine, più 15/30 bp per lato. Stesse aperture e prezzi congelati U24, orizzonte 2 gennaio 2020–1 luglio 2026. Stress con 15 bp e una seduta di ritardo come U24. Tabella completa per tre panieri, per anno e per i sottoperiodi U24. Il ritardo interessa le decisioni e conserva la protezione originale intraday. Confronti appaiati su mesi e bootstrap simultaneo della famiglia, diagnostici sullo storico già esplorato. Pubblicazione di tutte le varianti, parità dei replay U20/U24, verifica contabile e invarianza dei nuovi segnali a perturbazioni future. Nessuna modifica a configurazioni operative.
