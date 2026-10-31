# DUAL-01 — primi risultati economici USA149 / EU165

31 ottobre 2026. **Campagna completata; risultati verificati entro il contratto del simulatore, nessuna strategia promossa.**

## Perimetro realmente eseguito

112 checkpoint modello/anno, 288 fit XGBoost e 16 Ridge, 21 selettori, 40 politiche ciascuno, due costi e due universi: **3.360 simulazioni di portafoglio**, più quattro replay DUAL-SELECT. 29 test automatici superati. Ricalcolo indipendente di tutte le curve su otto periodi, 53.760 controlli CAGR/MaxDD: errori massimi circa 4,4e-15 e 6,1e-16. Sei verifiche sui veri input confermano che cambiare prezzi, score e regime dal 2023 non modifica decisioni e NAV precedenti; verificati i digest dei 112 checkpoint e label mature prima del cutoff annuale.

La sessione precedente aveva salvato log, ma non predizioni o sorgenti di lavoro. Al riavvio non c'erano processi attivi o run Actions per questo branch. La ripartenza ha quindi rifatto i training da input congelati; non è stata dichiarata recuperata alcuna predizione mancante. Il codice ricostruito conserva le righe di previsione senza target futuro maturo. Le differenze rispetto ai vecchi log sono descritte in `../RECOVERY_20261031.md`. Il kernel125 coincide col digest precedente; non è affermata parità col programma di lavoro perduto.

**DUAL-01 è una versione nuova**, con feature corrette, mercato locale mediano, eleggibilità e motore esecutivo comuni. Non eredita i vecchi CAGR Stage19/RH-50 del 31–39%. I nuovi first-stage sono riaddestrati; gli score Hybrid ET/XGB sono riutilizzati dagli archivi nativi annuali, non rifittati in questa campagna.

## Limite importante di copertura

Le curve vanno dal **1 aprile 2019 al 1 luglio 2026**. Sono disponibili **70 mesi di segnale comuni sui 88 mesi marzo 2019–giugno 2026**. In 18 mesi la copertura europea/as-of è insufficiente: entrambi gli universi conservano le posizioni, senza nuovo ribilanciamento mensile programmato, continuando ad applicare le protezioni. Nessun Open viene inventato.

Mesi esclusi: 2019-12; 2020-01/02/05/06/07/12; 2021-01/02/12; 2022-01/02; 2024-12; 2025-01/02/12; 2026-01/02. Alcune date europee di fine dicembre hanno solo 5–7 strumenti con Close osservato nel calendario aggregato; la richiesta di tre mesi Hybrid propaga la scarsa copertura. Altri mesi dipendono dall'allineamento temporale degli score. Il contratto multiborsa/as-of richiede una revisione specifica prima di approvare una strategia mensile generale. Questi sono confronti controllati sul calendario dichiarato, non una certificazione di tutti i mesi investibili.

## Confronto principale: aprile 2019–dicembre 2024

Costi 10 bp per lato; stop con slippage aggiuntivo 10 bp; cash a rendimento zero. CAGR secondo 252 sedute; dati locali e stessa politica in entrambi i mercati. Universo europeo per quotazione/domicilio, non necessariamente per esposizione sottostante. Valori di una traiettoria per mercato, non medie di tre revisioni.

| Configurazione | USA CAGR | USA MaxDD | Europa CAGR | Europa MaxDD |
|---|---:|---:|---:|---:|
| Baseline BASE+Hybrid, Top2 50/50 | 17,27% | −19,39% | 3,82% | −25,08% |
| Stesso score, peso basato sul margine | 17,50% | −19,30% | 4,02% | −23,83% |
| Return-Rank+Hybrid, Top2 50/50 | 13,11% | −33,77% | 3,87% | −29,01% |
| Target multi 45/35/20 + Hybrid, Top2 50/50 | 15,83% | −18,42% | 7,08% | −21,39% |
| Consensus multi + Hybrid, Top2 50/50 | 16,32% | −17,45% | 4,43% | −23,06% |
| Committee, Top5 equiponderato | 11,76% | −17,02% | 7,91% | −20,27% |
| Hybrid solo, Top2 equiponderato | 13,30% | −28,32% | 10,26% | −18,54% |

La baseline è `BASE_H_K2_EQ_B0_R1_S1`: nessun buffer, esposizione dimezzata sotto MA200 del mercato locale e stop attivi. Le altre righe mantengono queste politiche salvo selettore e numero/pesi esplicitati.

La scelta congelata massimizza l'incremento di log-growth nel mercato peggiore, a 30 bp, senza peggiorare il MaxDD in nessuno. Risulta prima `BASE_H_K2_MARG_B0_R1_S1`, ma il vantaggio nel mercato peggiore è soltanto **0,1178 punti logaritmici annui**. A 30 bp i CAGR baseline/candidato sono USA 13,66%/13,81% ed Europa 0,73%/0,85%. Il miglior risultato descrittivo di una ricerca su 840 configurazioni non è una promozione automatica. La maggiore concentrazione resta candidata, con vantaggio modesto e incerto.

## Risultato utile: il target lungo va confrontato con lo stesso training

`BASE_MATURE63` mantiene il target a 21 sedute ma usa esattamente le righe in cui sono mature anche le label42/63. Hash delle chiavi di training identici per ogni anno/mercato fra controllo e due target multi.

