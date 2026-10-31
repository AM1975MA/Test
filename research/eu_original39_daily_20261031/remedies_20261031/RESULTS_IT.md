# Rimedi al crollo 2020 e alla debolezza 2021–2023: risultati e limiti

31 ottobre 2026. Nuova analisi sui checkpoint congelati di Original39/RH50. Nessuna modifica alla strategia operativa, nessun nuovo fit. Tutte le modifiche testate negli USA e in Europa. Il 18,26% resta il risultato storico della configurazione originale europea, non una garanzia né una configurazione ormai validata.

## Risposta operativa

Le perdite possono essere ridotte, ma i primi rimedi non conservano automaticamente il rendimento. Nessuna delle varianti esaminate risolve contemporaneamente il crollo del2020, la scarsa selezione2021–2023 e la crescita composta nei due universi. Abbiamo separato un difetto dei dati/segnali, il problema del rientro dopo lo shock e il costo dei filtri difensivi. Non vengono scartate ipotesi per la sola inclusione dello zero; vengono mostrati risultati economici e compromessi reali.

Il18,26% non e' il massimo gia' osservato nello stesso archivio: Hybrid isolato con supporto abbinato e controlli originali fa18,87%, Momentum252 nel suo universo disponibile19,35%. Il passivo Nasdaq UCITS fa22,14%, ma e' una diversa esposizione, non una strategia equivalente. I vecchi risultati V5 su2021–2024 non sono confrontabili direttamente con il periodo2019–2026.

## Il2020: le protezioni esistono, ma il rientro e' fragile

Fra decisioni1febbraio–31marzo2020, Original39 europeo registra3 trigger sistemici e7 esecuzioni di stop. Il rendimento di quella finestra e'-17,99%, MaxDD-26,88%; senza controlli di rischio, sugli stessi score e pesi, -24,16% e-36,75%. La frase 'non e' intervenuta alcuna protezione' non e' sostenuta dal ledger.

Il problema e' quando intervengono e quando cessano. Fra decisioni20–27febbraio il conto perde13,37%, prima della riduzione del28febbraio. Il28febbraio target gross25%; il5marzo torna94,5% dopo la scadenza del breve cooldown. Il5marzo->6marzo perde3,88%; il6marzo->9marzo perde7,69%. Si riattiva la difesa il9marzo. Nella logica originale lo stop e' condizionale e riferito al Close precedente: non e' un tetto alla perdita cumulata.

Il registro salva decision_date e valuation_date: E[k] e' la ricchezza al successivo Open rispetto alla decisione k. Le finestre2020 sopra seguono date decisionali, con ultimo valore al successivo Open. Non sono conti di regolamento di un broker.

## La debolezza prolungata richiede un confronto esplicito

Novembre2021–dicembre2023: Original39 europeo +10,66% cumulato, MaxDD-28,66%; Hybrid con supporto abbinato +32,62%. Il controllo passivo Europa EXSA +7,07% e S&P500 UCITS +11,92%: non e' corretto chiamarla sottoperformance rispetto a qualunque mercato, ma lo e' rispetto alla componente Hybrid nel confronto esaminato.

Nel2022 Original39 perde10,13% e nel2023 recupera24,49%. Hybrid abbinato perde4,74% nel2022 e recupera48,70% nel2023. Nelsettembre2022 la coppia immobiliare resta investita intorno94,5–100% pur essendo sottoMA200 e con rendimento63sedute negativo. Ridurre l'esposizione puo' contenere il drawdown, ma non genera da solo le opportunita' scartate dal ranking.

## Copertura dei segnali: il difetto coincide con le fasi indicate

| Data del segnale | Hybrid corrente disponibile | Combinazione originale disponibile |
|---|---:|---:|
| 31gennaio2020 |145|6|
| 28febbraio2020 |145|6|
| 31gennaio2022 |149|5|
| 28febbraio2022 |149|5|

La media Hybrid .4 corrente+.3 precedente+.3 secondo precedente propaga i NaN del mese di dicembre anche quando i forecast correnti sono tornati disponibili. Gennaio2020/marzo2022 nell'etichetta dei dati non vanno confusi con le rispettive date di ingresso del portafoglio. Non si stanno confrontando normalmente tutti i165ETF.

