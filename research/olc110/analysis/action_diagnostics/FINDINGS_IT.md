# OLC110 — Diagnosi delle azioni a stato iniziale identico

## Esito

Le nuove opportunità mostrano un **vantaggio locale medio positivo rispetto al cash a 21 sedute**, condizionato agli eventi classificati come ingressi puri con orizzonte completo. Il vantaggio a cinque sedute è piccolo e spesso assorbito dai costi. I rientri FAST non danno un risultato coerente fra configurazioni; le conferme del probe della configurazione STAGED senza nuove opportunità risultano sfavorevoli soprattutto per i rendimenti successivi, non per le sole commissioni. Le uscite pure hanno markout medio negativo a 21 sedute in tutti i 15 incroci esaminati.

Queste evidenze **non dimostrano alpha e non modificano il fallimento del modello primario nel conto completo**. Sono confronti locali fra due conti con identico stato iniziale, successivi al segnale, con finestre sovrapposte. Non si sommano e non si trasformano in CAGR. Il confronto con cash a rendimento zero non elimina il premio per il rischio delle attività acquistate.

## Perimetro e verifica

Cinque configurazioni — EXIT21_MONTHLY, EXIT21_STAGED, EXIT63_STAGED, EXIT21_STAGED_FRESHW e EXIT21_STAGED_FRESHD — nei tre scenari BASE, LAG2 e NEXT_CLOSE. Sono inclusi **tutti i 3.869 eventi inframensili**, per 11.607 intervalli nominali T+1/T+5/T+21, senza selezione per esito. Le decisioni iniziali e mensili sono escluse: perciò EXIT21_MONTHLY non presenta rientri in questo campione.

Il libro delle istruzioni è stato ricostruito dalle istruzioni e dai fill archiviati: non aveva ordini pendenti o in coda in tutti i 3.869 casi, in accordo con metadati e trace. Il portafoglio poteva comunque contenere posizioni investite. I **4.395 fill confrontabili prima della maturazione di una successiva istruzione** coincidono esattamente per quantità, prezzo, controvalore e costo. Errore massimo di conservazione contabile: 1,10×10⁻¹¹ EUR. Sono rimasti invariati codice finanziario, prezzi e risultati dei 78 percorsi. Fonti: [VALIDATION.json](VALIDATION.json), [FILL_VALIDATION.csv](FILL_VALIDATION.csv), [EMPTY_BOOK_VALIDATION.csv](EMPTY_BOOK_VALIDATION.csv), [PROVENANCE.json](PROVENANCE.json).

## Modello primario FRESHW: cosa produce la singola azione

BASE, T+21. Tutti i valori monetari relativi sono **bp del NAV del conto al Close del segnale**, non rendimenti dell'ETF. Costi positivi rappresentano una deduzione; V/P/N indica conteggi di vantaggi, perdite e pareggi netti. N include soltanto orizzonti completi.

| Azione | N | Mercato lordo bp | Costi bp | Differenza netta bp | V/P/N |
| --- | --- | --- | --- | --- | --- |
| Uscita pura | 163 | -32,22 | 8,59 | -40,80 | 76/87/0 |
| Rientro stesso ETF | 88 | -28,83 | 7,78 | -36,61 | 44/44/0 |
| Conferma probe | 64 | +30,97 | 4,68 | +26,29 | 32/32/0 |
| Nuova opportunità | 68 | +42,64 | 4,91 | +37,73 | 39/29/0 |
| Misto / differito | 15 | +28,02 | 12,20 | +15,82 | 9/6/0 |

A T+1 le nuove opportunità FRESHW sono a −2,93 bp medi; a T+5 arrivano a +1,80 bp, composti da +6,69 bp di mercato meno 4,90 bp di costi. A T+21 il +37,73 bp ha mediana +7,66 bp e 39 vittorie su 68 eventi: la media è maggiore dell'esito mediano. Le conferme passano da −13,57 bp a T+1 e −8,48 bp a T+5 a +26,29 bp a T+21; la loro mediana T+21 è soltanto +0,29 bp.

