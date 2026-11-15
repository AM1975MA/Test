# OLC109 — Selezione per gruppi, allocazione e protezione

## Autorità e obiettivo

Il 15 novembre 2026 l'utente ha autorizzato la prosecuzione autonoma della ricerca e la scelta dei test. L'obiettivo di ricerca è CAGR almeno 30% annuo, drawdown campionato non peggiore di −25%, Calmar almeno 1, senza leva di conto o posizioni corte e con non più di 24 giorni di negoziazione annui. Questi sono criteri di confronto storico, non garanzie. Le scelte sotto sono dell'analista, non parametri comunicati dall'utente.

## Evidenza precedente e approcci

OLC108 V3: 2.096 ETF EUR, 76 percorsi, audit indipendente; nessuno supera gli obiettivi. DUAL21 mensile CAGR22,375%, DD−43,553%; LEADERS14,517%, stesso DD; vantaggio concentrato nel2020; LAG2 annulla il vantaggio. Il peggior ribasso comune è la doppia esposizione ad azioni blockchain DAVV/BLCH dicembre2023–gennaio2024. Regole SMA200 non avrebbero impedito quel ribasso. Non si cancella2024.

La lettura del repository AM1975MA/Test ha verificato: OLC74 e OLC99 non sostengono il riordinamento Ridge dei Top10 né i pesi appresi da controfattuali sullo stesso conto; OLC102/103 non sostengono una maggiore stabilizzazione dei punteggi. OLC105 ha già fallito un trasferimento ancorato del modello FUSION. Il modello originale richiede checkpoint e contratti specifici: non viene sostituito tacitamente da un'altra formula. I risultati quantitativi di tali studi non sono confrontabili causalmente con il dataset V3 odierno. Le copie e le fonti precise sono in research/prior_repo.

Si testa quindi una famiglia distinta: raggruppamento causale dei rendimenti per ridurre le esposizioni duplicate, con controlli per isolare liquidità, gruppo, punteggio, allocazione e protezione. Nessun modello supervisionato, selezione automatica del vincitore o ottimizzazione di soglie viene aggiunto.

## Dati e contabilità immutabili

Input principale: OLC108 V3 source/data/XETRA_EUR_ETF.npz, SHA256 14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96. 2.096 ISIN, valuta di quotazione EUR, osservazioni2019-02-01–2026-10-30. Pannello derivato dal catalogo Xetra attuale: non è un universo storico privo di survivorship bias. Si mantengono le cinque quarantene di serie e le correzioni V3. Il catalogo copre ETF quotati su Xetra in EUR, non tutti gli ETF mondiali. La valuta EUR non elimina il rischio cambio sottostante.

Il nuovo pannello di controvalore usa raw Close×Volume dalle copie già archiviate; si ammette il valore soltanto dove observed V3 è vero, altrimenti zero. Mediana mobile delle ultime63 sessioni, includendo gli zeri; nessun dato futuro. La soglia EUR100.000 è un filtro di ricerca sugli scambi della singola sede, non una certificazione della liquidità complessiva dell'ETF. L'idoneità precedente resta: almeno253 osservazioni effettive totali, almeno241/253 recenti, ultima osservazione entro5 giorni di calendario. I nuovi filtri di liquidità richiedono anche Close osservato nella data del segnale.

Periodo comune 2020-03-02–2026-10-30, EUR10.000 iniziali, unità economiche frazionarie su prezzi aggiustati, liquidità con rendimento0, imposte escluse. Nessuna leva/short. Decisioni a Close, esecuzione Open successivo; nessun riempimento di Open mancante; vendite prima degli acquisti, cassa non negativa, banda di ribilanciamento3%. Stessa base contabile di OLC108. L'Open disponibile è filtrato usando il volume del giorno completato: convenzione retrospettiva di qualità del fornitore, non informazione nota all'apertura. La disponibilità storica dei fattori di aggiustamento non è certificata. I ritardi sono stress, non rimedi completi a questi limiti.

## Gruppi causali e rappresentanti

