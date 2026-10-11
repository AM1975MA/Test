# Replay economico richiesto dall'utente

Estensione registrata dopo l'avvio dei fit e prima dell'accesso ai loro risultati:
l'utente ha chiesto il CAGR ottenuto, quindi il replay completo viene eseguito
anche se il candidato non supera il precedente schermo predittivo. Nessuna
modifica a rete, iperparametri, target, feature, split o checkpoint selezionato.
La preregistrazione originaria resta immutata come evidenza del fit.

Il confronto conserva tutti i tre download congelati, lo storico originale,
universo Original149, calendario 2017–2026, allocazione, costi e logica V2.
Si riutilizzano gli artefatti originali learner-full-BASE-r1/r2/r3 del run
37195399755 e i prezzi del run37121749852; nessun fit BASE viene ripetuto.

La modifica riguarda soltanto gli score Compact21 dell'artefatto annuale.
Tail, Compact63 e Macro restano quelli già verificati. Si ricalcola TIT_R
attraverso models.variants canonico. Nel produttore MA3, il training delle
42 feature e delle label HYBRID_TARGET non dipende dai valori TIT_R: il
codice incorpora TIT_R soltanto come colonna BASE dopo il training.
Pertanto si conservano ET_TAIL, XGB_TAIL e TAIL_HYBRID già congelati e si
sostituisce soltanto BASE dopo una verifica esatta delle chiavi/calendari.
La composizione e il replay successivi restano canonici. Non si congela
alcun discendente dipendente dal valore Compact21.

Prima del candidato, il replay della cache BASE deve riprodurre il CAGR,
MaxDD, Sharpe e le selezioni originali; errori nelle chiavi, input o metriche
interrompono il test. Conservare il percorso giornaliero NPZ e le selezioni,
oltre a hash di raw/cache/checkpoint e alla prova di identità del controllo.

Riportare ogni acquisizione separatamente: CAGR netto, MaxDD e Sharpe,
media, range e deviazione standard popolazione del CAGR, disaccordi Top1,
Top2 ordinato e Top2 non ordinato. I dati giornalieri ripetono decisioni
mensili e non costituiscono osservazioni indipendenti. Le tre acquisizioni
non sono mercati indipendenti. Nessuna promozione soltanto per CAGR medio.

Dopo i risultati, discussione fra agenti in italiano: proposta, obiezione
indipendente, risposta e decisione congiunta. Valutare prove, identificazione
causale, rispetto della maturazione, costo e robustezza. Obiettivo operativo:
CAGR elevato e drawdown contenuto con selezioni stabili; nessuna pretesa di
massimo futuro matematicamente garantito né nuovo tuning sullo stesso test.
