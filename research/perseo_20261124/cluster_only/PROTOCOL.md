# Perseo — addestramento di primo livello sui cluster

Test retrospettivo separato da U27. Obiettivo: verificare se i rendimenti dei cluster permettono di scegliere in anticipo l'esposizione del mese successivo. Nessuna decisione del modello riguarda un singolo ticker.

## Definizione dei cluster

Primo giorno di mercato del mese. Usa le 126 variazioni giornaliere dei prezzi chiusi prima dell'apertura. Valuta soltanto fondi con storico osservato e continuità sufficiente. Per Trade Republic usa la whitelist tradabile U19 e, se disponibile, turnover storico mediano di almeno 100.000 EUR sulle ultime 63 sedute. Replica il metodo gerarchico complete-link OLC109 con distanza 1 − correlazione e soglia 0,85. Un cluster contiene almeno due ticker. Il controllo Europa usa la tassonomia economica EU165 archiviata, esclude i singoletti e si riaddestra sul proprio dataset. In entrambi i casi la composizione è fissata per l'intero intervallo.

## Addestramento e calendario

Una riga è un cluster disponibile a una data. Le feature sintetizzano rendimenti, ampiezza dei rialzi, dispersione, volatilità, drawdown, correlazione e regime di mercato, usando solo chiusure precedenti. Il modello non riceve ticker, nomi di gruppo o identificatori persistenti. Il risultato da apprendere è il rango del rendimento futuro del cluster equiponderato, da apertura ad apertura il mese seguente. I due candidati fissati sono Ridge lineare e HistGradientBoosting, con loss quadratica sul rango e iperparametri fissi. Per i cluster per correlazione si addestra insieme sui tre panieri con peso uniforme per paniere-mese; per la tassonomia si usa solo EU.

Ogni mese si rifà il fit sugli ultimi 48 mesi maturati. L'apertura che chiude un'etichetta deve precedere strettamente l'apertura relativa alla scelta nuova. Occorrono almeno 24 mesi distinti disponibili prima della prima previsione per ciascuna famiglia di clustering. Previsioni confrontate sulle stesse date e sui medesimi cluster. Rendimenti del mese in cui si ricostruisce la composizione esclusi dal fit fino alla maturazione completa.

## Verifica

Riferimenti fissati: media equiponderata dei cluster, momentum 21 sedute, media dei ranghi momentum 21/63/126. Metrica economica principale: extra rendimento lordo mensile Top2 rispetto al momentum combinato. Si misurano anche Top1 vincente e confronto al caso, Top1 nel quartile migliore, rank IC, sottoperiodi comuni, rendimenti e drawdown dei portafogli Top2. I portafogli usano la stessa regola neutrale per tutti i selettori: al massimo due ETF per cluster selezionati per turnover disponibile; in assenza di volumi, osservabilità recente e ordine alfabetico come spareggio. Le etichette e le metriche informative restano medie di tutti i membri. Costi da 1 unità per ordine più 15 o 30 punti base per lato, apertura mensile di esecuzione, ritardi su titoli senza apertura osservata. L'equal weight fra cluster resta riferimento lordo informativo.

Bootstrap appaiato a blocchi di sei mesi per l'extra Top2, con intervalli nominali e simultanei fra modelli e panieri. Diagnostica per veri mesi separati, non per righe ETF o cluster. Un vantaggio storico richiede un confronto credibile con momentum su più periodi; un solo tasso di successo elevato o un singolo paniere non bastano. Nessuna selezione intra-cluster appresa in questa campagna.

## Controllo con i cluster storici di Perseo

Prima dei replay, aggiunto il controllo sui cluster storici P0 di OLC07 per USA ed Europa e sulle assegnazioni U19 di Trade Republic agli ancoraggi UE. Per ogni decisione si usa l'ultima composizione archiviata con data pari o precedente alla chiusura limite. Si addestrano i due modelli su questa famiglia per conto proprio, aggregando i tre panieri come nel test per correlazione. La tassonomia dei gruppi economici EU165 rimane il terzo controllo, limitato all'Europa. In tutte le famiglie si richiedono almeno quattro cluster confrontabili per mese dopo la rimozione dei singoletti.

Il controllo preliminare di copertura delle quotazioni, prima di calcolare i risultati dei modelli, ha mostrato che la finestra interamente priva di buchi eliminava quasi tutto l'universo europeo in diversi mesi. Si richiede il 90% di chiusure osservate in 127 sedute e si propaga l'ultima chiusura osservata per al massimo due sedute consecutive. La finestra residua deve essere completa per costruire la correlazione. La regola vale per tutti i gruppi. Le aperture utilizzate per l'esecuzione devono essere osservate secondo la maschera disponibile. In assenza della maschera americana si usa l'eleggibilità dei prezzi congelati finiti e positivi.
