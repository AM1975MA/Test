"""Build the Italian research report from the frozen, audited evidence."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ARMS = json.loads((ROOT / "docs/EXPERIMENT_FREEZE.json").read_text())["arms"]
S = pd.read_csv(ROOT / "results/SCORECARD.csv", float_precision="round_trip")
B = S[S.scenario == "BASE"].set_index("arm").loc[ARMS]
A = pd.read_csv(ROOT / "results/ANNUAL_RETURNS.csv", float_precision="round_trip")
D = pd.read_csv(ROOT / "analysis/action_diagnostics/SUMMARY_BY_CLASS.csv", float_precision="round_trip")
LABELS = {
    "BASE": "OLC109 originale", "STATIC_HALF": "50% investito / 50% cash",
    "STATIC_75": "75% investito / 25% cash", "REFRESH_WEEKLY": "Selettore settimanale",
    "EXIT21_MONTHLY": "Uscita 21 / rientro mensile", "EXIT21_SLOW": "Uscita 21 / rientro lento",
    "EXIT21_FAST": "Uscita 21 / rientro rapido pieno", "EXIT21_STAGED": "Uscita 21 / rientro graduale",
    "EXIT63_STAGED": "Uscita 63 / rientro graduale", "TRAIL15_STAGED": "Trailing 15% / graduale",
    "VOLTRAIL_STAGED": "Trailing volatilità / graduale",
    "EXIT21_STAGED_FRESHW": "Nuove opportunità settimanali (primaria)",
    "EXIT21_STAGED_FRESHD": "Nuove opportunità giornaliere",
}


def num(value, decimals=2):
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pct(value):
    return num(value * 100) + "%"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"] +
                     ["| " + " | ".join(str(v) for v in row) + " |" for row in rows])


base_table = table(["Configurazione", "CAGR", "DD Open/Close", "Esposizione media", "Ordini"], [
    [LABELS[a], pct(B.loc[a, "cagr"]), pct(B.loc[a, "maxdd_sampled"]),
     pct(B.loc[a, "mean_exposure"]), int(B.loc[a, "orders"])] for a in ARMS])

scenarios = ["BASE", "ZERO_COST", "DOUBLE_COST", "LAG1", "LAG2", "NEXT_CLOSE"]
indexed = S.set_index(["arm", "scenario"])
stress_table = table(["Configurazione", "BASE", "Costi zero", "Costi doppi", "+1 seduta", "+2 sedute", "Close T+1"],
                     [[LABELS[a]] + [pct(indexed.loc[(a, s), "cagr"]) for s in scenarios] for a in ARMS])
annual_arms = ["BASE", "STATIC_75", "EXIT21_MONTHLY", "EXIT63_STAGED", "EXIT21_STAGED_FRESHW", "EXIT21_STAGED_FRESHD"]
annual = A[A.scenario == "BASE"].pivot(index="year", columns="arm", values="annual_return")
annual_table = table(["Anno", "OLC109", "75% investito", "Uscita 21 / mensile", "Uscita 63 / graduale", "Nuove settimanali", "Nuove giornaliere"],
                     [[str(y) + ("*" if y in [2020, 2026] else "")] + [pct(annual.loc[y, a]) for a in annual_arms] for y in annual.index])
activity = table(["Modello", "Giorni con scambi / anno", "Ordini totali", "Turnover annuo, due lati", "Costi cumulati", "Capitale finale"],
                 [[LABELS[a], num(B.loc[a, "trading_days_per_year"]), int(B.loc[a, "orders"]),
                   num(B.loc[a, "two_sided_turnover_per_year"]) + "×", "€" + num(B.loc[a, "costs"]),
                   "€" + num(B.loc[a, "end_equity"])] for a in ["BASE", "STATIC_75", "EXIT63_STAGED", "EXIT21_STAGED_FRESHW", "EXIT21_STAGED_FRESHD"]])
diag_names = {"PURE_EXIT": "Sola uscita", "SAME_ASSET_REENTRY": "Rientro sullo stesso ETF",
              "PROBE_CONFIRMATION": "Aumento dopo conferma", "FRESH_ENTRY": "Nuova opportunità",
              "MIXED_DEFERRED": "Azioni miste o differite"}
diag = D[(D.arm == "EXIT21_STAGED_FRESHW") & (D.scenario == "BASE") & (D.horizon_sessions == 21)]
diag_table = table(["Azione", "Intervalli completi", "Differenza netta media", "Componente di mercato", "Costi diretti", "Casi favorevoli"], [
    [diag_names[r.category], int(r.complete_intervals), num(r.mean_increment_bp) + " bp",
     num(r.mean_market_markout_bp) + " bp", num(r.mean_direct_cost_bp) + " bp", num(r.win_pct) + "%"]
    for r in diag.itertuples()])
segments = pd.read_csv(ROOT / "results/DESCRIPTIVE_SEGMENTS.csv", float_precision="round_trip")
seg = segments[(segments.scenario == "BASE") & (segments.segment == "2021_2026")].set_index("arm")
exclude_2020 = table(["Periodo 2021–30 ottobre 2026", "CAGR"],
                     [[LABELS[a], pct(seg.loc[a, "cagr"])] for a in ["BASE", "STATIC_75", "EXIT63_STAGED", "EXIT21_STAGED_FRESHW", "EXIT21_STAGED_FRESHD"]])

report = f'''# OLC110 — Protezione, cash e rientro sulle opportunità

**Rapporto del 15 novembre 2026. Esito: nessuna nuova protezione promossa.**

## 1. Risultato e decisione

La strategia OLC109 è stata salvata nel repository **AM1975MA/Test**, nel branch [research/olc109-freeze-20261115](https://github.com/AM1975MA/Test/tree/research/olc109-freeze-20261115/research/olc109), al commit [12908133d98dba91d09cdb1a5266a64421d9d075](https://github.com/AM1975MA/Test/commit/12908133d98dba91d09cdb1a5266a64421d9d075). Il salvataggio comprende codice, test, protocollo, tutti i 200 risultati precedenti e i conti completi dei cinque scenari del candidato. I 428 file remoti sono stati verificati rispetto agli hash attesi.

Ho poi mantenuto fisso il selettore OLC109 e sviluppato una nuova gestione di uscita, liquidità e rientro: **13 configurazioni, sei scenari di esecuzione/costo, 78 conti completi**. Il candidato dichiarato prima dei risultati, **EXIT21_STAGED_FRESHW**, esce quando il trend breve si deteriora, rientra gradualmente su un rebound e cerca nuove opportunità ogni settimana quando ha liquidità effettiva.

Questo candidato fallisce il confronto: **CAGR 6,61%, drawdown campionato −46,78%**, contro **25,75% e −37,92% di OLC109**. La perdita di CAGR è di **19,14 punti percentuali annui**; il drawdown peggiora di **8,86 punti**. Il capitale finale da €10.000 scende da **€46.045,58** del riferimento a **€15.319,17**.

La protezione dinamica con il CAGR più alto nel caso BASE è **EXIT63_STAGED**, con **17,50% e −36,62%**. Anche questa è superata dal controllo semplice che investe nominalmente il 75% ai ribilanciamenti mensili: **20,50% e −31,96%**. **Tutte le nove protezioni dinamiche BASE sono dominate da questo controllo su entrambe le misure.** Il controllo riduce il rischio rinunciando a una parte del rendimento del riferimento; non dimostra una capacità di prevedere i momenti migliori.

Nessuno dei 78 conti raggiunge il CAGR del 30%, nemmeno a costi zero. OLC109 resta il riferimento di ricerca. Questi risultati non giustificano la sostituzione con una delle nuove protezioni. La capacità di rientrare meglio è un'ipotesi ancora aperta, non un risultato ottenuto.

Fonti numeriche: [SCORECARD.csv](results/SCORECARD.csv), [ANALYSIS_SUMMARY.json](analysis/ANALYSIS_SUMMARY.json), [CONTROL_DOMINANCE.csv](analysis/CONTROL_DOMINANCE.csv).

![Risultati OLC110](figures/OLC110_RISULTATI.png)

## 2. Che cosa è stato testato

L'universo resta il pannello V3 di **2.096 ETF quotati in EUR su Xetra**, non i soli 29 del primo progetto. È un universo ampio di quotazioni osservate nel catalogo disponibile; non è una ricostruzione di tutti gli ETF mondiali e di tutti quelli cessati nel passato. La quotazione in EUR non elimina automaticamente il rischio valutario degli investimenti sottostanti.

Il periodo è **2 marzo 2020–30 ottobre 2026**, con €10.000 iniziali, cash remunerato allo 0%, imposte escluse e unità economiche frazionarie. Non c'è leva di conto né vendita allo scoperto. Il selettore **DEDUP_DUAL_TREND_OPP** mantiene due posti nominali del 50%, distingue leader e opportunità in accelerazione, richiede liquidità mediana a 63 sedute di almeno €100.000 e controlla la correlazione a 126 sedute con soglia 0,85. La selezione mensile originale è stata ricostruita indipendentemente, senza modificarne gli 80 target.

Le nuove regole hanno tre componenti separate:

1. **Uscita:** deterioramento sotto media a 21 sedute con momentum a cinque sedute negativo; alternativa più lenta sotto media a 63 con momentum a 21 negativo; oppure discesa del 15% da un massimo a 63 sedute, o soglia dipendente dalla volatilità congelata all'ingresso. Un segnale a Close autorizza un ordine successivo: non consente di vendere retroattivamente al massimo o alla soglia.
2. **Rientro sullo stesso ETF:** conferma lenta sopra media 63 e momentum 21 positivo, oppure rebound breve sopra il massimo delle cinque chiusure precedenti, media 10 e momentum 5 positivo. Nel rientro graduale il primo acquisto vale metà posto, cioè il 25% nominale del conto; il pieno richiede una conferma successiva all'acquisto realmente eseguito.
3. **Nuove opportunità:** se il posto è effettivamente libero e il vecchio ETF non è ammesso al rientro, ricerca di un altro ETF nel pool emergente, con trend e accelerazione positivi e controllo di correlazione contro tutte le posizioni effettive. La frequenza è settimanale nel candidato primario e giornaliera nell'alternativa. Anche questa entrata parte a metà posto.

Sono stati aggiunti controlli con il 50% e il 75% nominale investito e un selettore completo settimanale senza protezione. Questi controlli distinguono il beneficio della minore esposizione da quello di un vero timing e il beneficio delle nuove opportunità dal semplice aumento della frequenza di trading. I pesi dei controlli sono ripristinati al calendario mensile: non restano esattamente costanti ogni giorno.

L'esecuzione rispetta quantità e cash reali. Un ordine di uscita ancora ineseguito non libera un posto; un probe richiesto ma non acquistato non può essere promosso. Le azioni su un ETF non modificano le quantità degli altri. Le istruzioni pendenti e le quotazioni mancanti possono ritardare le azioni. I controlli di queste proprietà sono parte dell'audit, non assunzioni implicite.

Le soglie, i 13 casi e il candidato primario sono stati congelati **prima** dei 78 rendimenti. Le evidenze precedenti erano già note: lo studio è adattivo e non possiede un periodo di verifica mai osservato. Non sono stati aggiunti altri modelli dopo aver visto questi risultati.

Specifiche integrali: [protocollo](docs/DESIGN_AND_PROTOCOL.md), [congelamento di codice e dati](docs/EXPERIMENT_FREEZE.json).

## 3. Tutti i risultati BASE

Commissione di €1 più 15 punti base per ciascun ordine, esecuzione al primo Open accettato da T+1. Il drawdown usa Open e Close, quindi può essere maggiore di quello calcolato soltanto sulle chiusure. Non è il massimo intraday osservato tick per tick.

{base_table}

Il rientro veloce pieno non migliora il rientro lento: il CAGR passa da 5,75% a 4,91%. Il rientro graduale recupera parte del danno e arriva al 5,97%. Aggiungere le nuove opportunità settimanali porta al 6,61%; la ricerca giornaliera arriva al 9,96%. Sono miglioramenti rispetto al debole modello di uscita breve e rientro graduale, ma restano molto lontani dal riferimento senza protezione.

L'uscita 21 con attesa mensile consegue 15,03%, con esposizione media del 45,62% e **626 sedute interamente cash**. Il controllo con il 50% investito ottiene 14,24% con drawdown −24,52%, contro −32,96% del modello dinamico. Una riduzione marcata del tempo investito non assicura una migliore protezione del percorso del capitale.

La configurazione primaria ha esposizione media dell'80,54% e **87 sedute interamente cash**; quella con ricerca giornaliera arriva all'87,01% e 42 sedute cash. L'aggiunta di opportunità impiega più capitale, ma non recupera il rendimento perduto dalle uscite e dai rientri del sistema complessivo.

## 4. Costi e prezzi di esecuzione

La tabella riporta il CAGR di tutti i casi; le percentuali non sono rendimenti di singoli anni.

{stress_table}

BASE usa €1 + 15 bp per lato; costi doppi usa €2 + 30 bp. I ritardi aggiungono una o due sedute all'esecuzione ordinaria. Close T+1 usa il primo Close osservato e accettato successivo al segnale. In quest'ultimo scenario il drawdown è su Close prima/dopo i costi, non sul campionamento Open/Close: le due misure non vanno confrontate come se avessero la stessa frequenza.

**I costi sono una parte del problema, ma non lo esauriscono.** Il candidato primario senza costi arriva al 14,21%, mentre OLC109 senza costi arriva al 28,82%. La differenza BASE–costi zero del candidato è di 7,60 punti di CAGR; quella del riferimento è di 3,07. Sono confronti tra conti completi, nei quali i costi modificano anche il capitale disponibile: non si ottengono sottraendo linearmente la somma delle commissioni da un rendimento annuo.

{activity}

I giorni con scambi non sono il numero di singoli ordini. Il turnover è la somma di acquisti e vendite rapportati al patrimonio e annualizzata secondo la convenzione del runner. La ricerca settimanale delle opportunità porta le giornate operative da circa 12 a 73 annue e gli ordini complessivi da 226 a 674. La ricerca giornaliera arriva a 757 ordini.

I ritardi producono risultati non monotoni. Per esempio, TRAIL15_STAGED con una seduta extra ottiene 20,46%, superando il riferimento dello stesso scenario a 18,65%, ma con due sedute extra scende al 9,18%. Questo singolo confronto favorevole non viene scelto a posteriori come nuova strategia; il ritardo non è una variabile ottimizzata. La dominanza del controllo 75% dichiarata sopra si riferisce allo scenario BASE, non indiscriminatamente a ogni scenario.

Fonti: [CAGR_BY_SCENARIO.csv](analysis/CAGR_BY_SCENARIO.csv), [COST_AND_ACTIVITY.csv](analysis/COST_AND_ACTIVITY.csv), conti completi in [results](results/).

## 5. I singoli anni e il peso del 2020

{annual_table}

\\* 2020 dal 2 marzo; 2026 fino al 30 ottobre. Nessuno dei due è un anno civile completo. Il 2024 è incluso esplicitamente: l'originale guadagna 33,95%, mentre l'uscita lenta/graduale perde 5,41% e il candidato primario perde 15,70%. Il danno non è quindi limitato all'ultimo episodio negativo del 2026.

Il 2020 ha un peso elevato sul CAGR complessivo, anche per OLC109. Togliendo quel periodo iniziale, con una nuova base di misurazione a fine 2020, i CAGR descrittivi diventano:

{exclude_2020}

Questa suddivisione non è un test indipendente: tutti i periodi sono già stati osservati. Mostra però che il 25,75% aggregato del riferimento non descrive uniformemente gli anni successivi e che le nuove protezioni non risolvono questa dipendenza.

Fonte: [ANNUAL_RETURNS.csv](results/ANNUAL_RETURNS.csv), [DESCRIPTIVE_SEGMENTS.csv](results/DESCRIPTIVE_SEGMENTS.csv).

## 6. Dove il meccanismo perde: confronto sullo stesso conto

Ho isolato **3.869 istruzioni inframensili** di cinque modelli nei casi BASE, ritardo di due sedute e Close T+1: **11.607 intervalli** a una, cinque e 21 sedute. Per ogni evento i due rami partono dalle stesse quantità, dallo stesso cash e dallo stesso NAV al segnale. Il primo esegue soltanto quell'istruzione; il secondo conserva il conto iniziale. Nessuno dei due riceve le successive decisioni della strategia. Sono rispettati costi, prezzi accettati, maturazione e tentativi di esecuzione.

La differenza è espressa in punti base del **NAV comune al segnale**, non in rendimento percentuale dell'ETF comprato. Per una vendita il controllo continua a detenere il titolo; per un acquisto conserva il cash. La componente di mercato è la differenza netta più i costi diretti sulle quantità effettivamente finanziate, non un nuovo backtest a costi zero.

Per il candidato primario, BASE, a 21 sedute:

{diag_table}

**Le uscite hanno un costo medio di opportunità rilevante:** −40,80 bp netti per evento rispetto a restare investiti, di cui −32,22 legati al percorso dei prezzi e 8,59 di costi. I rientri sul vecchio ETF hanno una differenza media di −36,61 bp contro restare cash. Il semplice riconoscimento del rebound non ha quindi risolto il problema del rientro nello stesso investimento.

**Le istruzioni di solo nuovo ingresso mostrano un indizio più interessante:** +37,73 bp medi a 21 sedute, con 57,35% degli intervalli favorevoli. A cinque sedute il vantaggio scende però a **+1,80 bp netti**, dopo 4,90 bp medi di costo. Questa categoria non comprende tutti gli acquisti di opportunità: le istruzioni con transizioni diverse contemporanee restano nella categoria mista. La misura a 21 sedute cambia molto tra anni ed è negativa nel 2022 e nel 2024; i campioni annuali sono piccoli. I risultati completi dei ritardi e della chiusura successiva sono conservati, senza selezionare soltanto le condizioni migliori.

Questo indizio **non dimostra alpha**, non valuta il miglior candidato alternativo e può contenere il semplice premio per assumere rischio rispetto a detenere cash. Gli eventi sono condizionati ai conti generati dal modello fallito. Le finestre si sovrappongono, gli stessi ETF ricorrono più volte e le azioni modificano i futuri stati del conto. Non si possono sommare o capitalizzare queste medie per spiegare i 19,14 punti di CAGR persi o costruire un rendimento alternativo.

Ci sono **101 intervalli troncati**, relativi a 82 eventi, conservati e segnalati ma esclusi dalle medie a orizzonte completo. La censura a fine campione può escludere dai confronti a 21 sedute ingressi recenti e le loro conseguenze; le perdite dell'ultima parte di ottobre restano invece integralmente nel conto di strategia. Nel candidato primario i nuovi ingressi puri sono 69, di cui 68 completi a 21 sedute. Il caso mancante riguarda IS0D, non LBRA. Il segnale del 9 ottobre che porta all'acquisto LBRA il 12 ottobre fa invece parte di un'istruzione **mista**, seguita da un segnale di conferma il 13 ottobre, eseguito il 14: entrambe le finestre sono troncate prima di 21 sedute. La differenza parziale dell'intera istruzione mista, che include anche un altro ETF, è di **−607,75 bp in 15 sedute**; quella dell'istruzione di conferma è **−578,94 bp in 13 sedute**. Sono eventi sovrapposti, quindi non vanno sommati. Questo chiarisce perché una media favorevole degli ingressi puri non possa essere presentata come un successo di tutte le nuove opportunità, né cancellare la perdita complessiva del modello.

Le 3.869 fotografie iniziali e i libri privi di istruzioni pendenti sono stati verificati; **4.395 esecuzioni** antecedenti a successive sostituzioni sono state ridimensionate indipendentemente e coincidono in quantità, prezzo, controvalore e costo. Nessun nuovo conto di strategia è stato ottimizzato per questa diagnostica.

Fonti: [diagnostica degli eventi](analysis/action_diagnostics/), [SUMMARY_BY_CLASS.csv](analysis/action_diagnostics/SUMMARY_BY_CLASS.csv), [SUMMARY_BY_YEAR.csv](analysis/action_diagnostics/SUMMARY_BY_YEAR.csv), [VALIDATION.json](analysis/action_diagnostics/VALIDATION.json).

## 7. Perché un'uscita dopo il calo può arrivare tardi

La diagnosi precedente ai nuovi test aveva già evidenziato due difficoltà. Nel drawdown massimo di OLC109, dal picco del 19 marzo 2020 al minimo dell'11 agosto, il fondo su futures VIX contribuiva per circa **€8.352,87** a una perdita dal picco di **€8.389,68**. La posizione completa restava tuttavia in utile sul suo periodo di detenzione. Una protezione basata soltanto sulla perdita rispetto al prezzo di acquisto non coglie automaticamente la restituzione di un grande profitto accumulato.

Inoltre, nei 20 peggiori giorni osservati del riferimento, il **65,67% della somma delle perdite aritmetiche** ricadeva nel tratto fra Close precedente e Open successivo. È una descrizione di quei giorni selezionati a posteriori, non una previsione né una quota costante del rischio. Spiega perché un segnale calcolato alla chiusura dopo lo shock non possa evitare retroattivamente quel primo gap.

Il controllo dei massimi precedenti e il trailing legato alla volatilità sono stati inclusi proprio per esplorare la restituzione dei guadagni. Le regole testate non hanno comunque migliorato il sistema nel suo insieme. Ci sono episodi nei quali l'uscita evita ulteriori perdite e altri in cui vende vicino a un minimo; la selezione di soli esempi riusciti non può decidere quale regola adottare.

Fonti: [forensics OLC109](research/forensics/FORENSICS_REPORT.md) e tabelle sottostanti. Il fondamento generale dell'ipotesi resta condizionale: [Kaminski e Lo, 2014](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee) studiano come il valore degli stop dipenda dalla dinamica dei rendimenti; [Daniel e Moskowitz](https://www.nber.org/papers/w20439) studiano rischi di momentum nei rebound, in strutture soprattutto long/short diverse da questa. Nessuno dei due lavori certifica queste soglie per ETF EUR.

## 8. Incertezza statistica e controlli

I confronti accoppiati usano gli 80 rendimenti mensili, ricampionando blocchi circolari di sei mesi, 10.000 volte, con seed 110. Le stesse date sono usate per candidato e controllo. La statistica è la **differenza media dei log-rendimenti moltiplicata per 12**: non coincide con la differenza tra i CAGR calcolati sui giorni di calendario.

Per il candidato primario contro OLC109, BASE, questa differenza log annualizzata è **−16,51 punti**, con intervallo descrittivo al 95% **[−28,47; −5,15]**. Il risultato sfavorevole non dipende soltanto da un singolo anno nella ricostruzione a blocchi. L'intervallo è condizionato al campione e ai modelli già scelti; non corregge l'esplorazione precedente o i confronti multipli e non rende il periodo fuori campione. Tutti i 13 confronti nidificati nei sei scenari sono conservati, anche quando l'intervallo include zero.

La revisione indipendente verifica **78 conti, 32.533 ordini, 20.810 istruzioni e 183.492 righe di stato**. Sono ricostruiti i segnali, le ammissioni, i posti liberi, le conferme dopo l'acquisto, le maschere di azione e il finanziamento. Le 546 righe annuali includono tutti i 78 risultati del 2024. I cinque scenari del riferimento ereditati da OLC109 sono replicati esattamente.

Le perturbazioni di prezzi, disponibilità e liquidità future lasciano invariati tutti i prefissi controllati: 13 modelli, due convenzioni di esecuzione, tre date, per **78 confronti**. Dieci alterazioni deliberate di target, quantità, date, costi o stato vengono respinte. Questi controlli verificano implementazione e causalità interna sui casi esercitati; non provano qualità prospettica dei segnali.

Per preservare il comportamento numerico degli zeri del conto congelato, l'auditor prima ridimensiona e verifica ogni esecuzione e poi registra le quantità e i controvalori serializzati già verificati. Commissioni e valorizzazioni vengono ricalcolate. Non si presenta il risultato come una seconda catena di virgola mobile completamente disconnessa dal libro: una prima versione aveva lasciato 5,68 × 10⁻¹⁴ unità residue, con effetto sul NAV inferiore a €10⁻¹¹. La convenzione e la diagnosi sono documentate; non è stata cambiata la strategia.

Fonti: [PAIRED_COMPARISONS.csv](analysis/PAIRED_COMPARISONS.csv), [audit indipendente](validation/INDEPENDENT_REVIEW_IT.md), [nota di precisione](validation/AUDITOR_PRECISION_NOTE.md), [COMPLETION_QA.json](validation/COMPLETION_QA.json).

## 9. Limiti materiali dei dati e dell'esecuzione

L'audit delle fonti copre tutti i 78 conti, **235 ISIN effettivamente negoziati**, di cui 81 nuovi rispetto all'insieme OLC109, e 238 storie sottostanti. Non trova esecuzioni su una quotazione o maschera accettata errata, discrepanze fra prezzi accettati e sorgente o discrepanze del turnover. Le quarantene precedenti restano immutate. La massima anzianità del Close usato per un investimento effettivo o una valorizzazione di ripiego è cinque giorni di calendario.

Questo esito non certifica la negoziabilità. **65 ordini su 32.533 hanno controvalore almeno pari all'intero turnover giornaliero riportato sulla sede**: 55 nelle simulazioni all'Open e dieci in quelle al Close. Il massimo è 6,407 volte tale turnover. Nel candidato primario BASE un ordine arriva a 3,300 volte; nel modello giornaliero cinque ordini superano il 100%. Il riferimento BASE non supera il 100%, ma il suo massimo è comunque il 48,64% del turnover di sede. La migliore protezione dinamica BASE arriva al 93,04%.

Il denominatore è volume di tutta la giornata per Close grezzo, non liquidità dell'asta, spread osservato o capacità complessiva di un ETF su tutte le sedi. Il filtro sulla liquidità mediana dei 63 giorni precedenti non garantisce capienza al successivo giorno di vendita. Applicare 15 o 30 bp costanti non prova che quelle quantità fossero eseguibili al prezzo registrato.

Un evento materiale è **LBRA il 26 ottobre 2026**, già esaminato nella validazione V3 ma usato ora da nuovi conti. Il NAV dell'emittente archiviato passa da €30,5324 a €24,8836, pari a −18,5010%, sostenendo la presenza di una forte perdita economica. Il Close della sorgente perde 19,6950%; l'esatto Open di €22,84 e la profondità dell'asta non sono certificati indipendentemente. Il candidato primario conserva **−€1.709,67** di P&L sul titolo quel giorno, circa **−10,06%** del NAV precedente; il modello giornaliero conserva **−€2.049,21**. Il selettore settimanale senza protezione conserva anche il guadagno di €566,41 derivante dall'acquisto all'Open e dal rimbalzo intraday. Non sono state eliminate selettivamente né perdite né vincite.

Restano il survivorship del catalogo corrente, il vintage non certificato degli aggiustamenti e l'uso della disponibilità degli Open originari legata anche al volume positivo dell'intera giornata, non noto all'apertura. L'esecuzione al Close successivo tratta diversamente quest'ultima convenzione, ma non ricostruisce fondi cessati né vintage storici. Le simulazioni frazionarie, il cash a rendimento zero e le imposte escluse completano il perimetro delle ipotesi economiche.

Fonti: [audit fonti/esecuzione](validation/source_execution/AUDIT_NOTES.md), [capienza di tutti i conti](validation/source_execution/ALL_78_PATH_CAPACITY_SUMMARY.csv), [impatto degli eventi](validation/source_execution/MATERIAL_EVENT_ACCOUNT_IMPACT.csv).

## 10. Conclusione di ricerca e materiale conservato

Il salto desiderato richiede che la decisione di ridurre esposizione eviti abbastanza perdite e che l'ingresso successivo recuperi abbastanza rendimento da compensare falsi segnali, gap e costi. In questa iterazione il primo requisito non è soddisfatto dal sistema complessivo. Accelerare il ranking o moltiplicare i rientri non basta; le nuove opportunità hanno alcuni esiti locali interessanti, ma la loro interazione con la protezione produce ancora un conto peggiore.

La domanda utile per una successiva ipotesi è se esista **informazione osservabile prima dell'azione** capace di distinguere una perdita destinata a continuare da una discesa seguita da recupero, e se tale informazione regga a costi ed esecuzione realistici. Un eventuale passo successivo dovrebbe separare il controllo dell'esposizione del portafoglio dal segnale di acquisto e misurare il valore dell'opportunità contro cash e contro alternative comparabili. Queste sono direzioni motivate dai risultati, non modelli già validati. Non vengono aggiunte soglie a posteriori a OLC110.

Il pacchetto conserva **tutti i 78 conti completi**, codice, test, protocollo congelato, rendimenti annuali, confronti, diagnostica degli eventi, audit, figura e questo rapporto. I due pannelli grandi sono identici a quelli OLC109 e sono richiamati tramite hash e procedura di ripristino. Il README del repository descrive il ripristino e i comandi di riproduzione. Nessuna operazione di mercato reale o modifica di automazioni fa parte di questa ricerca.
'''

(ROOT / "RAPPORTO_OLC110_IT.md").write_text(report, encoding="utf-8")
print(f"Wrote RAPPORTO_OLC110_IT.md: {len(report.split())} words; tables generated from frozen evidence.")