A ogni fine mese, esclusivamente sugli ETF idonei e liquidi, si calcola la correlazione Pearson delle ultime126 sessioni di log-rendimenti; il riempimento di Close segue la stessa convenzione causale V3. Clustering gerarchico complete-linkage con distanza1−correlazione e taglio0,15 (correlazione minima di gruppo0,85). Ordine iniziale ISIN; parità risolte con ISIN. Le statistiche di gruppo sono mediane dei punteggi dei componenti: ciascun gruppo ha un voto nella graduatoria, indipendentemente dal numero di ETF. Il rappresentante è il componente con la maggiore mediana di controvalore63, parità ISIN. La composizione varia nel tempo; non sono categorie settoriali certificate. Gruppi singoli sono ammessi salvo specifica ablazione PEERS2. Classi acc/dist e diversi emittenti non sono osservazioni economicamente indipendenti.

Oltre al clustering, i rappresentanti scelti devono avere correlazione126 non superiore a0,85 con ogni altro rappresentante selezionato. Si scorre la graduatoria fino a riempire2 o4 posti. Ogni posto pesa1/K; posti non riempiti restano in cassa. Un gruppo non compare due volte.

## Segnali e pesi

LEADERS e DUAL21 di controllo sono esattamente quelli di OLC108. Le varianti LIQ applicano solamente il filtro di liquidità alla maschera idonea, ricalcolando le graduatorie relative nel nuovo insieme.

LEADERS di gruppo: mediana del log-rendimento252. DUAL21 di gruppo conserva il leader principale e sostituisce l'ultimo posto con un gruppo emergente, se presente e poco correlato ai gruppi conservati. Il gruppo emergente deve avere mediana log-rendimento21 positiva, percentile21 almeno2/3, percentile del precedente105 diviso5 inferiore a2/3, accelerazione21 positiva, rappresentante sopra SMA63. È ordinato per accelerazione; deve battere su21 il gruppo uscente. Sono esclusi tutti i gruppi già selezionati. Il confronto è fatto sul primo emergente compatibile; se non batte il gruppo uscente non si cerca un vincitore alternativo. Il peso rimane invariato.

TREND: selezione annuale limitata a gruppi con mediana252>0, mediana63>0 e rappresentante sopra SMA200.

SLOW: stessa idoneità TREND, graduatoria della mediana di 0,5×[(m126−m21)×252/105+(m252−m21)×252/231], escludendo l'ultimo mese dalla misura di persistenza. SLOW_RVOL divide il punteggio di gruppo per max(mediana volatilità63 annualizzata,0,05). SLOW_DUAL21 applica la sostituzione emergente ai leader SLOW, fra gruppi TREND.

RESID mantiene gli stessi due ETF di CLUSTER_DUAL21 e pesa inversamente alla volatilità residua126 rispetto a SXR8 (OLS con intercetta, un solo fattore). Volatilità residua annualizzata minima0,05; pesi tra25% e75%, somma1 se due gruppi presenti. Con un solo posto si mantiene il peso0,5. Non replica il paper sui rendimenti residui di singole azioni né il modello2fattori del vecchio progetto.

REVERT mantiene i due ETF e assegna65% a quello con minore log-rendimento21,35% all'altro; parità50/50. Non è una previsione stimata. CASH mantiene i titoli scelti, azzerando i posti il cui rappresentante è sotto SMA200 o ha m63<=0, senza cercare sostituti.

RISK15/RISK20 mantengono la selezione CLUSTER_DUAL21 e scalano soltanto verso il basso i pesi a volatilità obiettivo15%/20%; riduzione giornaliera se la volatilità stimata supera1,25×obiettivo, come nell'engine precedente. Nessuna leva.

EXIT63 e TRAIL15 mantengono la selezione indicata, ma azzerano a ogni decisione mensile le posizioni che soddisfano il criterio di uscita e controllano le posizioni anche al Close dell'ultima sessione della settimana. EXIT63: prezzo<SMA63 e m21<0. TRAIL15: prezzo/massimo Close delle ultime63 sessioni−1<=−0,15. Le uscite settimanali vendono solamente e non aprono nuove posizioni; rientri soltanto mensili. Decisione mensile prevale sul controllo settimanale. Nessuna istruzione o allerta se il controllo non richiede riduzione. Le riduzioni maturate sono limitate alle posizioni effettive anche in presenza di gap/ritardi.

