# OLC110 — Protezione, cash e rientro sulle opportunità

## Mandato e stato della conoscenza

Il 15 novembre 2026 l'utente ha chiesto di salvare OLC109 in AM1975MA/Test e continuare con protezione, cash e rientro tempestivo su rebound o nuove opportunità. L'autorizzazione precedente dà libertà di sviluppo e test; non sono necessarie altre approvazioni per questa ricerca. OLC109 è salvato al commit `12908133d98dba91d09cdb1a5266a64421d9d075`, branch `research/olc109-freeze-20261115`.

OLC109 DEDUP_DUAL_TREND_OPP è il selettore accettato: CAGR BASE 25,7526%, DD Open/Close -37,9205%. I 200 percorsi precedenti sono già osservati. Questo studio è esplorativo e adattivo rispetto a tali evidenze; non esiste un holdout incontaminato nel 2020–2026. Non si deve dichiarare una superiorità prospettica né un ottimo globale.

Le vecchie protezioni EXIT63/TRAIL15 erano applicate a DEDUP_DUAL21, non a TREND_OPP. I loro risultati sono una diagnosi preliminare, non un confronto controllato con il candidato attuale. Le analisi descrittive delle perdite e dei recuperi precedono i nuovi risultati e sono conservate in `research/forensics/`.

## Obiettivo

Misurare separatamente uscita, recupero dello stesso investimento, esposizione parziale e acquisto di opportunità emergenti usando cash effettivo. Il CAGR 30% rimane un obiettivo; DD e Calmar sono misure, non soglie di esclusione. La promozione di ricerca richiede valutare insieme CAGR, DD, costi, ritardi, anni e costo della liquidità. Un minor DD ottenuto soltanto con una minore esposizione non dimostra capacità di timing.

L'ipotesi primaria è **EXIT21_STAGED_FRESHW**. Tutti gli altri casi sono controlli o alternative dichiarate, non occasioni indipendenti di conferma. Tutte le 13 configurazioni e i sei scenari devono essere riportati, anche se sfavorevoli. Nessuna ottimizzazione di soglie dopo i risultati in questa iterazione.

## Input e convenzioni invarianti

- Pannello V3 OLC109 di 2.096 ETF EUR Xetra, SHA-256 `14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96`.
- Liquidità storica SHA-256 `b95fa3d67837fa06c5705aa4aea09807d396464ab44ec1671031d797b57f4485`.
- Periodo 2 marzo 2020–30 ottobre 2026, EUR 10.000 iniziali, cash con rendimento zero, imposte escluse, unità economiche frazionarie, nessuna leva di conto o short.
- Selettore DEDUP_DUAL_TREND_OPP identico; liquidità mediana 63 sedute EUR 100.000, correlazione 126 sedute <=0,85, due posti nominali al 50%.
- Decisioni a Close; esecuzione successiva, nessuna vendita retroattiva al prezzo del segnale o alla soglia di stop; costi su ogni ordine; banda ordinaria del 3%.
- Le quarantene precedenti restano invariate. Catalogo attuale, vintage degli aggiustamenti e disponibilità degli Open non sono certificati point-in-time. L'Open originario usa la disponibilità accettata che dipende anche dal volume della giornata completata.

## Scenari: 13 configurazioni × 6 = 78 percorsi

| Scenario | Commissione | Costo proporzionale per lato | Esecuzione |
| --- | --- | --- | --- |
| BASE | EUR 1 | 15 bp | Primo Open accettato da T+1 |
| ZERO_COST | 0 | 0 | Come BASE |
| DOUBLE_COST | EUR 2 | 30 bp | Come BASE |
| LAG1 | EUR 1 | 15 bp | Una seduta extra |
| LAG2 | EUR 1 | 15 bp | Due sedute extra |
| NEXT_CLOSE | EUR 1 | 15 bp | Primo Close accettato da T+1 |

NEXT_CLOSE è uno stress alternativo di prezzo/esecuzione. Usa C accettati come quotazioni eseguibili e la maschera di Close osservati. I valori intermedi denominati nav_open nel motore sono in questo scenario marcature al Close prima dei costi; il DD è quindi su Close pre/post costi, non sul percorso intraday. Non elimina survivorship o vintage degli aggiustamenti. Gli altri cinque scenari mantengono esattamente il pannello e le convenzioni OLC109.

## Matrice dichiarata

