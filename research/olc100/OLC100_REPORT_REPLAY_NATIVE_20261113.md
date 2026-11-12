# OLC100 — Replay contabile nativo luglio–novembre 2026

**Esecuzione e audit: 13 novembre 2026. Snapshot prezzi: 12 novembre 2026.**  
**Stato: replay retrospettivo VERIFICATO; validazione prospettica NON ANCORA AVVIATA; nessuna promozione.**

## Decisione

Le selezioni Top2 del modello originale, già rigenerate per luglio–ottobre 2026 senza refit, sono state applicate al **motore originale OLC19** conservando l'intero stato pregresso: liquidità, posizioni, V6, stop, blocchi e riacquisti. I replay partono dal febbraio 2019 e proseguono fino al 12 novembre 2026. Nessun azzeramento del portafoglio al 1° luglio. Le quattro architetture componenti sono state mantenute separate dal candidato completo.

Confronto principale: **dal 3 agosto al 2 novembre**, tre decisioni nuove con outcome mensile maturato. I rendimenti sono cumulativi, **non CAGR**; netti delle commissioni e della frizione stop interne al simulatore OLC19, non netti di spread/impact broker certificati.

| Architettura | EU rendimento | USA rendimento | EU MaxDD¹ | USA MaxDD¹ | Stop EU/USA |
|---|---:|---:|---:|---:|---:|
| OLC19 — 50/50 immediato | -3,25% | +0,35% | -13,27% | -20,63% | 4/5 |
| OLC67 — MINVAR63 + DELAY3 | +0,24% | +11,77% | -10,08% | -21,35% | 4/3 |
| FUSION senza contesto | +1,01% | +0,21% | -13,01% | -19,91% | 3/4 |
| Solo MINVAR63 | -2,39% | +0,62% | -10,10% | -20,97% | 4/5 |
| Solo DELAY3 | -1,94% | +11,88% | -13,24% | -20,72% | 4/3 |
| Senza FAST_LOCK3 | -1,30% | +1,49% | -13,64% | -18,29% | 0/0 |

¹ MaxDD misurato sulle aperture del solo intervallo, non intraday; non è il MaxDD dell'intero storico.

Il differenziale candidato – baseline è **+3,49 pp in Europa** e **+11,41 pp negli USA**, ma non ha significatività prospettica con tre osservazioni mensili.

## Evoluzione mensile del conto

| Mercato | Intervallo dalla prima apertura | OLC19 | OLC67 | Delta OLC67 – OLC19 |
|---|---|---:|---:|---:|
| EU | Aug 2026 | +3,64% | +4,36% | +0,71 pp |
| EU | Sep 2026 | +4,58% | +3,18% | -1,40 pp |
| EU | Oct 2026 | -10,74% | -6,91% | +3,83 pp |
| USA | Aug 2026 | +15,36% | +27,10% | +11,74 pp |
| USA | Sep 2026 | -6,05% | -3,98% | +2,07 pp |
| USA | Oct 2026 | -7,40% | -8,42% | -1,01 pp |

Il vantaggio USA si concentra in **agosto**. Escludendo agosto, la differenza cumulata su settembre–ottobre è modesta: OLC19 **−13,01%** contro OLC67 **−12,06%**. Il test non dimostra stabilità interregime.

## Forensic: esecuzione del 3 agosto USA

Al segnale di venerdì 31 luglio, Top2 contestuale **BNO/USO**. Il 3 agosto OLC19 immediato apre entrambe le posizioni e il motore le ferma nella stessa seduta:

- **BNO:** stop intraday sul livello 47,6091, apertura superiore alla barriera; quantità appena acquistata positiva.
- **USO:** apertura 120,80 inferiore alla barriera 122,0656, quindi stop modellato all'apertura, ancora su quantità appena acquistata positiva.

DELAY3 trattiene invece temporaneamente **PPLT/PALL**. Dal 3 al 4 agosto i loro prezzi Open→Open salgono rispettivamente di **6,77%** e **6,73%**, mentre BNO/USO scendono di **6,77%** e **3,15%**. Il rendimento giornaliero simulato al 3 agosto è **−0,43% OLC19** contro **+6,76% OLC67**: un differenziale di **7,18 punti** nella sola prima seduta.

**Questo è il principale meccanismo economico identificato**, ma espone la conclusione a ipotesi di fill intraday, ordini di ingresso/stop contestuali e lockout. Un modello di stop basato su O/L/C giornalieri non prova che i due ordini avrebbero avuto realmente quei fill.

## Stress costi già congelato

Commissione 0,001 e 0,003; frizione stop 0,001 e 0,005. Nessuna scelta a posteriori di un costo favorevole.

| Mercato | Fee | Frizione stop | OLC19 | OLC67 | Differenziale |
|---|---:|---:|---:|---:|---:|
| EU | 0.001 | 0.001 | -3,25% | +0,24% | +3,49 pp |
| EU | 0.001 | 0.005 | -4,01% | -0,15% | +3,86 pp |
| EU | 0.003 | 0.001 | -5,02% | -1,42% | +3,60 pp |
| EU | 0.003 | 0.005 | -5,77% | -1,81% | +3,96 pp |
| USA | 0.001 | 0.001 | +0,35% | +11,77% | +11,41 pp |
| USA | 0.001 | 0.005 | -0,65% | +11,21% | +11,86 pp |
| USA | 0.003 | 0.001 | -1,71% | +10,02% | +11,73 pp |
| USA | 0.003 | 0.005 | -2,69% | +9,47% | +12,16 pp |

