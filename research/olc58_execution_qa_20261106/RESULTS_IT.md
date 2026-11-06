# OLC58 — Verifica dell'esecuzione DELAY3, costi differenziali e dati ortogonali

**Data:** 6 novembre 2026  
**Stato:** RICERCA / NO PROMOTION  
**Strategia originale OLC19:** invariata.  
**Campione:** EU165 e USA149, febbraio 2019–prima apertura luglio 2026, con analisi principale 2021–2024. Il periodo fino a luglio 2026 NON è un holdout indipendente.  
**Decisione:** DELAY3 resta una pista esplorativa; nessun segnale quantitativo nuovo è pronto per la produzione.

## Sintesi

1. I replay nativi OLC19 sono identici bit per bit sui sette array di controllo. I rendimenti giornalieri delle due policy coincidono con OLC56 entro `1e-16`; la riconciliazione mensile ha errore massimo inferiore a `2e-12` **log-bp**.
2. Correzione forense rispetto a OLC57: i primi due **giorni di calendario del mese** non coincidono necessariamente con le due sedute dopo il **segnale di cambio ETF**. Rialliniamo a `q.events`, con rendimento della barra da apertura t ad apertura t+1.
3. Il vantaggio DELAY3 2021–2024 nasce interamente nelle prime due sedute dopo il segnale; le sedute successive sottraggono valore. Tuttavia questa scomposizione di NAV di due policy include effetti di percorso sulla gestione rischio/stops: non è una stima causale del solo delay.
4. Costi **differenziali** sulla sola policy DELAY3 (baseline congelata a fee `0.001`) annullano il vantaggio a incrementi del **coefficiente fee OLC19** relativamente piccoli sul periodo completo: EU `12,36 bp`, USA `8,78 bp`.
5. Il modello non dispone delle offerte/domande eseguibili, degli ordini effettivamente riempiti o dei volumi d'asta storici. L'ipotesi di stop-fill è un proxy da barra OHLC. Nessun backtest a prezzo realmente eseguito è stato completato.
6. Il controllo di una fonte gratuita di **flussi ETF USA** ha trovato 11 ticker coperti sui 48 realmente negoziati nel replay e dati solo dal 2026: NON abilitata a validare 2021–2024.

## A. Attribuzione delle prime due sedute **dall'evento**

Differenza sommata dei log rendimenti giornalieri DELAY3–IMMEDIATE, misurata in **basis point di log rendimento cumulato**, non in differenza di CAGR:

| Mercato/finestra | Sedute evento 0–1 | Sedute evento >= 2 | Totale |
|---|---:|---:|---:|
| EU 2021–2024 | +1.926,48 | −336,56 | +1.589,93 |
| USA 2021–2024 | +3.424,41 | −2.241,13 | +1.183,28 |
| EU 2025–lug 2026 parziale | −7,07 | −109,66 | −116,74 |
| USA 2025–lug 2026 parziale | −378,32 | +267,26 | −111,06 |

La vecchia attribuzione OLC57 sui primi due giorni di **calendario** era: EU +900,27 / +689,66 bp nel MAIN; USA +3.080,07 / −1.896,78. La somma di ogni riga restava corretta, ma **non identificava esattamente le due sessioni di ritardo**; il presente rapporto sostituisce quella lettura, senza sovrascrivere OLC57.

## B. Replay fedele e stress dei costi

Il motore nativo mantiene OLC19 `FAST_LOCK3`, stesse selezioni, rischio, stop, `PREVIOUS` exposure, `NOW` stop, fee `0.001` e stop friction `0.001`.

| Mercato | Finestra | CAGR baseline | CAGR DELAY3 | Delta CAGR |
|---|---|---:|---:|---:|
| EU | 2021–2024 | 23,20% | 28,11% | +4,91 pp |
| USA | 2021–2024 | 50,77% | 55,31% | +4,54 pp |
| EU | 2019–lug 2026 | 19,76% | 22,05% | +2,28 pp |
| USA | 2019–lug 2026 | 39,48% | 43,26% | +3,77 pp |