| Target, identico campione di training | USA CAGR | USA MaxDD | Europa CAGR | Europa MaxDD |
|---|---:|---:|---:|---:|
| Controllo rank21, campione maturato a 63 | 10,62% | −19,39% | 1,12% | −23,15% |
| .45 rank21 + .35 rank42 + .20 rank63 | **15,83%** | **−18,42%** | **7,08%** | **−21,39%** |
| Consensus multi | 16,32% | −17,45% | 4,43% | −23,06% |

Il target45/35/20 migliora il CAGR di circa **5,21 punti USA e 5,96 Europa** e il drawdown in entrambi rispetto al controllo abbinato. Questa strada resta aperta: non viene scartata per inclusione dello zero. Ma il training con maturazione più lunga perde osservazioni recenti e abbassa il controllo. Il beneficio del target non va sommato al 17,27% della baseline completa; contro quest'ultima il candidato resta inferiore negli USA nel periodo principale.

## Distribuzioni probabilistiche

Modello dichiarato NIW bivariato su contrasti logaritmici annualizzati di blocchi non sovrapposti: prior mu0=(0,0), kappa=.5, nu0=4, Psi=.20²I, 20.000 estrazioni seed20261031. Correlazione USA/Europa mantenuta, non prodotto delle probabilità marginali. Sensibilità a prior e blocchi riportata nei CSV. Confronti aggiuntivi sul controllo MATURE63 sono esplicitamente diagnostica post-replay, non nuovi dati né modifica della regola di scelta.

Per MULTI_H contro MATURE63_H a 10 bp:

| Quantità condizionata sul beneficio medio | Blocchi3mesi | Blocchi6mesi |
|---|---:|---:|
| P(miglioramento USA) | 80,0% | 80,9% |
| P(miglioramento Europa) | 98,5% | 93,3% |
| P(miglioramento entrambi) | **79,1%** | **76,7%** |
| P(danno oltre2punti log/anno in almeno uno) | 11,3% | 10,3% |

Le probabilità sono condizionate a prior/modello, stazionarietà e indipendenza approssimata dei blocchi; NON probabilità di battere la baseline nel prossimo anno e NON corrette automaticamente per selezione fra tanti tentativi. I blocchi6mesi coprono aprile2019–settembre2024, omettendo gli ultimi3mesi; quelli3mesi coprono fino a dicembre2024. La diversa copertura è dichiarata.

Contro la baseline completa, P(beneficio entrambi) di MULTI_H è soltanto 35,2% con blocchi3mesi e 17,8% con blocchi6mesi. Il riferimento cambia, quindi non c'è contraddizione con il confronto sul training abbinato. Per l'allocazione a margine scelta dal criterio descrittivo, la probabilità congiunta è circa25–34% nelle sensibilità a10bp. Nessun automatismo del95% viene usato come veto o accettazione.

## Il router cronologico non viene adottato

DUAL-SELECT elegge a gennaio una sola configurazione per entrambi i mercati usando soltanto esiti fino al dicembre precedente, almeno24mesi e la regola30bp già dichiarata. I quattro replay sono singoli conti continui: nessuna concatenazione di NAV indipendenti. La verifica di alterazione degli esiti futuri non cambia l'elezione2022.

| Strategia, 2019–24 a10bp | USA CAGR | USA MaxDD | Europa CAGR | Europa MaxDD |
|---|---:|---:|---:|---:|
| Baseline | 17,27% | −19,39% | 3,82% | −25,08% |
| DUAL-SELECT | **11,86%** | **−31,76%** | **0,82%** | **−32,69%** |

Questa specifica regola peggiora rendimento e rischio nei due universi. Non ritocco ora finestre o soglie per salvarla. La scelta è motivata dall'esito economico, non dalla sola significatività.

Nel 2025, non usato per eleggere il candidato fisso pre2025: baseline USA−4,38%/EU+10,05%; margine USA−4,79%/EU+15,91%; MULTI_H USA+23,63%/EU+16,65%; RETURN_H USA+43,09%/EU+20,87%; router USA−4,82%/EU+15,04%. La graduatoria è instabile per regime; il2025 è già stato studiato, non diventa holdout indipendente. Il2026 parziale termina il primo luglio: i CAGR annualizzati dei CSV non sono rendimenti di un anno intero.

## Decisione e conservazione

Mantengo baseline, multi-orizzonte e alternative come riferimenti separati, senza promuovere una strategia. Prima della prossima accettazione occorre riconciliare il calendario europeo/as-of e ripetere gli stessi confronti nei due mercati. Non si eliminano asset/categorie dopo il risultato per salvare un modello.

Altri limiti: universi sopravvissuti scelti nel2026; total return, corporate actions e distribuzioni non certificati; dati USA/EU non omogenei per costruzione; spread e capacità reali non convalidati; Hybrid non rifittato; molteplicità e storia riusata. La campagna non ha rieseguito tutti gli esperimenti dei293branch inventariati.

Il codice è nel branch di ricerca, non in main. Le tabelle/curve/ledger completi e i checkpoint sono nei pacchetti scaricabili con manifest. I modelli binari non sono archiviati: sono conservati parametri, seed, hash del modello e predizioni, più sorgenti e input per rifare il fit. Il nuovo pacchetto di continuazione conserva risultati reali, non solo log. Nessun impiego operativo o promessa di rendimento futuro.