I differenziali rimangono favorevoli a OLC67 in tutte e quattro le ipotesi, ma nel caso più oneroso il suo rendimento EU è negativo. Lo stress è un test interno del simulatore, non una verifica delle condizioni di negoziazione.

## Pesi congelati sul nuovo periodo

MINVAR63 usa i 63 rendimenti log giornalieri completi precedenti alla prima apertura della decisione, con cap [25%,75%] e fallback 50/50.

| Mercato | Segnale | Top1 | Top2 | Peso Top1 MINVAR63 |
|---|---|---|---|---:|
| EU | 2026-07-31 | VVSM.DE | IBCJ.DE | 25.00% |
| EU | 2026-08-31 | VVSM.DE | EXV3.DE | 25.00% |
| EU | 2026-09-30 | VVSM.DE | LBRE.DE | 25.00% |
| EU | 2026-10-30 | EXV6.DE | LBRE.DE | 25.00% |
| USA | 2026-07-31 | BNO | USO | 69.39% |
| USA | 2026-08-31 | PPLT | SLV | 75.00% |
| USA | 2026-09-30 | TAN | ICLN | 25.00% |
| USA | 2026-10-30 | SLV | URA | 56.63% |

Lo score originale di Return125, ET/XGB, memoria, FUSION e rivalutazione contestuale non è stato modificato. Futures e posizioni short non sono introdotti come strumenti acquistabili.

## Audit indipendente e parità

- **48 percorsi nativi** = 6 configurazioni × 2 mercati × 2 commissioni × 2 frizioni stop.
- **20 verifiche** della serie giornaliera dei cinque bracci già presenti in OLC67 su entrambi i mercati e commissioni, **massimo errore assoluto log 6.67e-16**.
- I due baseline OLC19, EU/USA, e il controllo selezione originale riproducono esattamente le **sette matrici contabili archiviate** fino al punto di raccordo. La seduta finale storica (1 luglio) diventa normalmente negoziabile nel replay esteso.
- Le **180 decisioni storiche MINVAR63** riproducono i pesi congelati OLC56 entro 1e−10; ulteriori otto pesi luglio–ottobre calcolati senza dati successivi al segnale.
- I segnali giornalieri di stop/rischio ricostruiti coincidono negli **ultimi 250 giorni congelati**; il gross V6 coincide negli **ultimi 180 giorni** per entrambi i mercati.
- Ricalcolo indipendente del rendimento per la finestra principale dal logaritmo dei rendimenti giornalieri: errore massimo **1.35e-15**; il MaxDD del sotto-periodo è calcolato dalle aperture.

## Qualità dati e limiti ancora bloccanti

Lo snapshot contiene **314 ETF**, 79 barre OHLC segnalate su 15 ticker. **Nessuno dei ticker dei nuovi Top2 (compreso il controllo FUSION originale) coincide con quei 15 ticker**. Nelle nuove sedute V6 non ha selezionato alcun ETF alternativo; il controller V6 ha livelli gross 0,95 o 1,00 e la trasformazione congelata mantiene esposizione teorica 1,00 in assenza di altri blocchi. La sensibilità principale deriva quindi da timing e FAST_LOCK3.

Ciò **non certifica** qualità complessiva della fonte: i prezzi sono stati scaricati/ricalibrati il 12 novembre dopo che erano noti gli outcome luglio–ottobre, e il dataset non è un archivio autentico di quote point-in-time alla data dei vecchi segnali. Mancano ancora certificazione storica dell'universo ETF, maschera originale USA, dividendi/total-return/FX, prezzi bid/ask e verifica degli stop realmente eseguibili. Il rischio di errori per split, restatement o contratti di stop resta aperto.

I contrasti di layer derivano da **replay completi con stati contabili diversi**, non da counterfactual perfettamente matched-state al medesimo evento. Non vanno interpretati come effetti causali puri di singole feature; per questi serve un esperimento cloned-state separato, predefinito e con fill certificato.

## Conclusione operativa

**Mantenere OLC19 come baseline e OLC67 come candidato di ricerca**, senza promozione. Congelare questi risultati e non usare il comportamento di agosto per ottimizzare ulteriormente ritardi, pesi, stop o parametri. Il vero test prospettico comincia quando il segnale di fine novembre viene prodotto e registrato prima della prima apertura di dicembre, con dati verificati. Nessun ordine è stato inviato e `main` non è stato modificato.

## Riproduzione e provenienza

Sorgenti congelate: OLC19 ZIP SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`. Materiali richiesti da Library: OLC19, OLC56, OLC67, archivio OLC100 Top2 luglio–ottobre e snapshot sorgenti 314 ETF del 12 novembre. Il pacchetto allegato contiene il runner, il forensic stop e tutti i risultati numerici, ma non include i binari degli archivi originali (oltre 100 MB).
