# U20B — trasferimento delle esposizioni, estensione esplorativa
Registrato dopo U20: lo stop isolato migliora USA ma peggiora TR. Non è un esperimento deciso prima di osservare U20.

Ipotesi: mantenere il selettore USA originale come linguaggio comune delle esposizioni e tradurre ogni sua scelta in un ETF del paniere locale. Modello economico unico; le differenze di catalogo cambiano soltanto lo strumento di replica. Non riaddestrare il ranking sui percentili di ciascun catalogo. Il caso USA è l'identità e conserva i segnali nativi.

A ogni cambio della coppia USA, scegliere per ciascun titolo il proxy locale con minimo errore quadratico di tracking su rendimenti a5sedute non sovrapposti, fino a252 date comuni precedenti. Minimo26 osservazioni. Conversione comparativa EUR/USD tramite differenza di log-rendimenti SXR8–SPY sulle medesime date; è un proxy di valuta e asincronia, non una serie FX ufficiale. La rimozione della media rende il criterio indipendente dalla performance media osservata. Richiedere90% osservazioni del candidato nelle precedenti63sedute e quotazione precedente disponibile.

Regola principale: correlazione>=0,75 ed errore RMS di tracking<=0,75volatilità del titolo USA; in assenza di proxy, metà portafoglio in cash. Una controprova UNFILTERED usa il proxy più vicino anche se non supera i due requisiti: serve a misurare il costo della copertura, non a scegliere retrospettivamente la soglia. Nessuna ricerca di iperparametri.

Pesi50/50, esecuzione prima seduta locale non antecedente alla seduta di attuazione USA, usando solo chiusure strettamente precedenti. Le scelte USA diventano note alla chiusura USA precedente; nessun dato della successiva apertura USA è usato come segnale. Congelare i proxy fino al nuovo segnale mensile, salvo esclusione all'acquisto per prezzo non osservato come nel motore precedente.

Rischio: stesso V6 BASE locale, cash e costi U19. Controllo senza protezione per separare selezione da protezione. Confrontare sull'intero2020–giugno2026, per anno e per mese con nativeEU, nativeUSA, LOCALTR, e benchmark locale. Questi risultati sono retrospettivi, non una nuova validazione indipendente. Qualità replica e disponibilità dei proxy sono risultati essenziali insieme al rendimento.
