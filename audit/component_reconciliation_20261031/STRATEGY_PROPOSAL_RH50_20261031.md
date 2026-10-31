# ETF Trader RH-50 — proposta di strategia, non promozione in produzione

31 ottobre 2026. Specifica di progetto basata sulla riconciliazione Original149. Nessuna modifica al codice operativo, nessun nuovo training e nessun nuovo backtest raw. Sono state rilette le curve già archiviate e ricalcolati tre confronti temporali.

**Requisito vincolante aggiunto su indicazione dell'utente: la strategia deve funzionare sia sull'universo di ETF USA sia su quello di ETF europei. Un risultato favorevole soltanto su Original149 non autorizza la promozione.** Questa modifica registra il criterio di accettazione; non dichiara eseguiti o superati nuovi test europei.

## Decisione proposta

Usare come unica candidata principale **la selezione Return-Rank + Hybrid MA3, senza il Ridge Tail di Titanium, con ripartizione 50/50 del capitale destinato ai primi due ETF e controlli operativi originali mantenuti**. Il nome breve proposto è RH-50. Nei risultati esistenti coincide con `R_HALF`, oppure `R_T0_H1` con policy mask 62. La parità NAV fra questi due archivi è esatta su tutte le tre revisioni dei prezzi.

La scelta è un giudizio progettuale: privilegia un selettore complementare, un allocatore semplice e una perdita massima storica inferiore al BASE originale. Non è una prova che il 50/50 sia universalmente ottimale, né una promessa di rendimento futuro. Per "migliore" si assume qui un obiettivo di crescita composta netta elevata senza aumentare il rischio rispetto al riferimento operativo originale; non il massimo CAGR in una ricerca esaustiva. Questo obiettivo deve essere verificato separatamente nei due universi, con riferimenti applicabili a ciascuno.

## Contratto della prima versione

| Componente | Scelta |
|---|---|
| Universi di accettazione | Original149 USA e un universo europeo predefinito e versionato: entrambi obbligatori, con la stessa specifica strategica; nessuna promozione basata soltanto sugli USA |
| Segnale | Esatta configurazione archiviata `R_T0_H1`; nessun nuovo blend dei modelli |
| Modulo aggiuntivo | Ridge Tail Titanium disattivato soltanto in questa combinazione; Hybrid resta attivo |
| Selezione | Primi due strumenti della graduatoria combinata, secondo calendario e schedule originali |
| Allocazione relativa | 50/50 sul budget investito nei due leader; nessuna interpretazione probabilistica del margine di ranking |
| Protezioni | Gap sistemico e stop condizionali originali mantenuti; stop 5,5% con condizioni/cooldown invariati, non stop universale o perdita massima garantita |
| DD-first/HighCAGR e V6 | Invariati nella prima versione per non sommare rimozioni non certificate; beneficio modesto non equivale a equivalenza dimostrata |
| Costi | Attivi con la convenzione originale per la riconciliazione; per l'accettazione, tariffa, slippage e turnover coerenti con l'esecuzione di ciascun mercato |
| Produzione | Solo da raw e sorgenti ricostruibili; score e NAV archiviati sono oracle di verifica, non input produttivi |

Il 50/50 si applica al capitale tra ETF, NON al peso dei modelli nell'ensemble. Se f_t è il budget operativo finale assegnato ai due leader, i target relativi sono f_t/2 e f_t/2 prima di fill, costi e interventi intraday. Il residuo segue il contratto originale: V6 e strumenti di liquidità sono contabilizzati separatamente; il sistema non resta obbligatoriamente investito al 100%.

## Risultati storici delle configurazioni esistenti

Medie descrittive di tre revisioni correlate dei medesimi prezzi, 1 febbraio 2017–1 luglio 2026, 2.366 osservazioni. Non sono tre mercati indipendenti. Costi e protezioni originali attivi. Questi risultati riguardano Original149; non attestano il superamento del requisito europeo.

| Configurazione | CAGR medio | MaxDD medio | Intervallo CAGR fra revisioni |
|---|---:|---:|---:|
| BASE originale | 31,7581% | -32,2164% | 29,7534%–34,6771% |
| BASE con allocazione 50/50 | 33,1250% | -25,7776% | 29,7654%–35,1503% |
| Return-Rank+Hybrid, pesi propri | 39,3304% | -29,4084% | 37,8812%–40,7078% |
| **RH-50** | **38,6059%** | **-27,0426%** | **34,1750%–43,6581%** |
| Return-Rank+Hybrid, pesi della graduatoria Hybrid | 41,3909% | -29,7338% | 40,3099%–42,3275% |

RH-50 perde circa 0,7245 pp di CAGR rispetto ai pesi propri e migliora il MaxDD medio di circa 2,3659 pp. Rispetto al BASE originale guadagna circa 6,8478 pp di CAGR e migliora il MaxDD di 5,1739 pp. Tuttavia NON domina tutte le alternative: il BASE 50/50 ha drawdown più contenuto; la combinazione con pesi Hybrid ha maggiore rendimento e minore dispersione del CAGR tra revisioni. La maggiore semplicità dell'allocatore non prova maggiore stabilità ai dati: la dispersione 34,18%–43,66% di RH-50 resta un rischio da indagare.