**Break-even con stress asimmetrico:** baseline OLC19 sempre al coefficiente fee `0.001`. DELAY3 viene rieseguito con lo stesso motore, aumentando soltanto il suo coefficiente fee e mantenendo la friction dello stop `0.001`. Interpolazione binaria del coefficiente al quale i due CAGR diventano uguali:

| Mercato | MAIN 2021–24: fee extra bp | FULL: fee extra bp |
|---|---:|---:|
| EU | 28,69 | **12,36** |
| USA | 11,05 | **8,78** |

**Unità:** `fee * half-turnover + fee degli stop` è la convenzione contabile originale, non la stima di uno spread eseguibile, un ticket di broker o un costo per lato dell'ordine. Non convertire quei 8,78/12,36 bp in spread bid–ask effettivamente disponibili. Lo stress asimmetrico è deliberatamente prudenziale: se tutte le policy pagassero *identici* costi aggiuntivi, anche la baseline sarebbe penalizzata.

Lo stress **simmetrico** `fee=.003` (entrambe le policy) lascia il MAIN EU al `19,88%` baseline / `24,67%` DELAY3, USA al `42,73%` / `47,19%`. Aumentare la sola stop-friction `0.001 → 0.005` in entrambe lascia nel MAIN EU `22,60%` / `27,53%`, USA `48,35%` / `52,80%`. Questi sono stress di input modellistico, **non verifiche di fill reali**.

## C. Stop, apertura e qualità del prezzo

Sono stati riconfermati 33 stop OLC56 DELAY3 per EU e 97 per USA sull'intero campione; nel MAIN 2021–2024 sono 10 EU e 40 USA. Il modello assume una vendita al prezzo di apertura se il gap attraversa il livello di stop; altrimenti alla barriera intraday, meno stop-friction.

- Nel FULL DELAY3 sono **11 EU** e **19 USA** le vendite con apertura già sotto la barriera.
- In **10 EU** e **26 USA** stop il minimo giornaliero è più di **3% sotto la barriera**; in 3 EU e 14 USA supera il 5% sotto barriera. Questo NON prova un prezzo di fill peggiore, ma espone la criticità dell'assunzione di esecuzione a barriera usando solo il Low giornaliero.
- Esempio forense: **UNG**, 30 giugno 2022, apertura **+7,32% sopra** barriera, minimo **−11,55% sotto** barriera. Il backtest valorizza lo stop teorico a barriera meno friction; il prezzo eseguibile durante lo scivolamento reale non è noto.

Il motore USA non contiene una maschera delle quotazioni originali osservate distinta da quelle eventuali ricostruite; l'Europa dispone di `observed`/`low_observed`, ma non di bid/ask, volume, timestamp o venue. Non reinterpretare un prezzo `O` come prezzo di un ordine realmente eseguito.

## D. Fonti di book che servono e pilot minimo

**Campione completo da verificare:** 1.999 ordini principali (sommati EU/USA, IMMEDIATE/DELAY3, intero campione) e 256 stop nel manifest. Sono 89 ticker distinti con ordini, inclusa una quota di ticker europei `.MI` (es. `EM1015.MI`), che richiedono dati della sede italiana e non solo Xetra.

Prima di comprare uno storico integrale, il file `OLC58_PRIORITY_QUOTES.csv` seleziona **183 righe quotazione** su **16 mesi/mercati**, con tre mesi più favorevoli, tre meno favorevoli del 2021–2024 e due mesi negativi del 2025 per ciascun mercato. È **campionamento forense orientato agli estremi**, non un periodo OOS né un nuovo filtro di trading. Per ogni riga richiedere ISIN verificato, esatta sede (Xetra, Euronext Milan o USA), dati d'asta se appropriati, trade con timestamp, best bid/ask immediatamente eseguibili, size, trade condition e identificazione della fonte. La verifica di eseguibilità non può essere completata con uno snapshot senza volumi/size o un simple daily OHLC.

Sedi e dati disponibili alla fonte:

