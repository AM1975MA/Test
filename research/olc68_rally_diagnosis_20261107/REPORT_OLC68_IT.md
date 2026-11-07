# OLC68 — Perché OLC67 sacrifica i rally e come conservare l'efficacia di OLC19 (2024–2026)

**7 novembre 2026 · Research only · OLC19/main invariati**

## Risultato principale

L'analisi causale nel senso **di confronto controllato fra policy**, non di identificazione di cause macroeconomiche, mostra che il sacrificio dei rialzi nasce soprattutto dalle **combinazioni dei pesi a minima varianza e del ritardo di ingresso**, e in alcuni episodi dagli stati di stop/rientro che queste scelte generano. L'esistenza di un forte rally da sola non identifica quale policy vincerà: OLC67 batte OLC19 in Europa nel 2024, ma perde negli USA nello stesso anno; nel 2025 il segno è opposto fra i due mercati. Il 2026 è soltanto **gennaio–prima apertura di luglio**, non l'anno intero.

### Rendimento annuale: confronto esatto, coefficiente fee 0,001

| Anno | EU OLC19 | EU OLC67 | differenza pp | USA OLC19 | USA OLC67 | differenza pp |
|---|---:|---:|---:|---:|---:|---:|
| 2024 | 22,44% | 35,17% | +12,73 | 78,61% | 68,88% | −9,73 |
| 2025 | 17,95% | 10,15% | −7,80 | 13,57% | 17,83% | +4,26 |
| 2026 parziale | 16,51% | 15,28% | −1,22 | 62,44% | 52,06% | −10,38 |

### Attribuzione, in **punti percentuali di log-rendimento cumulato**

| Mercato/anno | Solo MINVAR63 | Solo DELAY3 | Interazione pesi×timing | Totale |
|---|---:|---:|---:|---:|
| EU 2024 | +5,39 | +2,75 | +1,76 | +9,89 |
| USA 2024 | −3,17 | +0,97 | −3,40 | −5,60 |
| EU 2025 | −3,12 | −3,13 | −0,59 | −6,84 |
| USA 2025 | +1,52 | +2,96 | −0,80 | +3,68 |
| EU 2026 parziale | −2,91 | +1,96 | −0,11 | −1,06 |
| USA 2026 parziale | −1,51 | −4,07 | −1,03 | −6,60 |

Le tre colonne sommano esattamente nel log-rendimento; **non sommare queste cifre alle differenze di rendimento aritmetico** della tabella precedente. Sono effetti *condizionali* alla politica FAST_LOCK3 e includono le conseguenze sul percorso di rischio e stop: non sono effetti economici universalmente causali di ciascun parametro.

## Evidenza delle sedute favorevoli

Per ogni anno abbiamo separato **a posteriori** i giorni con OLC19 positivo e quelli con OLC19 non positivo. OLC67 generalmente perde rispetto a OLC19 sui primi e recupera sui secondi.

| Mercato/anno | Differenza su giorni OLC19 positivi | su giorni OLC19 non positivi | saldo |
|---|---:|---:|---:|
| EU 2024 | −8,66 log-pp | +18,56 log-pp | +9,89 log-pp |
| USA 2024 | −22,18 | +16,58 | −5,60 |
| EU 2025 | −9,83 | +2,99 | −6,84 |
| USA 2025 | −2,32 | +6,00 | +3,68 |
| EU 2026 parziale | −5,82 | +4,76 | −1,06 |
| USA 2026 parziale | −13,15 | +6,55 | −6,60 |

**Attenzione:** classificare i giorni in base a un rendimento conosciuto solo dopo la seduta non permette di creare uno switch causale in tempo reale. Serve soltanto a descrivere il meccanismo di partecipazione ai rialzi e protezione dalle perdite.

## I mesi che spiegano gran parte dei sacrifici

Le differenze seguenti si riferiscono al **mese di valorizzazione**, non sempre esattamente al mese di decisione, poiché i rendimenti sono da apertura a apertura successiva:

