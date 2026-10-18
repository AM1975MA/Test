# RESET SCIENTIFICO DELLA RICERCA ETF — da zero, non OASIS V3

18 ottobre 2026 | `AM1975MA/Test` | research/149-foundational-reset-20261018

**Decisione del coordinatore: STOP all'ottimizzazione incrementale di OASIS, LM, Return-Rank, top-K, HMM, probabilità di switch e parametri EWMA sui 149.** I risultati negativi non vanno cancellati. La produzione `etf_trader` non si tocca. Questo documento è un'analisi metodologica, **non** un backtest né una nuova strategia performante.

## Critica rigorosa alle nostre stesse procedure

**Domanda sbagliata.** Abbiamo usato una label semplificata `P(rendimento del candidato - rendimento incumbent > 30 bp nei successivi 21 giorni)`; essa non misura la massima utilità di una rotazione reale, la grandezza asimmetrica della perdita, la durata dell'opportunità, la traiettoria intraperiodo, lo spread effettivo o il confronto con il benchmark. Vincere una classificazione di segno (Brier 0.249) non è una dimostrazione di creazione di ricchezza; fallire la classificazione non prova l'assenza di qualunque informazione a tutte le scale temporali.

**Unità economica sbagliata.** Il trading non avviene per coppie indipendenti di ticker: un'esposizione a più ETF quasi identici equivale a un'unica scommessa fattoriale. Nel `universe.csv`, SPY/IVV/VTI occupano posizioni diverse; `C06_REAL_ASSETS` raggruppa GLD, USO, UNG, REIT e GDX, asset con meccanismi economici incompatibili. `C02_SECTOR_THEME` mescola petrolio/tecnologia/health. R2 un ETF per ognuna di sei etichette non è una diversificazione economica rigorosa. Gli ETF USO/UNG investono in futures e incorporano roll, non replicano lo spot.

**Tempo sbagliato.** Segnale una volta al mese, label a 21 sedute, controllo del rischio con volatilità ritardata: questa architettura è inidonea a catturare transizioni su 2–5 giorni mantenendo trend plurimensili. Non va modificata arbitrariamente con un filtro giornaliero, ma va *misurata* la reale scala temporale delle opportunità al netto del ritardo.

**Rischio sbagliato.** Indice sintetico medio dei 149 e HMM fittizio non rappresentano il rischio delle posizioni e dei fattori. Un 'breathing' di mercato può convivere con una crisi idiosincratica del titolo posseduto. Non esiste garanzia che una crisi sia anticipabile: **rilevarne il decorso** e ridurre perdite future è un obiettivo distinto dal prevedere il primo gap.

**Campione abusato.** 2017–2026 è stato osservato e riusato decine di volte. PBO/DSR non si risolvono semplicemente con una nuova branch o una preregistrazione retroattiva. Il 149 è una lista ex post di survivor statunitensi, non un'universo ricostruito di strumenti commercializzabili in EUR nel passato. EUR60, 150, 69 sono a loro volta già esplorati. No nuovo claim di holdout sulle vecchie date.

**Controlli troppo facili.** Battere Top2 che perde il 60% non significa creare valore; su original149 anche la migliore configurazione risk-only G6 EWMA CAGR circa 7.72% e MaxDD -28.81% è storicamente inferiore al proxy statico 60/40 SPY/AGG (CAGR 11.39%, MaxDD -23.55%), con costi non completamente uniformi. Il piccolo G6 incremento non sopravvive come prova prospettica solo perché nel singolo ablation bootstrap il limite inferiore >0.

## Riformulazione del problema PRIMA di scegliere un modello

La vera domanda è se **esistano opportunità economicamente significative, sufficientemente persistenti e osservabili PRIMA di esaurirsi**, per le quali un agente adattivo possa migliorare il rendimento netto e la protezione del capitale rispetto a un benchmark passivo investibile.

