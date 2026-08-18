# Politica panieri e cluster

| Componente | Titanium V2 ufficiale/parity | Successore S3B/Opportunity |
|---|---|---|
| Panieri | 500 membership ufficiali congelate | Può usare un nuovo universo, ma non può chiamarsi replica V2 |
| Struttura paniere | 24 ETF, 4 per ognuna delle 6 categorie macro statiche | Da dichiarare e versionare separatamente |
| Ranking base | `TIT_R` autenticato | Modello retrained/versionato |
| Cluster dinamici | Non determinano panieri o selezione base | Ricalcolati mensilmente: difensivi fissi + 7 cluster PCA/balanced K-means |
| Gate storico | 56.500/56.500 selezioni identiche | Confronto diagnostico, non requisito di identità |

La risposta alla domanda “stesso numero di ticker negli stessi cluster?” è quindi: sì per le **sei categorie macro statiche** (4 per categoria), no per gli **otto cluster dinamici S3B**. La precedente live aveva ricalcolato S3B; non lo aveva importato tout court da un artefatto ufficiale congelato.
