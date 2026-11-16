# OLC109 — Proposta finale: capitale separato per leader a 3, 6 e 12 mesi

**15 novembre 2026. Memo di progetto; nessun nuovo rendimento calcolato.** Il responsabile della ricerca ha scelto la famiglia seguente dopo i primi 160 percorsi. Prima del congelamento, l'utente ha accettato un drawdown maggiore nella fase attuale e rinviato i nuovi modelli di protezione. Questo documento incorpora tale decisione: nessun nuovo controllo RISK15/RISK20, tre controlli TOP1 al loro posto. Non modifica i protocolli o il codice finanziario. Il successivo protocollo congelato dal responsabile è l'autorità esecutiva.

## Decisione e motivo

Testare tre selezioni autonome di leader individuali, a 63, 126 e 252 sedute, e destinare un terzo del capitale obiettivo a ciascuna selezione. Ogni selezione di base detiene fino a tre esposizioni, equiponderate, con i gruppi di correlazione usati esclusivamente per limitare la concentrazione. Tre controlli paralleli, uno per ogni orizzonte, investono invece il 100% nel primo leader. Il punteggio rimane quello dell'ETF effettivamente comprato. L'obiettivo attuale è esplorare rendimento e concentrazione; la costruzione di nuove protezioni è rinviata.

Questa architettura conserva una quota dei leader recenti anche quando il loro rango annuale è ancora basso, senza affidare metà del conto a una sostituzione opportunistica. Una media dei punteggi produce una sola graduatoria e può escludere il vincitore di un singolo orizzonte; la media dei **pesi obiettivo dopo la selezione** gli riserva capitale. Questa distinzione è il meccanismo da falsificare, non una previsione di successo.

Tre approcci ragionevoli, in ordine di ruolo nella prova:

| Approccio | Perché merita una prova | Ruolo scelto |
|---|---|---|
| Leader individuali a 63 o 126 sedute | Il rango annuale può conservare esposizioni la cui leadership più recente è cambiata. | Controlli necessari contro il medesimo selettore a 252 sedute. |
| Capitale diviso fra i tre orizzonti | Riduce la dipendenza da una sola finestra senza stimare pesi o scegliere l'orizzonte vincente dopo il risultato. | Architettura principale `CAPITAL_3H`. |
| Piccola preferenza per il paniere con accelerazione recente positiva | Verifica l'opportunità come allocazione del capitale fra selezioni già ammesse. | Un solo confronto `CAPITAL_3H_TILT`, separato dalla protezione. |

Il paper di Moskowitz, Ooi e Pedersen documenta persistenza su più orizzonti in futures e forward e distingue momentum relativo e assoluto. È una motivazione per confrontare finestre recenti e annuali, non una validazione di questa selezione long-only di ETF o del target del 30%.[W1] La scelta precisa 63/126/252 e dei terzi uguali è una regola di ricerca interpretabile, non una calibrazione ricavata dal paper.

## Controllo delle sovrapposizioni con la ricerca precedente

- `EU165_FACTOR_4V9_README.md` contiene già controlli MOM63/126/252 su piccoli insiemi F4/F9. Cambiare soltanto finestra non sarebbe un meccanismo nuovo; questi tre bracci servono come controlli sul supporto V3 comune.[L3]
- `OLC73_REPORT_IT.md` ha già studiato il 65% al maggiore MOM63 nella coppia ML fissata, senza una regola universalmente migliore nei due mercati. La nuova preferenza riguarda il capitale fra tre selezioni autonome e non va presentata come prova che il momentum di breve periodo determini il peso ottimale.[L4]
- `OLC102_REPORT_IT.md` ha testato medie dei ranghi ML a chiusure giornaliere successive. Qui cambia l'orizzonte economico del segnale e si mescolano pesi dopo selezioni separate, nello stesso istante mensile. La precedente evidenza negativa rimane visibile.[L5]
- Il blocco 1 ha modificato punteggio e rappresentante usando mediane di gruppo; questa proposta usa i gruppi soltanto per il budget di esposizione. Non ripete il ranking delle mediane.[L1]
- Nessun Ridge, target controfattuale, scelta appresa di policy o nuovo trasferimento FUSION è necessario. Le evidenze negative relative a quelle famiglie restano nel riepilogo precedente.[L6]

