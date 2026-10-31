# Original39 e RH-50 su EU165: retest e diagnosi giornaliera

31 ottobre 2026. Ricerca storica, nessuna promozione. Motore e formule originali preservati; adattamenti europei espliciti. Non e' DUAL-01.

## Risultato

| Periodo / misura | Pesi originali EU | RH-50 EU |
|---|---:|---:|
| Febbraio 2019–1 luglio 2026, CAGR | 18,2578% | 14,9443% |
| Stesso periodo, MaxDD | -35,9464% | -36,3018% |
| Febbraio 2019–dicembre 2024, CAGR | 8,2664% | 6,9322% |
| 2025, rendimento effettivo non annualizzato | +47,2394% | +30,6518% |
| Gennaio–1 luglio 2026, rendimento effettivo parziale | +48,8891% | +45,9595% |

Il risultato complessivo viene alzato dal 2025 e dal 2026 parziale; non riassume bene la debolezza 2019–2024. Il vecchio 39,33% era la media di tre revisioni USA. Il controllo USA r1 di questa prova riproduce esattamente le curve Original39 (CAGR40,7078%) e RH-50 (43,6581%): non le confondo con le medie delle tre revisioni. Scarti NAV <1e-12, selezioni discrete identiche.

## Lavoro effettivo

24 nuovi fit annuali XGBoost, 2019–2026, tre seed; original legacy125, original RETURN_RANK_NDCG 0..15, 360 round. Label mature prima del cutoff annuale. Gli score Hybrid EU ET/XGB sono riusati dagli archivi annuali nativi, NON riaddestrati. Gruppi iniziali singleton esclusi perche' non consentono un confronto di ranking. Sono stati eseguiti 50 percorsi fra strategie e controprove USA/EU. Ogni strategia principale europea ha1897 intervalli giornalieri piu' l'ultima osservazione piatta. In totale101402 intervalli contabili; ricostruzione indipendente NAV errore massimo4,41e-13, identita' log giornaliera errore6,56e-16. Dodici test passati.

Il registro di ciascun giorno contiene decision_date, valuation_date, ETF proposti ed effettivamente detenuti, peso, esposizione, cash, trigger sistemico, stop, quote osservate, costi/slippage, PnL per posizione, effetto meccanico degli stop e contributi logaritmici che sommano esattamente al rendimento. Sono distinti proposta, ribilanciamento e possesso. E[k] del vecchio motore e' il capitale al successivo Open rispetto alla decisione k: le due date sono conservate.

## 1. La selezione Return-Rank peggiora Hybrid nel sottoperiodo debole

Con identici candidati disponibili, pesi50/50 e medesimi controlli/costi, febbraio2019–dicembre2024:

| Selettore | CAGR EU | MaxDD |
|---|---:|---:|
| Return-Rank isolato, supporto abbinato | 1,10% | -32,92% |
| Hybrid isolato, supporto abbinato | 14,56% | -31,69% |
| Return-Rank+Hybrid, RH-50 | 6,93% | -36,30% |

Senza controlli di rischio, gli stessi Hybrid e RH-50 producono15,12% e8,15%. Il ponte logaritmico RH-50 meno Hybrid e' -6,2455 punti/anno di diversa selezione nella stessa politica senza rischio, -0,6419 di diversa risposta ai controlli: totale -6,8873 punti log/anno. Non e' quindi soltanto un problema di stop o commissioni.

L'intervallo bootstrap appaiato21sedute e' [-15,02;+0,58] punti log/anno; quello63sedute [-14,54;-0,23]. Sono confronti diagnostici post-replay, non corretti per tutti i precedenti esperimenti. Lo zero non e' un veto automatico; la diagnosi nasce dalle decisioni e dall'esito economico, non da un bollino di significativita'. Nessuna probabilita' posteriore e' stata inventata.

## 2. Settembre2022: concentrazione immobiliare

La coppia EEPG.DE/ZPRP.DE appartiene allo stesso gruppo immobiliare europeo secondo l'anagrafica archiviata. Nel2022 due slot sono nello stesso gruppo immobiliare per109sedute, almeno uno per130. Fra decisioni1–30settembre, ultima valutazione3ottobre, Original39 perde12,80%, RH-50 12,81%, Hybrid abbinato3,03%. Nessun intervento sistemico o stop in quell'episodio. Due ticker non significano due esposizioni economiche indipendenti.

## 3. Novembre2023: opportunita' persa rispetto a un controllo ex ante

La combinazione compra DXSE.DE/EXV4.DE, classificati sanita'; Hybrid compra IM2A.DE/EEAA.DE. Non sono i migliori titoli futuri scelti a posteriori, ma le scelte del controllo gia' disponibile.

| Decisione -> valorizzazione | Original39 | RH-50 | Hybrid |
|---|---:|---:|---:|
| 2->3 novembre2023 | +0,10% | +0,13% | +5,49% |
| 14->15 novembre2023 | -0,36% | -0,28% | +5,81% |

Sul mese decisionale, fino al1dicembre: circa+1,56% per le due combinazioni contro+13,00% Hybrid. Nessuno stop o trigger spiega il ritardo: qui e' selezione.

## 4. Agosto2024: una discontinuita' concreta tra pesi e protezioni

Stessa coppia QDVE.DE/VVSM.DE, tecnologia USA/semiconduttori globali secondo l'archivio.

