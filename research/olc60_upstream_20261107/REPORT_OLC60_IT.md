# OLC60 — Opportunità e persistenza: primo esperimento davvero a monte
**7 novembre 2026 · ricerca esplorativa · nessuna modifica a OLC19, main o produzione**

## Decisione

L'ipotesi **«basta riaddestrare un classificatore lineare sulle 42 feature native per scegliere ETF che persistono tra i leader per 21 e 42 sedute»** non supera il gate: il miglioramento modesto europeo non è replicato negli USA, dove sia la precisione Top2 sia il payoff futuro diminuiscono sensibilmente. Questo *non* falsifica la prospettiva di intervenire a monte: identifica la necessità di ottimizzare la **coda Top2 con utilità economica coerente con l'orizzonte del possesso**, invece di aggiungere un bonus sul ranking già formato.

## Precedenti determinanti

- **OLC11:** classificatore di top quintile su Y di rango composito batte il regressore nativo *nel layer isolato*, ma i benefici non sopravvivono uniformemente alla composizione; NDCG EU XGB 0,4730→0,5235, USA 0,4562→0,4929 sul main, senza validazione economica nuova.
- **OLC25:** bonus diretti di momentum 126/252 e persistenza3 peggiorano il CAGR dei due mercati nel main rispetto a OLC19.
- **OLC26/27:** IC di momentum e previsione leadership 126d può crescere a livello cross-sectional ma non produce nuove coppie Top2 redditizie nell'holding mensile.
- **OLC31/32:** calibrazione lineare dei raw score e previsione diretta 21 sedute con feature aggiunte peggiorano RMSE e top5 economic edge. Non giustificano re-ranking finale.

## Protocollo OLC60 effettivamente eseguito

Input originali verificati con SHA256: `OLC14_Heads_Checkpoint_20261101.zip` (`a8f2c177...e458`) e `OLC14_Fitting_Risultati_20261101.zip` (`4259b9e...e1`). 42 feature native **X/XP prima del ranking/fusione**, chiavi ed etichette datate dai checkpoint OLC11/14. Non si addestrano meta-correzioni dello score finale.

Venti modelli totali: EU/USA × 2021–2025 × due etichette. Ogni fit annuale usa esclusivamente esempi con `exit_date_63` **anteriore** al primo gennaio del relativo anno; imputazione e standardizzazione *train only*; `LogisticRegression` L2, `C=0,1`, nessun retuning. Due target:

- `NEAR42X`: appartenenza al miglior 20% dei rendimenti relativi **futuri** a 21 sedute;
- `PERSIST42X`: appartenenza al miglior 20% dei rendimenti relativi **sia a 21 sia a 42** sedute.

Si scelgono due posizioni direttamente dalle previsioni del modello *a monte*. Confronti `B0_NATIVE = ORIGINAL_CURRENT` e, **solo come riferimento**, `B0_FUSION_CONTEXT = ORIGINAL_FUSION`. I pareggi nel Top2 seguono esattamente i pesi frazionari del codice originario OLC14, senza scegliere arbitrariamente il ticker alfabeticamente primo. Rendimento: media degli `fwd_ret_21` o `fwd_ret_42` degli ETF scelti. Sono **rendimenti statici di singolo orizzonte senza costi, stop, rischio o rebalancing**, *non CAGR, né simulazione OLC19*.

## Risultati principali, 48 mesi 2021–2024 per mercato

Le percentuali `hit` sono quote ponderate delle due posizioni Top2 che risulteranno nel miglior quintile a 21/42; un 20% di `persist` equivale a 0,4 delle due posizioni in media per mese.

| Mercato | Modello | Top2 leader 21d | Top2 leader persistenti 21d+42d | Media r21 (21 sedute) | Media r42 (42 sedute) |
|---|---|---:|---:|---:|---:|
| EU | Originale CURRENT | 38,02% | 20,31% | +1,14% | +2,57% |
| EU | Nuovo NEAR42X | 34,38% | 13,54% | +0,82% | +1,26% |
| EU | Nuovo PERSIST42X | 40,63% | **21,88%** | +1,71% | +2,59% |
| EU | Originale FUSION (riferimento) | 42,71% | **33,33%** | +2,13% | +3,75% |
| USA | Originale CURRENT | 32,29% | **21,88%** | +2,44% | +2,91% |
| USA | Nuovo NEAR42X | 23,96% | 13,54% | −0,41% | −1,06% |
| USA | Nuovo PERSIST42X | 26,04% | 12,50% | +0,03% | −1,05% |
| USA | Originale FUSION (riferimento) | **40,63%** | 23,96% | +3,50% | +3,90% |