## Contratto comune dei tre selettori

Riusare il pannello V3, le cinque quarantene, il filtro di osservabilità, il requisito di storia e la mediana di controvalore63 almeno EUR100.000 già dichiarati. È l'universo ampio di ETF quotati in EUR su Xetra disponibile nel pannello, non il sottoinsieme di 29 strumenti. Restano i limiti del catalogo attuale e della disponibilità storica documentati nel protocollo.[L1]

Alla chiusura mensile, mantenere soltanto i candidati con **m252 > 0, m63 > 0 e Close > SMA200**. Questo filtro è comune ai tre bracci: l'unica differenza fra `HORIZON63`, `HORIZON126` e `HORIZON252` è il rendimento logaritmico usato per ordinare i singoli ETF. Non aggiungere un'esclusione dell'ultimo mese o un nuovo filtro su m5.

Per ogni orizzonte H:

1. Ordinare i candidati per mH decrescente; parità per ISIN.
2. Scorrere la graduatoria e ammettere al massimo tre ETF. Nessun gruppo compare due volte e ogni nuovo ETF deve avere correlazione126 non superiore a 0,85 con tutti quelli già selezionati.
3. Usare i gruppi complete-linkage già definiti, calcolati una sola volta alla stessa data sull'universo liquido comune. Non ricalcolare gruppi diversi per ciascun orizzonte; non imporre PEERS2 e non sostituire un ETF con il rappresentante più liquido.
4. Ogni posto ha peso **1/3**. I posti vuoti restano in cassa: nessuna normalizzazione verso il 100% quando mancano candidati.

Il filtro comune sui leader e il passaggio da due a tre posti sono cambiamenti rispetto a `DEDUP_DUAL_TREND_OPP`. Per questo serve il nuovo `HORIZON252`: il confronto con il precedente braccio annuale non isola da solo l'effetto degli orizzonti.

## Media del capitale e limiti di concentrazione

Siano q63, q126 e q252 i vettori dei pesi appena descritti, inclusa la cassa. Definire:

`CAPITAL_3H = (q63 + q126 + q252) / 3`.

Gli ISIN uguali sono sommati prima di generare ordini; un unico conto esegue i flussi netti. Non si mediano CAGR, NAV storici o rendimenti di conti separati; i terzi sono budget obiettivo a ogni decisione, non patrimoni autonomi lasciati derivare.

Il numero di ISIN investiti è al massimo nove. Ogni ETF pesa al massimo 1/3. Soprattutto, **ogni gruppo pesa complessivamente al massimo 1/3**, anche quando finestre diverse scelgono wrapper differenti del medesimo gruppo: ciascun qH contiene al massimo un suo membro con peso 1/3, e una combinazione convessa preserva il limite.

Anche qualsiasi coppia con correlazione126 > 0,85 ha somma dei pesi obiettivo non superiore a 1/3. Ogni selettore ne ammette al massimo uno; la stessa disuguaglianza rimane vera nella media. Più in generale ciò vale per un insieme i cui membri sono tutti reciprocamente sopra 0,85. Non costituisce una certificazione di indipendenza economica: esposizioni correlate in modo imperfetto e correlazioni future diverse restano possibili.

**Il limite riguarda i target.** La banda operativa del 3%, i prezzi di esecuzione, i costi e la deriva dei prezzi fra ribilanciamenti possono lasciare pesi effettivi superiori a 1/3. Conservare il motore comune e misurare queste eccedenze; non dichiarare un limite continuo garantito o introdurre vendite supplementari senza registrare il cambiamento di contratto.

## Opportunità: scelta finale del responsabile

La proposta iniziale considerava trasferire una piccola quota a un singolo ISIN già selezionato, finanziata dagli altri gruppi e soggetta a vincoli lineari. Il responsabile ha preferito una **variazione dei pesi fra i tre panieri**, più semplice da riprodurre e con i limiti di gruppo preservati automaticamente. Questa è la sola variante da implementare.