Controllo: benchmark B deve utilizzare esattamente la stessa valuta, calendario, classe di strumenti ammessi, costo, liquidità e vincolo sul rischio. Un portafoglio di riferimento può essere un indice diversificato con una componente difensiva, scelto e congelato prima del test; `SPY/AGG 60/40` è solo un comparatore USD storico, non necessariamente investibile in Italia.

Stato del sistema: `x_t` = posizioni correnti, cash, distribuzione di esposizioni ai fattori economici, prezzo/esecuzione; informazione `F_t` = solamente ciò che è osservabile entro il segnale. Azioni `a_t` = mantieni, riduci, incrementa, ruota; oltre a non fare nulla. Vincoli di costo, slippage, margine, liquidità e concentrazione. Criterio naturale: crescita logaritmica **in eccesso al benchmark**, soggetta a vincoli ex ante di shortfall e drawdown, confrontando una frontiera rischio/rendimento/costi anziché massimizzare CAGR senza condizionalità.

`E[log(W_T^pi/W_T^B)]` non è direttamente noto e non va ottimizzato ex post su una lista di possibili politiche; richiede vera abilità predittiva o una regola di controllo robusto indipendente dal rendimento. Nessun algoritmo può garantire sovraperformance se tale informazione non esiste nei dati.

## Esperimento M0: mappa del VALORE DELLE OPPORTUNITÀ (analisi di fattibilità)

Ancora **nessun training ML**. Su 149 come laboratorio, ricostruire prezzi, costi e fattori, poi eseguire, con *finalità puramente diagnostica*:

1. **Oracle perfetto con costi**: DP che conosce tutta la traiettoria futura, limiti a massimo 2-6 esposizioni, turnover, costi e min hold. Genera SOLO il limite superiore a posteriori, matematicamente non investibile.
2. **Oracle con ritardi imposti**: stessa conoscenza futura ma obbligo di attendere +1/+3/+5/+10 sedute per cambiare posizione. Serve solo a misurare la distruzione di valore per ritardo; resta un limite di chiaroveggenza, NON un benchmark operabile.
3. **Durata e qualità delle opportunità**: ricavare episodicità, persistenza del vantaggio netto, relazione con fattori comuni, sensibilità alla latenza, frequenza di false rotazioni ex post e quota di utile teorico proveniente dai 10 giorni migliori. Evitare definire 'real opportunity' facendo direttamente lookahead nelle azioni del sistema fattibile.
4. **Feasible naive controls**: benchmark statici, relative trend 21/63, 'never trade' e daily rebalance con hurdle reale, tutti causali. Il confronto distingue *esistenza storica ex post* da *segnalabilità ex ante*.
5. **Controlli nulli**: rotazioni casuali matched turnover, permutazioni a blocchi preservando dipendenza, benchmark con pari esposizione fattoriale; non riportare la migliore casuale come 'valid alpha'.
6. **Regime event-level**: individuare i periodi storici di shock/ripresa per diagnosticare il costo del riconoscimento con latenza; nessuna scelta di etichette del modello usando futuro.

**M0 GO solo se** una porzione economicamente rilevante dei guadagni dell'oracle sopravvive a ritardi realistici ed emerge un minimo di separazione fra politiche fattibili causali e null benchmark. L'ampio gap oracle/naive non è di per sé prova di previsione possibile! Se opportunità quasi tutte concentrate in switch troppo rapidi, la decisione scientifica è **non perseguiamo una strategia di rotazione aggressiva su questo universo/dati**.

## Esperimento M1: stimare la FRONTIERA DI PREDICIBILITÀ, non indovinare il winner

Dopo M0, non usare una sola label binaria a 21 sedute. Studiare *valore atteso incrementale* e *distribuzione asimmetrica* della politica rispetto al benchmark, condizionati a fattori e posizione, con orizzonti 5/21/63 sedute fissati in anticipo. Non predire rendimenti assoluti quando il rischio è dominato dal fattore comune: prima definire esposizioni economiche reali e residui peer-to-peer.

