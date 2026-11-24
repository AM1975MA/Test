# Perseo U20 — un miglioramento strutturale, non ancora una strategia validata

23 novembre 2026. Ricerca retrospettiva; dati congelati dal 2 gennaio 2020 al 1 luglio 2026. Nessun ordine reale e nessuna modifica alle automazioni esistenti.

**Risultato:** trasferire le esposizioni del selettore USA in strumenti del paniere locale, usando il ranking locale quando manca una replica credibile, migliora il candidato su EU e Trade Republic. Il processo annuale che dovrebbe decidere quando adottarlo non conferma il risultato. Non dichiariamo risolto il problema della strategia unificata.

La novità è il trasferimento delle esposizioni. Sul paniere USA la trasformazione è l'identità: il 40,23% annuo è il vecchio risultato preservato, non un nuovo guadagno attribuito a U20.

## Confronto omogeneo

| Paniere | U19 comune: CAGR / DD | Nuova selezione: CAGR / DD | S&P500: CAGR / DD |
|---|---:|---:|---:|
|EU|18,16% / -32,39%|20,78% / -31,25%|14,78% / -33,69%|
|USA|32,60% / -25,52%|40,23% / -26,81%|15,31% / -32,05%|
|TR|17,96% / -35,66%|25,07% / -29,53%|14,78% / -33,69%|

CAGR netti dei costi simulati: capitale iniziale 10.000, commissione 1 unità monetaria+15 bp per lato, quote frazionarie, nessuna leva sul conto, cash senza interesse, nessuna fiscalità. USA in USD; EU e TR in EUR, ciascuno con benchmark nella propria valuta. Drawdown misurato alle aperture, non massimo intraday. Il benchmark paga il costo iniziale. I rendimenti non sono previsioni.

Il vecchio **USA nativo 40,23% / DD−26,81%** rimane il riferimento forte. Il vecchio EU nativo è 17,50% / DD−29,66%; U19 LOCAL ha più CAGR ma anche più drawdown. Nessuno dei due viene nascosto. L'architettura di trasferimento porta EU da 18,16% a 20,78% e TR da 17,96% a 25,07%, cioè+2,62 e+7,11 punti annui. Su TR il DD passa da−35,66% a−29,53%.

![Capitale e drawdown](PERSEO_U20_CONFRONTO.png)

## Come funziona la stessa regola sui panieri

Il selettore canonico è quello USA originale, con i suoi segnali congelati e walk-forward ereditati. Per ogni ETF selezionato si cerca il proxy locale con il minor errore di tracking sui rendimenti a 5 sedute precedenti, fino a 252 date comuni; almeno 26 osservazioni. Si richiedono correlazione≥0,75 e tracking error normalizzato≤0,75. Si usa la differenza SXR8–SPY come proxy di conversione valuta e asincronia; non è una serie FX ufficiale.

La ricerca del proxy usa solo chiusure precedenti all'esecuzione. I proxy non sono scelti per il rendimento futuro o per il CAGR realizzato. Se non c'è un proxy qualificato, lo slot utilizza una delle due scelte LOCAL già disponibili. Pesi 50/50; V6 originale come protezione. La regola è uguale per tutti, con il caso USA uguale all'identità. Il ranking LOCAL usato nel fallback conserva le feature e le previsioni della campagna U19; in U20 non abbiamo addestrato nuovi modelli.

Il test con cash al posto dei proxy mancanti rende 14,04% EU e 23,58% TR. Il completamento con LOCAL rende 20,78% EU e 25,07% TR. Il test senza filtro di qualità dei proxy rende 14,86% EU e 23,92% TR: cercare comunque una somiglianza non risolve l'assenza dell'esposizione.

**Confidenza di replica e confidenza di rendimento sono diverse.** Correlazione e tracking misurano se uno strumento rappresenta l'esposizione desiderata; non stimano la probabilità che quell'esposizione salga.

## Il problema economico emerso

Solo circa 51% degli slot USA trova una replica qualificata nel vecchio EU e 75% nel TR. Sono percentuali delle decisioni 2020–2026, non pesi medi investiti. Semiconduttori come SOXX/SMH trovano proxy in entrambi. UNG non passa mai; USL e numerose scelte di petrolio, palladio e altri metalli restano prive di una replica sufficientemente fedele. Queste assenze limitano il trasferimento del risultato USA. La semplice crescita dell'S&P500 dal 2023 non implica che tutti i cataloghi offrano le esposizioni scelte dal motore.

