# PAPER_LTR_V1 — fattibilità offline ListNet

Protocollo fissato prima dei nuovi risultati. Unico candidato: **LISTNET_DECILE_64**.
Repository autorizzato: AM1975MA/Test. Nessun cambiamento o adozione in produzione;
nessun backtest di portafoglio in questa fase. Un fallimento respinge questa
ricetta e non l'intera famiglia ListNet. Original149 è evidenza di sviluppo già
consultata; le tre acquisizioni non sono mercati indipendenti.

## Fonte primaria e distanza dalla replica

Poh, Lim, Zohren e Roberts, *Building Cross-Sectional Systematic Strategies By
Learning to Rank*, https://arxiv.org/html/2012.07149, §§IV-C–D, V-B e VII-A–B.
La fonte documenta due strati nascosti, decili ordinati, loss ListNet fra due
softmax, Adam, split 90/10, massimo 100 epoche, patience 25 e la griglia di
iperparametri. Non documenta configurazione vincente, attivazione,
inizializzazione, parametri Adam secondari, purge né split temporale preciso.
Non verifica revisioni Yahoo o stabilità dei rifit. Il suo studio azionario e i
blocchi quinquennali non costituiscono evidenza diretta sugli ETF V2.

La presente ricetta sceglie una sola configurazione, senza HyperOpt né grid.
ReLU, preprocessing, semi, inizializzazione, split purgato e calendario annuale
sono adattamenti dichiarati. Le date native Original149 costituiscono query
complete; non si presume che siano identiche alle query del paper.

## Ricetta congelata

- Tutti i 125 attributi canonici, non quantizzati; eleggibilità originaria con
  almeno 30 attributi validi. Ogni acquisizione conserva la propria coorte.
- Rete condivisa per asset: 125 → Dense64/ReLU → Dropout0.2 → Dense64/ReLU →
  Dropout0.2 → Dense1 lineare; 12.289 parametri. Inizializzazione He normale
  negli strati nascosti e normale con deviazione standard sqrt(1/64) nello
  strato finale; bias zero. CPU, float64 e un solo thread numerico.
- Etichette `clip(ceil(10 * target_rank_21),1,10)`, interi 1–10, senza ricalcolo del
  percentile dopo il filtro e senza ordinamento dei pareggi mediante ticker.
  Softmax delle etichette a temperatura uno. Per data: `q=softmax(decile)`,
  `p=softmax(score)`, `loss=-sum(q*log(p))`; media delle loss per query.
- Mediane e standardizzazione apprese sul solo training interno dopo il purge;
  valori non finiti trattati come mancanti. Colonne interamente mancanti
  imputate a zero, mantenendo i 125 attributi. Validazione e inferenza usano
  queste stesse trasformazioni senza rifit.
- Adam: learning rate 1e-4, beta (0.9,0.999), epsilon 1e-8, weight decay zero;
  clipping della norma globale a 1; batch di 16 date complete; massimo 100
  epoche; patience 25. Loss di validazione media per data, senza dropout;
  miglioramento strettamente positivo. Conservare e ripristinare separatamente
  il primo checkpoint migliore di ciascun seme, includendo il modello iniziale
  come epoca zero se nessuna epoca migliora la loss, senza addestrare nuovamente
  sulla coorte completa. Semi 101/202/303; shuffle delle date deterministico.
- Inferenza senza dropout; media aritmetica degli score dei tre semi. Nessuna
  trasformazione percentile prima della loss o dell'aggregazione degli score.
  Eventuali normalizzazioni downstream restano canoniche, ma nessun replay
  downstream è eseguito in questa fase.

## Input, maturazione e split

Tre `TI_COMPACT.parquet` congelati dal run 37150436612. Confronto soltanto con
BASE predictive V2 conservato dal run 37229180477: `RESULT.json`,
`NATIVE_PREDICTIONS.parquet`, `COMMON_PREDICTIONS.parquet`. Il workflow documenta
l'origine del download; il runner verifica hash dei dati, hash dei due parquet,
stato/variante/anni del BASE, determinismo/parità già dichiarati, chiavi e
target nativi esatti, nonché `evaluation_coverage` per tutti i dieci anni
prima di qualsiasi fit. Non si esegue alcun fit BASE. Il solo nome della
directory non prova l'origine dell'artefatto.

Fit annuali 2017–2026. `signal_date` ed `exit_date_21` strettamente precedenti
il primo gennaio; target presente e stessa eleggibilità canonica. Nessuna
intersezione delle coorti di training. Ordinamento per signal_date,ticker.
Validazione: ultimo 10% delle date mature, arrotondato per eccesso; nessuna
query divisa. Dal training interno eliminare integralmente ogni data che
contenga un esito con exit_date_21 uguale o successiva alla prima data di
validazione. Se lo split è vuoto o non valido, il fit fallisce senza fallback.