- **USA 2024:** maggio e giugno sommano −1.265,8 log-bp, una perdita superiore al saldo annuale di −559,9 log-bp; gli altri mesi recuperano parte del divario. A maggio il portafoglio aveva la coppia **UNG/URA**, con tilt MINVAR sul primo ETF intorno al 26,5%, rispetto al 50/50 originale. La ricostruzione dei confronti singoli mostra un'interazione peso×timing fortemente negativa nel semestre.
- **Europa 2025:** maggio e giugno rappresentano −546,9 dei −684,3 log-bp annuali (circa 80%). Le coppie sul segnale includono **VVSM.DE/IBCJ.DE** (maggio) e **VVSM.DE/XDWT.DE** (giugno), con peso MINVAR del primo ETF al 25% in entrambi i mesi.
- **USA 2026:** marzo pesa −583,9 dei −660,4 log-bp semestrali (circa 88%). Coppia sul segnale **KRE/KBE**, peso MINVAR del primo ETF 25%; il contributo dominante al calo della policy è il DELAY3 e la sua interazione.
- **Europa 2026:** giugno perde −379,1 log-bp mentre il saldo semestrale è −105,7: nel resto del periodo i vantaggi hanno compensato gran parte della perdita. Coppia sul segnale **EXV9.DE/EXV5.DE**, peso MINVAR del primo ETF 25%.

Si tratta di diagnosi ex post **non di istruzioni su quali ETF comprare**.

## Protezione: cosa è e cosa non è la causa

Sono stati riprodotti i percorsi OLC19 originali e OLC67, assieme ai due controfattuali a un solo cambiamento, e confrontati con precisione meglio di 1e−12 nei rendimenti giornalieri originali OLC67.

| Mercato/anno | Esposizione media OLC19 | OLC67 | Stop rapidi OLC19 | OLC67 |
|---|---:|---:|---:|---:|
| EU 2024 | 95,1% | 95,3% | 5 | 5 |
| USA 2024 | 92,7% | 91,4% | 6 | 8 |
| EU 2025 | 93,8% | 93,9% | 8 | 8 |
| USA 2025 | 83,6% | 83,5% | 19 | 19 |
| EU 2026 parziale | **100%** | **100%** | 0 | 0 |
| USA 2026 parziale | 79,1% | 76,5% | 14 | 16 |

**Conclusione**: disattivare FAST_LOCK3 perché la policy talvolta manca i rally sarebbe un errore metodologico. Nel 2025 EU l'esposizione e il numero di stop delle due policy sono praticamente identici ma i rendimenti divergono. Nella prima metà del 2026 EU entrambe sono interamente esposte e senza stop: lì la perdita deriva necessariamente dalle differenti allocazioni e date d'ingresso, non dal layer di protezione.

## Le informazioni *ex ante* già disponibili bastano a prevedere il regime?

Sono stati ricostruiti alla data del segnale i momentum 63/126 delle coppie, breadth dell'universo su 63 sedute, dispersione, direzione del tilt MINVAR e concentrazione. Le sedute non osservate EU sono state gestite scegliendo l'ultima seduta **effettivamente comune precedente** al segnale (>=80% strumenti osservati) e 63/126 sedute comuni precedenti, evitando falsi breadth di zero nei festivi. Non è stato eseguito fitting. L'associazione con il vantaggio futuro OLC67−OLC19 non si mantiene nello stesso senso e nella stessa forza fra fase 2019–2023 e 2024–2026 o fra EU/USA. Per esempio Spearman breadth63 versus differenziale futuro: EU −0,279 nella fase iniziale contro +0,226 nella fase successiva; USA +0,189 contro +0,013. Sono statistiche esplorative, con test multipli, esiti futuri già ampiamente studiati e serie point-in-time non integralmente certificate.

**Non proporre oggi** uno switch basato esclusivamente su momentum di mercato o ampiezza dei rialzi: non esiste ancora un indicatore di regime validato.