Il risultato TR migliora in 44 mesi su 78, EU in 39 su 78. Sul TR marzo 2020 passa da−21,55% a−10,17%; settembre 2020 da−12,33% a−1,19%; settembre 2024 da+0,54% a+15,70%. Esistono anche errori rilevanti: aprile 2026 scende da+49,32% a+15,94% rispetto a LOCAL. Il nuovo candidato guadagna meno nel grande mese dell'idrogeno, pur avendo un CAGR complessivo migliore. Non dipende quindi soltanto dal conservare quel picco.

| Anno | EU U19 → nuovo | USA U19 → nativo conservato | TR U19 → nuovo |
|---|---:|---:|---:|
|2020|-6,84% → -5,77%|33,98% → 12,32%|-11,16% → -8,77%|
|2021|20,00% → 22,33%|12,99% → 15,91%|-5,13% → -4,28%|
|2022|-16,71% → -7,89%|22,82% → 75,31%|-14,14% → -5,07%|
|2023|69,95% → 57,41%|13,21% → 25,55%|43,64% → 60,32%|
|2024|21,61% → 19,37%|58,00% → 74,19%|13,27% → 35,85%|
|2025|29,96% → 13,69%|24,46% → 12,48%|21,98% → 30,96%|
|2026¹|18,18% → 50,27%|50,97% → 60,11%|103,61% → 80,83%|

¹2026 è parziale, termina con la valorizzazione del 1 luglio. I rendimenti mensili/annuali attribuiscono ogni P&L apertura→apertura alla seduta iniziale. Questo criterio è coerente con il capitale finale ma può spostare un rendimento di confine rispetto alle vecchie tabelle U19. Nei selettori annuali si usano solo le valorizzazioni effettivamente disponibili prima del cutoff.

Il punto ancora debole è il 2020–2022: il nuovo TR perde circa 6,05% annuo, contro 10,05% di LOCAL. Migliora ma resta negativo, mentre il benchmark guadagna. Il nuovo EU produce circa 2,27% annuo nello stesso sottoperiodo. Dopo il 2023 il nuovo TR arriva a circa 59,98% CAGR: il miglioramento resta fortemente dipendente dal regime. Le finestre di regime usano aperture 2020-01-02→2023-01-03 e 2023-01-03→2026-07-01.

## Cosa ha detto il vero processo di adozione walk-forward

Abbiamo simulato anche la scelta dell'architettura, non soltanto l'esecuzione dei singoli modelli. Ogni gennaio dal 2022 valuta i 24 mesi precedenti; la scelta è unica per i tre panieri. Richiede vantaggio positivo nel paniere peggiore, penalizza il deterioramento del drawdown e tiene un solo conto continuo, con costi alle transizioni.

La versione economica seleziona LOCAL nel 2022, trasferimento con cash nel 2023, trasferimento con fallback LOCAL nel 2024, poi LOCAL nel 2025–2026. Ottiene **13,09% EU,36,76% USA,18,75% TR**. Peggiora nettamente EU e non raggiunge il vecchio USA nativo. Non viene promossa.

La versione con confidenza — limite inferiore unilaterale 80% del minimo vantaggio, bootstrap appaiato a blocchi 3 mesi — non trova sufficiente evidenza e rimane sempre LOCAL. Anche il primo selettore annuale delle sei varianti di stop rimane BASE. Questo fallimento viene conservato e ha precedenza sulle conclusioni ottimistiche ricavate dal miglior candidato fisso.

Questi sono processi causali sullo storico. La scelta di studiare queste architetture è avvenuta oggi, dopo molta ricerca precedente: **non esiste un holdout vergine né una verifica prospettica**. U20A, U20B, U20C eU20D hanno protocolli separati che mostrano l'ordine delle estensioni.

## Stop, contagio del rischio e rientro

Nel motore precedente uno stop individuale impone anche cooldown globale per 3 sedute. Separare lo stop locale dall'allarme sistemico porta il vecchio USA da 40,23% a 44,31% CAGR e riduce il DD da−26,81% a−25,99%. Sul TR LOCAL, invece, il CAGR scende 17,96%→17,54%. Il beneficio USA non è stato presentato come beneficio comune.

Stop dimensionati sulla volatilità portano USA nativo 46,60%, ma DD−32,18%; peggiorano TR. Il rientro dopo recupero della media 5 non migliora la famiglia comune. Tutte le sette varianti, incluso il controllo senza protezione, sono registrate.

