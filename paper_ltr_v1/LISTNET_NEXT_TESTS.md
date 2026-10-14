# ListNet: diagnosi e prossimo percorso di ricerca

Data: 12 ottobre 2026. Repository autorizzato: AM1975MA/Test. Nessuna modifica
al produttivo. Questa è una proposta dopo il primo esperimento, non una nuova
preregistrazione già eseguita né una dichiarazione di performance futura.

## Evidenza che orienta la decisione

Il replay completo dei tre download congelati ha CAGR ListNet
22,8594 / 22,1741 / 21,3070%, contro BASE 29,7534 / 30,8437 / 34,6771%.
Il CAGR medio passa da31,7581 a22,1135%; lo span da4,9236 a1,5524pp.
Il MaxDD migliora su r1/r3 e peggiora su r2. Sharpe inferiore in tutti i repeat.
Non è una soluzione accettabile al problema attuale.

Il percentile realizzato medio Top1 è0,503118 contro BASE0,583437; RankIC
0,000481 contro0,064614. Tuttavia exact-hit Top1 è6,19% contro0,67% casuale,
e hit nei migliori cinque18,58% contro3,36%. Quindi IC quasi zero non dimostra
assenza di ogni informazione: bisogna misurare anche le code delle perdite.
Il controllo casuale riguarda ranking, non è un portafoglio casuale simulato.

Audit riproducibile su90 reti, senza fit:63 si fermano al limite100 epoche,
27 per patience; nessuna usa il checkpoint iniziale. Migliore epoca mediana96.
Fra le63 al limite, nelle ultime10 epoche train loss migliora in63 e validation
loss in52. Miglioramento relativo mediano tardivo:0,11057% training e0,01536%
validation. Questo giustifica una prova del limite di epoche, non prova underfit,
convergenza né un aumento futuro del CAGR.

Riferimenti verificati:
- Fit: https://github.com/AM1975MA/Test/actions/runs/38179662587
- Replay e confronto: https://github.com/AM1975MA/Test/actions/runs/38180179897
- Artefatto fit11717520887: ZIP SHA256
  5a3bcc9a13017e5c887e4c98fe6f9eed2abc71dbb355d2b0946a8272b79825f6.
- Diagnostica locale: results/TRAINING_DIAGNOSTIC.json, riproducibile con
  diagnose_training.py sul RESULT dell'artefatto conservato.

## Discussione fra i revisori, in italiano

Agente ML /root/review_history_gate: il limite100 merita un test isolato;
le verifiche di gradienti, invarianza a shift degli score, permutazione delle
query e purge non mostrano un bug evidente. Non equiparare una loss più bassa
a migliore selezione economica. Proposta di controllo lineare della stessa loss.

Agente finanziario /root/stability_evidence: contesta l'interpretazione
«assenza di segnale», perché gli hit nelle code superano il caso. Su113 mesi
maturi Repeat2 rileva UNG primo38 volte e22 ticker distinti. Questa concentrazione
è un sospetto da verificare con volatilità ex ante e distribuzione dei rendimenti,
non una causa provata; nessuna rimozione ex post di UNG.

Agente statistico /root/scientific_statistics: accetta la prova300 soltanto
come falsificazione del troncamento; il guadagno tardivo validation è piccolo.
Contesta ricerca dal CAGR outer già osservato e tre download come repliche
indipendenti. Convergenza condivisa: audit prima, due nuove ricette al massimo
nella prima fase; target, temperatura e preprocessing rinviati alla diagnosi.
I ruoli sono agenti AI, non consulenze o approvazioni degli autori del paper.

## Fase0: spiegare il fallimento senza addestrare

1. Chiudere i controlli ancora aperti su linkage input fit/cache e date leader/NPZ.
2. Misurare CE meno entropia del target, cioè KL(q||p), e confronto uniforme log(n).
   Il confronto fra loss con target differenti richiede KL/qualità, non CE grezza.
3. Distribuzione dei rendimenti Top1/Top2: media, mediana, code, frequenza dei
   migliori e peggiori decili; concentrazione ETF e relazione con rischio ex ante.
4. Per seed: dispersione score entro query, accordo dei leader, scale dei logit.
   La media di score può attribuire più peso a reti con scala maggiore.
5. Decomporre differenza economica per mese: selezione, esposizione, costi.
   Decomposizione contabile non equivale a identificare una causa.

## Prima fase: due prove distinte, non una griglia