Per le uscite primarie il mercato successivo vale −32,22 bp medi, cui si aggiungono 8,59 bp di costo; per i rientri sullo stesso ETF −28,83 bp di mercato e 7,78 bp di costo. La debolezza di queste due componenti non è dunque spiegata soltanto dalle commissioni. Fonte: [SUMMARY_BY_CLASS.csv](SUMMARY_BY_CLASS.csv).

## Rientro rapido: risultato instabile

Rientri puramente FAST, T+21: differenza media netta in bp e numerosità degli intervalli completi. I casi che combinano FAST e SLOW restano nel sottotipo separato FAST_AND_SLOW; non sono inclusi nella tabella.

| Configurazione | BASE | LAG2 | NEXT_CLOSE |
| --- | --- | --- | --- |
| EXIT21_STAGED | -4,20 (n=47) | -5,79 (n=39) | -9,96 (n=47) |
| EXIT63_STAGED | +34,95 (n=41) | -7,54 (n=38) | +22,44 (n=41) |
| FRESHW | +24,85 (n=14) | +98,81 (n=16) | +24,96 (n=14) |
| FRESHD | -2,70 (n=4) | +1,27 (n=8) | -2,11 (n=4) |

Nel controllo EXIT21_STAGED, FAST produce +0,26 bp lordi e paga 4,46 bp: il netto −4,20 bp deriva quasi interamente dai costi. Ma le sue conferme sono molto peggiori: −79,65 bp netti in BASE (15 casi), di cui −75,52 bp di mercato e 4,13 bp di costo; LAG2 dà −160,19 bp e NEXT_CLOSE −72,00 bp. EXIT63 cambia segno con il ritardo. Il FAST positivo nel primario riguarda pochi eventi; la ricerca giornaliera lascia solo quattro casi puri in BASE. Non è una base solida per attribuire capacità predittiva al rientro rapido. Fonte: [SUMMARY_BY_SUBTYPE.csv](SUMMARY_BY_SUBTYPE.csv).

## Nuove opportunità: segnale locale favorevole, margine breve limitato

Ingressi FRESH puri; N può variare fra gli orizzonti per la censura finale. Gli scenari hanno date e stati di conto differenti: la tabella non è un confronto casuale fra trattamenti.

| Modello | Scenario | Netto T+5 bp | Netto T+21 bp | Costi T+21 bp | Vittorie T+21 |
| --- | --- | --- | --- | --- | --- |
| FRESHW | BASE | +1,80 (n=69) | +37,73 (n=68) | 4,91 | 57,35% |
| FRESHW | LAG2 | -0,02 (n=40) | +63,32 (n=39) | 5,12 | 56,41% |
| FRESHW | NEXT_CLOSE | -0,33 (n=69) | +35,71 (n=68) | 5,05 | 58,82% |
| FRESHD | BASE | +5,79 (n=112) | +16,80 (n=111) | 4,57 | 54,95% |
| FRESHD | LAG2 | -1,71 (n=66) | +41,44 (n=65) | 4,91 | 56,92% |
| FRESHD | NEXT_CLOSE | +2,61 (n=112) | +13,72 (n=111) | 4,66 | 52,25% |

In BASE i costi assorbono 4,90 dei 6,69 bp lordi FRESHW a T+5; FRESHD conserva +5,79 bp dopo 4,56 bp di costo. A T+21 il margine medio supera i costi in entrambi, ma il conteggio degli esiti non elimina la dipendenza fra finestre o il rischio sistematico degli ETF. La possibilità di restare investiti nell'intervallo isolato non equivale al percorso effettivo, che può vendere, confermare o cambiare assegnazione prima di T+21.

### Anni degli ingressi FRESH puri, BASE T+21

Anno del segnale, differenza media netta e N. Gli anni iniziale e finale sono parziali; il 2024 è incluso. La tabella completa per tutte le azioni, i tre scenari e i tre orizzonti è in [SUMMARY_BY_YEAR.csv](SUMMARY_BY_YEAR.csv).