## Perché non scegliere automaticamente il 41,39%

Il sorgente `tail_only_allocation_v1/intervene.py` calcola la graduatoria di selezione e quella di peso separatamente. Nel ramo R_H, gli ETF provengono dalla selezione Return-Rank+Hybrid, mentre peso e margine sono ricavati dai leader della graduatoria Hybrid. Non è una stima di fiducia riferita necessariamente agli stessi titoli acquistati.

Questa costruzione non è automaticamente invalida: potrebbe contenere informazione di contesto. Il suo ottimo risultato e la minore dispersione fra revisioni vanno preservati come controprova, non ignorati. Ma trasformarla direttamente in regola definitiva soltanto perché massimizza lo storico introdurrebbe una nuova selezione ex post. Per un allocatore successivo chiederei evidenza temporale sulla stessa coppia di ETF realmente selezionata e sul risultato netto incrementale rispetto a 50/50. Una versione che ricalcoli il margine Hybrid sulla coppia effettivamente comprata è NUOVA e non può ereditare il 41,39%.

## Controllo temporale aggiuntivo sulle curve esistenti

Confronti appaiati, media delle tre revisioni prima del ricampionamento; bootstrap circolare, 10.000 estrazioni, seed 20261031. Unità: punti di rendimento logaritmico annualizzato. Diagnostica post-selezione: nessuna correzione per tutte le ricerche passate e nessun holdout indipendente.

| RH-50 meno riferimento | Differenza | IC 95%, blocchi 21 sedute | IC 95%, blocchi 63 sedute |
|---|---:|---:|---:|
| BASE originale | +5,0401 | [-4,7025; +14,5523] | [-4,5502; +14,5276] |
| BASE 50/50 | +4,0115 | [-4,3623; +12,5169] | [-3,5639; +11,7412] |
| Return-Rank+Hybrid, pesi propri | -0,5573 | [-5,4346; +4,3118] | [-4,8614; +3,7150] |

Tutti comprendono zero. Il confronto favorevole fra selezione Return-Rank+Hybrid e Hybrid solo della riconciliazione precedente NON dimostra la superiorità di RH-50 rispetto al BASE. Gli intervalli del precedente candidato al 39,33% non sono stati riutilizzati per RH-50.

## Opportunità e rischio: due compiti distinti

Il selettore deve conservare la capacità di intercettare movimenti ampi. Non aggiungerei adesso veto automatici per sola volatilità elevata, trailing gain elevato o divergenza fra modelli. L'utilità di un filtro va misurata su perdite evitate MENO opportunità eliminate, nei confronti effettivamente eseguiti. Non introdurrei nuovi gate HMM, nuovi meta-tree, V5 fattoriale, Kelly sui rank-score o ulteriori massimizzazioni di Top-K nella prima versione.

Il controllo rischi modifica il capitale esposto e l'esecuzione, non deve essere confuso con capacità predittiva. Il reporting deve separare il nucleo di selezione con costi dall'overlay difensivo, specificando il contributo degli strumenti di liquidità e di V6. Nessun nuovo modello tattico STAY/BIL è incluso; il rendimento della parte difensiva non viene etichettato come alpha del selettore.

## Requisito vincolante: trasferibilità USA / Europa

L'utente richiede che una buona strategia funzioni sia sugli ETF USA sia su quelli europei. Il trasferimento europeo non è più un controllo facoltativo successivo a una promozione USA: è parte obbligatoria dell'accettazione della medesima strategia.

**Una sola specifica.** Congelare prima dei test architettura, formule delle feature, target, iperparametri, combinazione dei segnali, numero di posizioni, allocazione, regole di rischio e procedura di refit. Non usare una configurazione ottimizzata sugli USA e un'altra ritoccata sugli esiti europei per chiamarle la stessa strategia. Un refit cronologico su dati locali può essere previsto dalla stessa procedura, ma non consente di scegliere a posteriori parametri diversi per mercato. Coefficienti appresi diversi non vanno confusi con iperparametri ottimizzati separatamente. La modalità di training, locale o condivisa, deve essere dichiarata prima del confronto.

**Universi confrontabili, senza selezione ex post.** Congelare composizione ed eleggibilità storiche degli universi, distinguendo sede di quotazione/domicilio, esposizione sottostante, classe di attività, leva, valuta e copertura del cambio. Documentare la sovrapposizione dei sottostanti; versionare la deduplicazione delle classi equivalenti. Presentare sia il confronto su esposizioni comparabili sia quello sul reale universo investibile di ciascun mercato. Non eliminare dopo i risultati categorie sfavorevoli, ad esempio obbligazionari o immobiliare, per salvare il backtest europeo.

**Stessa logica, implementazione realmente eseguibile.** Calendari, orari, disponibilità dei dati, costi, spread, cambio e strumenti difensivi devono rispettare ciascun mercato e regole di conversione dichiarate. Non imporre riempimenti artificiali dei giorni senza scambi né prezzi di esecuzione precedenti al segnale. Eventuali strumenti locali sostitutivi devono avere una funzione prestabilita, non essere scelti dal miglior CAGR. Le differenze strutturali non vanno occultate né trattate automaticamente come difetti del modello.

