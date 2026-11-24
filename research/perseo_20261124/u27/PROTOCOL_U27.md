# Perseo U27 — stop locale con PROFIT_RAMP

Protocollo fissato prima dei risultati. Si testa l'interazione tra l'uscita/rampa U24 e la separazione tra stop sul singolo ETF e cooldown dell'intero portafoglio già studiata in U20. L'allarme sistemico U24 continua a ridurre l'esposizione. Soglia di stop, esclusione individuale e ranking restano quelli di U24.

- LOCAL_STOP: ogni stop individuale esclude soltanto il titolo fermato. Nessun cooldown globale attivato dallo stop individuale.
- CORR80: stop locale quando la correlazione giornaliera stimata dei due ETF è inferiore a 0,80. I livelli 0,70 e 0,90 misurano la sensibilità del risultato.
- CORR80_BREADTH: richiede anche quota negativa uneg della seduta precedente sotto il 60%, così l'isolamento richiede un mercato meno uniformemente debole.

Sono necessari due ETF reali distinti e almeno 45 variazioni valide nella finestra mobile di 63 sedute. Il calcolo usa chiusure già disponibili, senza inizializzazione pre-2020. Si impiega la coppia del ranking U20 prima del trailing U24. Nel test di ritardo si ritarda di una seduta anche il segnale di correlazione, per allinearlo alla coppia ritardata. La stessa regola vale su tutti e tre i panieri. I risultati sono diagnostici sullo storico già usato.

Valutazione come U25: due costi, ritardo, sottoperiodi, risultati per anno e mese, nessuna modifica operativa. L'interpretazione considera il beneficio comune, il drawdown e il 2020–2022 su TR.