**A — Budget300.** MLP64x64, target a decili,125 feature, dropout0,2,
Adam1e-4, batch16 query, clipping1, tre seed e patience25 invariati.
Cambia soltanto il massimo100→300 epoche. Mantenere split e maturazione,
salvare curve e migliori checkpoint. Non forzare il modello a usare epoca300.
Le reti che già si fermano per patience non richiedono duplicazione del fit
quando la parità della procedura è certificata. Non si possono riprendere
esattamente le altre dal solo checkpoint migliore: manca lo stato finale Adam.
Se la qualità Top1/Top2 non migliora nelle validazioni, aumentare ulteriormente
le epoche non è una risposta supportata. Se il limite è ancora attivo a300,
registrarlo come limite, senza estendere il budget guardando il CAGR.
Gate diagnostico proposto dal revisore statistico, da congelare prima dei fit:
riduzione mediana KL validation almeno1% nei63 modelli prima limitati,
miglioramento in almeno42/63, qualità Top1 e NDCG5 validation almeno95% del
controllo100. Queste sono soglie progettuali proposte, non esiti già misurati.
Verificare identità del prefisso100 epoche e dei modelli già fermati per patience.

**B — Controllo ListNet lineare.** Score x·w, stessa loss/query/target,
preprocessing e split. Definire prima solver, eventuale regolarizzazione e
tolleranza; problema convesso in w, ma senza garanzia di ottimo unico o buon
CAGR. Serve a distinguere capacità/nonconvessità della MLP da informazione
disponibile e obiettivo a decili. Non è la ripetizione del vecchio Ridge:
Ridge cambia loss e supervisione, qui si conserva la loss ListNet.

Eseguire queste prove in sequenza, senza cambiare portafoglio, costi o V6.
BASE e primo ListNet restano controlli già conservati. Ogni nuova ricetta deve
superare il controllo di non duplicazione nei registri prima del dispatch.

## Seconda fase solo se gli audit ne dimostrano la necessità

- Percentile continuo con scala fissata confrontabile ai decili: elimina il
  pareggio della supervisione dentro il decile, non necessariamente il rumore.
- Target di utilità a21 sedute e rischio stimato causalmente: solo se la
  preferenza per code/volatilità è verificata; è una nuova domanda economica.
- Preprocessing robusto appreso dal solo training: solo se outlier/scale dominano.
- Media dei percentile-rank dei seed: solo se differenze di scala dominano
  l'ensemble; non cambiare contemporaneamente target o architettura.

Alzare la temperatura non distingue ETF nello stesso decile. Con decili
equipopolati softmax(1..10) assegna63,21% della massa al decile alto e86,47%
ai due più alti; la temperatura cambia il focus delle code, non risolve da sola
l'identificazione del singolo vincitore. Nessun braccio automatico temperatura.

## Come scegliere e interpretare il risultato

La selezione annuale di ricetta/checkpoint deve usare solo finestre interne
temporali prima del cutoff, query complete e purge degli exit futuri.
Valutare qualità Top1/Top2, regret e stabilità sugli stessi supporti; se serve
scegliere A/B, preregistrare prima criterio e tie-break a minore complessità.
Non scegliere la ricetta mediante CAGR medio2017–2026 o il download migliore.
Possibile politica nested proposta: anni outer2020–2026; per l'annoY usare
soltanto risultati delle tre annualità precedenti, con etichette interamente
mature prima di gennaioY. Ogni fit di quelle annualità ha la propria validation
anteriore e purgata. I risultati annuali conservati possono essere riutilizzati
senza rifit per ciascuna combinazione. Questa politica copre2020–2026: non
confonderla con il confronto delle ricette fisse2017–2026. Il fit lineare non
ha semi se solver e input sono deterministici:30 fit contro al massimo90 MLP.
Nessuna combinazione aggiuntiva e limite di calcolo dichiarato nel futuro
protocollo. Nessun esperimento di questa proposta è stato avviato oggi.

Rapporto finale: tre CAGR/MaxDD/Sharpe, range e deviazione standard dei CAGR,
disaccordo Top1/Top2 su feature comuni, native e dopo il portafoglio.
Presentare frontiera Pareto rendimento/rischio/stabilità, con ogni peggioramento
per repeat esplicito. Uno schermo con tolleranze95% o2pp, se scelto in un futuro
protocollo, è una convenzione di ricerca e non prova statistica di noninferiorità
né successo dell'obiettivo «più CAGR e migliore DD».

Per rivendicare quel successo empirico richiedere miglioramento effettivo del
rendimento e del rischio, accompagnato da maggiore stabilità, senza compensare
silenziosamente una perdita con una somma ponderata. Le tre acquisizioni sono
revisioni correlate del medesimo mercato. L'intero2017–2026 è già stato osservato:
split nested rende causalmente corretta una procedura retrospettiva, ma non crea
un holdout vergine. Con i tre input congelati possiamo scegliere una direzione
di ricerca; non certificare un massimo CAGR futuro né promuovere in produzione.

Fonte primaria e differenze: https://arxiv.org/html/2012.07149 , sezioni IV-D e
VII-B. Il paper usa50 ricerche di iperparametri e un portafoglio long/short ampio;
il primo esperimento qui era una sola ricetta di trasferimento a Top1/Top2 V2.
Non basta a scartare l'intera famiglia ListNet, né giustifica50 tentativi sul
nostro backtest già visto.