Controllo nuovo 'AVAILABLE_LAGS': richiede un forecast corrente autentico e usa soltanto i lag storici disponibili, rinormalizzando i pesi .4/.3/.3. Non trascina un vecchio forecast al posto di uno corrente mancante. Dove tutti i lag sono presenti, mantiene esattamente la formula originale.

La copertura passa6->145 nei due segnali2020 e5->149 nei due segnali2022. Negli USA, con lag completi, NAV e decisioni restano identici. In Europa il CAGR full scende18,26%->12,31%, MaxDD peggiora-35,95%->-44,56%. Il2022 peggiora da-10,13% a-22,21%. Il risultato storico e' quindi sensibile alla restrizione involontaria dell'universo; non si deve conservare il difetto per difendere il18,26%.

Questo e' un rimedio alla propagazione dei NaN, NON la ricostruzione completa dei calendari per borsa e del training Hybrid. Dicembre senza forecast e maggio2020 mancante restano irrisolti. Non dimostra quanto rendera' il sistema completamente corretto e rifittato.

## Ipotesi congelate prima delle relative prove

Primo lotto: tutti gli8fattoriali di3interventi, due universi, due politiche di peso e due costi:64percorsi.

A SHOCK_MEMORY: drawdown della coppia da63close <=-10% oppure rendimento5sedute<=-5%, informazioni del Close precedente; cap25%, mantenuto fino a3conferme consecutive di recupero (trigger spento, prezzo/MA20>=1 e rendimento5positivo). Nessun prezzo corrente/futuro entra nel nuovo segnale.

B SLOW_TREND: se almeno meta' del peso proposto e' in ETF sottoMA200 e con rendimento63negativo, cap50%. Nessun ETF eliminato, nessuna modifica alla selezione.

F RANK_FUSION: percentili contemporanei di Return e Hybrid smussato sul medesimo supporto finito; pesi47,5/52,5immutati; ricalcolo conseguente di nomi, margini, pesi e V6. Non e' una probabilita' calibrata.

Dopo aver letto i risultati sfavorevoli di queste difese generalizzate, una seconda ipotesi esplicitamente registrata: RECOVERY_ONLY, trigger originali immutati, ma cooldown decrementato soltanto dopo conferme di recupero della coppia su precedenti Close; altrimenti reset a3. Otto percorsi piu'16controlli/sensibilita' con trigger-gap ritardati di una seduta.

Controllo ulteriore: budget rischioso fisso massimo75%, senza nuova previsione,8percorsi. Non e' alpha ne' una raccomandazione personale di allocazione.

Infine AVAILABLE_LAGS:8percorsi. Totale104replay, inclusi controlli e sensibilita'. Ogni ipotesi successiva e' dichiarata post-primi-risultati; non e' nascosta come pre-registrazione originaria. Nessuna ricerca di soglie alternative.

## Compromessi: pesi originali, costi originali

Periodo comune USA/EU: febbraio2019–1luglio2026. CAGR e MaxDD sono calcolati su una traiettoria per mercato; USA usa r1, non la media3revisioni del vecchio39,33%.

| Variante | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| Originale |18,26%|-35,95%|43,27%|-30,13%|
| Solo conferma del rientro RECOVERY_ONLY |15,42%|-40,35%|35,45%|-27,99%|
| Solo cap fisso75% |14,39%|-27,47%|34,08%|-25,24%|
| Shock con memoria A |12,20%|-25,51%|19,31%|-23,15%|
| Trend lento B |13,78%|-35,36%|28,29%|-21,15%|
| Shock+trend A+B |12,04%|-21,34%|19,63%|-23,15%|
| Fusione a percentili F |12,10%|-36,70%|38,80%|-26,36%|
| Lag disponibili, senza forecast stantii |12,31%|-44,56%|43,27%|-30,13%|

Le differenze rispetto al39,33% USA non sono un nuovo cambio di strategia: stessa r1, ma finestra comune2019–2026. Nel suo periodo completo2017–2026 il controllo USA riproduce40,7078%, come prima.

