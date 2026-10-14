# LINEAR_NUMERICAL_REPAIR — protocollo separato

Protocollo scritto il 14 ottobre 2026 prima dell'implementazione della
riparazione e della sua esecuzione reale. Questa è una nuova esecuzione
successiva al FAILED originale, non una continuazione né una sostituzione
retroattiva dell'esito LINEAR preregistrato.

Origine: run38565352286/job115872018518, primo fold2017/r1,
residuo1.1632278976516936e−7 >1e−7. Diagnostica indipendente
run38578561014/job115902048005: stessi fingerprint input PASS,
15059×125,136 query, identico residuo; ultima coppia accettata370,
1629 coppie scartate; contrazione locale .99995149486.

Unica modifica ammessa: sostituire il filtro assoluto sᵀy>1e−12 con
`isfinite(sy) and isfinite(||s||₂) and isfinite(||y||₂) and sy>0 and
sy>eps_float64*||s||₂*||y||₂`, eps_float64=2.220446049250313e−16.
La verifica deve essere applicata in un unico sito del solver originale
estratto AST; fallire se il sito non è esattamente uno. Il learner originale
resta invariato; registrare hash sorgente originale, hash modulo riparazione,
formula e identità della nuova ricetta.

Restano invariati: zero iniziale, float64, L2 .001, L-BFGS memoria10,
Armijo1e−4/max50, massimo2000 iterazioni, gradinf≤1e−7, feature, target,
split purgato, preprocessing e stessi30 fold anno/acquisizione2017–2026.
Usare gli stessi input frozen e fingerprint certificati, controlli originali
conservati e pipeline completa già fissata per qualità, stabilità e replay
economico. Nessuna variazione di famiglie, selezione di configurazioni,
soglie, budget o tuning guidato da CAGR. Tutti gli esiti già esposti restano
evidenza esplorativa; questa riparazione non crea un holdout vergine.

Prima di esecuzioni reali: test sintetico che fallisce con l'originale e
passa con la riparazione, toy esistente, inizializzazione zero, controllo
che gradtol e maxiter restino identici e che i sorgenti originali non mutino.
Al mancato residuo chiudere FAIL, conservando parziali e dettagli senza
allargare soglie o budget. Non lanciare ulteriori configurazioni in risposta
agli esiti. La diagnostica locale esegue soltanto dati sintetici.

Un eventuale completamento va riportato come LINEAR_NUMERICAL_REPAIR,
accanto al FAILED originale. Confronti e gate economici restano quelli
fissati nel protocollo v2; il CAGR non può sanare un fallimento numerico.