| Decisione -> valutazione | Original39 | RH-50 |
|---|---:|---:|
| 1->2 agosto2024 | -7,20% | -7,64% |
| 2->5 agosto2024 | -9,94% | -1,31% |

Il2agosto gap individuali -3,3204% e-5,7640%,81,44% dell'universo con gap negativo. La regola sistemica richiede gap ponderato <=-4,4% e almeno75% di gap negativi. Con60,6000% sul primo ETF il gap ponderato e'-4,2831%: NON scatta. Con50/50 e'-4,5422%: scatta. Cambiano esposizione, applicabilita' degli stop e stato successivo; non e' semplicemente qualche punto di peso in piu'.

Dal1al6agosto, ultima valutazione7agosto, perdite16,50% Original39,8,88% RH-50,3,78% Hybrid. La protezione originale e' condizionale: non garantisce perdita massima5,5% e usa il Close precedente. L'assunzione legacy di conoscere il gap e intervenire allo stesso Open NON e' certificata realizzabile.

## 5. Calendario: un difetto vero, ma non la promessa di recuperare39%

89 mesi di forecast nativi su90 (manca maggio2020); in15mesi meno di20score combinati, spesso5–7. Il30dicembre2024 ci sono165Close; il31dicembre7: BEL.BR,CAC.PA,E40.PA,IAEX.AS,ISFA.AS,LYXIB.MC,TELE.PA. Il calendario ufficiale Deutsche Boerse conferma l'ultima seduta Xetra/Francoforte al30dicembre. Il motore delle feature/forecast tratta quindi il calendario multiborsa in modo che la chiusura di una borsa riduce drasticamente le alternative. I NaN di dicembre si propagano ai due mesi successivi tramite lo smoothing Hybrid, anche quando le quotazioni tornano disponibili.

Controprova: riuso massimo di uno score mensile precedente quando manca quello nuovo, non prezzi o futuro. Il CAGR full PEGGIORA a13,67% Original39 e10,56% RH-50. Negli USA, con score gia' completi, la stessa operazione non cambia nulla. Questo e' un controllo con forecast stantii, non un calendario corretto e riaddestrato. Il difetto puo' alterare favorevolmente o sfavorevolmente lo storico. Nessun recupero automatico del39% dimostrato.

Fonte ufficiale: https://cashmarket.deutsche-boerse.com/cash-en/Stay-Informed/circulars-newsletters/deutsche-boerse-circulars/Final-trading-session-2024-4066452

## 6. Costi e rischio non spiegano da soli il divario

2019–2024: senza tutti i controlli di rischio Original39 fa11,22%, RH-50 8,15%; senza costi9,70% e8,35%. La media dell'esposizione rischiosa prima degli stop e'circa96,36%, quindi non siamo rimasti prevalentemente in cash. La controprova USA a cash zero riduce il CAGR full di circa0,10 e0,08punti, non decine di punti.

Commissioni: cost=.001 applicato al turnover originale, definito come meta' delle variazioni assolute dei pesi, piu' fee/slippage stop. Non e' automaticamente10bp per lato. Anche il trigger sistemico ritardato di una seduta e' testato in entrambi i mercati come sensibilita' di eseguibilita', non selezionato per salvare il CAGR.

## Adattamenti che impediscono di chiamarla replica europea letterale

Formule legacy e equazioni rischio mantenute. Per le feature manca SPY, quindi si usa il fallback mediano gia' presente nel sorgente originale. Per il rischio si usano SPY/HYG/IEF reali come segnali esterni non investibili, con Close USA strettamente antecedente al Close europeo usato. Il residuo e' cash EUR zero-return, NON BIL/SHV inUSD senzaFX e NON bond duration travestito da cash. V6 limitato a ETF europei disponibili al Close precedente. Nessun mese mancante europeo sopprime le decisioni USA.

Quote: nessuna nuova operazione/stop su Open non osservato. Zero ribilanciamenti bloccati in questo campione;16giorni con posizioni detenute su barra mancante e valorizzazione all'ultimo Open passato. Replay permissivo coincide qui, ma non rende eseguibili prezzi inventati.

Dati:527841barre complete, zero incoerenze elementari OHLC;45713volumi nulli. Almeno una posizione detenuta ha volume archiviato nullo in148giorni Original39 e165 RH-50. Dividendi, corporate action, spread, esecuzione reale, survivorship e forecast Hybrid non sono integralmente certificati. Universi e storia gia' usati ripetutamente. I test contabili non rimuovono questi limiti.

## Stato e file

Nessuna variante promossa, nessun settore eliminato a posteriori, nessuna soglia ritarata. I risultati non dimostrano impossibilita' di rendimenti europei migliori, ma non confermano la trasferibilita' del39% al porting eseguito. Priorita' motivata: rigenerare l'intera catena multiborsa (inclusi Hybrid), quindi testare separatamente selezione e interazioni peso/protezioni su entrambi gli universi.

Nel repository sono conservati protocollo, implementazione centrale e risultati essenziali. Il pacchetto completo consegnato nella conversazione contiene anche tutti i sorgenti ausiliari, modelli salvati, input preparati,50NAV e registri giornalieri completi, con hash. La copia su GitHub NON va descritta come un upload integrale dei grandi input/modelli. Main e produzione invariati.
