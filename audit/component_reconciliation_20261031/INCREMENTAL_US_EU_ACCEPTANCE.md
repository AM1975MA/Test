# Verifica USA / Europa obbligatoria a ogni incremento

31 ottobre 2026 — precisazione vincolante dell'utente alla proposta RH-50.

**Ogni step e ogni singolo miglioramento devono essere verificati su entrambi gli universi. Non basta validare in Europa la strategia finale o soltanto il vincitore selezionato negli USA.**

Questo addendum precisa e rende più stringente `STRATEGY_PROPOSAL_RH50_20261031.md`. Si applica al lavoro successivo; non modifica retroattivamente il protocollo congelato della riconciliazione Original149 né dichiara eseguiti nuovi test. Nessun codice operativo viene cambiato con questo documento.

## Unità di avanzamento

Partire da una baseline identificata e riprodotta separatamente negli USA e in Europa. La versione e le regole strategiche sono comuni; dati, strumenti negoziabili e costi devono rispettare il contratto prestabilito di ciascun universo. Finché non esiste una baseline verificata su entrambi, il lavoro è qualificazione del riferimento, non promozione di miglioramenti.

Per ogni baseline B_k e modifica candidata delta:

B_k -> stessa modifica delta -> confronto appaiato USA + confronto appaiato Europa -> decisione congiunta -> eventuale B_(k+1).

**B_(k+1) è accettata soltanto se PASS_USA e PASS_EU.** Non si sommano i risultati dei due mercati per compensare un esito negativo. Dati mancanti o un test non eseguito non equivalgono a PASS.

## Ogni variante, non soltanto il finalista

Ogni candidato oggetto di valutazione o selezione deve essere verificato sui due universi. Non ottimizzare sugli USA, congelare il vincitore e presentare soltanto il suo successivo test europeo come applicazione di questo requisito. I confronti sui due universi devono entrare nella decisione fin dall'inizio.

Il vincolo copre aggiunta, rimozione e modifica di feature; target; learner e iperparametri; combinazione dei modelli; selettori; numero di posizioni; calibrazione e pesi; filtri di regime; esposizione; stop; altre protezioni; regole di esecuzione e trattamento dei costi. Comprende semplificazioni e modifiche apparentemente minori.

L'intervento deve essere esplicito e versionato. Mantenere invariato tutto ciò che non è oggetto del test. Quando due componenti devono essere valutati insieme per una precisa ipotesi d'interazione, dichiarare il fattoriale e i controlli prima dei risultati e ripeterli in entrambi gli universi, senza nascondere un pacchetto di cambiamenti sotto il nome di singolo miglioramento.

All'interno di ciascun universo, baseline e candidato devono usare gli stessi snapshot, eleggibilità, date confrontabili, costi e convenzioni di esecuzione salvo l'unico intervento dichiarato. Conservare i confronti appaiati e le incertezze temporali separatamente. Fra universi restano ammesse soltanto le differenze strutturali prestabilite di calendario, valuta, strumenti e costi. Un refit locale può produrre coefficienti diversi, ma la procedura e gli iperparametri non si ritoccano separatamente dopo gli esiti.

## Il criterio dipende dal compito del layer

Prima dell'esecuzione fissare metrica primaria, controlli, limiti di non peggioramento, criteri di incertezza e decisione. Non introdurre soglie numeriche osservando chi vince. Non richiedere che ogni singolo indicatore cresca in entrambi i mercati: richiedere che il cambiamento soddisfi in entrambi il proprio contratto di miglioramento.

Per feature e selettori verificare qualità predittiva e delle scelte, cattura delle opportunità, regret e contributo economico incrementale, senza ridurre tutto a CAGR o hit-rate. Per allocatori verificare l'utilità netta del capitale assegnato, a selezione controllata. Per controlli di rischio verificare perdite e drawdown evitati insieme al costo delle opportunità eliminate e ai costi operativi. Un controllo difensivo può ridurre il CAGR entro il compromesso dichiarato; questo non lo rende automaticamente fallito. Costi, rischio e integrazione restano guardrail anche quando non sono la metrica primaria.

Ogni intervento destinato alla strategia deve inoltre essere verificato nel sistema integrato in entrambi gli universi prima di entrare nella baseline successiva. Le ablation di layer non sostituiscono il test delle interazioni a valle. Nessun componente viene promosso perché migliora soltanto il suo indicatore isolato.

## Esiti e registro

- PASS USA + PASS Europa: promozione ammessa entro il perimetro verificato; congelare la nuova baseline con hash di codice, configurazione e dati.
- PASS in un solo universo e FAIL nell'altro: non promuovere come miglioramento della strategia comune.
- Qualsiasi risultato inconclusivo, bloccato o non eseguito: mantenere il candidato in ricerca, senza promozione.

Per ogni esperimento registrare ID, baseline, intervento preciso, ipotesi, protocollo congelato, metriche della baseline e del candidato per ciascun universo, differenze appaiate, incertezza, costi e rischi, verifiche integrate, esito separato USA/Europa e decisione finale. Conservare anche i tentativi respinti. Ogni nuova correzione o ritaratura crea un nuovo esperimento da verificare su entrambi.

Le correzioni obbligatorie di errori, leakage o formule non diventano facoltative perché riducono il rendimento storico: vanno controllate su entrambi, invalidano dove necessario il riferimento precedente e non possono ereditare le sue performance. Non si preserva un bug per ottenere PASS economico.

## Conseguenza per RH-50 e per le evidenze precedenti

Le scelte Return-Rank + Hybrid, esclusione del Ridge Tail e allocazione 50/50 restano ipotesi da qualificare individualmente e nelle interazioni su USA ed Europa. I risultati Original149 non costituiscono un'esenzione da questo gate. RH-50 non è una baseline già accettata su entrambi.

Il test congiunto finale resta necessario, ma si aggiunge alla verifica incrementale di ogni step: non la sostituisce. Testare ripetutamente USA ed Europa rende entrambi universi di ricerca; non li trasforma in holdout intatti. Conservare quindi anche i requisiti di causalità, controllo della selezione fra molti tentativi e verifica temporale con specifica e segnali congelati prima degli esiti.

**Stato di questa modifica: aggiornamento del criterio di ricerca e accettazione, non esecuzione di esperimenti o dichiarazione di successo USA/Europa.**
