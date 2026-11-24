# Perseo U23 — altre linee, 24 novembre 2026

Registrato prima dei risultati. Benchmark U20 UNIFIED: EU/TR trasferimento con fallback locale, USA nativo conservato. Nessun modello U22. Il ranking 125/42 e le alternative difensive U20 restano congelati. Prove di allocazione e gestione della protezione, non nuovo addestramento del selettore.

Stesso periodo 02/01/2020–01/07/2026, conto iniziale 10.000, 1 unità per ordine +15 bp per lato, stress 30 bp, frazioni, niente imposte o leva sul conto, cash senza interesse. EUR EU/TR, USD USA. Nessuna liquidazione finale artificiale. Protezione intraday originale ancora simulata a barra. Storico già esplorato: nessun holdout vergine.

Famiglia chiusa di dieci regole comuni (BASE più nove alternative):

1. BASE: U20 senza modifiche; parità bitwise obbligatoria.
2. CORE25: 75% del portafoglio principale originale e 25% S&P 500 del paniere.
3. CORE_WEAK: quota 25% S&P 500 solo quando entrambi i rendimenti ponderati del portafoglio a 21 e 63 sedute sono negativi; se S&P 500 a 63 è negativo, quota in cash.
4. LEG_BENCH: per ogni ETF con rendimenti 21 e 63 negativi, dirottare metà del suo peso su S&P 500 se il suo rendimento 63 è positivo, altrimenti cash.
5. TREND_CASH: dirottare in cash un ETF quando chiusura sotto EMA63 e rendimento21 negativo per tre chiusure; rientrare con chiusura sopra EMA21 e rendimento5 positivo per due chiusure. Stato mantenuto fra rivalutazioni.
6. TRAIL_CASH: guardia sulla discesa dal massimo del prezzo durante la presenza nella proposta corrente. Banda clamp(2*sigma21*sqrt(5),8%,18%). Uscita alla rivalutazione successiva alla chiusura sotto banda. Rientro quando la chiusura supera le dieci chiusure precedenti e rendimento5 positivo; massimo azzerato al rientro o all'ingresso di un nuovo candidato.
7. RECOVERY: il cooldown globale originale può terminare prima se S&P 500 è sopra EMA21 e rendimento5 positivo per due chiusure. Non annulla un nuovo allarme sistemico né esclusioni individuali o il limite macro g.
8. RAMP: durante i tre giorni di cooldown usare esposizione principale 25%,50%,75% al posto di 25%,25%,25%. Nuovo allarme sistemico conserva 25%; limite macro g invariato.
9. TREND_RECOVERY: TREND_CASH + RECOVERY.
10. LEG_RECOVERY: LEG_BENCH + RECOVERY.

Le guardie di composizione sono valutate ogni cinque sedute dal calendario di ciascun paniere e ad ogni variazione della proposta originale. Usano esclusivamente chiusure precedenti, nessuna apertura corrente nel segnale. CORE25 usa la stessa cadenza e segue i cambi del ranking. Il mantenimento del target fra rivalutazioni evita ribilanciamenti giornalieri. I pesi sono sempre completi; le quote eliminate sono cash esplicito, senza perdita contabile. Il capitale che le protezioni originali riducono resta gestito dal motore originario. Il peso di un singolo fattore/ticker non è una misura calibrata di confidenza.

Le osservazioni prima del 2020 non sono incluse nell'archivio ripristinato. Il riscaldamento usa il solo passato disponibile: EMA63 richiede 63 chiusure, volatilità21 almeno18, EMA21 almeno21. Quando il segnale richiesto manca, non si attiva una nuova uscita. Per gli USA manca la maschera originale delle osservazioni e si conserva l'assunzione ereditata di disponibilità dei prezzi archiviati.

Valutazione completa: 60 conti fissi (10 regole x3 panieri x2 costi), tabella mensile e annuale, sottoperiodi 2020–22 e 2023–26, contributo di costi e operazioni, controlli contabili. Stress di ritardo: ulteriori 30 conti a15bp, differendo di una seduta gli ingressi del motore (selezione, alternativa difensiva, g e segnali nuovi); confronto con BASE ritardata, non con BASE immediata.

Walk-forward del processo di scelta: dal gennaio2022, scegliere una sola regola per tutti i panieri usando i24mesi precedenti. Score = minimo dei vantaggi log annualizzati rispetto a BASE, meno0,5*peggioramento del drawdown nella finestra per ogni mercato. Candidato ammesso soltanto se score>0 e rendimento relativo positivo su tutti i panieri. Variante prudente richiede inoltre quantile20% >0 del minimo vantaggio, bootstrap condiviso a blocchi3mesi con500repliche. In assenza, BASE. 2020–21 BASE. Conti continui, nessuna concatenazione di NAV, nessun azzeramento di capitale/cooldown. Parametri uguali per tutti i mercati; nessuna scelta annuale a posteriori. 12 conti WF (2 procedure x3 panieri x2 costi).

Statistiche nominali: bootstrap appaiato mensile a blocchi12mesi, 3.000 repliche, dipendenza fra panieri preservata; non è correzione completa per tutti i test storici. Tutte le varianti e gli esiti sono conservati. Nessun aggiornamento live o modifica delle automazioni.

Precisazione cronologica prima dell'esecuzione: la selezione annuale usa patrimoni marcati alle chiusure già concluse entro il 31 dicembre, non il rendimento dell'ultima apertura di dicembre verso la prima apertura di gennaio. I conti e i confronti finali restano apertura/apertura. Ogni scenario di costi seleziona sui costi corrispondenti. Lo stress di una seduta riguarda ranking, macro g, alternativa difensiva e guardie nuove; gli stop di sicurezza originari restano tempestivi. Non è una simulazione di indisponibilità assoluta del broker.