**Accettazione separata nei due universi.** Non richiedere CAGR identici: richiedere utilità economica netta e comportamento di rischio coerenti rispetto a controlli applicabili a ciascun universo, su periodi e regimi comparabili. Verificare separatamente contributo della selezione, crescita composta netta, drawdown/perdite di coda, turnover/cost stress, cattura dei grandi movimenti e costo dei falsi veto. Soglie numeriche, controlli primari e regole statistiche devono essere fissati prima dell'esecuzione; nessuna soglia viene dedotta dai risultati già visti. La media USA+Europa non può nascondere il fallimento di uno dei due. Con evidenza insufficiente l'esito rimane inconclusivo e non si promuove.

**Nessuna promozione unilaterale.** Se la versione congelata fallisce in uno dei due universi, non soddisfa il requisito dell'utente. Indagare dati, esecuzione, composizione e generalizzazione senza attribuire automaticamente ogni fallimento all'overfitting. Qualunque modifica strategica correttiva crea una nuova versione e riapre la verifica di entrambi gli universi, senza usare gli stessi esiti per ottimizzare e poi proclamare una conferma indipendente.

**Necessario, non sufficiente.** Superare entrambi i mercati non elimina da solo il rischio di overfitting: sottostanti comuni ed esiti storici già studiati non costituiscono repliche indipendenti. Restano obbligatori controlli temporali, prevenzione del leakage e conferma con segnali congelati prima degli esiti. Il requisito non impone rendimento positivo in ogni singolo anno, ma impedisce di promuovere una strategia la cui utilità sia documentata soltanto su un universo.

## Gate prima di una decisione operativa

1. **Identità del sistema.** Ricostruire dai raw e dai sorgenti il selettore e l'allocatore; riprodurre prima score, selezioni, pesi, ordini e NAV di riferimento. Le feature originali non diventano matematicamente corrette per effetto della parità. Correzioni necessarie vanno versionate, rifittate e rivalidate; non possono conservare per attribuzione il vecchio CAGR.
2. **Causalità ed eseguibilità.** Controllare timestamp di ogni input, maturazione delle label e ordine segnale→ordine→fill. Una protezione che osserva un gap all'apertura richiede un'esecuzione successiva realisticamente modellata, oppure una specifica realizzabile degli ordini pre-apertura: la semplice parità con fill allo stesso Open non basta. Validare corporate actions, dati mancanti, calendario, universe history e costi per nozionale reale. Eventuali differenze misurate impongono nuovi numeri.
3. **Confronti separati e già dichiarati.** BASE originale, BASE 50/50, R_R e R_H restano controlli; non scegliere dopo il test il vincitore e chiamarlo conferma indipendente. Misurare log-growth netto, drawdown e perdite di coda, turnover, cattura dei grandi movimenti, costo dei falsi veto e sensibilità alle revisioni dati. I 500 panieri canonici sono diagnostica di composizione: sono sovrapposti, non 500 osservazioni indipendenti.
4. **Congelamento e verifica nuova.** Bloccare configurazione e segnali prima degli esiti; usare un protocollo temporale prestabilito e cost stress. Un walk-forward rifatto su anni già studiati resta ricerca retrospettiva. Non specificare un nuovo obiettivo di rendimento annuale dal backtest; la tolleranza monetaria al rischio e un eventuale limite personale restano decisioni separate.
5. **Doppia accettazione USA ed Europa.** La stessa versione deve soddisfare il contratto cross-market precedente in entrambi gli universi, con risultati separati e nessuna compensazione contabile del fallimento di un mercato con il successo dell'altro. Fino ad allora RH-50 rimane una candidata di ricerca, anche in presenza di risultati USA favorevoli.

## Stato e fonti

Questa è una proposta concreta e controllabile, non una strategia universalmente migliore e non un rilascio live. Il codice operativo rimane invariato. Le cifre del 38,61% e del -27,04% appartengono al replay storico Original149 con le convenzioni originarie, non a una futura implementazione con causalità o fill modificati né a una strategia già convalidata sugli ETF europei. L'aggiunta del requisito USA/Europa non comporta l'esecuzione di nuovi test.

Fonti: `results/ARCHIVED_51_PATHS_RECONCILIATION.csv`, `results/POLICY_FACTORIAL.csv`, `results/POLICY_LEAVE_ONE_OUT.csv`, `results/ALL_384_POLICY_PATHS.zip`, `REPORT_IT.md` nella stessa directory. Sorgente dell'intervento: `tail_only_allocation_v1/intervene.py` al commit `13443836649d0f107d2063eb7acc1039135d6e9b`. Controlli aggiuntivi documentati in `RH50_CANDIDATE_CONTRASTS.csv` e `RH50_COMPARE_EXISTING_PATHS.py`.

Riferimento sul rischio di selezionare il vincitore di molti backtest: Bailey e López de Prado, *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality*, Journal of Portfolio Management, 2014, DOI 10.2139/ssrn.2460551. In questa proposta non è stato calcolato un Deflated Sharpe Ratio.