- [Deutsche Börse — Historical Data](https://www.mds.deutsche-boerse.com/mds-en/historical-data): book/trade Xetra da storico, prodotto da richiedere.
- [Euronext NextHistory](https://www.euronext.com/en/products-services/nexthistory): per Borsa Italiana, pacchetti Trades/BBO/Full Book.
- [Cboe Equity & ETF Trades](https://datashop.cboe.com/equity-etf-trades) e [Quotes](https://datashop.cboe.com/equity-etf-quotes): dati USA con trade/NBBO, da verificare separatamente la procedura di asta della sede primaria.

`VENUE_QUOTES_TEMPLATE.csv` è **vuoto**, intenzionalmente. `match_venue_quotes.py` verifica solo la *copertura* e la divergenza rispetto al proxy Open da fonte acquistata/fornita. Se manca, restituisce esplicitamente `NO_VENUE_QUOTES`. Anche con book e snapshot non pretende di conoscere il fill del broker e non ricalcola un CAGR inventato.

## E. Dati ortogonali: controllo fonte gratuita di ETF flows

- [isaergun/etf-flows-data](https://github.com/isaergun/etf-flows-data/blob/main/data/etf_flows.csv) rilevato il 6 novembre 2026, blob SHA `f0308ec2a5957750e6f60974fab68c2fbdd5ae7b`: 6.076 righe, 51 ticker, date dal 2 gennaio al 6 novembre 2026, 2.035 `flow_usd` vuoti (non automaticamente flussi zero). Dei 48 ETF USA realmente negoziati in OLC19, **11** sono presenti (22,9%); **37** non sono coperti.
- La [serie shares](https://github.com/isaergun/etf-flows-data/blob/main/data/etf_shares.csv) contiene 3.079 righe e 52 ticker, con dati dal 5 marzo 2025: non ricostruisce il 2021–2024. Il mancato dato è un limite di questa fonte, non prova che l'informazione sia economicamente inutile.
- Possibile feature veramente indipendente: creazioni/rimborsi netti normalizzati per patrimonio, con data di **pubblicazione disponibile ex ante**, id fondo e venuta, correzioni e maschera di osservazione. Non utilizzare a posteriori serie N-PORT pubblicate dopo il trade come se disponibili alla data dell'ordine; verificare finestre temporali e latenza effettiva. Nessun training addizionale o nuovo CAGR eseguito con questa fonte.

## F. Decisione e gate di promozione

**Non promuovere DELAY3.** La differenza di rendimento è fragile ai costi differenziali, la verifica dei fill è assente, alcuni stop sono molto incerti e l'USA FULL ha drawdown peggiore dell'originale (`−30,40%` vs `−26,12%`, vedi OLC56). Bootstrap OLC56 FULL contiene zero. Anche il campione EU non è indipendente.

**Sequenza:** (1) validare quotazioni reali di un campione dei 16 mesi del manifest, con ISIN/venue; (2) misurare spreads, opening auctions, quote-to-fill, stop-price dispersion e assenza di prezzi; (3) rigiocare contabilità con prezzi eseguibili solo dopo validazione della fonte; (4) testare su nuove date non esplorate con policy congelata. In parallelo, cercare fonte PIT ampia di flussi, non addestrare la fonte incompleta.

## Riproducibilità

Richiede due ZIP originali, entrambi salvati nella ChatGPT Library:

- `/ETF_Research/OLC19_Rischio_Rientro_20261102/OLC19_Rischio_Rientro_Checkpoint_20261102.zip`, SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`.
- `/ETF_Research/OLC56_Robust_Timing_20261106/OLC56_TESTS_20261106_VERIFICATI.zip`, SHA256 `f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573`.

Comando:

```bash
python run_olc58.py --olc19 OLC19_Rischio_Rientro_Checkpoint_20261102.zip \
    --olc56 OLC56_TESTS_20261106_VERIFICATI.zip --out results
```

Python >=3.10 con `numpy`, `pandas`. Risultati scritti nel folder `results/`. La verifica della sorgente si ferma se cambiano gli hash, se fallisce la parità dei sette array originali o i rendimenti OLC56. Gli stress dei costi sono `SAME_FEE`, `DELAY_ONLY_FEE` e `SAME_STOP_FRICTION` e non devono essere confusi. `OLC58_QUOTE_MATCH_EMPTY.csv` prova il fail-closed del test quote con input vuoto: nessuna quotazione originale verificata.