La variante contestuale isola lo stop solo con correlazione dei due ETF<0,80, stimata prima dell'apertura. Applicata al nuovo selettore produce:

| Variante comune di rischio | EU CAGR / DD | USA CAGR / DD | TR CAGR / DD |
|---|---:|---:|---:|
| Correlazione 0,80 | 20,18% / -31,25% | 43,37% / -28,69% | 25,43% / -30,16% |

Su USA aumenta il CAGR ma peggiora il DD rispetto al nativo. Su EU riduce leggermente il CAGR rispetto al trasferimento con V6 BASE. Le soglie 0,70 e 0,90 sono conservate come sensibilità, senza promuovere il migliore numero. Il 44,31% USA isolato e il 25,43% TR contestuale appartengono a regole diverse: non vengono assemblati in una falsa strategia comune.

## Robustezza e confidenza

| Scenario | EU CAGR | USA CAGR | TR CAGR |
|---|---:|---:|---:|
|15 bp per lato|20,78%|40,23%|25,07%|
|30 bp per lato|16,49%|32,96%|19,44%|

Ritardare di una seduta le decisioni del nuovo selettore porta EU20,78%→17,59% e TR25,07%→28,71%. I risultati mostrano sensibilità all'attuazione, con effetti di segno opposto. Non è stata scelta la data più redditizia. Lo stress ritarda anche il segnale dell'alternativaV6; la protezione di mercato resta disponibile alla data corretta.

Bootstrap appaiato 12 mesi,3.000 repliche sui 78 mesi, con gli stessi blocchi per tutti i mercati: il vantaggio logaritmico annualizzato del nuovo candidato rispetto a LOCAL ha intervallo 95% **EU−6,89/+12,88 punti; TR−4,49/+16,75 punti**. Entrambi includono zero. Per il minimo fra tre panieri l'intervallo è−8,07/+6,69 punti. Le percentuali di repliche positive sono descrittive, non probabilità di successo futuro. Nessuna correzione integrale di tutti i tentativi storici.

La verifica di liquidità TR trova 535 ordini, di cui 39 oltre 5% della media precedente del turnover e 13 oltre 10%; 14 senza stima sufficiente. Massimo 3.38 volte la media. I15 bp non sono una dimostrazione di eseguibilità su quei fondi. Il file dettaglia ogni ordine; non viene dichiarata capacità professionale del conto.

I cataloghi e le quotazioni rettificate non sono pienamente point-in-time. Le maschere di osservazione U19 includono controlli su barre complete e qualità retrospettiva; gli stop sono proxy su barre giornaliere. Questi limiti restano anche quando gli indicatori nuovi usano rigorosamente dati passati. Il DD intraday potrebbe essere peggiore.

## Verifiche e decisione

Parità bitwise dei 5 riferimenti con U19; verifica indipendente di quote, cash e ordini su 107 conti; riconciliazione P&L e commissioni; controlli di invarianza al taglio dello storico e alla modifica dei prezzi presenti/futuri sugli indicatori nuovi; date di replica strettamente precedenti all'esecuzione. I107 conti comprendono controlli e stress correlati: non sono 107 prove statistiche indipendenti.

**Conserviamo il trasferimento delle esposizioni come candidato di ricerca. Non sostituiamo il vecchio USA con LOCAL e non promuoviamo il selettore annuale fallito.** Il prossimo problema concreto è separare il valore del trasferimento nei regimi negativi dalla disponibilità effettiva degli strumenti: prima di aggiungere nuove feature, occorre spiegare e ridurre le perdite 2020–2022 e verificare l'esecuzione sui proxy selezionati. Questa campagna non dimostra ancora 30% CAGR su tutti i panieri.

Fonti consultate: [Kaminski e Lo, When do stop-loss rules stop losses?](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee), per misurare il contributo incrementale della protezione; [Daniel e Moskowitz, Momentum Crashes](https://business.columbia.edu/faculty/research/momentum-crashes), per il rischio di rimbalzi dopo periodi di panico; [Moskowitz, Ooi e Pedersen, Time Series Momentum](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum), per distinguere segnali del singolo asset e ranghi di universo. Non sono prove della performance di Perseo e i loro portafogli non coincidono con i nostri ETF long-only. Il trasferimento per tracking è un'ipotesi operativa sviluppata qui.