### Correggere il2020 non basta

RECOVERY_ONLY migliora il rendimento effettivo2020EU da+1,50% a+9,00% e il MaxDD da-29,46% a-22,66%. Ma il rendimento2020USA scende+33,21%->+6,78%; sull'intera storiaEU il drawdown peggiora. Non lo promuovo come soluzione comune.

A+B riduce nel febbraio–marzo2020EU la perdita da17,99% a5,14% e il MaxDD da26,88% a14,41%. Pero' il rendimento effettivo2020EU scende da+1,50% a-5,43%: parte della risalita viene persa. Per novembre2021–dicembre2023 l'originale fa+10,66%, A+B -3,61%, pur con MaxDD migliorato da-28,66% a-12,86%. Non e' una riparazione della selezione; e' molta meno esposizione.

B da solo riduce nel2022EU la perdita da10,13% a6,72% e il MaxDD da28,66% a17,73%, ma nel2023 il recupero scende24,49%->19,02%. Sul periodo complessivo tarda2021–2023 il risultato scende10,66%->3,54%.

F non conferma l'intuizione che basti rendere confrontabili le scale per migliorare il risultato. Non ritocco adesso i pesi della fusione per salvarlo.

## Valutazione e decisione

Il rischio si puo' ridurre con un budget piu' basso:75% e A+B mostrano scambi rendimento/drawdown possibili su entrambi gli universi. La preferenza fra questi profili richiede una tolleranza al rischio; non viene inventata. Nessuno di questi esempi e' un miglioramento gratuito o una ragione per distribuire una nuova strategia.

Priorita' tecnica: sanare calendario/feature/forecast di tutta la catena e rifittare mantenendo il vecchio risultato come confronto diagnostico, non come target da preservare. Priorita' predittiva: capire quando il contributo Return migliora davvero Hybrid sulla coppia selezionata, con calibrazione cronologica e confronto economico/di rischio. Priorita' difensiva: distinguere crisi sistemica da normali ribassi dei leader; non applicare un cap generico che smonta il rendimento americano e poi definirlo miglioramento.

Le ultime due sono direzioni di ricerca, NON correzioni validate da questi104percorsi. Qualunque nuova modifica deve ripetere il confronto USA/EU, anche se parte da un episodio europeo. Nessun anno-specifico switch.

## Verifiche e limiti

22test automatici:12ereditati e10nuovi. Otto perturbazioni degli input effettivi dopo2023 non cambiano i nuovi segnali precedenti. Quattro controlli all-off riproducono esattamente le NAV archiviate. I64percorsi del primo lotto sono stati rieseguiti dopo l'ultima modifica del motore e hanno le stesse NAV byte per byte. Contabilita' ricalcolata per104percorsi: scarto massimo3,20e-13, identita' giornaliera8,55e-15.

Bootstrap temporale appaiato3/6mesi,6000estrazioni, seed20261031, rendimenti log mensili comuni febbraio2019–giugno2026. Intervalli esplorativi, non posteriori, non corretti per tutte le ricerche precedenti. Nessun veto basato solo sullo zero e nessun nuovo modello addestrato. Le peggiori prestazioni delle varianti sono spiegate prima nei flussi e nei compromessi, non trasformate in impossibilita' universali.

Restano: stessi dati/forecast storici gia' studiati, limiti total-return/survivorship, segnali mancanti, sola vintageUSA r1 e assunzione legacy di gap/fill allo stesso Open. La sensibilita' ritardata non e' una prova di eseguibilita' reale. Uno stop non garantisce il prezzo di esecuzione: riferimento regolatore https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15 .

Input SHA256826d2b03865e58317e6edb4aa920cc309d3fcfa164d3779499a648b1620b98b8 del checkpoint EU_Original39_RH50_Checkpoint_20261031.zip. Tutti i sorgenti,104NAV eledger, tabelle complete, test e manifest sono consegnati nel nuovo ZIP della conversazione; grandi input non duplicati. Questo rapporto e i protocolli sono persistiti nel branch di ricerca. Main e produzione non modificati.