Segnali di inferenza fino al 2026-06-30, indipendenti dalla disponibilità del
target futuro. Qualità solo su query completamente mature entro il 2026-07-01.
Le righe comuni sono l'intersezione diagnostica delle chiavi delle tre
inferenze; i loro attributi e target provengono da Repeat2. Inferenza nativa
anche su ciascuna coorte originaria, con copertura esplicita.

Gate numerico identico a predictive V2: versioni Python3.13, NumPy2.3.5,
pandas2.2.3, sklearn1.8.0, XGBoost3.1.3, LightGBM4.6.0, SciPy1.17.0,
PyArrow23.0.1, Numba0.65.1; PYTHONHASHSEED=0, profilo Haswell/AVX2 e thread
numerici uno. Implementazione della rete offline NumPy, senza nuove dipendenze
neurali. Un solo rifit candidato indipendente: Repeat2 del 2017, tutti e tre
i semi, confronto byte esatto delle predizioni comuni e native. Il risultato
non certifica il determinismo degli altri anni; non si modifica la ricetta
per correggere differenze empiriche dopo l'accesso agli esiti.

## Endpoint e criteri di fattibilità

Confronto candidato–BASE sulle stesse date e ticker; tre coppie 1–2,1–3,2–3.
Media delle date con uguale peso, quindi media delle tre coppie. Rank MAD:
media per data delle differenze assolute dei ranghi percentili sullo stesso
input Repeat2 comune; inferenza nativa: disaccordo Top1 e coppia ordinata
Top1/Top2 sulle chiavi diagnostiche comuni. Score decrescenti, ticker crescenti
per i pareggi, senza usare esiti futuri per la selezione.

La ricetta supera lo schermo solo se TUTTI i criteri seguenti passano:

1. Integrità di input/BASE/copertura, maturazione, valori finiti, checkpoint
   conservati e rifit Repeat2 2017 byte esatto.
2. Rank MAD comune almeno 25% inferiore a BASE.
3. Disaccordo Top1 nativo almeno 25% inferiore a BASE.
4. Disaccordo della coppia ordinata Top1/Top2 nativa non superiore a BASE.
5. Qualità Top1 (percentile realizzato), NDCG@5 con gain lineare canonico e
   Precision@5 ciascuna almeno 95% di BASE, sul medesimo supporto comune con
   i medesimi target Repeat2; uguale peso a ciascuna data, poi ai tre modelli
   di acquisizione. Le predizioni primarie sono native, gli esiti sono comuni
   Repeat2; la qualità sulle feature comuni Repeat2 è un diagnostico aggiuntivo.
   NDCG non equivale ad accuratezza del vincitore.

Se il denominatore di una riduzione è zero, il candidato deve essere zero.
Metriche indisponibili non sono pass. Gli esiti maturi parziali per query
falliscono la validazione. Qualità nativa per acquisizione, dettaglio annuale,
ogni coppia, conteggi e copertura rimangono diagnostici dichiarati: nessun
salvataggio del candidato attraverso CAGR o altre metriche favorevoli.
La soglia del 95% è uno schermo descrittivo di fattibilità, non prova
statistica di non inferiorità. Nessuna pretesa di holdout intatto o significatività
dopo le ricerche precedenti.

Incertezza descrittiva: confronto appaiato delle qualità per data con 20.000
campioni bootstrap, seed 20261012, blocchi temporali di 3 mesi, sensibilità a
1 e 6 mesi. Le tre acquisizioni restano unite nella stessa data. I limiti
non correggono la storia dei test e non diventano criteri ulteriori di scelta.

## Evidenza conservata e arresto

Output: RESULT.json incrementale e finale, INPUT_CONTRACT.json, due parquet
con predizioni comuni/native, checkpoint persistenti in `out/models`, log e
audit di split/preprocessing/semi/epoche. Hash di fonti, preregistrazione,
input, predizioni e checkpoint. Ogni interruzione successiva all'inizializzazione
scrive lo stato FAILED e conserva l'evidenza; nessuna eliminazione temporanea
dei modelli. Il controllo di determinismo conserva anche i checkpoint ripetuti.

Il mancato superamento respinge questa singola ricetta. Vietati ricerca
outcome-driven, modifica della rete/label/split/soglie a risultati visibili,
replay completo automatico e promozione in produzione. Un eventuale seguito
richiede un protocollo separato; nessun esito di questo test dimostra la
robustezza dell'intera famiglia ListNet.
