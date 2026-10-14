# Audit indipendente del solver LINEAR

Perimetro: sola lettura dei learner, preregistrazioni e test v1/v2; nessun
fit su dati ETF, nessuna lettura del vendor, nessuna modifica ai learner.
Evidenza riproducibile: `python paper_ltr_v2/diagnostics_solver/synthetic_audit.py`.
Risultati: `synthetic_audit.json` (NumPy locale 1.26.4; non equivale al profilo CI).

Per query disgiunte non vuote, q=softmax(label), p=softmax(Xw), la loss è
F(w)=media_q CE(q,p)+.001||w||²/2. Il gradiente implementato è
media_q Xqᵀ(p−q)+.001w. La Hessiana è
media_q Xqᵀ[diag(p)−ppᵀ]Xq+.001I: positiva definita, λmin≥.001.
Quindi esiste un unico minimo e F(w)−F*≤||∇F(w)||₂²/(2·.001).
Il gradiente e il two-loop L-BFGS sono algebricamente corretti. Armijo
controlla diminuzione sufficiente; non impone la condizione di Wolfe.

Differenze finite indipendenti, query di lunghezze 3/7/25: errore massimo
2.2837e−11 sul gradiente lineare, 3.8467e−11 sul gradiente degli score.
Il toy del test esistente converge in 8 iterazioni, residuo 7.64423e−9;
copre una geometria semplice con due colonne identiche e non questo rallentamento.

Riproduzione sintetica seed0: 100 righe, 18 colonne standardizzate, 10 query;
8 colonne quasi duplicate introducono direzioni debolmente curve. Il solver
congelato fallisce a 2000 iterazioni con residuo 1.3162394032933717e−7.
Il risultato è identico al solver originale estratto AST senza strumentazione.
25 coppie accettate, ultima all'iterazione24; 1975 scartate dal gate assoluto
sᵀy>1e−12. Ultimo sᵀy=2.56158e−17, passo Armijo1, nessun passo nullo.
La memoria rimane quindi congelata: l'algoritmo prosegue come discesa con
metrica fissa. Raggio locale di contrazione 0.9995057483, rapporto degli
ultimi residui 0.9994980143. È rallentamento misurabile, non stazionarietà
certificata né prova di errore della loss.

Al terminale sintetico λmin=0.001001734997 e il bound di subottimalità è
5.1056163e−11. Una sola valutazione diagnostica del punto w−H⁻¹g produce
residuo7.53045e−14 e differenza F di −5.07843e−11. Quel punto non è salvato
come modello, non sostituisce l'esito originale e non genera predizioni/CAGR.

Il gate assoluto è una scelta numerica fragile, non un errore di derivazione
né una violazione esplicita della ricetta testuale. Una possibile riparazione
futura è un filtro di curvatura relativo alla scala di s e y con positività
e salvaguardie numeriche; richiederebbe protocollo separato e regressioni
sintetiche. Non è stata implementata né provata qui.

Il fallimento reale riportato (run38565352286/job115872018518, primo2017/r1,
residuo1.1632278976516936e−7) resta FAIL secondo la soglia originale1e−7.
La riproduzione identifica un meccanismo possibile e dimostrato sul sintetico;
attribuirlo a quel fold richiede la sua traccia numerica. Non dimostra alcuna
relazione con stabilità dei leader o rendimento economico.