Separare 3 skill:
- `S1` persistenza di un vantaggio relativo, al netto di turnover;
- `S2` rischio di deterioramento dei titoli effettivamente detenuti;
- `S3` rientro/riallocazione durante una ripresa, con ritardo realistico.
Una buona stima della volatilità (G5 EWMA) è un risultato S2 accessorio, **non S1 né S3**. VIX/VVIX/OVX/GVZ/VXEEM G4b e loro varianti hanno FALLITO previsione netta; non aggiungerli solo per essere sofisticati.

Valutare presenza del segnale tramite modelli null e semplici; contare la differenza nel log score, Brier quando appropriato, regressione log-payoff, *decision-focused utility* al netto di costo senza sceglierne la soglia sulla stessa storia. Al solo miglioramento significativo di proper score non corrisponde automaticamente profitto realizzabile: imporre test economico indipendente con benchmark e gli stessi fill.

## Esperimento M2: controllo adattivo sotto INFORMAZIONE PARZIALE

Soltanto se M1 fornisce una distribuzione calibrata di opportunità, impostare un controllo di tipo POMDP/impulse-control con costi e stato posizioni. La decisione no-trade è un'azione positiva, non assenza di modello. I segnali hanno diverse scale di decadimento e costi: Gârleanu–Pedersen dimostrano perché un adattamento parziale al target dinamico può essere razionale con transaction costs (Journal of Finance 2013, doi:10.1111/jofi.12080). Hysteresis = no-trade region giustificata dall'incertezza calibrata e dai costi, NON classifica Top5. La componente difensiva non dipende da scelte casuali di crash flags.

Principio *chiave*: alcuni shock sono imprevedibili prima dell'apertura, ma un buon controller può reagire alla fase di propagazione e riaccumulo. Misurare separatamente valore della reazione, ritardo e costo dei falsi allarmi. Non promettere cattura dell'inversione esatta.

## M3: verifica INDISPENSABILE

- Richiedere una nuova popolazione timestamped di ETF PIT con debutti e delisting, ISIN/venue/quote EUR, bid/ask o penalizzazione conservativa, cash reale e regole di accessibilità commerciale. Il 149 USA resta un corpus di sviluppo.
- Generare file di decisioni e previsione **immutabili prima** delle aperture testate. Per materiale storico già osservato NON chiamare mai il periodo 'vergine'.
- Registrare TUTTE le prove/model/versioni nel trial ledger e applicare penalità per trial multipli: PBO/CSCV diagnostico se applicabile, deflated Sharpe/Reality Check; nulla elimina il bisogno di serie future nuove.
- Successo = miglioramento netto non fragile vs benchmark B su **frontiera rendimento/rischio/costi**, eventi di crisi fuori sviluppo, exposure matching e opportunità nuovi strumenti. Il sistema può correttamente rimanere in modalità 'no-active-alpha' se nessuna predizione è affidabile.
- **Nessun progresso sul trading** da M0/M1 che non abbia superato verifica economica PIT con benchmark coerente.

## Il reset non è ancora un risultato: non fingiamo di avere identificato un modello superiore

Il salto scientifico consiste nel cambiare la domanda: da **«quali ETF classificare ai primi posti?»** a **«quali opportunità sono realmente osservabili, persistenti ed economicamente sfruttabili con la latenza ed i costi di un sistema causale?»**. L'intero piano va scartato se la verifica iniziale mostra che non esiste segnale informativo replicabile.

Fonti teoriche: Bailey et al. (2017), *The Probability of Backtest Overfitting*, doi:10.21314/JCF.2016.322; Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, doi:10.3905/jpm.2014.40.5.094; Gârleanu & Pedersen (2013), *Dynamic Trading with Predictable Returns and Transaction Costs*, doi:10.1111/jofi.12080.