Per ogni H, usare soltanto i componenti selezionati oggi, senza ricostruire un ipotetico passato finanziato del paniere:

`bH = media di m21 dei componenti presenti`

`aH = media di (m126 - m21) / 5 dei componenti presenti`

`accH = bH - aH`.

Le medie sono equiponderate tra i componenti presenti, quindi corrispondono ai pesi normalizzati del selettore. Un paniere è candidato alla preferenza solo se bH > 0 e accH > 0. Un paniere vuoto non è candidato.

**Applicare la preferenza soltanto se tutti e tre i selettori hanno tre posti pieni e gross target pari a 1.** Negli altri casi lasciare i terzi uguali. Così l'esperimento non cambia la quota di cassa.

Se esiste almeno un candidato, individuare la massima accH fra quelli ammissibili. Assegnare 0,25 di capitale a ciascuno dei tre selettori, più un bonus totale di 0,25 ai selettori a pari massimo, diviso equamente. Un vincitore unico produce **50/25/25**; due vincitori producono **37,5/37,5/25**; tre producono i terzi. In assenza di candidati restano i terzi.

I pesi finali degli ETF sono la combinazione dei qH con questi coefficienti. Tutti i selettori mantengono peso strettamente positivo: l'unione degli ISIN selezionati è identica al controllo `CAPITAL_3H`. Gross e cassa sono identici grazie alla condizione di pieno investimento. I limiti di gruppo e delle coppie fortemente correlate rimangono 1/3 per convessità. Il confronto isola quindi una scelta di allocazione, senza la sostituzione permanente di un leader con un nuovo candidato.

## Matrice finale: sei controlli di orizzonte/concentrazione e due combinazioni

| Nome | Unica funzione del braccio | Confronto principale |
|---|---|---|
| `HORIZON63` | Tre leader individuali a 63 sedute | Contro `HORIZON252`: finestra recente |
| `HORIZON126` | Tre leader individuali a 126 sedute | Contro `HORIZON252`: finestra intermedia |
| `HORIZON252` | Medesimo contratto con rango annuale | Controllo comune |
| `CAPITAL_3H` | Media dei pesi dei tre selettori | **Confronto primario della famiglia contro `HORIZON252`** |
| `CAPITAL_3H_TILT` | Preferenza 50/25/25 sopra specificata | Contro `CAPITAL_3H`: sola allocazione |
| `HORIZON63_TOP1` | 100% nel primo leader a 63 sedute | Contro `HORIZON63`: concentrazione |
| `HORIZON126_TOP1` | 100% nel primo leader a 126 sedute | Contro `HORIZON126`: concentrazione |
| `HORIZON252_TOP1` | 100% nel primo leader a 252 sedute | Contro `HORIZON252`: concentrazione |

I tre controlli TOP1 usano esattamente gli stessi filtri, osservazioni e ranghi del rispettivo selettore a tre posti. Il primo ISIN è quindi comune. Se non esiste alcun candidato restano interamente in cassa; altrimenti il target è 100% nel primo. Nessun secondo strumento, leva di conto o posizione corta. **Il limite di gruppo 1/3 descritto sopra appartiene ai tre selettori a tre posti e alle loro combinazioni, non ai controlli TOP1**, che ammettono intenzionalmente il 100% in una sola esposizione.

Otto bracci per BASE, ZERO_COST, DOUBLE_COST, LAG1 e LAG2 producono **40 nuovi percorsi**, portando OLC109 a 200. I nuovi bracci RISK15/RISK20 inizialmente considerati sono ritirati **prima di qualsiasi loro simulazione in questo blocco**, seguendo la nuova istruzione dell'utente. I modelli protettivi già completati nei blocchi precedenti rimangono nel registro storico. Nessun nuovo stop, riduzione giornaliera o overlay di volatilità viene aggiunto in questa fase.

## Lettura del risultato e verifiche essenziali

