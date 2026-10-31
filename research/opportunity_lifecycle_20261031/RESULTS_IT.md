# Opportunita, capitale e permanenza: diagnosi CL01 e prossima specifica

31 ottobre 2026. Nuova diagnosi su USA149/EU165; nessun nuovo modello predittivo, nessuna nuova strategia promossa. La priorita diventa stimare il rendimento residuo e la durata del vantaggio, poi scegliere azioni dal portafoglio realmente detenuto. Non aggiungere un altro veto soltanto per ridurre turnover.

## 1. Gli stessi cambi a tre orizzonti

Ricostruiti quattro conti CL01 (USA/Europa, pesi originali/50-50), poi estratti i ticker realmente detenuti prima del ribilanciamento e quelli acquistati. Non viene usato l'incumbent Top1 Momentum del mese precedente del vecchio studio specialisti. Se due nomi cambiano insieme, l'abbinamento uscita/entrata usa il punteggio contemporaneo, non il rendimento futuro; non e una relazione causale univoca fra ordini.

Per ogni coppia: rendimento del nuovo meno quello del vecchio, con entrambi ipoteticamente mantenuti fino all'orizzonte. Si paga10bp per vendita e10bp per acquisto: valore acquistato=(1-c)/(1+c), vantaggio netto=valore_acquistato*(1+r_nuovo)-(1+r_vecchio). Costi stressati30bp conservati. Questi costi diagnostici sono distinti dalla convenzione del simulatore originale.

Campione identico21/42/63, con tutte le label maturate prima del2025:81coppie EU in51mesi,72coppie USA in56mesi. Medie prima entro mese, poi fra mesi. Unita: punti percentuali sul capitale idealmente trasferito, NON CAGR e NON rendimento annualizzato.

| Orizzonte | EU vantaggio medio | USA vantaggio medio | IC95 EU | IC95 USA |
|---|---:|---:|---|---|
|21sedute|-0,1057pp|+1,6659pp|[-2,1595;+2,3020]|[-0,4499;+4,1212]|
|42sedute|+1,0539pp|+2,8618pp|[-1,2014;+3,5419]|[-0,9694;+6,9657]|
|63sedute|+2,6089pp|+1,9333pp|[-0,0953;+5,3145]|[-1,5225;+5,8412]|

Bootstrap circolare su mesi di calendario, blocchi6mesi,10000estrazioni seed20261031; disponibili anche3mesi. Intervalli esplorativi, non posteriori e non un veto automatico quando comprendono zero. Le distribuzioni non eliminano selezione storica e dipendenze.

In13dei51mesi EU, vantaggio medio non positivo a21diventa positivo a63; sette casi opposti. Negli USA quattro mesi in ciascuna direzione. A livello coppia,18casi EU hanno vantaggio non positivo a21e positivo a63. Tutti18 vengono interrotti prima di63sedute, durata mediana continua21intervalli. NON sono18errori evitabili dimostrati: il reinvestimento successivo puo fare meglio e i controlli rischi cambiano il percorso. Il risultato suggerisce di stimare durata e valore residuo, non di imporre63giorni di possesso.

## 2. Allargare la shortlist non e un miglioramento sufficiente

Unione contemporanea Top5Return, Top5Hybrid, Top5momentum63, Top5momentum252, sul medesimo supporto finito CL01. Circa15-16nomi. Misura: quota dei cinque migliori rendimenti futuri positivi a63sedute inclusi nell'insieme. I vincitori futuri sono solo valutazione, mai input. Tutte le label dell'universo disponibili e mature prima2025:65mesi EU e69USA.

| Insieme | Copertura EU | Copertura USA |
|---|---:|---:|
|Top2 CL01|8,31%|6,96%|
|Unione quattro shortlist|32,31%|32,46%|
|Stessa numerosita dalla graduatoria CL01|34,46%|37,68%|
|Stessa numerosita da volatilita63 alta|39,69%|47,25%|

Due nomi hanno una copertura massima40% di cinque vincitori; la lista ampia puo arrivare100%. Non chiamare il salto Top2->shortlist capacita predittiva. A pari numerosita l'unione non vince a63sedute. La volatilita cattura estremi, ma questa metrica non misura profitto netto o downside: non e una strategia promossa. I rendimenti dei migliori due titoli selezionati dopo entro la shortlist sono soltanto un soffitto diagnostico irrealizzabile.

## 3. Capitale: il primo posto non determina da solo il sovrappeso

