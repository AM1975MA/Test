# L2-M — correzione numerica del rango (audit prima delle metriche)

Nel primo run, l'obbligo del protocollo di avere rango pieno ha interrotto il calcolo **prima della produzione delle metriche**, perché in una categoria tutti gli ETF potevano avere momentum dello stesso segno: in tale caso `|M|` = `M` oppure `−M`, quindi le sei variabili non sono linearmente indipendenti. Il problema è **matematico**, non un esito economico.

**Correzione applicata senza modificare date, target o parametri sulla base di IC/CAGR:** `np.linalg.lstsq(X,y,rcond=1e-12)` realizza la proiezione su `col(X)` anche con matrice non a rango pieno tramite SVD, usando la soluzione a norma minima. Non ha senso richiedere sei coefficienti distinti quando i regressori non sono identificabili. Prescritto: `rank(X)>=3`, almeno 10 ETF validi per categoria/data, verificare a posteriori indipendentemente che `max_j |corr(resid,X_j)|<1e-10`; altrimenti fallire senza etichetta.

Il controllo sui dati finiti in seguito ha registrato **274 su 678** coppie mese/categoria del periodo di valutazione con rango <7; ranghi osservati `{4:34,5:93,6:147,7:404}`. Il difetto era strutturale e la correzione ne evita la perdita arbitraria di gruppi interi. I test dell'audit indipendente riproducono 31 proiezioni con SVD indipendente e verificano il valore dei residui entro `2.4e-13`. L'etichetta **post-amendment numerical fix** accompagna i risultati; la modifica non è una diversa ipotesi finanziaria o selezione post hoc.

Altre correzioni solo software: disambiguazione del suffisso colonna `log_vol63_catrank` duplicato dal merge in Pandas, senza alcun cambiamento a feature, labels o coorte.