`PERSIST42X` contro CURRENT: EU +1,56 punti percentuali di persistenza, +0,57 pp di r21 e +0,02 pp di r42; USA **−9,38 pp** persistenza, **−2,42 pp** r21, **−3,96 pp** r42. Bootstrap circolare blocchi 6 mesi sulle 48 osservazioni mensili appaiate, IC95% *descrittivi* sul delta di `r42`: EU **[−1,18;+1,28] pp**, USA **[−5,75;−2,10] pp**. Il 2025 (già esplorato, **non** un holdout vergine) dà risultati misti: in EU la persistenza Top2 passa da 29,17% del CURRENT a 16,67% del PERSIST42X, mentre in USA passa da 29,17% a 33,33%. I rendimenti futuri r21/r42 dei nuovi Top2 restano tuttavia inferiori al CURRENT in USA. Queste osservazioni retrospettive non ribaltano il rifiuto del candidato nel periodo MAIN.

Le ROC AUC di `PERSIST42X` nella cross-section 2024 sono EU ~0,640 e USA ~0,655, migliori del caso ma non sufficienti a rendere la prima coppia economicamente migliore. La classifica globale **non equivale alla precisione della coda**.

## Audit forense aggiuntivo: il retrieval Top10 ha spazio di miglioramento?

Una diagnostica **ex post con informazione futura** quantifica la quota di gap fra coppia realmente selezionata dalla FUSION e coppia economicamente migliore nell'intero universo, che sarebbe recuperabile scegliendo *con conoscenza perfetta del futuro* soltanto all'interno del Top10 esistente.

| Finestra 2021–2024 | EU 21d | EU 42d | USA 21d | USA 42d |
|---|---:|---:|---:|---:|
| Gap teorico recuperabile dall'ottimo del Top10 FUSION | 60,53% | 55,86% | 56,69% | 57,75% |

Questo **non è un alpha, un forecast o un nuovo portafoglio**: usa il futuro ed è un upper bound descrittivo. Mostra soltanto che gran parte del *potenziale teorico* esiste già dentro una shortlist ragionevole, quindi sono importanti sia **candidate retrieval** sia **discriminazione economica finale all'interno dei leader**. La parte rimanente del gap fuori Top10 segnala anche opportunità non recuperate dal ranking iniziale. Il Top10 è diagnostico: la produzione continua a selezionare Top2 originali senza nuove soglie.

## Qualità e limitazioni

- **20 fit**; `18.099` righe di previsioni out-of-annual-sample negli anni 2021–2025; nessun modello non convergente.
- Baseline OLC14: **196/196** righe `CURRENT` e **192/192** righe `FUSION` nel MAIN identiche per ticker, score e peso (massima differenza **zero**). Tutti i 480 record mensili (2 mercati × 5 anni × 12 mesi × 4 strategie) e i pesi riconciliati; nessun doppione.
- Il pareggio nativo Top2 ha richiesto una **correzione di sola metodologia dopo la prima esecuzione**, applicata uniformemente a tutti i metodi. Il log e la correzione sono mantenuti nel protocollo; parametri, feature e etichette invariati.
- Includiamo i punteggi del modello originale per confronto, non rivendichiamo riproduzione del motore OLC19 (risk, V6, fee e stop **non rieseguiti**).
- La storia 2021–2025 è stata ripetutamente selezionata nei lotti precedenti; validazione causale entro anno non equivale a OOS mai esplorato. I rendimenti e il Top10 ex post dipendono da quotazioni non tutte certificate PIT, survivorship, possibili correzioni multi-borsa, dividendi/FX e assenza di broker fills. Un bootstrap su periodi riutilizzati non rimuove questi problemi.

## Direzione successiva: intervento **nativo** su target e rappresentazione, non sul post-ranking

La prossima ipotesi va posta **prima dell'addestramento dei learner**: trasformare l'obiettivo da «quale percentile futuro?» a «quale ETF ha un vantaggio economico significativo sul prossimo periodo *e* una leadership che probabilmente sopravvive?». Costruire un target a due componenti sulla stessa **unità mercato/mese**, calcolando utilità con rendimenti futuri a 21/42 sedute; usare un loss o campionamento *train-only* che presti particolare attenzione a errori di selezione nei primissimi posti, evitando un nuovo gate sui due ticker già scelti. I nuovi predittori, anch'essi **as-of**, dovrebbero modellare velocità, accelerazione, stabilità **del rango relativo** e breadth dei temi, non sommare ingenuamente momentum al FUSION (OLC25 già negativo).

Proposta di sequenza pre-registrata per il successivo lotto OLC61: (1) disegno del target economico-persistente con maturità di gruppo; (2) stessa base 42 feature e un piccolo blocco addizionale di dinamica dei ranghi costruibile dai dati originali; (3) fitting annuale con un criterio che remuneri la coda Top2; (4) confronto **prima** di fusione/rischio su stessi ticker/date, yield r21, r42, hit di persistenza e rimpianto economico; (5) solo se il gate riesce in entrambi i mercati, replay integrale OLC19 nativo e verifica dei dati indipendenti. Niente griglia di pesi giornalieri o ulteriori layer finali. I dettagli di implementazione vanno congelati prima di visionare un nuovo risultato.

**Verdetto finale:** scartare il semplice classifier PERSIST42X, ma mantenere prioritaria la ricerca sul **target economico-persistente e sulla precisione di coda del learner nativo**. La sola riduzione dei costi/ritardo di esecuzione non corregge questa debolezza strutturale.