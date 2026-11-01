# OLC13 — risultati del confronto controllato del target

1 novembre 2026. Esperimento concluso. Nessuna modifica a main o a Etf_trader; nessuna promozione operativa. Protocollo registrato prima dei nuovi fit nel commit d8892583614486703b76c14906aefd04ed8dd911, parent OLC12 8709a652eaa5100e1348c738f34abc05b3709901.

## Decisione

Nessuna delle tre alternative offre un miglioramento comune nei due universi. L'esponenziale con emivita42 e potenza1.5 migliora il portafoglio europeo, ma peggiora quello USA. Le due varianti lineari peggiorano nettamente il periodo principale nei due mercati. Manteniamo ORIGINAL_P15 come riferimento, non come optimum dimostrato. Non scegliamo una formula diversa per mercato dopo aver visto gli esiti.

## Contratto e lavoro eseguito

Quattro target cumulativi sugli stessi percentili dei rendimenti futuri a21/42/63 sedute:
- ORIGINAL_P15: pesi .45/.35/.20, potenza1.5.
- EXP42_P15: pesi proporzionali a2**(-h/42), normalizzati .4530818393/.3203772410/.2265409197, potenza1.5.
- ORIGINAL_P10: pesi originali, potenza1.
- EXP42_P10: pesi esponenziali42, potenza1.

288 nuovi fit:3 nuovi target x2 famiglie regressori x8 anni2019–2026 x3 seed101/211/307 x2 mercati. Altri4 refit di parità;96 controlli regressivi originali riutilizzati tramite previsioni archiviate autenticate. Stessi Hybrid42, stessi parametri ET/XGB, imputazione, ordine e gruppi di training interamente maturi OLC11. Media delle previsioni grezze dei tre seed prima dei percentili. Nessun classificatore nuovo. Return125 con RSI corretto resta congelato.

## Portafoglio integrato, finestra primaria2021–2024

Riferimento esatto OLC12 MATCHED_REG, non la precedente curva a seed unico. IMMEDIATE, parametro di costo .001 applicato al turnover del motore (metà L1), gestione stop ereditata. CAGR annualizzato a252 sedute. MaxDD nella finestra. Valori percentuali:

| Target | CAGR EU | MaxDD EU | CAGR USA | MaxDD USA |
|---|---:|---:|---:|---:|
| ORIGINAL_P15 | 20.03 | -23.25 | 39.92 | -27.00 |
| EXP42_P15 | 23.10 | -23.25 | 33.05 | -28.88 |
| ORIGINAL_P10 | 9.39 | -38.44 | 7.25 | -32.51 |
| EXP42_P10 | 8.89 | -39.12 | 2.99 | -36.67 |

EXP42_P15: delta CAGR +3.07 punti percentuali EU, -6.87 USA. Composizione e motore sono invariati; pesi nominali50/50 sulle due scelte. I flussi ausiliari di esposizione e V6 sono congelati per attribuzione appaiata: non viene rigenerato ogni sottosistema dal nuovo target. I trigger dipendenti dai ticker possono comunque cambiare.

## Selettore isolato e interazione con la fusione

CURRENT=.6*rank_ET+.4*rank_XGB. Eccesso lordo medio a21 sedute delle prime due scelte rispetto alla media equiponderata dell'universo eleggibile, NON CAGR e NON netto costi. Campione comune completamente maturo a63:44 mesi EU e45 USA, segnali2021–2024 con uscite prima del1 gennaio2025. La finestra di segnali è più restrittiva di quella di valorizzazione del portafoglio.

| Target | Eccesso21 EU % | Eccesso21 USA % |
|---|---:|---:|
| ORIGINAL_P15 | 0.488 | 1.847 |
| EXP42_P15 | 0.095 | 2.104 |
| ORIGINAL_P10 | 0.496 | 0.194 |
| EXP42_P10 | 0.448 | 0.215 |

La direzione geografica del solo CURRENT è opposta al portafoglio. La differenza si osserva già sugli stessi gruppi dopo la composizione: eccesso21 FUSION da1.453% a1.716% in EU, da3.126% a2.428% negli USA. Negli USA il deterioramento compare già con SMOOTH (1.382% ->1.093%); in EU SMOOTH passa1.036% ->0.942%, poi il vantaggio emerge con Return. Si documenta un'interazione fra target, memoria e fusione, non una causa di mercato dimostrata.

## Rendimenti incrementali delle stesse scelte iniziali

