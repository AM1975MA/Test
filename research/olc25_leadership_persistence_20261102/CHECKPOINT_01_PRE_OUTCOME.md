# OLC25 — checkpoint di controlli prima dei risultati economici

2 novembre 2026. Il ranking AUTH produce gli stessi otto conti economici OLC20 nei due mercati, con confronto degli array identico. Le feature causali a 126/252 sedute e PERSIST3 sono state materializzate; 3 test locali passano.

**Correzione verificata senza ispezionare esiti candidati:** nel controllo negativo il rimescolamento avviene esclusivamente tra ETF che in quella data hanno sia percentile finito sia previsione FUSION AUTH finita. Il primo test (intenzionalmente fallito) ha rivelato che mescolare anche ticker con previsione AUTH assente modifica la distribuzione delle feature tra gli ETF effettivamente selezionabili; il cambiamento limita gli indici alla maschera congiunta per conservare il multiset fra candidati validi. Nessun parametro empirico, seed, peso o scenario economico è stato cambiato. Le sei varianti autentiche sono immutate.

Fonte prezzi: EU richiede 'observed' alla data t e a t-126/t-252; USA richiede prezzi preparati finiti/positivi perché la maschera originale non è disponibile. Finestra disponibile dal febbraio 2019: parte dei segnali 2019/2020 non dispone dei lookback, neutro predefinito. Nessun training ETF eseguito.