Il risultato del mix va confrontato con **tutti e tre** i controlli a tre posti, senza scegliere dopo il migliore come se fosse stato previsto. `CAPITAL_3H` contro `HORIZON252` identifica il cambiamento complessivo degli orizzonti e del portafoglio risultante; non dimostra separatamente un premio causato dal maggior numero di posizioni. La variante TILT ha un confronto diretto con selezione identica. I tre confronti TOP1 contro tre posti separano il cambio di orizzonte dalla scelta di concentrare il conto; l'effetto della concentrazione include l'eliminazione del secondo e terzo ETF e della relativa diversificazione.

Oltre alle metriche e agli audit già obbligatori, registrare: numero di componenti per selettore; sovrapposizione di ISIN e gruppi; pesi target e reali per gruppo; numero di mesi ammissibili al tilt; candidato e coefficienti; differenze di gross/cassa contro il mix (devono essere nulle per TILT); numero di ordini netti, turnover, partecipazione agli scambi e giorni di negoziazione. Verificare prefix causality e formule dei pesi con casi sintetici, senza una nuova ricerca numerica di parametri.

**Il target attuale resta CAGR almeno 30%. Drawdown -25% e Calmar almeno 1 non sono criteri di esclusione di questo nuovo blocco**, secondo l'ultima indicazione dell'utente riportata dal responsabile. Drawdown, durata delle perdite, Calmar e rendimenti annuali rimangono obbligatori nella presentazione: una maggiore concentrazione non deve nasconderne il costo. Restano assenza di leva di conto e posizioni corte, contabilità e stress comuni, e il limite di 24 giorni operativi annui finché non viene modificato esplicitamente. Raggiungere il solo target di CAGR non certifica robustezza o opportunità di impiego reale; costi, ritardi, concentrazione dei contributi e limiti esecutivi rimangono parte della valutazione. Tutto il periodo è già stato esplorato: nessun segmento viene rinominato holdout indipendente.[L1,L2]

## Fonti consultate

### Fonti locali

- **[L1]** `../../docs/DESIGN_AND_PROTOCOL.md` — contratto V3, clustering, costi, limiti e primo blocco.
- **[L2]** `../../docs/STAGE2_PROTOCOL.md` — ranking individuale e controlli del secondo blocco.
- **[L3]** `../prior_repo/EU165_FACTOR_4V9_README.md` — precedenti MOM63/126/252 su F4/F9.
- **[L4]** `../prior_repo/OLC73_REPORT_IT.md` — allocazioni fisse, MOM63 e instabilità dell'ordine migliore.
- **[L5]** `../prior_repo/OLC102_REPORT_IT.md` — media dei ranghi ML fra chiusure giornaliere.
- **[L6]** `../prior_repo/PRIOR_EVIDENCE_AND_FUSION.md` — ricerca precedente e trasferimento FUSION.
- **[L7]** `../failure_diagnosis/DIAGNOSIS_V3.md` — limiti del rango annuale, concentrazione e sostituzioni opportunistiche.

### Letteratura primaria, consultata il 15 novembre 2026

- **[W1]** Tobias J. Moskowitz, Yao Hua Ooi, Lasse H. Pedersen (2012), *Time Series Momentum*, Journal of Financial Economics. [Pagina degli autori/AQR](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum). Riferimento di consultazione `turn137view1` / `turn136search2`. Universo futures/forward e portafogli diversi dalla presente proposta; nessuna metrica del paper è trasferita al backtest ETF.
- **[W2, consultato ma rinviato]** Alan Moreira, Tyler Muir (2016 working paper; 2017 Journal of Finance), *Volatility-Managed Portfolios*. [NBER working paper 22208](https://www.nber.org/papers/w22208). Riferimento di consultazione `turn136search4`. Fonte considerata per i controlli protettivi iniziali; nessun nuovo modello da questa famiglia è incluso nella decisione aggiornata.

Nessuna simulazione finanziaria, previsione di CAGR o probabilità di raggiungimento del target è stata prodotta durante questa revisione di progetto.