| Anno del segnale | FRESHW bp (N) | FRESHD bp (N) |
| --- | --- | --- |
| 2020 (parziale) | +58,83 (n=9) | +41,61 (n=17) |
| 2021 | +8,83 (n=16) | -13,14 (n=23) |
| 2022 | -31,63 (n=2) | -34,34 (n=11) |
| 2023 | +31,22 (n=13) | +0,50 (n=19) |
| 2024 | -7,45 (n=9) | -19,57 (n=15) |
| 2025 | +57,68 (n=8) | +57,66 (n=13) |
| 2026 (parziale) | +105,24 (n=11) | +105,58 (n=13) |

Il risultato non è uniforme: FRESHW è negativo nel 2022 e 2024; FRESHD nel 2021, 2022 e 2024. I valori positivi degli ingressi puri del 2026 non rappresentano il rendimento 2026 del modello: **FRESHW BASE perde il 29,08% dal principio dell'anno al 30 ottobre**, nel conto completo. La classificazione e la censura sotto riportate spiegano perché non si deve usare +105,24 bp come compensazione o smentita di quella perdita. Fonte del rendimento del conto: [ANNUAL_RETURNS.csv](../../results/ANNUAL_RETURNS.csv).

## Uscite: il costo del mancato investimento successivo

Differenza media netta T+21 delle uscite pure, in bp; negativa significa che la vendita isolata ha prodotto meno NAV del mantenimento delle stesse quantità.

| Configurazione | BASE | LAG2 | NEXT_CLOSE |
| --- | --- | --- | --- |
| EXIT21_MONTHLY | -53,57 | -84,38 | -60,42 |
| EXIT21_STAGED | -24,02 | -60,35 | -30,97 |
| EXIT63_STAGED | -39,58 | -97,29 | -47,58 |
| FRESHW | -40,80 | -21,03 | -50,11 |
| FRESHD | -39,99 | -37,91 | -49,31 |

Tutti i 15 valori sono negativi. Ciò non implica che ogni uscita sia sbagliata: la frequenza e la dimensione degli esiti possono divergere. Per esempio EXIT63_STAGED BASE vince nel 52,73% degli intervalli T+21, ma perde in media 39,58 bp. Le azioni miste non sono state ripartite artificialmente fra uscite e acquisti.

## Censura finale e caso LBRA

**101 intervalli su 11.607 sono incompleti**, relativi a 82 eventi: 19 a T+5 e 82 a T+21. Si conservano con l'orizzonte realmente osservato fino al 30 ottobre 2026 e non entrano nelle medie dichiarate a orizzonte completo. [TRUNCATED_INTERVALS.csv](TRUNCATED_INTERVALS.csv) conserva tutti i valori parziali, anche negativi.

Per FRESHW BASE FRESH_ENTRY a T+21 ci sono **69 eventi totali, 68 completi e uno censurato**. L'evento censurato è l'istruzione 486, segnale 23 ottobre, acquisto 26 ottobre, ISIN IE00B6R51Z18 (IS0D.DE, Oil & Gas): non è LBRA. Sono osservabili cinque sedute, con +41,76 bp netti, senza informazione sull'esito a 21.

LBRA, ISIN LU1900066207, è entrato il 12 ottobre attraverso l'**istruzione mista 479**, decisa il 9 ottobre, insieme a un'altra operazione. La sua finestra T+21 è censurata: il risultato dell'intera istruzione mista dopo 15 sedute è **−607,75 bp**. La successiva **conferma 481**, segnale 13 ottobre ed esecuzione 14 ottobre, ha **−578,94 bp** dopo 13 sedute. L'uscita 487 decisa dopo il calo del 26 ottobre produce +236,87 bp rispetto al mantenimento nei quattro giorni osservabili successivi. Non si sommano questi confronti, che partono da stati diversi e si sovrappongono.