1. BASE: selettore originale mensile, nessuna protezione.
2. STATIC_HALF: stessi target mensili moltiplicati per 0,50.
3. STATIC_75: stessi target mensili moltiplicati per 0,75.
4. REFRESH_WEEKLY: stesso selettore completo ricalcolato settimanalmente, nessuna protezione.
5. EXIT21_MONTHLY: uscita giornaliera, rientro SLOW solo al ribilanciamento mensile.
6. EXIT21_SLOW: stessa uscita, rientro SLOW giornaliero.
7. EXIT21_FAST: stessa uscita, rientro FAST al posto pieno.
8. EXIT21_STAGED: stessa uscita, rientro FAST a metà posto, pieno su conferma SLOW.
9. EXIT63_STAGED: cambia soltanto la regola di uscita da NORMAL rispetto a 8.
10. TRAIL15_STAGED: cambia soltanto la regola di uscita da NORMAL rispetto a 8.
11. VOLTRAIL_STAGED: come 10 con ampiezza legata alla volatilità e stesso massimo 63.
12. EXIT21_STAGED_FRESHW: come 8, nuove opportunità solo nei posti liberi, ricerca settimanale.
13. EXIT21_STAGED_FRESHD: come 12, ricerca giornaliera.

## Regole di prezzo, tutte da osservazioni <= T

`m5` e `m21` sono log-rendimenti a 5 e 21 sedute; SMA10/21/63 medie semplici; `high5_prev=max(C[T-5:T])` esclude il Close corrente; `peak63=max(C[T-62:T+1])` lo include. Sigma21 è deviazione standard campionaria dei 21 log-rendimenti giornalieri, senza annualizzazione.

Uscite da stato NORMAL:

- EXIT21: C<SMA21 e m5<0.
- EXIT63: C<SMA63 e m21<0.
- TRAIL15: C/peak63-1 <= -0,15.
- VOLTRAIL: C/peak63-1 <= -width, con `width=clip(2,5*sqrt(5)*sigma21,0,05,0,20)` congelata al segnale di ingresso in NORMAL. Il calo osservato non allarga la soglia della posizione già aperta. Il massimo ha lo stesso orizzonte 63 di TRAIL15; nessuna taratura ex post.

SLOW: C>SMA63 e m21>0 **e assenza dell'uscita NORMAL della configurazione**. Per VOLTRAIL, l'ammissione deve essere valida anche con la nuova width che verrà congelata. Ciò risolve il possibile conflitto tra trend lungo positivo e allarme breve.

FAST: C>high5_prev, C>SMA10 e m5>0. REBOUND fallisce se C<SMA10 e m5<0. Le uscite hanno precedenza sulla promozione. Non si applica immediatamente l'uscita NORMAL a un nuovo REBOUND ancora sotto una vecchia soglia: il suo stop resta quello breve finché SLOW non conferma.

Segnali e aggiornamenti di stato richiedono Close corrente osservato. Close mancanti non generano nuove conclusioni di prezzo. I mark contabili possono essere riportati causalmente come nel motore precedente.

## Stato del posto e rientro

Ogni posto ha ETF base mensile, ETF correntemente assegnato, stato NORMAL/CASH/REBOUND, livello desiderato, width congelata e indice del primo acquisto effettivo del probe. Due posti non possono intenzionalmente assegnare lo stesso ETF.

Una vecchia identità conservata da un posto CASH già liquidato non è proprietà delle quantità acquistate successivamente dall'altro posto. Alla ricomposizione mensile si conserva prima l'assegnazione attiva, poi l'eventuale uscita non ancora confermata e infine il riferimento CASH originale. Questo mantiene correttamente il probe anche quando lo stesso ETF è passato fra i due posti.

- All'inizio e per un nuovo ETF mensile si entra NORMAL se l'uscita è falsa; altrimenti CASH, senza un rientro FAST sullo stesso primo segnale. Se un ETF attualmente assegnato rimane nel target mensile conserva il proprio stato anche quando cambia l'ordine dei posti; il calendario non annulla una protezione. Il ritorno all'ETF base dopo una sostituzione FRESH è invece un nuovo ingresso mensile quando esso non è più attualmente assegnato.
- NORMAL→CASH: il target di quel posto diventa zero. La vendita avviene soltanto alla quotazione eseguibile successiva. Uno stato desiderato CASH non prova che la vendita sia già stata eseguita.
- Un rientro richiede che sia stata osservata la liquidazione effettiva dell'ETF uscente (quantità <=1e-10 a libro libero), che non ci siano istruzioni pendenti/in coda e che esista cash utilizzabile. Il posto conserva la conferma di essere vuoto: acquisti successivi dello stesso ETF nell'altro posto non sono residui della vendita già completata. Questa regola vale anche quando un prezzo mancante o un ritardo ha impedito la vendita. Un ETF base già impegnato nell'altro posto impedisce soltanto quel rientro duplicato, senza disabilitare la ricerca FRESH del posto vuoto.
- CASH→NORMAL su SLOW: posto pieno, ogni giorno salvo MONTHLY (solo al calendario mensile).
- CASH→REBOUND su FAST nei casi FAST/STAGED: posto pieno per FAST, metà posto per STAGED. SLOW valido ha precedenza e permette il rientro pieno direttamente.
- REBOUND→NORMAL soltanto su SLOW e a una chiusura con indice strettamente successivo al primo acquisto realmente eseguito. Una richiesta non ancora eseguita non può essere promossa. Nessun periodo minimo aggiuntivo è ottimizzato.
- REBOUND→CASH su fallimento breve. Ogni nuovo probe azzera il riferimento al precedente acquisto.

