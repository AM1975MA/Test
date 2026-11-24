# Perseo — cluster come contributo al ranker USA

Protocollo fissato prima di generare i risultati. Il controllo è U27 CORR70 sul paniere USA149. I punteggi nativi sono TOP2_CONTEXT_REVALUE_FUSION dall'archivio OLC104. Il controllo a peso zero deve ricostruire esattamente le coppie native in tutti i 57 mesi di valutazione. Le previsioni dei cluster sono i Ridge comuni già salvati per gli otto cluster storici USA. L'analisi principale usa la versione con copertura TR recuperata; la prima versione dei Ridge è una sensibilità.

## Regole

Tutti i ticker eleggibili del ranking nativo restano candidati. La classifica nativa si porta su [0,1] per rango, con spareggio originale. La classifica degli otto cluster si porta sulla scala fra −0,5 e +0,5. Punteggio finale uguale al rango nativo più il rango centrato del cluster moltiplicato per un coefficiente, senza rinormalizzazione dei pesi di portafoglio. Per un ticker senza cluster disponibile il contributo è zero. Le appartenenze OLC07 e le predizioni Ridge devono risalire al massimo alla chiusura prima del trade. Si scelgono i due ticker migliori, anche dello stesso cluster o di cluster diversi, con pesi 50/50.

- RIDGE10 è l'esperimento principale con coefficiente 0,10.
- RIDGE05 e RIDGE20 misurano la sensibilità al coefficiente.
- MOM10 usa lo stesso coefficiente e classifica i cluster per momentum passato a 21 sedute.
- RIDGE10_ORIGINAL usa il Ridge precedente alla sensibilità di copertura TR.
- RAW10 usa il punteggio nativo scalato per lo spread 10º–90º percentile e somma lo stesso contributo Ridge a 0,10. Verifica se la trasformazione in ranghi cambia il risultato.

## Conto e verifica

Il conto inizia a gennaio 2020. Prima del 1º ottobre 2021 coincide con U27; si misura anche la finestra attiva 1º ottobre 2021–1º luglio 2026 con le posizioni in continuità. Il motore è PROFIT_RAMP e CORR70, rigenerati sulle coppie effettivamente proposte. Flusso macro e alternativa difensiva V6 congelati ai valori U27 in tutti i conti per isolare l'effetto sul ranking. Nessun nuovo fit o scelta del coefficiente sui rendimenti visti.

Capitale iniziale USD 10.000, quote frazionarie, costi da USD 1 per ordine più 15 bp/lato, 30 bp, ritardo di una seduta e 30 bp con ritardo. Lo stress di ritardo segue U27 e conserva gli stop originali tempestivi. Si misurano CAGR, drawdown massimo, anni, quante coppie cambiano, mesi favorevoli e sfavorevoli, ordini, mesi influenti e valore delle sostituzioni apertura-apertura prima delle protezioni. Confronto appaiato dei log-rendimenti mensili con intervalli a blocchi di sei mesi e correzione simultanea di famiglia. Verifiche di parità rispetto a U27 pubblicato, pianificazione point-in-time e ricostruzione indipendente dagli ordini. Il risultato resta una prova retrospettiva sullo stesso storico.