Stessa coppia e stessi mesi fra orizzonti, esiti maturi pre2025:65mesi EU,69USA. Peso medio primo ticker65,4%EU e73,9%USA. Originale rispetto50/50 a21sedute: -0,04ppEU, +0,48ppUSA. A63sedute circa+0,02ppEU e+0,01ppUSA. Intervalli ampi. Diagnostica statica senza successivi stop/cambi, non differenziale CAGR. Il50/50 non e dimostrato universalmente ottimale; la relazione fra score, durata e capitale deve essere verificata.

## 4. Proposta: modello del valore residuo e delle azioni

I vecchi esperimenti avevano gia provato HOLD/SWITCH, regressioni del differenziale21/42/63, probabilita, quantili, shortlist e persistenza. Il nuovo passo non puo essere un cambio di nome. La differenza da verificare e:

- Prevedere separatamente rendimento0-21, rendimento incrementale21-42 e42-63, non comprimerli subito in una media. Input sempre alla data decisionale; ogni testa usa solo label mature al proprio cutoff. Nessun esito futuro del primo segmento come feature per prevedere quello successivo. Il target breve non perde le osservazioni recenti per aspettare inutilmente63sedute.
- Valutare le azioni dal portafoglio effettivo: HOLD, incremento, riduzione, sostituzione parziale/completa, cash. Mantenere gli incumbent fra i candidati anche quando non sono piu Top2. Stato include capitale, esposizioni, rischio, eta posizione/segnale e previsioni residue.
- Confrontare DeltaU(a)=E[log(W_netto_futuro_a)-log(W_netto_futuro_HOLD)|informazioni]. Costi inclusi una volta nei due patrimoni, rischio/concentrazione come vincoli espliciti. Definire prima orizzonte e funzione; non scegliere il migliore risultato futuro fra21/42/63come target di finta abilita.
- Provare dosi parziali di trasferimento predefinite, non una concentrazione automatica da score. Non vendere un vincitore soltanto perche e gia salito o ha perso un posto in graduatoria; non tenere un perdente solo per recuperare il prezzo di carico. Si confrontano valore residuo, alternativa e costo del cambio.

Il modello di azione descritto NON e stato implementato o addestrato in questo lotto e non ha un rendimento attribuibile. La teoria di Gârleanu/Pedersen sulla persistenza dei segnali, costi e aggiustamento parziale e un riferimento metodologico, non una validazione ETF: https://www.nber.org/papers/w15205.

## 5. Verifica incrementale richiesta

Prima il profilo dell'opportunita e la sua utilita rispetto a ranking/momentum/alta volatilita; poi permanenza a capitale controllato e incumbent reali; infine dimensionamento e sostituzione parziale a segnale invariato. Ogni passo e combinazione deve essere verificato su entrambi gli universi. Il confronto include buffer, durate fisse con tutte le fasi e politiche originali. Misurare beneficio netto, grandi movimenti catturati, perdite dei falsi segnali, cambi utili evitati, opportunita perse, rischio e costi. Il CAGR e il risultato finale, non l'unico criterio per il singolo layer.

Non basta negoziare meno. Non bastano probabilita medie calibrate senza discriminazione. Non imporre p<.05oP>95%come automatismo. Se non emerge informazione sul rendimento residuo, un allocatore piu complesso non puo crearla: occorre una nuova ipotesi informativa sulle esposizioni/leadership, non altri veti ottimizzati.

## 6. Verifica e limiti

4riferimenti ricostruiti;156metriche confrontate con lo scorecard precedente, errore massimo1,9429e-16; identita NAV/PnL verificata. Non si dichiara confronto byte-per-byte con tutte1440vecchie curve.8test nuovi e10ereditati superati.27.191righe di date forecast/source controllate; segnale prima dell'ingresso. I fit originari non sono riaddestrati ne ri-auditati integralmente.

534righe opportunita,534dimensionamento,356eventi (due sistemi peso),2658controfattuali (ripetuti perorizzonte/costo/peso).443sostituzioni distinte verificate sui ledger,2586righe statiche con esito osservato; errore aritmetico costi<2,1e-16. Questi non sono campioni indipendenti. L'ultima riga piatta della NAV e esclusa da nuovi ingressi; prezzi mancanti non sono riempiti nelle label.

Tutto e storico gia esplorato. Restano limiti di survivorship,total-return,corporate actions,negoziabilita e stesso-Open legacy. I controfattuali statici non includono futuri switch/stop e non si concatenano in CAGR. L'inclusione dello zero non esclude la pista, ma non prova il beneficio. Nessuna modifica alla produzione.

Repo: protocollo,sorgenti,test,sintesi. Pacchetto offline: rapporto esteso,tutte le tabelle,4curve/ledger,log e manifest. Input grandi richiedono i tre archivi autenticati gia consegnati; non si dichiara upload di quei file suGitHub.