In presenza di istruzioni pendenti o in coda, i prezzi continuano ad aggiornare lo stato desiderato ma **non viene emessa una nuova azione inframensile**. Appena il libro torna libero si emette la differenza residua rispetto all'ultimo target richiesto. Questo evita che un'azione su un posto cancelli involontariamente la parte ineseguita di un altro ordine. Il normale ribilanciamento mensile resta un'istruzione completa e può sostituire le precedenti secondo la maturazione del motore. Il costo di questa prudenza viene misurato negli scenari ritardati.

## Nuove opportunità e cash

Prima si cerca il rientro dell'ETF base del posto. Solo se esso non è ammesso si può riempire un posto effettivamente vuoto con un'altra opportunità. Per FRESHW la ricerca avviene sul calendario settimanale, per FRESHD a ogni Close non mensile. Nessuna sostituzione di un posto ancora investito soltanto perché un concorrente accelera.

Il pool emergente mantiene le condizioni del selettore: liquid_eligible, b21>0, percentile b21>=2/3, percentile a21<2/3, accelerazione21>0, C>SMA63, m252>0, m63>0, C>SMA200. Aggiunge conferma di ingresso C>SMA10 e m5>0. Ordine per accelerazione decrescente, spareggio ISIN crescente. Si scartano ETF già detenuti/assegnati e correlazioni126>0,85 contro tutti i titoli effettivamente detenuti e contro l'altro posto impegnato. Il libro deve essere libero da istruzioni pendenti.

La nuova opportunità parte sempre REBOUND a metà posto, anche se SLOW è già positivo; la promozione richiede una chiusura successiva all'acquisto effettivo. Il sostituto resta assegnato fino all'uscita o al successivo aggiornamento mensile; non viene continuamente risostituito dal ranking. Se esce, il rientro dell'ETF base torna prioritario. Per ogni ammissione si richiede cash superiore al 3% del NAV, coerentemente con la banda minima ordinaria di esecuzione; i target vengono poi limitati al budget realmente disponibile.

## Esecuzione delle azioni mirate

Estendere il motore con un callback di conto che riceve copie di quantità, cash, NAV, ultimi indici di acquisto, stato pending/coda e flag di decisione iniziale/mensile. Nessun accesso a prezzi futuri. Nessun callback deve mutare il conto.

Un'azione inframensile include una maschera immutabile degli ETF coinvolti. **Le quantità degli ETF fuori maschera devono restare identiche**, anche se il loro peso sale tra segnale e apertura. Le quotazioni fuori maschera vengono rese non eseguibili, conservando i loro mark per il NAV. Le vendite precedono gli acquisti, che restano autofinanziati.

I target coinvolti sono limitati al budget disponibile dopo aver preservato le esposizioni non coinvolte. Si memorizza distintamente l'intenzione nominale del posto e il target eseguibile. Se un gap riduce il cash, il core scala gli acquisti; non vende un titolo non coinvolto per finanziarli. Solo i titoli nella maschera possono causare il rinvio di un'azione mirata. Un'azione di sola riduzione non può aggiungere quantità. Initial/mensile mantiene l'istruzione completa e la contabilità precedente.

## Evidenze e verifiche richieste

- Replica identica dei cinque conti BASE OLC109 e regressioni dei 51 test ereditati.
- Test mirati su mask, gap, costi, cash, pending, post-fill probe, collisione SLOW/exit, perseveranza del cash oltre il calendario, opportunità incompatibili e dati futuri perturbati.
- Protocollo e hash del codice/input congelati prima dei 78 rendimenti; nessuna omissione degli anni, incluso il 2024.
- Ricostruzione indipendente di contabilità e target; controlli di causalità dei prefissi, quantità, date, autofinanziamento e immutabilità.
- CAGR, DD, volatilità, esposizione media, giorni cash, turnover, costi, numero di azioni, ritardi; anni, 2021–2024, 2025–2026 e 2021–2026 descrittivi.
- Attribuzione delle decisioni di uscita/rientro su stesso stato: perdite evitate, rebound mancati, costi e gap. Non comporre intervalli sovrapposti come strategia.
- Confronti bootstrap mensili accoppiati descrittivi; no correzione implicita per selezione multipla, no etichette out-of-sample per dati già osservati.

## Fondamento e limiti dell'ipotesi

Kaminski–Lo (2014) mostra che il valore di uno stop dipende dalla dinamica dei rendimenti; Daniel–Moskowitz (2016) documenta rischi particolari del momentum durante i rebound, soprattutto in strutture long/short diverse da questa. Nessun paper dimostra che queste soglie siano ottime per ETF EUR. Fonti e ulteriori critiche sono in `research/design/PROTECTION_DESIGN_REVIEW.md`.

Nessuna operazione reale, modifica di workflow o automazione, messaggio a terzi o modifica di strategie precedenti è parte di questo studio.