Eccessi rispetto all'universo nel blocco indicato, non annualizzati; nessuna riselezione al giorno21/42. Incremento=(1+R_lungo)/(1+R_corto)-1.

| Target | EU21–42 % | EU42–63 % | USA21–42 % | USA42–63 % |
|---|---:|---:|---:|---:|
| ORIGINAL_P15 | 0.940 | 0.615 | 0.425 | 0.203 |
| EXP42_P15 | 1.016 | 0.851 | -0.117 | -0.043 |
| ORIGINAL_P10 | 0.369 | 1.193 | 0.427 | -0.889 |
| EXP42_P10 | -0.058 | 1.018 | 0.397 | -0.631 |

L'esponenziale1.5 migliora la prosecuzione in EU, la peggiora negli USA. Non è stato addestrato alcun target incrementale in questa fase.

## Curvatura, sensibilità e limiti

Togliendo la potenza, correlazione media fra graduatorie delle label e originali:0.9967EU/0.9970USA. Ma la sovrapposizione delle due scelte CURRENT scende a35.8%EU/17.8%USA; la correlazione dei punteggi è circa0.81/0.79. I regressori dipendono dai valori e distanze numeriche, non dal solo ordine. Cambiare curvatura e scala con regolarizzazione fissa modifica il problema appreso. Questo è un test drop-in, non una ricerca del miglior modello per ciascun target. Le varianti lineari selezionano meno casi nel quintile peggiore a21, ma perdono molto lato positivo soprattutto USA; non dimostrano un miglior rapporto rischio/rendimento.

64 replay:48 principali (4target x2mercati x3politiche IMMEDIATE/DELAY3/PHASE5 x2costi .001/.003) e16 sensitività IMMEDIATE con input sistemici ritardati di una seduta. Su tutte le8 configurazioni per mercato nel2021–2024, EXP42_P15 migliora EU (+2.08 a+3.14pp CAGR), peggiora USA (-7.54 a-6.76pp). Entrambe le varianti lineari peggiorano tutte le stesse configurazioni.

Intera storia da febbraio2019 al1 luglio2026, IMMEDIATE/costo.001, CAGR EU/USA: originale14.94%/38.13%; esponenziale1.5 16.19%/35.54%; originale lineare8.81%/22.04%; esponenziale lineare8.74%/20.25%.

Non ogni anno ha lo stesso esito: nel2025 USA rendimento del periodo12.16% originale,19.25% esponenziale1.5,20.61% originale lineare,22.02% esponenziale lineare. Nel2026 fino al1 luglio entrambe le varianti lineari superano il controllo in entrambi i mercati. Non sono risultati annuali completi e non cancellano il danno sul periodo principale e sulla storia completa. Il vantaggio CURRENT21 di EXP42_P15 è positivo in2/3 seed USA e1/3 seed EU, non uniforme fra fit.

Bootstrap appaiato descrittivo, blocchi6mesi,4000draw,95%: delta eccesso CURRENT21 EXP42_P15-originale EU -0.393pp [-0.845;-0.017], USA +0.257pp [-0.378;+0.905]. Non sono intervalli del CAGR; nessun veto automatico se comprendono zero. Storia riutilizzata, più confronti senza correzione complessiva e mercati correlati: nessun holdout intatto. Costi/spread, total-return/FX, survivorship e same-open sono limiti ereditati; LAG1 non certifica tutta l'esecuzione live.

## Verifica conclusiva

884 file parent autenticati.38 test ereditati (15+23) e25 nuovi passati.16 preparazioni annuali con target originale identico;4 refit di controllo identici; punteggi finali originali identici;16 percorsi originali identici (12principali+4LAG1).

288 nuovi modelli ricaricati con previsioni identiche;144 controlli delle impronte del codice di training;120288 intervalli contabili;3328 metriche di portafoglio ricalcolate con algoritmo alternativo;1780 NDCG verificati con scikit-learn;17800 payoff verificati separatamente;4 prove di perturbazione futura con prefisso invariato. Massimo errore contabile3.55e-15; massimo errore metriche1.44e-13. Calcoli alternativi nella stessa sessione, non revisione esterna da altro analista.

Il pacchetto sorgenti/risultati contiene codice, test, tabelle, log e grafico. Il checkpoint completo include anche parent, input e modelli. I file di consegna sono identificati nel relativo DELIVERY_MANIFEST. Il prossimo oggetto distinto da studiare è il valore incrementale/prosecuzione, non ancora testato in OLC13.
