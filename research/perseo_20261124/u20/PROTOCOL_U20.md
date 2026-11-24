# U20 — localizzare la protezione e validare il processo di scelta
Registrato il 23 novembre 2026 prima dei nuovi conti U20. Tutto lo storico è già esplorato: nessun holdout vergine.

Obiettivo: verificare se lo stop su un solo titolo, che nel motore congelato forza anche prudenza globale, distrugga rendimento trasferibile. Stessi parametri per EU165, USA149 e TR1846; nessun cambiamento del ranking durante questa campagna.

Controlli: LOCAL U19 comune sui tre panieri; NATIVE_REFERENCE EU/USA separati, senza sostituire il vecchio motore USA con LOCAL. Pesi 50/50, ingresso immediato; cash effettivo senza interesse. Prezzi e calendari congelati U19. Capitale iniziale 10.000, 1 unità monetaria +15bp per lato, stress30bp. Periodo 2 gennaio2020–1 luglio2026; prezzo finale di apertura. Nessuna fiscalità, quote frazionarie, nessuna leva sul conto.

Famiglia chiusa di sei regole operative:
0 BASE: V6 originale, stop giornaliero5,5%, esclusione3sedute e cooldown globale dopo stop individuale.
1 ISOLATED: come BASE ma lo stop individuale non impone cooldown globale. Allarme sistemico conserva il suo cooldown.
2 VOLATILITY: ISOLATED con stop clamp(3*sigma21,3%,10%); sigma stimata dai rendimenti delle sole chiusure precedenti.
3 REENTRY: ISOLATED, esclusione minima1seduta; rientro solo quando l'ultima chiusura supera media5 e chiusura del giorno prima. Attesa permane anche oltre3sedute se necessario.
4 COMBINED: VOLATILITY+REENTRY.
5 GLOBAL_ONLY: V6 macro/sistemico mantenuto, stop individuali disattivati.
NO_RISK: ulteriore controllo diagnostico, non candidato alla selezione.

Secondo livello: a ogni gennaio dal2022 scegliere UNA regola comune usando gli ultimi24mesi completi precedenti, sui tre panieri LOCAL. Punteggio = minimo tra mercati del log-rendimento annualizzato relativo a BASE meno 0,5 volte l'eventuale peggioramento del maxdrawdown. Miglior candidato ammesso solo se minimo vantaggio >0; altrimenti BASE. Soglia/confidenza: limite inferiore unilaterale80% del minimo vantaggio stimato con bootstrap appaiato a blocchi di3mesi,500repliche, deve essere >0. Nessuna scelta specifica per paniere. 2020–21 BASE. Confronto anche versione senza filtro statistico, dichiarata separatamente. Tutte le alternative e gli esiti sono conservati.

Processo risultante eseguito in un conto continuo; non concatenare NAV di candidati. Cambio regola non azzera quote, cash o stato delle esclusioni. Ultimi12mesi e semestre2026 sono sottoperiodi descrittivi. Audit: parità bitwise BASE con U19; conservazione capitale e costi; ricostruzione P&L; causalità segnali vol/rientro e cutoff selezione; stress costi. Confidenza finale bootstrap appaiato12mesi, senza falsa indipendenza fra universi né correzione integrale della ricerca storica.

I risultati non risolvono i limiti U19: cataloghi non point-in-time, prezzi rettificati, stop a barra, liquidità e osservabilità storica incompleta. Nessuna promozione live automatica.