## Matrice congelata

22 configurazioni ×5 scenari =110 percorsi finanziari; unico universo ETF EUR V3.

1. PASSIVE (SXR8)
2. LEADERS
3. DUAL21
4. LIQ_LEADERS
5. LIQ_DUAL21
6. CLUSTER_LEADERS
7. CLUSTER_DUAL21 — confronto principale dichiarato
8. CLUSTER_TREND
9. CLUSTER_SLOW
10. CLUSTER_SLOW_RVOL
11. CLUSTER_SLOW_DUAL21
12. CLUSTER_DUAL_RESID
13. CLUSTER_DUAL_REVERT
14. CLUSTER_LEADERS4
15. CLUSTER_DUAL4
16. CLUSTER_DUAL_CASH
17. CLUSTER_DUAL_RISK15
18. CLUSTER_DUAL_RISK20
19. CLUSTER_DUAL_EXIT63
20. CLUSTER_SLOW_EXIT63
21. CLUSTER_DUAL_PEERS2
22. CLUSTER_DUAL_TRAIL15

Scenari per tutti: BASE(EUR1+15bp/lato,lag0); ZERO_COST(0,0,0); DOUBLE_COST(EUR2+30bp/lato,lag0); LAG1(EUR1+15bp,1sessione extra); LAG2(EUR1+15bp,2extra). Nessuna variante viene esclusa dalla tabella se deludente.

## Verifiche e valutazione

Prima dei nuovi rendimenti: protocollo scritto e hash registrato; test sintetici per causality/prefix, duplicati, gruppi singoli, rappresentante liquido, vincoli dei pesi, protezione con gap e Open mancante. Tre baseline per5scenari devono riprodurre i precedenti percorsi OLC108 dove disponibili. Audit contabile indipendente di tutti110 percorsi: cash, unità, costi, NAV, cronologia, target maturato, Open valido, attribuzione P&L. Verifica indipendente dei segnali e campionamento dei cluster. Audit descrittivo dell'età dei prezzi e partecipazione agli scambi per le posizioni effettive; controllare eventuali nuove anomalie di fonte solo se emergono evidenze concrete.

Si riportano CAGR, DD Open/Close campionato (non intraday completo), Calmar, costi, giorni operativi, esposizione e rendimenti annuali compreso2024. Segmenti descrittivi:2021–2024,2025–2026,2021–2026;2020 separato. Confronti accoppiati primari CLUSTER_DUAL21 vs LIQ_DUAL21 e vs DUAL21: bootstrap a blocchi mobili circolari di6mesi,10.000 repliche, seed109, sulla differenza di log-rendimenti mensili; intervallo95% descrittivo, non correzione per tutte le prove o prova di ripetibilità futura. Nessun risultato trasforma il passato già esplorato in holdout incontaminato.

Il successo richiede anzitutto tutti i vincoli numerici nello scenario BASE; ritardi/costi, stabilità annuale e concentrazione dei contributi possono far scartare un successo nominale. Il 30% rimane obiettivo, non criterio con cui modificare soglie dopo la prova. Nessuna operazione reale, modifica all'automazione OLC100 o pubblicazione remota.

## Fonti metodologiche (motivazioni, non validazione di questa strategia)

- Moskowitz, Ooi, Pedersen, Time Series Momentum,2012: https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum
- Moskowitz, Grinblatt, Do Industries Explain Momentum?,1999: https://www.aqr.com/insights/research/journal-article/do-industries-explain-momentum
- Daniel, Moskowitz, Momentum Crashes,2014/2016: https://www.nber.org/papers/w20439
- Blitz, Huij, Martens, Residual Momentum,2011: https://repub.eur.nl/pub/22252/

I paper riguardano universi, strumenti e spesso portafogli long/short diversi: non stabiliscono che queste regole long-only su ETF EUR raggiungano30%.