L'ingresso misto LBRA è escluso dalla classe dei nuovi ingressi *puri* per definizione, ed è conservato nella classe mista; inoltre i suoi esiti finali e quelli della conferma sono censurati a T+21. La perdita del 26 ottobre resta interamente nel conto di strategia completo. Il +37,73 bp dei FRESH puri completi è quindi **un indizio strettamente condizionato**, non una misura dell'intero effetto delle nuove opportunità, non alpha e non una spiegazione additiva del CAGR. Dettagli: [CUTOFF_CHECK.json](CUTOFF_CHECK.json), [LBRA_CUTOFF_INTERVALS.csv](LBRA_CUTOFF_INTERVALS.csv), [FRESHW_BASE_CENSORED_FRESH.csv](FRESHW_BASE_CENSORED_FRESH.csv).

## Formula e convenzioni

Per ogni evento e si usano le quantità u₀ e il cash c₀ esatti di DECISIONS.npz prima dell'istruzione. Il NAV comune iniziale è N₀ = c₀ + Σu₀Cₜ. Alla chiusura T+h:

- Conto fermo: N_hold = c₀ + Σu₀Cₜ₊ₕ; nessuna istruzione, cash a rendimento zero.
- Conto dell'azione: N_action = cₕ + ΣuₕCₜ₊ₕ; soltanto l'istruzione immutabile originale, con eventuali retry.
- Differenza netta: Δ_bp = 10.000 × (N_action − N_hold) / N₀.
- Costi diretti: F_bp = 10.000 × Σcosti degli ordini eseguiti entro T+h / N₀.
- Contributo di mercato: M_bp = Δ_bp + F_bp, controllato anche come somma dei quantitativi firmati × (Close finale − prezzo del fill).

La componente di mercato usa le quantità realmente finanziabili **dopo** le commissioni; non è una simulazione alternativa a costo zero. Non è prevista una liquidazione artificiale a fine intervallo. La maschera conserva esattamente le quantità esterne; sell-only è limitato all'esposizione effettiva all'esecuzione; gli acquisti rispettano cash, commissione EUR1, costo proporzionale 15 bp e banda ordinaria. Le quotazioni non disponibili causano retry soltanto se coinvolte nella maschera. I mark di Close sono riportati causalmente come nel conto originale.

T è il Close del segnale. LAG2 può eseguire da T+3: tutti i suoi 1.049 esiti T+1 sono quindi pareggi senza transazione, non successo di timing. NEXT_CLOSE esegue al Close accettato da T+1: a T+1 la componente di mercato è zero e un fill produce soltanto costo. Le etichette WIN/LOSS/TIE usano esiti futuri esclusivamente a fini descrittivi, con tolleranza di pareggio 0,000001 bp.

Le classi derivano dai metadati e dalle variazioni effettive di target entro la maschera. 365 eventi misti/differiti rimangono separati, inclusi 186 DEFERRED_STATE di LAG2. Nessuna soglia o strategia è stata ottimizzata. Le finestre sono dipendenti, ricorrono gli stessi ETF e non esiste un holdout incontaminato. Restano i limiti storici dell'universo, degli aggiustamenti e dell'eseguibilità degli Open: la riconciliazione contabile non certifica quelle fonti.

## File riproducibili

[INTERVAL_MARKOUTS.csv](INTERVAL_MARKOUTS.csv) contiene tutti gli intervalli; [EVENT_CATALOGUE.csv](EVENT_CATALOGUE.csv) le azioni e le classificazioni; [ISOLATED_FILLS.csv](ISOLATED_FILLS.csv) gli ordini dei conti isolati. Le sintesi per classe, sottotipo e anno riportano anche numerosità, mediane, quantili, costi e frequenze di vittoria/perdita/pareggio. Le righe senza eventi rimangono esplicite.

Riproduzione: `python analysis/action_diagnostics/action_markouts.py . analysis/action_diagnostics`. Il codice usa solo Python, NumPy e pandas; nessun import dal simulatore o dal selettore. Quattro controlli sintetici coprono gap esterni, acquisti autofinanziati, lag/quote mancanti e censura del cutoff. Le evidenze RED/GREEN sono conservate. I CSV di origine sono letti con `float_precision='round_trip'`.