## Un benchmark ibrido indipendente, fissato prima del risultato: due sleeve 50/50

È stata eseguita una singola nuova composizione: 50% del capitale iniziale in OLC19 e 50% in OLC67, senza riequilibrio successivo e senza un selettore di regimi. Il NAV aggregato usa due percorsi contabili già eseguiti: 0,5×NAV(OLC19)+0,5×NAV(OLC67). Le commissioni dei due engine restano già incluse nei rendimenti giornalieri, ma non sono certificati spread/costi fissi, né netting di posizioni.

| Periodo/mercato | OLC19 CAGR | OLC67 CAGR | Sleeves 50/50 CAGR | DD max sleeves |
|---|---:|---:|---:|---:|
| EU 2021–2024 | 23,20% | 34,43% | **28,91%** | −24,36% |
| USA 2021–2024 | 50,77% | 51,27% | **51,04%** | −17,46% |
| EU FULL feb2019–lug2026 | 19,76% | 22,61% | **21,24%** | **−25,53%** |
| USA FULL feb2019–lug2026 | 39,48% | 42,10% | **40,83%** | −26,92% |

Con coefficiente fee 0,003 l'ibrido nel FULL restituisce **17,54% EU / 32,65% USA CAGR**, contro baseline 16,18% / 31,34% e OLC67 18,81% / 33,89%; non risolve l'incertezza di eseguibilità. Nel 2024–26, rispettivamente EU 29,30%/13,55%/15,84% parziale e USA 73,21%/15,88%/56,72% parziale. Questo compromesso *non è il salto di performance* ricercato, ma evita una scelta opportunistica del regime a posteriori e modera in parte i difetti delle singole policy.

## Proposta per la fase successiva

Non moltiplicare soglie sul passato. Due possibili linee con contratti separati:

1. **Allocazione di opportunità e rally capture**: stimare prima del segnale la convenienza relativa del 25/75 vs 50/50 a partire da fattori macro/trasversali e differenziale previsto di rendimento *dei due ETF scelti*, usando etichette completamente mature. Non abbandonare la diversificazione e lo stop quando manca un segnale verificato: fare fallback su un peso neutro. L'OLC52 Ridge precedente ha già mostrato che tre sole feature di rischio non bastavano.
2. **Timing come decisione distinta**: stimare se la perdita delle primissime sedute di un nuovo trend è recuperata nei giorni successivi e la stabilità del cambio leader; il precedente OLC56 ha evidenziato forte concentrazione in pochi mesi del vantaggio DELAY3. In assenza di un predittore di qualità, mantenere una policy fissa oppure diversificare le policy; non scegliere 1/2/3/4 giorni dopo aver visto il rendimento.

**Gate richiesto**: bloccare ex ante la regola, rieseguire il motore OLC19 con stop e rientri veri di ciascuna policy, controllare entrambi i mercati e anni 2024/25/26 come diagnostica già vista; la decisione di promozione richiede mesi **successivi a luglio 2026 non studiati** e verifica della qualità dei dati. Non usare la miglior combinazione 2021–24 come previsione di un nuovo regime.

## Riproducibilità e verifiche

- Origine OLC67 ZIP SHA256 `dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4` (verifica `OLC68_QA.json`).
- 256 rendimenti annui OLC67 ricalcolati indipendentemente con errore massimo 5,22e−15, sei ponti annuali log-bp 2024–2026 e 20 verifiche di CAGR dei due sleeve.
- Otto replay OLC19 per leggere risk_trace, parità OLC67 giornaliera entro 1e−12, dati originali e fonte `.zip` immutati.
- Analisi dei dati per un singolo segnale all'ultimo **Close noto prima del mese**; nessun input futuro come feature. Nessuna verifica broker o prezzo d'asta.

**Stato:** OLC68 completato come diagnosi. Nessuna modifica a `main` o a OLC19. Il candidato OLC67 resta research-only; il portafoglio due sleeve è un benchmark illustrativo, non una policy validata in avanti.